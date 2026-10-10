#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建 pkgtrans 的 .deb 包。

本机有 dpkg-deb 就用它（最权威）；没有就按 deb(5) 规范用纯 Python 手工组装
ar 归档 + control.tar.gz + data.tar.gz，产出结构等价的包。

用法:
    python3 packaging/build-deb.py [--outdir dist] [--version 1.0] [--revision 1]
"""

import argparse
import gzip
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAINTAINER = "Toru Momose <iris@iris-dream.top>"
HOMEPAGE = "https://github.com/IrisDream-Cubic/pkgtrans"
EPOCH = 1700000000          # 固定时间戳，保证可重复构建


def install_tree(root: str, version: str):
    """把要打包的文件放进 root（相当于 deb 的 ./）。"""
    def put(rel, src, mode):
        dst = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        os.chmod(dst, mode)

    put("usr/bin/pkgtrans", os.path.join(ROOT, "pkgtrans"), 0o755)
    put("usr/share/doc/pkgtrans/README.md", os.path.join(ROOT, "README.md"), 0o644)
    put("usr/share/doc/pkgtrans/copyright", os.path.join(ROOT, "LICENSE"), 0o644)
    put("usr/share/bash-completion/completions/pkgtrans",
        os.path.join(ROOT, "packaging", "pkgtrans.bash-completion"), 0o644)
    put("usr/share/zsh/site-functions/_pkgtrans",
        os.path.join(ROOT, "packaging", "_pkgtrans"), 0o644)

    # changelog.Debian.gz：少了它 lintian 会报 E: no-changelog。
    # 日期写死，保证可重复构建。
    dst = os.path.join(root, "usr/share/doc/pkgtrans/changelog.Debian.gz")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as fh:
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=EPOCH) as gz:
            gz.write(changelog_text(version).encode("utf-8"))
    os.chmod(dst, 0o644)


def changelog_text(version: str) -> str:
    return f"""pkgtrans ({version}-1) unstable; urgency=medium

  * 首个版本：支持 pacman / yay / paru、pamac、flatpak 三种输出方言
  * 多 API Key 管理与失败自动回退，可锁定为只用一个
  * 目标语言可切换（简体 / 繁體 / 日本語 / 世界语 …）
  * setup / putes 管理 shell 集成，on / off 全局开关

 -- {MAINTAINER}  Sat, 10 Oct 2026 12:00:00 +0800
"""


def control_text(version: str, revision: str, installed_kb: int) -> str:
    return f"""\
Package: pkgtrans
Version: {version}-{revision}
Architecture: all
Maintainer: {MAINTAINER}
Installed-Size: {installed_kb}
Depends: python3 (>= 3.9)
Suggests: pacman, yay, pamac, flatpak
Section: utils
Priority: optional
Homepage: {HOMEPAGE}
Description: AI translation for package manager search results
 pkgtrans translates the description lines of pacman / yay / paru / pamac /
 flatpak search results with an LLM API. Successful translations are shown
 in red, failed ones fall back to the original text in yellow.
 Useful when you can read package names but not the English descriptions.
"""


def _tarinfo(name: str, size: int, mode: int, is_dir=False):
    info = tarfile.TarInfo(name)
    info.size = 0 if is_dir else size
    info.mode = mode
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    info.mtime = EPOCH
    info.type = tarfile.DIRTYPE if is_dir else tarfile.REGTYPE
    return info


def make_tar_gz(root: str, entries) -> bytes:
    """按 deb 要求打包成 tar.gz（成员名以 ./ 开头，属主 root:root，时间戳固定）。"""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=EPOCH) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
            for rel, is_dir in entries:
                full = os.path.join(root, rel)
                if is_dir:
                    tar.addfile(_tarinfo("./" + rel.rstrip("/") + "/", 0, 0o755, True))
                else:
                    with open(full, "rb") as fh:
                        data = fh.read()
                    tar.addfile(_tarinfo("./" + rel, len(data),
                                         os.stat(full).st_mode & 0o777),
                                io.BytesIO(data))
    return buf.getvalue()


def collect_entries(root: str):
    """返回 [(相对路径, 是否目录)]；按层级排序，保证目录先于其内容出现。"""
    entries = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in dirs:
            entries.append((os.path.relpath(os.path.join(base, name), root), True))
        for name in files:
            entries.append((os.path.relpath(os.path.join(base, name), root), False))
    entries.sort(key=lambda e: (e[0].count(os.sep), e[0]))
    return entries


def walk_files(root: str):
    out = []
    for base, dirs, files in os.walk(root):
        dirs.sort()
        for name in sorted(files):
            out.append(os.path.relpath(os.path.join(base, name), root))
    return out


def ar_member(name: str, data: bytes) -> bytes:
    """一个 ar 成员：头部 60 字节 + 数据（奇数长度补 \\n）。"""
    header = (
        f"{name:<16}{EPOCH:<12}{0:<6}{0:<6}{0o100644:<8o}{len(data):<10}`\n"
    ).encode("ascii")
    assert len(header) == 60, len(header)
    pad = b"\n" if len(data) % 2 else b""
    return header + data + pad


def build_ar(members) -> bytes:
    out = [b"!<arch>\n"]
    for name, data in members:
        out.append(ar_member(name, data))
    return b"".join(out)


def build_with_dpkg_deb(tree: str, control_dir: str, out_path: str) -> bool:
    dpkg_deb = shutil.which("dpkg-deb")
    if not dpkg_deb:
        return False
    shutil.move(control_dir, os.path.join(tree, "DEBIAN"))
    proc = subprocess.run(
        # -Zgzip：新版 dpkg 默认用 zstd 压缩成员，而 Python 3.12 标准库解不了
        # zstd，后面的结构校验会挂；gzip 的兼容性也最好。
        [dpkg_deb, "--build", "-Zgzip", "--root-owner-group", tree, out_path],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout.decode("utf-8", "replace"))
        return False
    return True


def write_md5sums(tree: str, control_dir: str):
    """生成 control 里的 md5sums。

    两条构建路径都要有：dpkg-deb --build 自己**不会**算 md5sums
    （那是 dh_md5sums 的活），不显式写就不会出现在包里。
    """
    files = walk_files(tree)
    md5 = "".join(
        f"{hashlib.md5(open(os.path.join(tree, f), 'rb').read()).hexdigest()}  {f}\n"
        for f in files
    )
    with open(os.path.join(control_dir, "md5sums"), "w", encoding="utf-8") as fh:
        fh.write(md5)


def build_pure(tree: str, control_dir: str, out_path: str):
    control_entries = sorted(os.listdir(control_dir))
    control_tar = make_tar_gz(control_dir, [(e, False) for e in control_entries])
    data_tar = make_tar_gz(tree, collect_entries(tree))
    blob = build_ar([
        ("debian-binary", b"2.0\n"),
        ("control.tar.gz", control_tar),
        ("data.tar.gz", data_tar),
    ])
    with open(out_path, "wb") as fh:
        fh.write(blob)


def verify_deb(path: str):
    """重新解析一遍，确认 ar 结构、成员顺序和 control 必填字段都在。

    成员可能叫 control.tar.gz / .xz / .zst（取决于谁生成的），所以按前缀找，
    不写死扩展名。
    """
    with open(path, "rb") as fh:
        blob = fh.read()
    assert blob[:8] == b"!<arch>\n", "ar magic 不对"
    pos, names, bodies = 8, [], {}
    while pos + 60 <= len(blob):
        head = blob[pos:pos + 60]
        assert head[58:60] == b"`\n", "成员头 magic 不对"
        name = head[0:16].decode("ascii").strip().rstrip("/")
        size = int(head[48:58].decode("ascii").strip())
        bodies[name] = blob[pos + 60: pos + 60 + size]
        names.append(name)
        pos += 60 + size + (size % 2)
    assert names[0] == "debian-binary", f"第一个成员必须是 debian-binary，实际 {names[0]}"
    assert bodies["debian-binary"] == b"2.0\n", "debian-binary 内容不对"

    control_member = next((n for n in names if n.startswith("control.tar")), None)
    data_member = next((n for n in names if n.startswith("data.tar")), None)
    assert control_member and data_member, f"缺 control/data 成员：{names}"

    def open_member(member):
        try:
            return tarfile.open(fileobj=io.BytesIO(bodies[member]), mode="r:*")
        except tarfile.TarError as exc:
            raise AssertionError(f"{member} 解不开（压缩格式不支持？）：{exc}")

    with open_member(control_member) as tar:
        control = tar.extractfile("./control").read().decode("utf-8")
        assert "./md5sums" in tar.getnames(), f"{control_member} 里缺 md5sums"
    for field in ("Package:", "Version:", "Architecture:", "Maintainer:", "Description:"):
        assert field in control, f"control 缺 {field}"

    with open_member(data_member) as tar:
        data_names = tar.getnames()
        assert "./usr/bin/pkgtrans" in data_names, data_names
        assert tar.getmember("./usr/bin/pkgtrans").mode & 0o111, "pkgtrans 没有可执行位"
    return names, data_names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(ROOT, "dist"))
    ap.add_argument("--version", default="1.0")
    ap.add_argument("--revision", default="1")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    out_path = os.path.join(args.outdir, f"pkgtrans_{args.version}-{args.revision}_all.deb")

    tmp = tempfile.mkdtemp(prefix="pkgtrans-deb-")
    try:
        tree = os.path.join(tmp, "tree")
        control_dir = os.path.join(tmp, "DEBIAN")
        os.makedirs(tree)
        os.makedirs(control_dir)
        install_tree(tree, args.version)

        total = sum(os.path.getsize(os.path.join(b, f))
                    for b, _d, fs in os.walk(tree) for f in fs)
        with open(os.path.join(control_dir, "control"), "w", encoding="utf-8") as fh:
            fh.write(control_text(args.version, args.revision, (total + 1023) // 1024))
        write_md5sums(tree, control_dir)

        if build_with_dpkg_deb(tree, control_dir, out_path):
            builder = "dpkg-deb"
        else:
            build_pure(tree, control_dir, out_path)
            builder = "纯 Python ar 组装"
        names, data_names = verify_deb(out_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    size = os.path.getsize(out_path)
    print(f"✓ 已生成 {out_path}  ({size} 字节, 构建方式: {builder})")
    print(f"  ar 成员    : {', '.join(names)}")
    print(f"  data 内容  : {len(data_names)} 项，含 {data_names[0]}")
    print(f"  sha256     : {hashlib.sha256(open(out_path, 'rb').read()).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
