#!/bin/bash
set -e # Exit immediately on error

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ "$(id -u)" -ne 0 ]]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# https://github.com/patrikx3/onenote
# https://www.corifeus.com/onenote

APP_NAME="p3x-onenote"
APP_VERSION="2025.4.124" # TODO: Check for latest version
APP_IMAGE_URL="https://github.com/patrikx3/onenote/releases/download/v$APP_VERSION/$APP_NAME-$APP_VERSION.AppImage"
INSTALL_DIR="/opt/$APP_NAME"
DESKTOP_ENTRY="/usr/share/applications/$APP_NAME.desktop"

# ----------------------------------------------------------------
# ----------------------------------------------------------------

echo "Starting OneNote setup..."

# Ensure install directory exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Creating OneNote directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
fi

# Download AppImage if not already present
if [[ ! -f "$INSTALL_DIR/$APP_NAME.AppImage" ]]; then
    echo "Downloading $APP_NAME..."
    curl -L "$APP_IMAGE_URL" -o "$INSTALL_DIR/$APP_NAME.AppImage"
    chmod +x "$INSTALL_DIR/$APP_NAME.AppImage"
else
    echo "$APP_NAME is already downloaded.  Skipping download."
fi

# Create a desktop entry if needed
if ! grep -q "Exec=$INSTALL_DIR/$APP_NAME.AppImage" "$DESKTOP_ENTRY" 2>/dev/null; then
    echo "Creating desktop entry..."
    cat <<EOF >"$DESKTOP_ENTRY"
[Desktop Entry]
Name=P3X OneNote
Exec=$INSTALL_DIR/$APP_NAME.AppImage
Icon=applications-office
Type=Application
Categories=Office;
EOF
    chmod +x "$DESKTOP_ENTRY"
else
    echo "desktop entry already exists."
fi

echo "Installation complete.  You can run P3X OneNote from your applications menu or by executing: $INSTALL_DIR/$APP_NAME.AppImage"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/archive/onenote.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/archive/onenote.sh
