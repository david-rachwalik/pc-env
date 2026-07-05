#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# Subtitle Edit installer for Linux Mint
# https://github.com/SubtitleEdit/subtitleedit

SE_VERSION="4.0.13"
SE_FILENAME="SE4013.zip"
SE_URL="https://github.com/SubtitleEdit/subtitleedit/releases/download/${SE_VERSION}/${SE_FILENAME}"
APP_NAME="Subtitle Edit"

# ----------------------------------------------------------------
# --- Helper Functions ---
# ----------------------------------------------------------------

ensure_user_space() {
    if [[ "$(id -u)" -eq 0 ]]; then
        if [[ -n "${SUDO_USER:-}" ]]; then
            echo "[INFO] Root execution detected. Dropping privileges to user: $SUDO_USER"
            exec sudo -H -u "$SUDO_USER" bash "$(realpath "$0")" "$@"
        else
            echo "[ERROR] Run as root without SUDO_USER. Cannot determine target user space." >&2
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

install_subtitle_edit() {
    local install_dir="$1"
    local app_dir="$2"

    if [ ! -d "$app_dir" ]; then
        echo "[INFO] Downloading $APP_NAME $SE_VERSION..."
        mkdir -p "$install_dir"
        local tmp_zip="/tmp/$SE_FILENAME"
        wget -q "$SE_URL" -O "$tmp_zip"

        echo "[INFO] Extracting $APP_NAME..."
        unzip -q "$tmp_zip" -d "$app_dir"
        rm -f "$tmp_zip"
    else
        echo "[INFO] $APP_NAME binary already exists.  Verifying system links..."
    fi
}

create_desktop_launcher() {
    local desktop_entry="$1"
    local app_dir="$2"

    echo "[INFO] Creating Desktop Launcher..."
    mkdir -p "$(dirname "$desktop_entry")"

    atomic_write "$desktop_entry" 644 << EOF
[Desktop Entry]
Name=$APP_NAME
Comment=Open Source Subtitle Editor
Exec=mono "$app_dir/SubtitleEdit.exe"
Icon=$app_dir/Icons/mpc-hc.png
Terminal=false
Type=Application
Categories=AudioVideo;Video;Utility;
EOF
}

update_desktop_db() {
    if command -v update-desktop-database > /dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications" > /dev/null 2>&1 || true
    fi
}

# ----------------------------------------------------------------
# --- Main Orchestrator ---
# ----------------------------------------------------------------

main() {
    ensure_user_space

    local install_dir="$HOME/.local/share/subtitleedit"
    local app_dir="$install_dir/SubtitleEdit"
    local desktop_entry="$HOME/.local/share/applications/subtitleedit.desktop"

    install_subtitle_edit "$install_dir" "$app_dir"
    create_desktop_launcher "$desktop_entry" "$app_dir"
    update_desktop_db

    echo "✅ Successfully provisioned $APP_NAME"
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/subtitleedit.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/subtitleedit.sh
