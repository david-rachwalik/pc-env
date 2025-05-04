#!/bin/bash
set -euo pipefail # Exit immediately on error

# ======== Sets up everything for Marvel Heroes Omega client ========

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# === Config ===
APP_NAME="marvel-heroes"
GAME_NAME="Marvel Heroes"
GAME_DIR="/media/root/HDD-01/GameFiles/Marvel Heroes/UnrealEngine3/Binaries/Win64"
EXECUTABLE="MarvelHeroesOmega.exe"
LAUNCH_ARGS="-siteconfigurl=mhtahiti.com/SiteConfig.xml -nostartupmovies -nosplash"
SUDO_USER_HOME="/home/${SUDO_USER:-$USER}"
LAUNCHER_DIR="$SUDO_USER_HOME/.local/bin"
LAUNCHER_SCRIPT="$LAUNCHER_DIR/play-marvel-heroes.sh"

# Proton GE config
PROTON_VERSION="9-27"
PROTON_NAME="GE-Proton${PROTON_VERSION}" # extracted folder name
STEAM_DIR="$SUDO_USER_HOME/.steam/root"
STEAM_COMPAT_DIR="$STEAM_DIR/compatibilitytools.d"
PROTON_DIR="$STEAM_COMPAT_DIR/$PROTON_NAME"

# Desktop entry location (user-level)
DESKTOP_ENTRY="$SUDO_USER_HOME/.local/share/applications/$APP_NAME.desktop"
ICON_PATH="$GAME_DIR/icon.png"

# Proton compatibility data (Windows emulation)
PROTON_PREFIX_DIR="$SUDO_USER_HOME/.proton/$APP_NAME"
PROTON_FIXES_DIR="$SUDO_USER_HOME/.config/protonfixes"

# === Functions ===

setup_wineprefix() {
    echo -e "\n=== Setting up Wine Prefix ==="

    export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR"
    export STEAM_COMPAT_DATA_PATH="$PROTON_PREFIX_DIR"

    mkdir -p "$PROTON_PREFIX_DIR" "$PROTON_FIXES_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$PROTON_PREFIX_DIR"
    chown -R $SUDO_USER:$SUDO_USER "$PROTON_FIXES_DIR"

    "$PROTON_DIR/proton" run wineboot

    echo "✅ Wine prefix initialized at $PROTON_PREFIX_DIR"
}

create_launcher_script() {
    echo -e "\n=== Creating Launcher Script ==="

    mkdir -p "$LAUNCHER_DIR"

    cat >"$LAUNCHER_SCRIPT" <<EOF
#!/bin/bash
export WINEPREFIX="$PROTON_PREFIX_DIR"
export STEAM_COMPAT_DATA_PATH="$PROTON_PREFIX_DIR"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR"

"$PROTON_DIR/proton" run "$GAME_DIR/$EXECUTABLE" $LAUNCH_ARGS
EOF

    chmod +x "$LAUNCHER_SCRIPT"
    echo "✅ Launcher script created at: $LAUNCHER_SCRIPT"
}

create_desktop_entry() {
    echo "\n=== Creating Desktop Launcher ==="

    mkdir -p "$(dirname "$DESKTOP_ENTRY")"

    cat <<EOF >"$DESKTOP_ENTRY"
[Desktop Entry]
Name=${GAME_NAME} (MHServerEmu)
Comment=Launch ${GAME_NAME} via Proton GE
Exec=$LAUNCHER_SCRIPT
Terminal=false
Icon=${ICON_PATH:-application-x-executable}
Type=Application
Categories=Game;
StartupNotify=true
EOF

    chmod +x "$DESKTOP_ENTRY"
    echo "✅ Desktop entry created at: $DESKTOP_ENTRY"

    # Validate desktop entry
    if command -v desktop-file-validate &>/dev/null; then
        echo "Validating desktop entry..."
        desktop-file-validate "$DESKTOP_ENTRY" && echo "✅ Desktop entry validation passed." || echo "⚠️ Desktop entry validation failed."
    else
        echo "ℹ️ 'desktop-file-validate' not found.  Skipping validation."
    fi
}

# === Main ===

# Check if Proton is already installed
if [ ! -d "$PROTON_DIR" ]; then
    bash "$(dirname "$0")/provision-apps/proton-ge.sh"
else
    echo "Proton GE already installed at: $PROTON_DIR"
fi

# Set up Wine prefix if needed
if [ ! -d "$PROTON_PREFIX_DIR" ]; then
    setup_wineprefix
else
    echo "Wine Prefix already exists at: $PROTON_PREFIX_DIR"
fi

# Check if game launch script exists
if [ ! -f "$LAUNCHER_SCRIPT" ]; then
    create_launcher_script
else
    echo "Launcher script already exists at: $LAUNCHER_SCRIPT"
fi

# Check if desktop entry exists
if [ ! -f "$DESKTOP_ENTRY" ]; then
    create_desktop_entry
else
    echo "Desktop entry already exists at: $DESKTOP_ENTRY"
fi

echo "\n🎉 All done!  You can now launch '$GAME_NAME' from your applications menu."
exit 0

# sudo chmod +x ~/Repos/pc-env/setup-linux/setup-marvel-heroes.sh
# sudo bash ~/Repos/pc-env/setup-linux/setup-marvel-heroes.sh

# sudo rm ~/.local/bin/play-marvel-heroes.sh
# sudo rm ~/.local/share/applications/marvel-heroes.desktop
