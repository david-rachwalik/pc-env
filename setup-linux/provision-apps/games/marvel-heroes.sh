#!/bin/bash
set -euo pipefail # Exit immediately on error

# ======== Sets up a standalone Marvel Heroes Omega client using Proton GE ========

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root or with sudo. Exiting..."
    exit 1
fi

# === Config ===
APP_NAME="marvel-heroes"
GAME_NAME="Marvel Heroes"
# !! IMPORTANT: Update this path to your game installation directory !!
GAME_DIR="/media/root/HDD-01/GameFiles/Marvel Heroes/UnrealEngine3/Binaries/Win64"
EXECUTABLE="MarvelHeroesOmega.exe"
# Use localhost for the server URL to connect to the local Docker container
# TODO: test if should add `-nosteam -robocopy` to front
LAUNCH_ARGS="-nostartupmovies -nosplash -siteconfigurl=http://127.0.0.1:8088/SiteConfig.xml"

# --- User and Path Configuration ---
SUDO_USER_NAME="${SUDO_USER:-$USER}"
SUDO_USER_HOME=$(getent passwd "$SUDO_USER_NAME" | cut -d: -f6)
LAUNCHER_DIR="$SUDO_USER_HOME/.local/bin"
LAUNCHER_SCRIPT="$LAUNCHER_DIR/play-$APP_NAME.sh"

# --- Proton GE Config ---
# This script assumes a proton-ge installation script exists.
# If not, you must manually install Proton GE.
PROTON_VERSION="9-27"
PROTON_NAME="GE-Proton${PROTON_VERSION}"
STEAM_DIR="$SUDO_USER_HOME/.steam/root"
STEAM_COMPAT_DIR="$STEAM_DIR/compatibilitytools.d"
PROTON_DIR="$STEAM_COMPAT_DIR/$PROTON_NAME"

# --- Wine/Proton Prefix ---
PROTON_PREFIX_DIR="$SUDO_USER_HOME/.proton-prefixes/$APP_NAME"

# --- Desktop Entry ---
DESKTOP_ENTRY_DIR="$SUDO_USER_HOME/.local/share/applications"
DESKTOP_ENTRY="$DESKTOP_ENTRY_DIR/$APP_NAME.desktop"
# You can place an icon.png in your GAME_DIR or specify a system icon
ICON_PATH="$GAME_DIR/icon.png"

# === Functions ===

create_launcher_script() {
    echo -e "\n=== Creating Launcher Script ==="
    mkdir -p "$LAUNCHER_DIR"
    cat >"$LAUNCHER_SCRIPT" <<EOF
#!/bin/bash
# This script launches Marvel Heroes using a specific Proton version.

export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_DIR"
export STEAM_COMPAT_DATA_PATH="$PROTON_PREFIX_DIR"

# Launch the game, pointing to the local server
"$PROTON_DIR/proton" run "$GAME_DIR/$EXECUTABLE" $LAUNCH_ARGS
EOF
    # Set ownership and permissions
    chown "$SUDO_USER_NAME:$SUDO_USER_NAME" "$LAUNCHER_SCRIPT"
    chmod +x "$LAUNCHER_SCRIPT"
    echo "✅ Launcher script created at: $LAUNCHER_SCRIPT"
}

create_desktop_entry() {
    echo -e "\n=== Creating Desktop Launcher ==="
    mkdir -p "$DESKTOP_ENTRY_DIR"
    cat >"$DESKTOP_ENTRY" <<EOF
[Desktop Entry]
Name=$GAME_NAME (Local Server)
Comment=Launch Marvel Heroes via Proton GE
Exec=$LAUNCHER_SCRIPT
Icon=${ICON_PATH}
Terminal=false
Type=Application
Categories=Game;
EOF
    # Set ownership and permissions
    chown "$SUDO_USER_NAME:$SUDO_USER_NAME" "$DESKTOP_ENTRY"
    chmod +x "$DESKTOP_ENTRY"
    echo "✅ Desktop entry created at: $DESKTOP_ENTRY"
}

# === Main ===
echo "Starting Marvel Heroes client setup for user: $SUDO_USER_NAME"

# Validation
if [ ! -d "$GAME_DIR" ] || [ ! -f "$GAME_DIR/$EXECUTABLE" ]; then
    echo "❌ Error: Game directory or executable not found at '$GAME_DIR/$EXECUTABLE'."
    echo "Please update the GAME_DIR variable in this script."
    exit 1
fi

if [ ! -d "$PROTON_DIR" ]; then
    echo "⚠️ Warning: Proton GE not found at '$PROTON_DIR'."
    echo "Please ensure Proton GE is installed correctly in the Steam compatibility tools directory."
    # Optionally, you could call your proton-ge installer script here.
    # bash "$(dirname "$0")/provision-apps/proton-ge.sh"
fi

create_launcher_script
create_desktop_entry

echo -e "\n🎉 All done! You can now launch '$GAME_NAME' from your applications menu."
echo "Make sure your local MHServerEmu Docker container is running before you launch the game."
exit 0

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/marvel-heroes.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/games/marvel-heroes.sh

# sudo rm ~/.local/bin/play-marvel-heroes.sh
# sudo rm ~/.local/share/applications/marvel-heroes.desktop
