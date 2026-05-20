#!/usr/bin/env bash
set -euo pipefail

# Emulation Station, Desktop Edition (ES-DE) (https://es-de.org)
# (user install of AppImage for proper self-updating)

APPIMAGE_URL="https://gitlab.com/es-de/emulationstation-de/-/package_files/210210324/download"

# Dynamically find the path to the generic installer script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALLER="$SCRIPT_DIR/../../install-appimage.sh"

echo "[INFO] Installing EmulationStation DE to user space..."

# Call the generic script directly (no sudo needed)
bash "$INSTALLER" \
  --name "EmulationStation DE" \
  --id "es-de" \
  --url "$APPIMAGE_URL" \
  --categories "Game;Emulator;" \
  --extract-icon

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/es-de.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/games/es-de.sh
