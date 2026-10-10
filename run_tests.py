#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pkgtrans 自测：用本地 mock API 覆盖成功/失败/缓存/熔断/透传等路径。

不需要真实 API 密钥，也不会联网。用法:

    python3 ~/.local/share/pkgtrans/run_tests.py
"""

import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

PKGTRANS = os.path.expanduser("~/.local/bin/pkgtrans")
RED = "\x1b[31m"
YEL = "\x1b[33m"
DIM = "\x1b[2m"
RST = "\x1b[0m"
ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def plain(text):
    """去掉 ANSI 转义，只看文字。"""
    return ANSI_RE.sub("", text)


# 模拟 pacman -Ss 的输出：含重复描述、中文描述、AUR 风格、info 字段
SAMPLE = """\
extra/alpha 1.0-1
    First tool for doing things
extra/beta 2.0-1
    First tool for doing things
extra/gamma 3.0-1 (group-a)
    Second tool, does other things
aur/delta 4.0-1 (+12 0.50) [3d] 
    Third tool with a fairly long description of what it does
local/epsilon 5.0-1
    已经是一个中文描述了
extra/zeta 6.0-1
    Fifth tool
"""

SAMPLE_INFO = """\
Repository      : extra
Name            : alpha
Version         : 1.0-1
Description     : First tool for doing things
Architecture    : x86_64
URL             : https://example.com/a
"""

STATE = {"mode": "ok", "requests": [], "lock": threading.Lock()}


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw or b"{}")
        except ValueError:
            payload = {}
        with STATE["lock"]:
            STATE["requests"].append({"path": self.path, "payload": payload,
                                      "headers": dict(self.headers)})

        mode = STATE["mode"]
        # 密钥里带 bad 字样就返 401，用来测「优先密钥失败→自动切换备用」
        auth = (self.headers.get("Authorization") or self.headers.get("X-Api-Key") or "")
        if "bad-key" in auth:
            return self._send(401, b'{"error":{"message":"invalid api key"}}')
        if mode == "http500":
            return self._send(500, b'{"error":{"message":"upstream boom"}}')
        if mode == "http401":
            return self._send(401, b'{"error":{"message":"invalid api key"}}')

        is_anthropic = "system" in payload
        if is_anthropic:
            content = payload["messages"][0]["content"]
        else:
            content = payload["messages"][1]["content"]
        try:
            items = json.loads(content)
        except ValueError:
            items = []
        out = [f"\u3010\u8bd1\u3011{x}" for x in items]

        if mode == "badjson":
            text = "\u62b1\u6b49\uff0c\u6211\u4e0d\u80fd\u8fd9\u6837\u505a\u3002"
        elif mode == "fences":
            text = "```json\n" + json.dumps(out, ensure_ascii=False) + "\n```"
        elif mode == "dict":
            text = json.dumps({"translations": out}, ensure_ascii=False)
        elif mode == "chatty":
            text = "\u597d\u7684\uff0c\u8bd1\u6587\u5982\u4e0b\uff1a\n" + json.dumps(out, ensure_ascii=False) + "\n\u5e0c\u671b\u5e2e\u5230\u4f60\uff01"
        elif mode == "short":
            text = json.dumps(out[:1], ensure_ascii=False)
        else:
            text = json.dumps(out, ensure_ascii=False)

        if is_anthropic:
            body = {"content": [{"type": "text", "text": text}]}
        else:
            body = {"choices": [{"message": {"role": "assistant", "content": text}}]}
        self._send(200, json.dumps(body, ensure_ascii=False).encode("utf-8"))

    def _send(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------- 测试框架

PASSED = []
FAILED = []


def check(name, condition, detail=""):
    (PASSED if condition else FAILED).append(name)
    print(f"  {'PASS' if condition else 'FAIL'}  {name}" + (f"   {detail}" if not condition else ""))


def run(args, stdin=None, env_extra=None, cache_file=None, style="openai",
        config=None, keys=None, home=None):
    """跑一次 pkgtrans。

    config / keys 传路径时改用真实的临时配置与密钥库（测子命令用）；
    默认都指向不存在的路径，保证不会读到用户自己的配置或密钥去调真实 API。
    """
    env = dict(os.environ)
    for key in list(env):
        if key.endswith("_API_KEY") or key in ("OPENAI_BASE_URL", "OLLAMA_HOST") \
                or key.startswith("PSTRANS_"):
            env.pop(key, None)
    env.update({
        "PSTRANS_CONFIG": config or "/nonexistent/pkgtrans-test-config",
        "PSTRANS_KEYS_FILE": keys or "/nonexistent/pkgtrans-test-keys.json",
        "PSTRANS_API_BASE": f"http://127.0.0.1:{PORT}" + ("/v1" if style == "openai" else ""),
        "PSTRANS_API_KEY": "test-key",
        "PSTRANS_MODEL": "mock-model",
        "PSTRANS_API_STYLE": style,
        "PSTRANS_CACHE_FILE": cache_file or "/nonexistent/pkgtrans-test-cache.json",
        "no_proxy": "127.0.0.1,localhost",
        "NO_PROXY": "127.0.0.1,localhost",
    })
    if keys:
        # 用密钥库的场景，不该再保留显式的 base/key 环境变量（否则它们优先）
        for k in ("PSTRANS_API_BASE", "PSTRANS_API_KEY", "PSTRANS_MODEL", "PSTRANS_API_STYLE"):
            env.pop(k, None)
    if home:
        env["HOME"] = home
    env.pop("NO_COLOR", None)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run([PKGTRANS] + args, input=stdin, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return (proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def reset(mode="ok"):
    with STATE["lock"]:
        STATE["mode"] = mode
        STATE["requests"] = []


def nreq():
    with STATE["lock"]:
        return len(STATE["requests"])


TMP = tempfile.mkdtemp(prefix="pkgtrans-test-")
CACHE = os.path.join(TMP, "cache.json")


def main():
    print(f"pkgtrans 自测开始  (mock API: http://127.0.0.1:{PORT})\n")

    # ---------- 1. 成功：stdin 模式，重复描述去重，中文跳过 ----------
    print("[1] 成功翻译（stdin 模式）")
    reset()
    code, out, err = run(["--color", "always", "--chunk", "3"], stdin=SAMPLE.encode())
    check("退出码 0", code == 0, f"code={code}")
    check("包头行原样保留", "extra/alpha 1.0-1" in out and "aur/delta 4.0-1 (+12 0.50) [3d] " in out)
    check("描述变为红色译文", f"    {RED}【译】First tool for doing things{RST}" in out)
    check("重复描述两处都上色", out.count(f"{RED}【译】First tool for doing things{RST}") == 2)
    check("中文描述跳过 API 但仍为红", f"    {RED}已经是一个中文描述了{RST}" in out)
    check("没有黄色（无失败）", YEL not in out)
    check("去重后仅 4 条唯一文本发给 API",
          sum(len(json.loads(r["payload"]["messages"][1]["content"])) for r in STATE["requests"]) == 4,
          f"requests={nreq()}")
    check("分批：4 条 / chunk=3 -> 2 次请求", nreq() == 2, f"requests={nreq()}")
    check("原始英文不再出现（已被替换）", "\n    First tool for doing things\n" not in out)

    # ---------- 2. 缓存 ----------
    print("[2] 缓存命中")
    if os.path.exists(CACHE):
        os.remove(CACHE)
    reset()
    # 用真实 stdin 跑两次，共享缓存文件
    run(["--color", "always"], stdin=SAMPLE.encode(), cache_file=CACHE)
    first = nreq()
    reset()
    code, out2, _ = run(["--color", "always"], stdin=SAMPLE.encode(), cache_file=CACHE)
    check("首次写入缓存时发过请求", first > 0, f"{first}")
    check("二次运行 0 次请求（全部命中缓存）", nreq() == 0, f"requests={nreq()}")
    check("缓存命中输出与首次一致", f"{RED}【译】Fifth tool{RST}" in out2)

    # ---------- 3. 命令模式 + 退出码 + stderr 透传 ----------
    print("[3] 命令模式（模拟包管理器）")
    fake = os.path.join(TMP, "fakepm")
    sample_file = os.path.join(TMP, "sample.txt")
    with open(sample_file, "w", encoding="utf-8") as fh:
        fh.write(SAMPLE)
    with open(fake, "w", encoding="utf-8") as fh:
        fh.write(f'#!/bin/sh\necho ":: fake pm querying..." >&2\ncat {sample_file}\nexit 7\n')
    os.chmod(fake, 0o755)
    reset()
    code, out, err = run(["--color", "always", "--", fake, "-Ss", "anything"])
    check("搜索结果被翻译", f"{RED}【译】Fifth tool{RST}" in out)
    check("子进程退出码被透传（7）", code == 7, f"code={code}")
    check("子进程 stderr 原样透传", ":: fake pm querying..." in err)

    # ---------- 4. 服务端 500：全部黄色，不炸，请求数有界 ----------
    print("[4] 服务端 500（翻译失败 -> 黄色）")
    reset("http500")
    code, out, err = run(["--color", "always"], stdin=SAMPLE.encode(),
                         env_extra={"PSTRANS_RETRIES": "0"})
    check("退出码仍为 0", code == 0)
    check("描述变为黄色原文", f"    {YEL}First tool for doing things{RST}" in out)
    check("包头行不受影响", "extra/alpha 1.0-1" in out and "extra/zeta 6.0-1" in out)
    check("英文描述全部变黄", out.count(YEL) >= 4, f"yellow={out.count(YEL)}")
    check("仅无需翻译的中文描述为红", out.count(RED) == 1, f"red={out.count(RED)}")
    check("请求数有界（<=5，未指数爆炸）", nreq() <= 5, f"requests={nreq()}")
    check("stderr 报告失败原因", "500" in err or "失败" in err)

    # ---------- 5. 401：立刻熔断，只发极少请求 ----------
    print("[5] 401 密钥错误（硬错误应立即熔断）")
    reset("http401")
    code, out, err = run(["--color", "always"], stdin=SAMPLE.encode(),
                         env_extra={"PSTRANS_RETRIES": "2"})
    check("英文描述全部变黄", out.count(YEL) >= 4)
    check("仅中文描述为红", out.count(RED) == 1, f"red={out.count(RED)}")
    check("请求数 <=2（没有重复试探）", nreq() <= 2, f"requests={nreq()}")
    check("错误原因可见", "401" in err)

    # ---------- 6. 畸形返回的鲁棒性 ----------
    print("[6] 模型返回格式鲁棒性")
    for mode, label in (("fences", "```json 围栏"), ("dict", "包在对象里"),
                        ("chatty", "前后带废话"), ("short", "只返回 1 条")):
        reset(mode)
        code, out, err = run(["--color", "always"], stdin=SAMPLE.encode(),
                             env_extra={"PSTRANS_RETRIES": "0"})
        ok = f"{RED}【译】Fifth tool{RST}" in out and f"{RED}【译】Second tool, does other things{RST}" in out
        check(f"{label} 仍能全部译出", ok, f"out={out!r}"[:200])

    # ---------- 7. Anthropic 协议 ----------
    print("[7] Anthropic 协议")
    reset()
    code, out, err = run(["--color", "always"], stdin=SAMPLE.encode(), style="anthropic")
    check("Anthropic 路径可用", f"{RED}【译】Fifth tool{RST}" in out)
    check("走的是 /v1/messages", STATE["requests"][0]["path"] == "/v1/messages",
          STATE["requests"][0]["path"])
    hdrs = {k.lower(): v for k, v in STATE["requests"][0]["headers"].items()}
    check("带 anthropic-version 头", hdrs.get("anthropic-version") == "2023-06-01", str(hdrs))

    # ---------- 8. 透传与开关 ----------
    print("[8] 透传与开关")
    reset()
    code, out, err = run(["--raw"], stdin=SAMPLE.encode())
    check("--raw 逐字节透传", out == SAMPLE, f"{out!r}"[:120])
    reset()
    code, out, err = run([], stdin=SAMPLE.encode(), env_extra={"PSTRANS_DISABLE": "1"})
    check("PSTRANS_DISABLE=1 逐字节透传", out == SAMPLE)
    reset()
    code, out, err = run(["--color", "always", "--bilingual"], stdin=SAMPLE.encode())
    check("--bilingual 附原文", f"{RED}【译】Fifth tool{RST}{DIM}" in out, f"{out!r}"[:200])
    reset()
    code, out, err = run(["--color", "always", "--max-items", "2"], stdin=SAMPLE.encode())
    check("max-items=2：前两条上色", f"{RED}【译】First tool for doing things{RST}" in out)
    check("max-items=2：后续保持无着色", "    Second tool, does other things" in out and YEL not in out)
    reset()
    code, out2, err = run(["--color", "always", "--no-info"], stdin=SAMPLE_INFO.encode())
    check("--no-info 不动 -Si 的 Description", "First tool for doing things" in out2 and RED not in out2)
    reset()
    code, out3, err = run(["--color", "always"], stdin=SAMPLE_INFO.encode())
    check("-Si 的 Description 会被翻译（默认开）",
          f"Description     : {RED}【译】First tool for doing things{RST}" in out3, f"{out3!r}"[:200])

    # ---------- 9. 无密钥：黄色 + 提示，绝不失败 ----------
    print("[9] 无 API 配置的降级行为")
    env = dict(os.environ)
    for key in list(env):
        if key.endswith("_API_KEY") or key.startswith("PSTRANS_") or key in ("OPENAI_BASE_URL", "OLLAMA_HOST"):
            env.pop(key, None)
    env.pop("NO_COLOR", None)
    # 必须屏蔽真实配置，否则这条用例会读到用户自己配好的 key 真的去调 API
    env["PSTRANS_CONFIG"] = "/nonexistent/pkgtrans-test-config"
    env["PSTRANS_KEYS_FILE"] = "/nonexistent/pkgtrans-test-keys.json"
    env["PSTRANS_CACHE_FILE"] = "/nonexistent/pkgtrans-test-cache.json"
    env["no_proxy"] = "127.0.0.1"
    proc = subprocess.run([PKGTRANS, "--color", "always"], input=SAMPLE.encode(), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = proc.stdout.decode()
    err = proc.stderr.decode()
    check("仍然打印完整列表", "extra/zeta 6.0-1" in out and "extra/alpha 1.0-1" in out)
    check("全部黄色", out.count(YEL) >= 5 and RED not in out)
    check("给出配置提示", "PSTRANS_API_KEY" in err)

    # ---------- 10. --check ----------
    print("[10] --check 自检")
    reset()
    code, out, err = run(["--check"])
    check("--check 成功返回 0", code == 0, f"code={code} out={out[:200]}")
    check("--check 打印译文", "【译】" in out)

    # ---------- 11. pamac ----------
    print("[11] pamac（子命令语法 + 折行描述）")
    bindir = os.path.join(TMP, "bin")
    os.makedirs(bindir, exist_ok=True)

    def make_fake(name, body):
        path = os.path.join(bindir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(body)
        os.chmod(path, 0o755)
        return path

    pamac_search = (
        "zsh-vi-mode-git  0.6.0.r26.g20c7e76-1                                        AUR\n"
        "    A better and friendly vi(vim) mode plugin for ZSH\n"
        "zigdown-bin  1.3.1-1                                                         AUR\n"
        "    Parse and render Markdown-like content to the terminal, to HTML, or\n"
        "    inside Neovim\n"
        "neovim  0.12.5-1                                                            extra\n"
        "    Fork of Vim aiming to improve user experience, plugins, and GUIs\n"
    )
    pamac_info = (
        "Name                  : neovim\n"
        "Version               : 0.12.5-1\n"
        "Description           : Fork of Vim aiming to improve user experience, plugins,\n"
        "                        and GUIs\n"
        "URL                   : https://neovim.io\n"
        "Optional Deps         : xclip: for clipboard support\n"
        "                        wl-clipboard: for wayland clipboard\n"
    )
    f_search = os.path.join(TMP, "pamac_search.txt")
    f_info = os.path.join(TMP, "pamac_info.txt")
    open(f_search, "w", encoding="utf-8").write(pamac_search)
    open(f_info, "w", encoding="utf-8").write(pamac_info)
    pamac = make_fake(
        "pamac",
        f'#!/bin/sh\nfor a in "$@"; do\n  case "$a" in\n'
        f'    search) cat {f_search}; exit 0 ;;\n'
        f'    info) cat {f_info}; exit 0 ;;\n'
        f'    install) echo "installing..."; exit 3 ;;\n'
        f'  esac\ndone\nexit 0\n',
    )

    reset()
    code, out, err = run(["--color", "always", "--", pamac, "search", "vim"])
    body = plain(out)
    check("pamac search：包头行原样保留",
          "zsh-vi-mode-git  0.6.0.r26.g20c7e76-1" in body and " extra" in body)
    check("pamac search：折行描述被合并后翻译",
          "【译】Parse and render" in body and "inside Neovim" in body, f"{body!r}"[:220])
    check("pamac search：译文是红色", f"{RED}【译】" in out, f"{out!r}"[:200])
    check("pamac search：译文按原宽度折回（无超长行）",
          max(len(l) for l in body.splitlines()) <= 90,
          f"max={max(len(l) for l in body.splitlines())}")
    check("pamac search：3 条唯一描述 / chunk 24 -> 1 次请求",
          sum(len(json.loads(r["payload"]["messages"][1]["content"]))
              for r in STATE["requests"]) == 3, f"requests={nreq()}")

    reset()
    code, out, err = run(["--color", "always", "--", pamac, "info", "neovim"])
    body = plain(out)
    check("pamac info：Description 折行值被合并翻译",
          "【译】Fork of Vim aiming to improve user experience, plugins, and GUIs"
          in body.replace("\n                        ", " "), f"{body!r}"[:240])
    check("pamac info：字段前缀 `Description           : ` 保留",
          "Description           : " in body)
    check("pamac info：其它字段（含折行的 Optional Deps）不被翻译",
          "wl-clipboard: for wayland clipboard" in body and "【译】wl-clipboard" not in body)

    reset()
    code, out, err = run(["--", pamac, "install", "foo"])
    check("pamac install 原样透传且退出码不变(3)",
          out.strip() == "installing..." and code == 3, f"out={out!r} code={code}")

    # ---------- 12. flatpak ----------
    print("[12] flatpak（TSV 输出）")
    flatpak_tsv = (
        "Neovim\tVim-fork focused on extensibility and usability\t"
        "io.neovim.nvim\t0.12.5\tstable\tflathub\n"
        "neovide\tAdvanced graphical interface for Neovim\t"
        "dev.neovide.neovide\t0.16.2\tstable\tflathub\n"
    )
    f_flat = os.path.join(TMP, "flatpak_search.tsv")
    open(f_flat, "w", encoding="utf-8").write(flatpak_tsv)
    flatpak = make_fake(
        "flatpak",
        f'#!/bin/sh\ncase "$1" in run) echo "launching $2"; exit 5 ;; esac\n'
        f'for a in "$@"; do\n  case "$a" in\n'
        f'    search) cat {f_flat}; exit 0 ;;\n'
        f'  esac\ndone\nexit 0\n',
    )

    reset()
    # 假 flatpak 必须真的遵守 --columns，否则测不出列序定位是否正确
    flatpak = make_fake("flatpak", '''#!/usr/bin/env python3
import sys
ALL = ["name", "description", "application", "version", "branch", "remotes"]
ROWS = [
    ["Neovim", "Vim-fork focused on extensibility and usability",
     "io.neovim.nvim", "0.12.5", "stable", "flathub"],
    ["neovide", "Advanced graphical interface for Neovim",
     "dev.neovide.neovide", "0.16.2", "stable", "flathub"],
]
argv = sys.argv[1:]
if argv[:1] == ["run"]:
    print("launching " + (argv[1] if len(argv) > 1 else ""))
    sys.exit(5)
cols = ALL
for i, a in enumerate(argv):
    if a.startswith("--columns="):
        cols = a.split("=", 1)[1].split(",")
    elif a == "--columns" and i + 1 < len(argv):
        cols = argv[i + 1].split(",")
if "search" in argv:
    for row in ROWS:
        print("\\t".join(row[ALL.index(c)] for c in cols))
''')
    fake_tsv = ("Neovim\tVim-fork focused on extensibility and usability\t"
                "io.neovim.nvim\t0.12.5\tstable\tflathub\n"
                "neovide\tAdvanced graphical interface for Neovim\t"
                "dev.neovide.neovide\t0.16.2\tstable\tflathub\n")

    reset()
    code, out, err = run(["--color", "always", "--", flatpak, "search", "neovim"])
    rows = [l for l in out.splitlines() if l.strip()]
    fields = [r.split("\t") for r in rows]
    check("flatpak：制表符列结构完整（6 列）", all(len(f) == 6 for f in fields), f"{fields!r}"[:200])
    check("flatpak：只翻译 description 列",
          fields[0][1] == f"{RED}【译】Vim-fork focused on extensibility and usability{RST}",
          f"{fields[0]!r}")
    check("flatpak：其余列逐字节不变",
          fields[0][0] == "Neovim" and fields[0][2] == "io.neovim.nvim"
          and fields[0][3] == "0.12.5" and fields[0][4] == "stable" and fields[0][5] == "flathub",
          f"{fields[0]!r}")

    reset()
    code, out, err = run(["--color", "always", "--",
                          flatpak, "--columns=name,application,description", "search", "neovim"])
    fields = [l.split("\t") for l in out.splitlines() if l.strip()]
    check("flatpak --columns：按自定义列序定位 description",
          len(fields[0]) == 3 and fields[0][0] == "Neovim"
          and fields[0][1] == "io.neovim.nvim"
          and fields[0][2] == f"{RED}【译】Vim-fork focused on extensibility and usability{RST}",
          f"{fields[0]!r}")

    reset()
    code, out, err = run(["--", flatpak, "search", "-j", "neovim"])
    check("flatpak --json 原样透传不翻译", out == fake_tsv, f"{out!r}"[:160])

    reset()
    code, out, err = run(["--", flatpak, "run", "org.foo.Bar"])
    check("flatpak run 原样透传且退出码不变(5)",
          out.strip() == "launching org.foo.Bar" and code == 5, f"out={out!r} code={code}")

    # ---------- 13. 管道模式方言自动识别 ----------
    print("[13] 管道模式方言自动识别")
    reset("http500")   # 只验证结构还原，不验证译文
    code, out, err = run(["--color", "always"], stdin=pamac_search.encode())
    check("pamac 输出经管道仍能正确解析",
          "zsh-vi-mode-git" in plain(out) and out.count("\n") == pamac_search.count("\n"),
          f"{plain(out)!r}"[:200])
    reset("http500")
    code, out, err = run(["--color", "always"], stdin=flatpak_tsv.encode())
    check("flatpak TSV 经管道仍能正确解析",
          out.splitlines()[0].split("\t")[1]
          == f"{YEL}Vim-fork focused on extensibility and usability{RST}",
          f"{out.splitlines()[0]!r}"[:200])
    reset("http500")
    code, out, err = run(["--color", "always"], stdin=SAMPLE.encode())
    check("pacman 输出经管道仍走 pacman 解析",
          f"{YEL}First tool for doing things{RST}" in out, f"{out!r}"[:200])

    # ---------- 14. 调用分类 ----------
    print("[14] 调用分类矩阵")
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader("pkgtrans_mod", PKGTRANS)
    mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("pkgtrans_mod", loader))
    loader.exec_module(mod)
    cases = [
        (("pacman", ["-Ss", "x"]), ("search", "pacman")),
        (("pacman", ["-Qs", "x"]), ("search", "pacman")),
        (("yay", ["-Ssq", "x"]), ("search", "pacman")),
        (("pacman", ["-Si", "x"]), ("info", "pacman")),
        (("pacman", ["-Qi", "bash"]), ("info", "pacman")),
        (("pacman", ["-Syu"]), ("other", "pacman")),
        (("pacman", ["-Rns", "foo"]), ("other", "pacman")),
        (("yay", ["-Slq"]), ("other", "pacman")),
        (("pamac", ["search", "vim"]), ("search", "pamac")),
        (("pamac", ["info", "vim"]), ("info", "pamac")),
        (("pamac", ["install", "vim"]), ("other", "pamac")),
        (("pamac", ["update"]), ("other", "pamac")),
        (("flatpak", ["search", "vim"]), ("search", "flatpak")),
        (("flatpak", ["install", "x"]), ("other", "flatpak")),
        (("flatpak", ["run", "org.x"]), ("other", "flatpak")),
        (("flatpak", ["search", "-j", "x"]), ("other", "flatpak")),
    ]
    bad = [f"{c} {a} -> {mod.classify(c, a)} (期望 {w})" for (c, a), w in cases
           if mod.classify(c, a) != w]
    check(f"分类矩阵 {len(cases)} 条全部正确", not bad, "; ".join(bad))

    # ---------- 15. 子命令：密钥库管理 ----------
    print("[15] 子命令：密钥库管理")
    cdir = os.path.join(TMP, "cfg15")
    os.makedirs(cdir, exist_ok=True)
    cfg = os.path.join(cdir, "config")
    kf = os.path.join(cdir, "keys.json")
    fake_home = os.path.join(TMP, "home15")
    os.makedirs(fake_home, exist_ok=True)
    common = dict(config=cfg, keys=kf, home=fake_home)

    code, out, err = run(["keyadd", "DeepSeek", "sk-body-aaaaaaaaaaaa1111"], **common)
    check("keyadd：写入并给出提示", code == 0 and "已添加 DeepSeek" in err, f"{err!r}"[:200])
    check("keyadd：密钥库权限 600", oct(os.stat(kf).st_mode & 0o777) == "0o600",
          oct(os.stat(kf).st_mode & 0o777))

    run(["keyadd", "Claude", "sk-ant-zzzz-999988887777"], **common)
    code, out, err = run(["keylist"], **common)
    check("keylist：两条都列出", "DeepSeek" in out and "Claude" in out, f"{out!r}"[:200])
    check("keylist：不泄露完整密钥", "sk-body-aaaaaaaaaaaa1111" not in out
          and "*****" in out, f"{out!r}"[:200])
    check("keylist：给出数量与优先项", "共 2 个 API key" in out and "当前优先" in out,
          f"{out!r}"[:200])

    code, out, err = run(["keyprefer", "2"], **common)
    check("keyprefer 2：改成 Claude 优先", "已把 Claude" in err, f"{err!r}"[:200])
    code, out, err = run(["keyprefer"], **common)
    check("keyprefer（无参）：查询优先项", "Claude" in out, f"{out!r}"[:200])

    code, out, err = run(["keylock"], **common)
    check("keylock：提示已锁定", "已锁定" in err, f"{err!r}"[:200])
    check("keylock：落盘 locked=true", json.load(open(kf))["locked"] is True)
    code, out, err = run(["keyunlock"], **common)
    check("keyunlock：提示已解锁", "已解锁" in err, f"{err!r}"[:200])
    check("keyunlock：落盘 locked=false", json.load(open(kf))["locked"] is False)

    code, out, err = run(["keyremove", "1"], **common)
    check("keyremove：删掉后只剩 1 条", code == 0 and len(json.load(open(kf))["keys"]) == 1,
          f"{err!r}"[:200])
    code, out, err = run(["keyremove", "99"], **common)
    check("keyremove 不存在的编号：报错且不动文件",
          code == 2 and len(json.load(open(kf))["keys"]) == 1)

    # ---------- 16. 子命令：aim / on / off / setup ----------
    print("[16] 子命令：aim / on / off / setup / putes")
    code, out, err = run(["aim", "zh-hant"], **common)
    check("aim zh-hant：映射为繁體中文并提示", code == 0 and "繁體中文" in err, f"{err!r}"[:200])
    check("aim：写进配置文件", "target_lang = 繁體中文" in open(cfg).read())
    code, out, err = run(["aim"], **common)
    check("aim（无参）：查询当前语言", "繁體中文" in out, f"{out!r}"[:200])
    code, out, err = run(["aim", "eo-latn"], **common)
    check("aim eo-latn：映射为世界语", "世界语" in err, f"{err!r}"[:200])
    code, out, err = run(["aim", "default"], **common)
    check("aim default：回到简体中文", "简体中文" in err, f"{err!r}"[:200])

    code, out, err = run(["setup"], **common)
    check("setup（无参）：打印接管状态表",
          "包管理器" in out and "已接管" in out and "pacman" in out, f"{out!r}"[:200])
    code, out, err = run(["putes", "all"], **common)
    check("putes all：配置写成 none（不会自动反弹）",
          "shell_targets = none" in open(cfg).read(), open(cfg).read()[-120:])
    zshrc = os.path.join(fake_home, ".zshrc")
    check("putes all：块里不再定义任何函数", "() {" not in open(zshrc).read())
    code, out, err = run(["setup", "pamac", "flatpak"], **common)
    block = open(zshrc).read()
    check("setup pamac flatpak：只接管这两个",
          "pamac()" in block and "flatpak()" in block and "pacman()" not in block,
          f"{block!r}"[:300])
    check("setup：回执点出接管列表", "已接管：pamac, flatpak" in err, f"{err!r}"[:200])
    code, out, err = run(["putes", "pamac"], **common)
    check("putes pamac：取消接管", "已接管：flatpak" in err and "pamac()" not in open(zshrc).read(),
          f"{err!r}"[:200])
    code, out, err = run(["putesy", "flatpak"], **common)   # setup 反写的错拼也认
    check("putesy 别名可用（setup 反写）", code == 0 and "flatpak()" not in open(zshrc).read())
    code, out, err = run(["setup", "pamac"], env_extra={"SHELL": "/usr/bin/fish"}, **common)
    check("不支持的 shell：明确报错而不是瞎写 .zshrc",
          code == 1 and "不支持" in err, f"code={code} {err!r}"[:200])

    # 终端模拟器 ≠ shell：提示语要点出「窗口」和「shell」两层（提示走 stderr）
    code, out, err = run(["setup"], env_extra={"KITTY_WINDOW_ID": "1"}, **common)
    check("提示语能认出 kitty 窗口", "kitty 窗口" in err and "exec zsh" in err, f"{err!r}"[:220])
    code, out, err = run(["setup"], env_extra={"KONSOLE_VERSION": "260800",
                                              "KONSOLE_DBUS_SERVICE": ":1.5"}, **common)
    check("KONSOLE_* 泄露时不会被误报成 Konsole（弱信号不用）",
          "Konsole" not in err and "新开一个终端窗口" in err, f"{err!r}"[:220])
    code, out, err = run(["setup"], env_extra={"SHELL": "/bin/bash"}, **common)
    check("提示语跟着 shell 走（bash 时 exec bash）", "exec bash" in err, f"{err!r}"[:220])

    code, out, err = run(["off"], **common)
    check("off：提示已关闭并写盘", "已关闭" in err and "enabled = 0" in open(cfg).read(),
          f"{err!r}"[:200])
    reset()
    code, out, err = run([], stdin=SAMPLE.encode(), **common)
    check("off 之后搜索逐字节原样透传", out == SAMPLE, f"{out!r}"[:120])
    code, out, err = run(["on"], **common)
    check("on：提示已开启并写盘", "已开启" in err and "enabled = 1" in open(cfg).read(),
          f"{err!r}"[:200])

    # ---------- 17. 多密钥回退与锁定 ----------
    print("[17] 多密钥自动回退 / 锁定")
    kf2 = os.path.join(cdir, "keys2.json")
    mock_base = f"http://127.0.0.1:{PORT}/v1"
    entries = [
        {"id": 1, "provider": "DeepSeek", "style": "openai", "base": mock_base,
         "model": "mock", "key": "bad-key-1"},
        {"id": 2, "provider": "Claude", "style": "openai", "base": mock_base,
         "model": "mock", "key": "good-key-2"},
    ]

    def write_keys(preferred, locked):
        with open(kf2, "w", encoding="utf-8") as fh:
            json.dump({"version": 1, "preferred": preferred, "locked": locked,
                       "keys": entries}, fh, ensure_ascii=False)

    write_keys(1, False)
    reset()
    code, out, err = run(["--color", "always"], stdin=SAMPLE.encode(), keys=kf2, config=cfg)
    check("优先密钥 401 时自动切到备用并译出",
          f"{RED}【译】Fifth tool{RST}" in out and YEL not in out, f"{out!r}"[:250])
    check("stderr 说明切换过备用密钥", "切换过" in err, f"{err!r}"[:250])

    write_keys(1, True)          # 锁定：不切换
    reset()
    code, out, err = run(["--color", "always"], stdin=SAMPLE.encode(), keys=kf2, config=cfg)
    check("锁定后不切换：英文全黄、仅本就中文的为红",
          f"{YEL}Fifth tool{RST}" in out and out.count(RED) == 1, f"{out!r}"[:250])
    check("锁定后请求数很少（1 次即熔断）", nreq() <= 2, f"requests={nreq()}")

    write_keys(2, True)          # 锁定但优先项是好密钥
    reset()
    code, out, err = run(["--color", "always"], stdin=SAMPLE.encode(), keys=kf2, config=cfg)
    check("锁定时优先项可用则正常翻译", f"{RED}【译】Fifth tool{RST}" in out, f"{out!r}"[:250])

    # ---------- 18. info / help ----------
    print("[18] info / help")
    code, out, err = run(["info"], **common)
    lines = out.splitlines()
    check("info：打出大字图案", "█" in out and "╔" in out, f"{out!r}"[:120])
    check("info：图案 6 行等宽", len({len(l) for l in lines[:6]}) == 1,
          str({len(l) for l in lines[:6]}))
    check("info：开发者/版本/开发/网址齐全",
          "Toru Momose" in out and "1.0" in out and "DeepSeek v4 Pro" in out
          and "https://iris-dream.top" in out, f"{out!r}"[:300])
    for flag in ("-v", "--version"):
        code, out, err = run([flag], **common)
        check(f"{flag} 等同 info", "Toru Momose" in out)
    code, out, err = run(["help"], **common)
    check("help：列出子命令", all(k in out for k in ("keyadd", "keylist", "setup", "putes",
                                                    "aim", "on / off")), f"{out!r}"[:200])

    print()
    print("=" * 62)
    print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        for name in FAILED:
            print(f"  失败: {name}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    PORT = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        rc = main()
    finally:
        server.shutdown()
        shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(rc)
