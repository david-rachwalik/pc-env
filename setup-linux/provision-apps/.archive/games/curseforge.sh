#!/bin/bash
set -e # Exit immediately on error

APP_NAME="CurseForge"
APPIMAGE_URL="https://curseforge.overwolf.com/downloads/curseforge-latest-linux.AppImage"
APPIMAGE_NAME="CurseForge.AppImage"
INSTALL_DIR="$HOME/Applications"
APPIMAGE_PATH="$INSTALL_DIR/$APPIMAGE_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/curseforge.desktop"
ICON_URL="https://static.overwolf.com/curseforge/logo.png"
ICON_PATH="$INSTALL_DIR/curseforge.png"

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Ensure install directory exists
ensure_install_dir() {
    mkdir -p "$INSTALL_DIR"
}

# Download AppImage if missing or outdated
download_appimage() {
    if [ ! -f "$APPIMAGE_PATH" ]; then
        echo "[INFO] Downloading $APP_NAME AppImage..."
        curl -L "$APPIMAGE_URL" -o "$APPIMAGE_PATH"
        chmod +x "$APPIMAGE_PATH"
    else
        echo "[INFO] $APP_NAME AppImage already exists."
    fi
}

# Download icon
download_icon() {
    if [ ! -f "$ICON_PATH" ]; then
        echo "[INFO] Downloading $APP_NAME icon..."
        curl -L "$ICON_URL" -o "$ICON_PATH"
    fi
}

# Create desktop shortcut
create_desktop_entry() {
    echo "[INFO] Creating desktop entry..."
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=CurseForge
Comment=CurseForge Mod Manager
Exec=$APPIMAGE_PATH
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Game;Utility;
EOF
    update-desktop-database "$(dirname "$DESKTOP_FILE")" || true
}

# Main install routine
main() {
    echo "Starting $APP_NAME setup..."
    ensure_install_dir
    download_appimage
    download_icon
    create_desktop_entry
    echo "✅ $APP_NAME installed! You can launch it from your Start menu or run:"
    echo "   $APPIMAGE_PATH"
}

main "$@"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/curseforge.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/games/curseforge.sh
