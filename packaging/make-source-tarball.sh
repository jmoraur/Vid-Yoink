#!/usr/bin/env bash
# Build the RPM source tarball: tracked files (git archive) plus the pre-built
# frontend folded in, because rpmbuild runs offline and can't npm install.
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)
SPEC_VERSION=$(sed -n 's/^Version: *//p' packaging/yoink.spec)
if [ "$VERSION" != "$SPEC_VERSION" ]; then
    echo "version mismatch: pyproject.toml $VERSION vs yoink.spec $SPEC_VERSION" >&2
    exit 1
fi

OUT="${1:-$HOME/rpmbuild/SOURCES}"
mkdir -p "$OUT"

npm ci --prefix frontend
npm run build --prefix frontend  # emits yoink/static/ (vite outDir)

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
git archive --format=tar --prefix="yoink-$VERSION/" HEAD | tar -x -C "$STAGE"
cp -r yoink/static "$STAGE/yoink-$VERSION/yoink/static"
tar -C "$STAGE" -czf "$OUT/yoink-$VERSION.tar.gz" "yoink-$VERSION"

echo "wrote $OUT/yoink-$VERSION.tar.gz"
