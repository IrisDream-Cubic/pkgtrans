#!/bin/sh
# 本地把五种产物一次构建出来，统一放 dist/。
#
#   sh packaging/build-all.sh [输出目录]
#
# 优先用本机原生工具链；缺哪个就用 Docker 顶上（跑的是和
# .github/workflows/release.yml 完全相同的命令）。
# Docker 镜像默认用官方名，国内拉不动时可以用环境变量换成镜像源：
#
#   PSTRANS_ARCH_IMAGE=docker.m.daocloud.io/library/archlinux:latest \
#   PSTRANS_FEDORA_IMAGE=docker.m.daocloud.io/library/fedora:latest \
#   PSTRANS_NIX_IMAGE=dockerproxy.com/nixos/nix:latest \
#   sh packaging/build-all.sh dist

set -eu

OUT="${1:-dist}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

# 版本号只有一个来源：主程序自己。以前这里和 PKGBUILD / spec / nix
# 各写各的，改一处就漂了。
VERSION=$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' pkgtrans | head -1)
[ -n "$VERSION" ] || { echo "读不到版本号" >&2; exit 1; }

DOCKER="${PSTRANS_DOCKER:-docker}"
ARCH_IMAGE="${PSTRANS_ARCH_IMAGE:-archlinux:latest}"
FEDORA_IMAGE="${PSTRANS_FEDORA_IMAGE:-fedora:latest}"
NIX_IMAGE="${PSTRANS_NIX_IMAGE:-nixos/nix:latest}"

WORK="$ROOT/.build"          # 给容器写东西用的暂存区（容器里是 root，不直接写 dist）
mkdir -p "$OUT"

have_docker() {
  command -v "$DOCKER" >/dev/null 2>&1 && "$DOCKER" info >/dev/null 2>&1
}

# 容器里的工作目录统一挂到 /w；产物先落到 /w/.build/xxx，再由宿主机拷进 dist，
# 这样 dist 里的文件属主还是当前用户。
docker_build() {  # $1=镜像  $2=容器内脚本  $3=暂存子目录名
  rm -rf "$WORK/$3"
  mkdir -p "$WORK/$3"
  chmod 777 "$WORK/$3"
  # NIX_OVERRIDE 透传进容器：本地 GitHub API 被限流时可以用
  # PSTRANS_NIX_OVERRIDE_NIXPKGS 指定 nixpkgs 输入。
  "$DOCKER" run --rm -e NIX_OVERRIDE="${PSTRANS_NIX_OVERRIDE_NIXPKGS:-}" \
    -v "$ROOT:/w" -w /w "$1" bash -c "$2"
}

echo "版本号：$VERSION"
echo
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
elif have_docker; then
  echo "本机没有 makepkg，改用 $ARCH_IMAGE"
  docker_build "$ARCH_IMAGE" '
    set -e
    pacman -Syu --noconfirm --needed --disable-download-timeout base-devel python >/dev/null
    useradd -m builder
    mkdir -p /build
    cp packaging/PKGBUILD /build/
    cp dist/pkgtrans-*.tar.gz /build/
    chown -R builder /build
    su builder -s /bin/sh -c "cd /build && makepkg -f --nodeps --noconfirm" >/dev/null
    cp /build/*.pkg.tar.zst /w/.build/arch/
  ' arch
  cp "$WORK"/arch/*.pkg.tar.zst "$OUT/"
else
  echo "跳过：既没有 makepkg 也没有可用的 docker"
fi
[ -n "$(ls "$OUT"/*.pkg.tar.zst 2>/dev/null || true)" ] && \
  echo "✓ $OUT/$(ls "$OUT" | grep '\.pkg\.tar\.zst$' | head -1)"

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
elif have_docker; then
  echo "本机没有 rpmbuild，改用 $FEDORA_IMAGE"
  docker_build "$FEDORA_IMAGE" '
    set -e
    dnf install -y rpm-build python3 >/dev/null
    mkdir -p ~/rpmbuild/BUILD ~/rpmbuild/BUILDROOT ~/rpmbuild/RPMS ~/rpmbuild/SOURCES ~/rpmbuild/SPECS ~/rpmbuild/SRPMS
    cp dist/pkgtrans-*.tar.gz ~/rpmbuild/SOURCES/
    rpmbuild -bb --define "_topdir $HOME/rpmbuild" packaging/pkgtrans.spec >/dev/null
    cp ~/rpmbuild/RPMS/noarch/*.rpm /w/.build/rpm/
  ' rpm
  cp "$WORK"/rpm/*.rpm "$OUT/"
else
  echo "跳过：既没有 rpmbuild 也没有可用的 docker"
fi
[ -n "$(ls "$OUT"/*.rpm 2>/dev/null || true)" ] && \
  echo "✓ $OUT/$(ls "$OUT" | grep '\.rpm$' | head -1)"

echo
echo "==================== nix ===================="
# Nix 不产出可下载的包：nix build 的结果里 shebang 指向 /nix/store/...，
# 那个路径只在构建它的机器上存在，打成 tarball 发给别人是跑不起来的。
# Nix 用户本来也不下载 tarball，而是直接用仓库里的 flake：
#   nix run github:IrisDream-Cubic/pkgtrans -- keylist
# 所以这一步只做「flake 能不能构建 + 产物能不能跑」的验证。
if command -v nix >/dev/null 2>&1; then
  nix build ".#" --out-link "$WORK/nix-result" >/dev/null
  env -i "$WORK/nix-result/bin/pkgtrans" --version >/dev/null
  echo "✓ flake 构建通过（用 nix run github:IrisDream-Cubic/pkgtrans 安装）"
elif have_docker; then
  echo "本机没有 nix，改用 $NIX_IMAGE 验证 flake 可构建"
  docker_build "$NIX_IMAGE" '
    set -e
    mkdir -p /tmp/src
    cp -r pkgtrans default.nix flake.nix README.md LICENSE packaging /tmp/src/
    cd /tmp/src
    nix build .# --extra-experimental-features "nix-command flakes" \
        --no-write-lock-file ${NIX_OVERRIDE:+--override-input nixpkgs "$NIX_OVERRIDE"} >/dev/null
    env -i ./result/bin/pkgtrans --version >/dev/null
    env -i ./result/bin/pkgtrans help >/dev/null
    echo "  flake 构建通过，且 env -i 下能跑（shebang 已写死 store 路径）"
  ' nix
else
  echo "跳过：既没有 nix 也没有可用的 docker"
fi

rm -rf "$WORK"

echo
echo "==================== 产物 ===================="
ls -lh "$OUT"
