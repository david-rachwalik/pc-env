#!/bin/bash
set -e # Exit immediately on error

# Ensure the script is run as root (or sudo privileges)
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# Kdenlive: Free and Open Source Video Editor (https://kdenlive.org/en)

APP_NAME="kdenlive"
INSTALL_DIR="/opt/$APP_NAME"
APP_IMAGE_PATH="$INSTALL_DIR/$APP_NAME.AppImage"
# DESKTOP_ENTRY="$HOME/.local/share/applications/$APP_NAME.desktop"
DESKTOP_ENTRY="/usr/share/applications/$APP_NAME.desktop" # system-wide

# ----------------------------------------------------------------
# ----------------------------------------------------------------

echo "Starting $APP_NAME setup..."

# Ensure install directory exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Creating $APP_NAME directory: $INSTALL_DIR"
    install -d -m 755 "$INSTALL_DIR" # (mkdir+chmod)
fi

# Download AppImage if not already present
if [[ ! -f "$APP_IMAGE_PATH" ]]; then
    echo "Downloading $APP_NAME..."

    # APP_VERSION="24.12.3" # TODO: Check for latest version
    # APP_IMAGE_URL="https://download.kde.org/stable/$APP_NAME/24.12/linux/$APP_NAME-$APP_VERSION-x86_64.AppImage"

    # Get the latest directory version (e.g. "24.12")
    LATEST_DIR=$(curl -s https://download.kde.org/stable/kdenlive/ | grep -oP '(?<=href=")[0-9]+\.[0-9]+(?=/")' | sort -V | tail -1)
    # Go into that folder and find the actual AppImage filename (e.g. "kdenlive-24.12.3-x86_64.AppImage")
    LATEST_FILENAME=$(curl -s "https://download.kde.org/stable/kdenlive/$LATEST_DIR/linux/" | grep -oP 'kdenlive-\d+\.\d+\.\d+-x86_64\.AppImage' | sort -V | tail -1)
    APP_VERSION=$(echo "$LATEST_FILENAME" | grep -oP '\d+\.\d+\.\d+')
    APP_IMAGE_URL="https://download.kde.org/stable/$APP_NAME/$LATEST_DIR/linux/$LATEST_FILENAME"
    echo "Successfully downloaded $APP_NAME v$APP_VERSION"

    curl -L "$APP_IMAGE_URL" -o "$APP_IMAGE_PATH"
    chmod +x "$APP_IMAGE_PATH"
else
    echo "$APP_NAME is already downloaded.  Skipping download."
fi

# Create a desktop entry if needed
if ! grep -q "Exec=$APP_IMAGE_PATH" "$DESKTOP_ENTRY" 2>/dev/null; then
    echo "Creating desktop entry..."
    cat <<EOF >"$DESKTOP_ENTRY"
[Desktop Entry]
Name=Kdenlive
Exec=$APP_IMAGE_PATH
Icon=$APP_NAME
Type=Application
Categories=Video;AudioVideo;Multimedia;
EOF
    chmod +x "$DESKTOP_ENTRY"
else
    echo "Desktop entry already exists.  Skipping creation."
fi

echo "Installation complete.  Launch $APP_NAME from your applications menu or via: $APP_IMAGE_PATH"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/kdenlive.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/kdenlive.sh
