#!/usr/bin/env bash
set -euo pipefail

SRC=$(cd "$(dirname "$0")/.."; pwd)

install -Dm644 "$SRC/packaging/yoink.desktop" \
        "$HOME/.local/share/applications/yoink.desktop"
install -Dm644 "$SRC/packaging/icons/yoink.svg" \
        "$HOME/.local/share/icons/hicolor/scalable/apps/yoink.svg"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Installed."
echo "If KRunner doesn't pick it up immediately, log out + back in once."
