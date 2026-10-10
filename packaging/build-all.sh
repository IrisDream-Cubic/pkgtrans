#!/bin/sh
# 本地尽量把能构建的都构建出来，产物统一放 dist/。
#
#   sh packaging/build-all.sh [输出目录]
#
# 本机没有对应工具链的格式会明确跳过（rpm 需要 rpmbuild，nix 需要 nix）。
# 完整四件套由 .github/workflows/release.yml 在各自的容器里构建。

set -eu

OUT="${1:-dist}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION="1.0"
cd "$ROOT"
mkdir -p "$OUT"

echo "==================== 源码 tarball ===================="
sh packaging/build-source-tarball.sh "$VERSION" "$OUT"

echo
echo "==================== Arch (.pkg.tar.zst) ===================="
if command -v makepkg >/dev/null 2>&1; then
  tmp=$(mktemp -d)
  cp packaging/PKGBUILD "$tmp/"
  cp "$OUT/pkgtrans-$VERSION.tar.gz" "$tmp/"
  ( cd "$tmp" && makepkg -f --nodeps --noconfirm >/dev/null )
  cp "$tmp"/*.pkg.tar.zst "$OUT/"
  rm -rf "$tmp"
  echo "✓ $OUT/$(ls "$OUT" | grep '\.pkg\.tar\.zst$' | head -1)"
else
  echo "跳过：没有 makepkg"
fi

echo
echo "==================== deb ===================="
python3 packaging/build-deb.py --outdir "$OUT" --version "$VERSION"

echo
echo "==================== rpm ===================="
if command -v rpmbuild >/dev/null 2>&1; then
  top=$(mktemp -d)
  mkdir -p "$top"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
  cp "$OUT/pkgtrans-$VERSION.tar.gz" "$top/SOURCES/"
  rpmbuild --define "_topdir $top" -bb packaging/pkgtrans.spec >/dev/null
  find "$top/RPMS" -name '*.rpm' -exec cp {} "$OUT/" \;
  rm -rf "$top"
  echo "✓ $OUT/$(ls "$OUT" | grep '\.rpm$' | head -1)"
else
  echo "跳过：没有 rpmbuild（Fedora / RHEL 系才有）"
fi

echo
echo "==================== nix ===================="
if command -v nix >/dev/null 2>&1; then
  nix build ".#" --out-link "$OUT/result"
  echo "✓ $OUT/result -> $(readlink -f "$OUT/result")"
else
  echo "跳过：没有 nix"
fi

echo
echo "==================== 产物 ===================="
ls -lh "$OUT"
