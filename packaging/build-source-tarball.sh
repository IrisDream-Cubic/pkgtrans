#!/bin/sh
# 生成发布用源码 tarball：pkgtrans-<版本>.tar.gz
#
# 用 `git archive` 而不是 tar，好处是内容确定（只用被跟踪的文件、时间戳固定），
# 同样一个 commit 反复打出来的包 sha256 完全一样。
#
#   sh packaging/build-source-tarball.sh [版本] [输出目录]

set -eu

# ROOT 必须先算出来——下面的版本号默认值要用它去读主程序。
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VERSION="${1:-$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$ROOT/pkgtrans" | head -1)}"
OUT="${2:-dist}"
[ -n "$VERSION" ] || { echo "读不到版本号（$ROOT/pkgtrans）" >&2; exit 1; }
NAME="pkgtrans-$VERSION"

mkdir -p "$OUT"

if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$ROOT" archive --format=tar.gz --prefix="$NAME/" \
      -o "$OUT/$NAME.tar.gz" HEAD
else
  echo "不是 git 仓库，退回普通 tar" >&2
  tar -czf "$OUT/$NAME.tar.gz" -C "$ROOT" \
      --transform "s,^,$NAME/," \
      pkgtrans README.md LICENSE run_tests.py packaging .github
fi

echo "✓ $OUT/$NAME.tar.gz"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$OUT/$NAME.tar.gz"
else
  shasum -a 256 "$OUT/$NAME.tar.gz"
fi
