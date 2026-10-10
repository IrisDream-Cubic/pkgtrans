#!/bin/sh
# pkgtrans 通用安装脚本（不依赖任何包管理器，任意 Linux / macOS 都能用）
#
#   ./install.sh                 装到 /usr/local（需要写权限，可能要 sudo）
#   ./install.sh --user          装到 ~/.local（不需要 root，推荐）
#   ./install.sh --prefix /opt   自定义前缀
#   ./install.sh --uninstall     卸载
#
# 环境变量：PREFIX、DESTDIR（打包时用）

set -eu

SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX="${PREFIX:-/usr/local}"
DESTDIR="${DESTDIR:-}"
UNINSTALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --user)      PREFIX="$HOME/.local" ;;
    --prefix)    shift; PREFIX="${1:?--prefix 需要一个路径}" ;;
    --prefix=*)  PREFIX="${1#--prefix=}" ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help)   sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)           echo "未知参数：$1" >&2; exit 2 ;;
  esac
  shift
done

ROOT="$DESTDIR$PREFIX"
BIN="$ROOT/bin/pkgtrans"
ZSH="$ROOT/share/zsh/site-functions/_pkgtrans"
BASH="$ROOT/share/bash-completion/completions/pkgtrans"
DOC="$ROOT/share/doc/pkgtrans"

if [ "$UNINSTALL" -eq 1 ]; then
  rm -f "$BIN" "$ZSH" "$BASH"
  rm -rf "$DOC"
  echo "✓ 已卸载 $PREFIX 下的 pkgtrans"
  echo "  用户配置（密钥、缓存）保留在："
  echo "    ~/.config/pkgtrans/   ~/.cache/pkgtrans/"
  echo "  要一并删除：rm -rf ~/.config/pkgtrans ~/.cache/pkgtrans"
  echo "  别忘了从 shell 配置里删掉 '# >>> pkgtrans >>>' 那一段，或先跑 pkgtrans putes all"
  exit 0
fi

command -v python3 >/dev/null 2>&1 || {
  echo "✗ 需要 python3（3.9+）" >&2; exit 1; }

echo "安装到 $PREFIX"
install -Dm755 "$SRC/pkgtrans" "$BIN"
[ -f "$SRC/packaging/_pkgtrans" ] && \
  install -Dm644 "$SRC/packaging/_pkgtrans" "$ZSH"
[ -f "$SRC/packaging/pkgtrans.bash-completion" ] && \
  install -Dm644 "$SRC/packaging/pkgtrans.bash-completion" "$BASH"
[ -f "$SRC/README.md" ] && install -Dm644 "$SRC/README.md" "$DOC/README.md"
[ -f "$SRC/LICENSE" ] && install -Dm644 "$SRC/LICENSE" "$DOC/LICENSE"

echo "  ✓ $BIN"

case ":$PATH:" in
  *":$PREFIX/bin:"*) ;;
  *) echo "  ! $PREFIX/bin 不在 PATH 里，请自行加入" ;;
esac

echo
echo "装好了。接下来："
echo "  pkgtrans keyadd     添加 API Key"
echo "  pkgtrans setup      为 pacman / pamac / flatpak 启用翻译"
echo "  pkgtrans check      自检"
