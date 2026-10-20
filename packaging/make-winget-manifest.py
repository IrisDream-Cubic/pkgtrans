#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 winget 清单（manifest），用于提交到 microsoft/winget-pkgs。

exe 的 sha256 只有在 Windows 上打完包才知道，所以清单不能手写死在仓库里，
否则版本一升就对不上。release 工作流会调这个脚本，用真实 sha256 生成三份
yaml 打成 tar.gz 附在 Release 上；想发布到 winget 时解包提 PR 即可。

用法:
    python3 packaging/make-winget-manifest.py --version 1.2 \
        --sha256 <exe 的 sha256> --outdir out/winget

    # 只想看看长什么样（sha256 留空也能生成，只是会在 yaml 里写占位）
    python3 packaging/make-winget-manifest.py --version 1.2 --outdir /tmp/w
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PACKAGE_ID = "IrisDream.pkgtrans"
EXE_NAME = "pkgtrans-windows-x64.exe"
REPO = "IrisDream-Cubic/pkgtrans"
HOMEPAGE = f"https://github.com/{REPO}"
TAG_PREFIX = "v"


def source_version() -> str:
    with open(os.path.join(ROOT, "pkgtrans"), encoding="utf-8") as fh:
        m = re.search(r'^__version__ = "([^"]+)"', fh.read(), re.M)
    return m.group(1) if m else "0.0"


def version_manifest(version: str) -> str:
    return f"""\
# yaml-language-server: $schema=https://aka.ms/winget-manifest.version.1.6.0.schema.json
PackageIdentifier: {PACKAGE_ID}
PackageVersion: {version}
DefaultLocale: en-US
ManifestType: version
ManifestVersion: 1.6.0
"""


def installer_manifest(version: str, sha256: str) -> str:
    return f"""\
# yaml-language-server: $schema=https://aka.ms/winget-manifest.installer.1.6.0.schema.json
PackageIdentifier: {PACKAGE_ID}
PackageVersion: {version}
InstallerType: portable
Commands:
  - pkgtrans
Installers:
  - Architecture: x64
    InstallerUrl: {HOMEPAGE}/releases/download/{TAG_PREFIX}{version}/{EXE_NAME}
    InstallerSha256: {sha256.upper()}
    PortableCommandAlias: pkgtrans
ManifestType: installer
ManifestVersion: 1.6.0
"""


def locale_manifest(version: str, lang: str) -> str:
    if lang.startswith("zh"):
        desc = ("用 AI 翻译 pacman / yay / paru / pamac / apt / dnf / brew / winget / "
                "flatpak 搜索结果的描述文字。翻译成功显示红色，失败原样回退显示黄色。")
        short = "用 AI 翻译包管理器搜索结果的描述"
    else:
        desc = ("Translates the description lines of pacman / yay / paru / pamac / apt / "
                "dnf / brew / winget / flatpak search results with an LLM API. Successful "
                "translations are shown in red, failed ones fall back to the original text "
                "in yellow.")
        short = "AI translation for package manager search results"
    return f"""\
# yaml-language-server: $schema=https://aka.ms/winget-manifest.defaultLocale.1.6.0.schema.json
PackageIdentifier: {PACKAGE_ID}
PackageVersion: {version}
PackageLocale: {lang}
Publisher: Toru Momose
PublisherUrl: {HOMEPAGE}
PublisherSupportUrl: {HOMEPAGE}/issues
Author: Toru Momose
PackageName: pkgtrans
PackageUrl: {HOMEPAGE}
License: MIT
LicenseUrl: {HOMEPAGE}/blob/main/LICENSE
ShortDescription: {short}
Description: {desc}
Moniker: pkgtrans
Tags:
  - cli
  - translation
  - package-manager
  - winget
  - pacman
  - apt
  - dnf
  - brew
ManifestType: defaultLocale
ManifestVersion: 1.6.0
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=source_version())
    ap.add_argument("--sha256", default="0" * 64,
                    help="pkgtrans-windows-x64.exe 的 sha256（64 位十六进制）")
    ap.add_argument("--outdir", default=os.path.join(ROOT, "out", "winget"))
    args = ap.parse_args()

    if not re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256):
        ap.error("--sha256 必须是 64 位十六进制")

    # winget-pkgs 的目录结构：manifests/<首字母>/<Publisher>/<Package>/<Version>/
    first = PACKAGE_ID[0].lower()
    target = os.path.join(args.outdir, "manifests", first, *PACKAGE_ID.split("."),
                          args.version)
    os.makedirs(target, exist_ok=True)

    files = {
        f"{PACKAGE_ID}.yaml": version_manifest(args.version),
        f"{PACKAGE_ID}.installer.yaml": installer_manifest(args.version, args.sha256),
        f"{PACKAGE_ID}.locale.en-US.yaml": locale_manifest(args.version, "en-US"),
        f"{PACKAGE_ID}.locale.zh-CN.yaml": locale_manifest(args.version, "zh-CN"),
    }
    for name, content in files.items():
        with open(os.path.join(target, name), "w", encoding="utf-8") as fh:
            fh.write(content)

    print(f"✓ winget 清单已生成：{target}")
    for name in sorted(files):
        print(f"    {name}")
    print()
    print("提交到 microsoft/winget-pkgs 的步骤：")
    print("  1. fork https://github.com/microsoft/winget-pkgs")
    print(f"  2. 把 manifests/ 下这四级目录整个拷进去（路径原样保留）")
    print("  3. winget install wingetcreate，然后：")
    print(f"     wingetcreate submit --token <PAT> {PACKAGE_ID}")
    print("  4. 或者直接开 PR，让他们的 CI 校验")
    return 0


if __name__ == "__main__":
    sys.exit(main())
