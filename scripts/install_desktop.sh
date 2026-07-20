#!/usr/bin/env bash
# Per-user desktop install for a dev checkout: points Exec= at this checkout's
# launcher. The RPM installs the system-wide equivalent (Exec=yoink-app).
set -euo pipefail

SRC=$(cd "$(dirname "$0")/.."; pwd)

install -Dm644 "$SRC/packaging/yoink.desktop" \
        "$HOME/.local/share/applications/yoink.desktop"
install -Dm644 "$SRC/packaging/icons/yoink.svg" \
        "$HOME/.local/share/icons/hicolor/scalable/apps/yoink.svg"

sed -i "s|^Exec=.*|Exec=$SRC/scripts/yoink-app|" \
    "$HOME/.local/share/applications/yoink.desktop"

update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Installed."
echo "If KRunner doesn't pick it up immediately, log out + back in once."
