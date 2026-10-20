#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Windows 冒烟测试（CI 用，也接受本地传 exe 路径）。

完整的 150 多项自测在 Linux / macOS 上跑就够了——那套用例依赖 POSIX 的
.zshrc 和 `#!/bin/sh` 假二进制，Windows 上跑不了。这里只验 Windows 特有的部分：

  * exe 能启动、`--version` / `help` 正常
  * 平台判定是 windows，setup 表格里只有 winget / flatpak
  * winget show 的 Description 被识别到（着黄 = 没有 API 时的回退色）
  * winget search 这种没有描述列的输出逐字节原样
  * install-winget 在已装 winget 的机器上直接说「已经装了」
  * 配置落在 %APPDATA%\\pkgtrans 下，而不是家目录里的 .config

用法:
    python packaging/windows-smoke.py dist/pkgtrans-windows-x64.exe
"""

import os
import subprocess
import sys

EXE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "dist", "pkgtrans-windows-x64.exe")

PASSED, FAILED = [], []


def check(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    if cond:
        PASSED.append(name)
    else:
        FAILED.append((name, str(detail)[:300]))


def run(args, stdin=b""):
    env = dict(os.environ)
    # 别读到开发机上的真实配置和密钥，也别真去调 API
    for key in list(env):
        if key.startswith("PSTRANS_"):
            env.pop(key, None)
    env["PSTRANS_CONFIG"] = os.path.join(os.environ.get("TEMP", "."), "no-such-config")
    env["PSTRANS_KEYS_FILE"] = os.path.join(os.environ.get("TEMP", "."), "no-such-keys")
    env["PSTRANS_API_BASE"] = "http://127.0.0.1:9/v1"     # 必然连不上
    env["PSTRANS_API_KEY"] = "x"
    env["PSTRANS_CACHE"] = "0"
    return subprocess.run([EXE] + args, input=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env, timeout=180)


def text(raw):
    return raw.decode("utf-8", "replace")


print(f"检查 {EXE}")
print(f"  存在: {os.path.isfile(EXE)}  "
      f"大小: {os.path.getsize(EXE) // 1024 if os.path.isfile(EXE) else 0} KiB")
check("exe 文件存在", os.path.isfile(EXE), EXE)
if not os.path.isfile(EXE):
    sys.exit(1)

# 1. 基本启动
proc = run(["--version"])
out = text(proc.stdout)
check("--version 退出码 0", proc.returncode == 0, proc.returncode)
check("--version 输出版本号", "版本" in out and any(c.isdigit() for c in out), out)
check("--version 输出开发者", "Toru Momose" in out, out)

# 2. help
proc = run(["help"])
out = text(proc.stdout)
check("help 退出码 0", proc.returncode == 0, proc.returncode)
for word in ("install-winget", "setup", "keyadd", "aim"):
    check(f"help 里有 {word}", word in out, out[:400])

# 3. 平台判定
proc = run(["setup"])
out, err = text(proc.stdout), text(proc.stderr)
check("setup 表格里有 winget", "winget" in out, out[:400])
check("setup 说明当前是 Windows", "Windows" in err, err[:400])
check("setup 表格里没有 pacman", "pacman" not in out, out[:400])

# 4. winget show 的 Description 被认出来（没有 API 时着黄）
SHOW = (b"Found Neovim [Neovim.Neovim]\r\n"
        b"Version: 0.12.6\r\n"
        b"Publisher: Neovim\r\n"
        b"Description: Vim-fork focused on extensibility and usability\r\n"
        b"License: Apache-2.0 AND Vim AND MIT\r\n")
proc = run(["--color", "always"], stdin=SHOW)
out = text(proc.stdout)
check("winget show：Description 着黄（识别为待翻译）",
      "\x1b[33m" in out and "Description:" in out, out[:400])
check("winget show：License 没被当成描述",
      "License: Apache-2.0 AND Vim AND MIT" in out, out[:400])

# 5. 没有描述列的输出逐字节原样
SEARCH = (b"Name      Id              Version  Source\r\n"
          b"----------------------------------------\r\n"
          b"Neovim    Neovim.Neovim   0.12.6   winget\r\n")
proc = run([], stdin=SEARCH)
check("winget search：没有描述列 -> 逐字节原样",
      proc.stdout.replace(b"\r\n", b"\n") == SEARCH.replace(b"\r\n", b"\n"),
      proc.stdout)

# 6. install-winget（windows-latest 自带 winget）
proc = run(["install-winget"])
err = text(proc.stderr)
check("install-winget：已装 winget 时直接说已经装了",
      proc.returncode == 0 and "已经装了" in err, f"{proc.returncode} {err[:300]}")

# 7. 配置目录在 %APPDATA% 下
proc = run(["show-config"])
out = text(proc.stdout) + text(proc.stderr)
appdata = os.environ.get("APPDATA", "")
check("配置路径在 %APPDATA%\\\\pkgtrans 下",
      appdata and appdata.lower() in out.lower() and "pkgtrans" in out,
      out[:400])
check("配置路径不再是 ~/.config", ".config" not in out.lower(), out[:400])

print()
print("=" * 56)
print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
for name, detail in FAILED:
    print(f"  失败: {name}  {detail}")
sys.exit(1 if FAILED else 0)
