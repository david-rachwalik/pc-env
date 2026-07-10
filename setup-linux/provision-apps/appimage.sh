#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# ----------------------------------------------------------------
# --- Configuration ---
# ----------------------------------------------------------------

# Pipe-separated array format: "id|Name|Categories|fallback_icon|skip_on_minimal"
declare -a APPIMAGES=(
    "obsidian|Obsidian|Office;|obsidian|false"
    "kdenlive|Kdenlive|Video;AudioVideo;Multimedia;|kdenlive|true"
    "protonup-qt|ProtonUp-Qt|Utility;|system-software-update|false"
    "es-de|EmulationStation DE|Game;Emulator;|applications-games|false"
    # "retroarch|RetroArch|Game;Emulator;|applications-games|false"  # using apt instead
    "xemu|Xemu|Game;Emulator;|applications-games|false"
    "duckstation|DuckStation|Game;Emulator;|applications-games|false"
    "pcsx2|PCSX2|Game;Emulator;|applications-games|false"
    "rpcs3|RPCS3|Game;Emulator;|applications-games|false"
)

# Dynamically resolve latest download URLs (only called if installation is needed)
get_download_url() {
    local id="$1"
    case "$id" in
        obsidian)
            # Filter out arm64 releases and guarantee a single string return
            curl -sL https://api.github.com/repos/obsidianmd/obsidian-releases/releases/latest | jq -r '.assets[] | select(.name | endswith(".AppImage")) | .browser_download_url' | grep -iv 'arm64' | head -n 1 || true
            ;;
        kdenlive)
            local kden_dir kden_file
            kden_dir=$(curl -s https://download.kde.org/stable/kdenlive/ | grep -oP '(?<=href=")[0-9]+\.[0-9]+(?=/")' | sort -V | tail -1)
            kden_file=$(curl -s "https://download.kde.org/stable/kdenlive/$kden_dir/linux/" | grep -oP 'kdenlive-\d+\.\d+\.\d+-x86_64\.AppImage' | sort -V | tail -1)
            echo "https://download.kde.org/stable/kdenlive/$kden_dir/linux/$kden_file"
            ;;
        protonup-qt)
            curl -sL https://api.github.com/repos/DavidoTek/ProtonUp-Qt/releases/latest | jq -r '.assets[] | select(.name | endswith(".AppImage")) | .browser_download_url' | head -n 1 || true
            ;;
        es-de)
            echo "https://gitlab.com/es-de/emulationstation-de/-/package_files/210210324/download"
            ;;
        # retroarch)
        #     # RetroArch does not attach AppImages to their GitHub release tags
        #     # We fetch continuous build directly from the LibRetro buildbot
        #     echo "https://buildbot.libretro.com/nightly/linux/x86_64/RetroArch-Linux-x86_64.AppImage"
        #     ;;
        xemu)
            curl -sL https://api.github.com/repos/xemu-project/xemu/releases/latest | jq -r '.assets[] | select(.name | endswith(".AppImage")) | .browser_download_url' | head -n 1 || true
            ;;
        duckstation)
            curl -sL https://api.github.com/repos/stenzek/duckstation/releases/latest | jq -r '.assets[] | select(.name | endswith(".AppImage")) | .browser_download_url' | head -n 1 || true
            ;;
        pcsx2)
            curl -sL https://api.github.com/repos/PCSX2/pcsx2/releases/latest | jq -r '.assets[] | select(.name | endswith(".AppImage")) | .browser_download_url' | head -n 1 || true
            ;;
        rpcs3)
            # Fetch the raw releases array from their x86_64 repo and grab the newest AppImage
            curl -sL https://api.github.com/repos/RPCS3/rpcs3-binaries-linux/releases | jq -r '.[0].assets[]? | select(.name | endswith(".AppImage")) | .browser_download_url' | head -n 1 || true
            ;;
        *)
            echo ""
            ;;
    esac
}

# ----------------------------------------------------------------
# --- Helper Functions ---
# ----------------------------------------------------------------

# Self-demote if running as root so files natively belong to the user
ensure_user_space() {
    if [[ "$(id -u)" -eq 0 ]]; then
        if [[ -n "${SUDO_USER:-}" ]]; then
            echo "[INFO] Root execution detected.  Dropping privileges to user: $SUDO_USER"
            # -H flag ensures $HOME environment variable is updated to user's home dir
            exec sudo -H -u "$SUDO_USER" "$0" "$@"
        else
            echo "[ERROR] Run as root without SUDO_USER.  Cannot determine target user space." >&2
            exit 1
        fi
    fi
}

ensure_dirs() {
    mkdir -p "$@"
}

atomic_write() {
    local dest="$1"
    local mode="$2"
    local tmp
    tmp="$(mktemp "${dest}.XXXXXXXX")"
    cat > "$tmp"
    chmod "$mode" "$tmp"

    # Only overwrite if contents or permissions differ
    if [[ -f "$dest" ]] && cmp -s "$tmp" "$dest"; then
        local current_mode
        current_mode=$(stat -c "%a" "$dest" 2> /dev/null || echo "000")
        if [[ "$current_mode" == "$mode" ]]; then
            rm -f "$tmp" # State matches perfectly; silently discard temp
            return 0
        fi
    fi

    mv -f "$tmp" "$dest"
}

update_databases() {
    if command -v update-desktop-database > /dev/null 2>&1; then
        # Update user-space desktop database specifically, silencing third-party warnings
        update-desktop-database "$HOME/.local/share/applications" > /dev/null 2>&1 || true
    fi
}

# ----------------------------------------------------------------
# --- Worker Functions ---
# ----------------------------------------------------------------

download_appimage() {
    local url="$1"
    local dest="$2"
    local tmp

    echo "[INFO] Downloading AppImage..."
    tmp="$(mktemp "${dest}.XXXXXX")"
    trap "rm -f '$tmp'" EXIT INT TERM

    if command -v curl > /dev/null 2>&1; then
        curl -sL --fail --show-error --output "$tmp" "$url"
    elif command -v wget > /dev/null 2>&1; then
        wget -q -O "$tmp" "$url"
    else
        echo "[ERROR] Neither curl nor wget available" >&2
        exit 1
    fi

    chmod +x "$tmp"
    mv -f "$tmp" "$dest"

    trap - EXIT INT TERM
    echo "[INFO] Downloaded to $dest"
}

extract_icon_best_effort() {
    local appimage_path="$1"
    local icon_path="$2"

    if [[ ! -f "$appimage_path" || -f "$icon_path" ]]; then
        return 0
    fi

    echo "[INFO] Attempting to extract icon..."
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap "rm -rf '$tmp_dir'" EXIT INT TERM

    pushd "$tmp_dir" > /dev/null || return 1

    if "$appimage_path" --appimage-extract > /dev/null 2>&1; then
        if [[ -f squashfs-root/.DirIcon ]]; then
            cp squashfs-root/.DirIcon "$icon_path" 2> /dev/null || true
        else
            local found
            found="$(find squashfs-root -type f \( -iname '*.png' -o -iname '*.ico' \) | head -n1 || true)"
            [[ -n "$found" ]] && cp "$found" "$icon_path" 2> /dev/null || true
        fi
    elif command -v bsdtar > /dev/null 2>&1; then
        local candidate
        candidate="$(bsdtar -tf "$appimage_path" | grep -Ei '\.png$|\.ico$' | head -n1 || true)"
        if [[ -n "$candidate" ]]; then
            bsdtar -xf "$appimage_path" "$candidate"
            mv "$candidate" "$icon_path" 2> /dev/null || true
        fi
    fi

    # Convert sneaky ICO files inside PNG wrappers into actual PNG objects
    if [[ -f "$icon_path" ]] && file "$icon_path" | grep -iq 'ico' && command -v convert > /dev/null 2>&1; then
        local tmp_img
        tmp_img="$(mktemp)"
        if convert "${icon_path}[0]" -resize 256x256 "$tmp_img"; then
            mv -f "$tmp_img" "$icon_path"
            chmod 644 "$icon_path"
        else
            rm -f "$tmp_img"
        fi
    fi

    popd > /dev/null || return 1
    rm -rf "$tmp_dir"
    trap - EXIT INT TERM
}

create_wrapper() {
    local wrapper_path="$1"
    local appimage_path="$2"

    atomic_write "$wrapper_path" 755 << EOF
#!/usr/bin/env sh
exec "$appimage_path" "\$@"
EOF
}

create_desktop_entry() {
    local desktop_path="$1"
    local name="$2"
    local wrapper_path="$3"
    local icon_path="$4"
    local fallback_icon="$5"
    local categories="$6"

    local final_icon="$fallback_icon"
    [[ -f "$icon_path" ]] && final_icon="$icon_path"

    atomic_write "$desktop_path" 644 << EOF
[Desktop Entry]
Name=$name
Comment=$name
TryExec=$wrapper_path
Exec=$wrapper_path %U
Icon=$final_icon
Terminal=false
Type=Application
Categories=$categories
StartupNotify=true
EOF
}

provision_app() {
    local config_string="$1"
    IFS='|' read -r id name categories fallback_icon skip_on_minimal <<< "$config_string"

    if [[ "$MINIMAL_MODE" == true && "$skip_on_minimal" == true ]]; then
        echo "[INFO] Skipping $name (Minimal Mode)."
        return 0
    fi

    # Local user-space variables
    local install_dir="$HOME/.local/share/$id"
    local wrapper_path="$HOME/.local/bin/$id"
    local desktop_path="$HOME/.local/share/applications/${id}.desktop"
    local appimage_path="$install_dir/${id}.AppImage"
    local icon_path="${install_dir}/icon.png"

    # Evaluate if AppImage exists before installing
    if [[ ! -f "$appimage_path" ]]; then
        echo "--------------------------------------------------------"
        echo "[INFO] Installing AppImage binary for $name..."

        local url
        url=$(get_download_url "$id")
        if [[ -z "$url" ]]; then
            echo "[ERROR] Failed to resolve download URL for $id." >&2
            return 1
        fi

        ensure_dirs "$install_dir"
        download_appimage "$url" "$appimage_path"
        extract_icon_best_effort "$appimage_path" "$icon_path"
    else
        echo "[INFO] $name binary exists.  Verifying system links..."
    fi

    # Verify wrappers and .desktop entries (only writes if changed)
    ensure_dirs "$(dirname "$wrapper_path")" "$(dirname "$desktop_path")"
    create_wrapper "$wrapper_path" "$appimage_path"
    create_desktop_entry "$desktop_path" "$name" "$wrapper_path" "$icon_path" "$fallback_icon" "$categories"

    echo "✅ Successfully provisioned $name"
}

deprovision_app() {
    local target_id="$1"
    local found=false

    for config_string in "${APPIMAGES[@]}"; do
        IFS='|' read -r id name categories fallback_icon skip_on_minimal <<< "$config_string"
        if [[ "$id" == "$target_id" || "$target_id" == "all" ]]; then
            found=true
            echo "--------------------------------------------------------"
            echo "[INFO] Removing $name..."

            local install_dir="$HOME/.local/share/$id"
            local wrapper_path="$HOME/.local/bin/$id"
            local desktop_path="$HOME/.local/share/applications/${id}.desktop"

            # Remove all traces
            rm -rf "$install_dir" "$wrapper_path" "$desktop_path"
            echo "✅ Successfully removed $name"
        fi
    done

    if [[ "$found" == false ]]; then
        echo "[ERROR] Unknown AppImage ID: $target_id"
    fi
}

# ----------------------------------------------------------------
# --- Main Orchestrator ---
# ----------------------------------------------------------------

MINIMAL_MODE=false
REMOVE_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -m | --minimal)
            MINIMAL_MODE=true
            shift
            ;;
        -r | --remove)
            REMOVE_ID="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

main() {
    ensure_user_space

    # Handle Removal Mode
    if [[ -n "$REMOVE_ID" ]]; then
        echo "[INFO] Starting AppImage removal process for user: $USER"
        deprovision_app "$REMOVE_ID"
        update_databases
        echo "--------------------------------------------------------"
        echo "[INFO] Removal completed!"
        exit 0
    fi

    # Handle Provisioning Mode
    echo "[INFO] Starting AppImages provisioning for user: $USER"

    for app in "${APPIMAGES[@]}"; do
        provision_app "$app"
    done

    update_databases

    echo "--------------------------------------------------------"
    echo "[INFO] AppImages provisioning completed!"
}

main "$@"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/appimage.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/appimage.sh

# To completely uninstall an app:
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/appimage.sh --remove <id>
