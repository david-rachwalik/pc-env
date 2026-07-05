#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# ======== Sets up a standalone Marvel Heroes Omega client using Proton GE ========

# --- Config ---
APP_NAME="marvel-heroes"
GAME_NAME="Marvel Heroes"
# !! IMPORTANT: Update this path to your game installation directory !!
GAME_DIR="/media/root/HDD-01/GameFiles/Marvel Heroes/UnrealEngine3/Binaries/Win64"
EXECUTABLE="MarvelHeroesOmega.exe"
LAUNCH_ARGS="-nostartupmovies -nosplash -siteconfigurl=http://127.0.0.1:8088/SiteConfig.xml"

PROTON_VERSION="9-27"
PROTON_NAME="GE-Proton${PROTON_VERSION}"

# ----------------------------------------------------------------
# --- Helper Functions ---
# ----------------------------------------------------------------

ensure_user_space() {
    if [[ "$(id -u)" -eq 0 ]]; then
        if [[ -n "${SUDO_USER:-}" ]]; then
            echo "[INFO] Root execution detected. Dropping privileges to user: $SUDO_USER"
            exec sudo -H -u "$SUDO_USER" bash "$(realpath "$0")" "$@"
        else
            echo "[ERROR] Run as root without SUDO_USER." >&2
            exit 1
        fi
    fi
}

atomic_write() {
    local dest="$1"
    local mode="$2"
    local tmp
    tmp="$(mktemp "${dest}.XXXXXXXX")"
    cat > "$tmp"
    chmod "$mode" "$tmp"
    if [[ -f "$dest" ]] && cmp -s "$tmp" "$dest"; then
        rm -f "$tmp"
        return 0
    fi
    mv -f "$tmp" "$dest"
}

# ----------------------------------------------------------------
# --- Worker Functions ---
# ----------------------------------------------------------------

create_launcher_script() {
    local launcher_script="$1"
    local steam_dir="$2"
    local proton_prefix_dir="$3"
    local proton_dir="$4"

    echo "=== Creating Launcher Script ==="
    mkdir -p "$(dirname "$launcher_script")"

    atomic_write "$launcher_script" 755 << EOF
#!/usr/bin/env bash
# This script launches Marvel Heroes using a specific Proton version.

export STEAM_COMPAT_CLIENT_INSTALL_PATH="$steam_dir"
export STEAM_COMPAT_DATA_PATH="$proton_prefix_dir"

"$proton_dir/proton" run "$GAME_DIR/$EXECUTABLE" $LAUNCH_ARGS
EOF
    echo "✅ Launcher script created at: $launcher_script"
}

create_desktop_entry() {
    local desktop_entry="$1"
    local launcher_script="$2"
    local icon_path="$3"

    echo "=== Creating Desktop Launcher ==="
    mkdir -p "$(dirname "$desktop_entry")"

    atomic_write "$desktop_entry" 644 << EOF
[Desktop Entry]
Name=$GAME_NAME (Local Server)
Comment=Launch Marvel Heroes via Proton GE
Exec=$launcher_script
Icon=${icon_path}
Terminal=false
Type=Application
Categories=Game;
EOF
    echo "✅ Desktop entry created at: $desktop_entry"
}

# ----------------------------------------------------------------
# --- Main Orchestrator ---
# ----------------------------------------------------------------

main() {
    ensure_user_space
    echo "Starting Marvel Heroes client setup for user: $USER"

    # --- Path Resolution ---
    local launcher_dir="$HOME/.local/bin"
    local launcher_script="$launcher_dir/play-$APP_NAME.sh"

    local steam_dir="$HOME/.steam/root"
    local steam_compat_dir="$steam_dir/compatibilitytools.d"
    local proton_dir="$steam_compat_dir/$PROTON_NAME"
    local proton_prefix_dir="$HOME/.proton-prefixes/$APP_NAME"

    local desktop_entry_dir="$HOME/.local/share/applications"
    local desktop_entry="$desktop_entry_dir/$APP_NAME.desktop"
    local icon_path="$GAME_DIR/icon.png"

    # --- Validation ---
    if [ ! -d "$GAME_DIR" ] || [ ! -f "$GAME_DIR/$EXECUTABLE" ]; then
        echo "❌ Error: Game directory or executable not found at '$GAME_DIR/$EXECUTABLE'."
        exit 1
    fi

    if [ ! -d "$proton_dir" ]; then
        echo "⚠️ Warning: Proton GE not found at '$proton_dir'."
    fi

    # --- Execution ---
    create_launcher_script "$launcher_script" "$steam_dir" "$proton_prefix_dir" "$proton_dir"
    create_desktop_entry "$desktop_entry" "$launcher_script" "$icon_path"

    echo -e "\n🎉 All done! You can now launch '$GAME_NAME' from your applications menu."
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/marvel-heroes.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/games/marvel-heroes.sh

# sudo rm ~/.local/bin/play-marvel-heroes.sh
# sudo rm ~/.local/share/applications/marvel-heroes.desktop
