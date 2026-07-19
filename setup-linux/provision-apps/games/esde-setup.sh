#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# ES-DE Environment Setup
# (scaffolds emulator configurations, syncs RetroArch cores, & maps ROM directories)

# --- CONFIG ---
readonly EMULATION_BASE_DIR="/mnt/Z"

readonly LIBRETRO_NIGHTLY_BASE="https://buildbot.libretro.com/nightly/linux/x86_64/latest"
readonly RETROARCH_CORES=(
    "mesen_libretro.so.zip"
    "snes9x_libretro.so.zip"
    "genesis_plus_gx_libretro.so.zip"
    "mednafen_saturn_libretro.so.zip"
    "swanstation_libretro.so.zip"
    "pcsx_rearmed_libretro.so.zip"
    "mupen64plus_next_libretro.so.zip"
    "flycast_libretro.so.zip"
    "melonds_libretro.so.zip"
    "mame_libretro.so.zip"
    "fbneo_libretro.so.zip"
)

# ----------------------------------------------------------------
# --- Helper Functions ---
# ----------------------------------------------------------------

ensure_user_space() {
    if [[ "$(id -u)" -eq 0 ]]; then
        if [[ -n "${SUDO_USER:-}" ]]; then
            echo "[INFO] Root execution detected.  Dropping privileges to user: $SUDO_USER"
            exec sudo -H -u "$SUDO_USER" bash "$(realpath "$0")" "$@"
        else
            echo "[ERROR] Run as root without SUDO_USER." >&2
            exit 1
        fi
    fi
}

download_file() {
    local url="$1"
    local output="$2"
    if command -v wget > /dev/null 2>&1; then
        wget -q --show-progress "$url" -O "$output"
    elif command -v curl > /dev/null 2>&1; then
        curl -# -L "$url" -o "$output"
    else
        echo "[ERROR] Neither wget nor curl is installed." >&2
        return 1
    fi
}

safe_symlink() {
    local src="$1"
    local dest="$2"

    echo "Evaluating Symlink: $dest -> $src"

    # Fail early if source does not exist (evaluates both files & folders)
    if [ ! -e "$src" ]; then
        echo "  [Skip] Source data missing: $src"
        return
    fi

    # Scenario 1: Already a symlink
    if [ -L "$dest" ]; then
        local current_target
        current_target=$(readlink "$dest")
        if [ "$current_target" == "$src" ]; then
            echo "  [OK] Symlink is healthy and correct.  Skipped."
            return
        else
            echo "  [Fixing] Link points to wrong target.  Updating..."
            rm "$dest"
        fi

    # Scenario 2: Target exists (File or Directory)
    elif [ -e "$dest" ]; then
        # If an empty directory, can safely remove it
        if [ -d "$dest" ] && [ -z "$(ls -A "$dest")" ]; then
            echo "  [Cleanup] Removing empty directory: $dest"
            rmdir "$dest"
        else
            # Backup execution for directories or singular files
            local backup_path="${dest}-bak"
            if [ -e "$backup_path" ]; then
                backup_path="${dest}-bak-$(date +%s)"
            fi
            echo "  [Backup] Renaming existing target to '${backup_path##*/}'..."
            mv "$dest" "$backup_path"
        fi
    fi

    # Ensure parent folder of symlink exists (e.g., ~/.config/retroarch), then link
    mkdir -p "$(dirname "$dest")"
    ln -s "$src" "$dest"
    echo "  [Linked] Successfully mapped directory."
}

# ----------------------------------------------------------------
# --- Worker Functions ---
# ----------------------------------------------------------------

sync_retroarch_cores() {
    echo -e "\n=== Synchronizing RetroArch Cores ==="
    local core_dir="$HOME/.config/retroarch/cores"

    # Ensure unzip is available natively
    if ! command -v unzip > /dev/null 2>&1; then
        echo "[ERROR] 'unzip' is not installed.  Skipping core sync." >&2
        return 1
    fi

    # Destination folder must already exist for unzip's extract
    mkdir -p "$core_dir"

    for core_zip in "${RETROARCH_CORES[@]}"; do
        local core_so="${core_zip%.zip}" # Strip .zip extension
        local target_path="$core_dir/$core_so"

        if [[ ! -f "$target_path" ]]; then
            echo "  -> Downloading ${core_so}..."
            local tmp_zip="/tmp/${core_zip}"

            if download_file "$LIBRETRO_NIGHTLY_BASE/$core_zip" "$tmp_zip"; then
                unzip -qo "$tmp_zip" -d "$core_dir"
                rm -f "$tmp_zip"
            else
                echo "  [ERROR] Failed to fetch $core_zip"
                rm -f "$tmp_zip"
            fi
        else
            echo "  [OK] $core_so already exists."
        fi
    done
    echo "✅ Core synchronization complete."
}

map_symlinks() {
    echo -e "\n=== Automated ES-DE ROM Symlink Mapping ==="
    local source_rom_dir="$EMULATION_BASE_DIR/ROMs"
    local esde_rom_dir="$HOME/ROMs"

    if [ ! -d "$source_rom_dir" ]; then
        echo "  [WARN] Source ROM drive not found at: $source_rom_dir"
        return
    fi

    # Iterate through folders in the ROM drive, checking for bracket [system] designations
    for folder in "$source_rom_dir"/*; do
        if [ -d "$folder" ]; then
            local folder_name
            folder_name=$(basename "$folder")

            # Bash regex to capture whatever is inside the trailing brackets
            if [[ "$folder_name" =~ \[([^\]]+)\]$ ]]; then
                # Convert the captured match to lowercase
                local system_name="${BASH_REMATCH[1],,}"
                local system_dest="$esde_rom_dir/$system_name"

                safe_symlink "$folder" "$system_dest"
            fi
        fi
    done
}

# ----------------------------------------------------------------
# --- Main Orchestrator ---
# ----------------------------------------------------------------

main() {
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: $0"
        echo "Scaffolds native emulation directories, downloads libretro cores, and maps ES-DE symlinks."
        exit 0
    fi

    ensure_user_space

    echo "[INFO] Starting ES-DE Environment Setup for $USER..."

    sync_retroarch_cores
    map_symlinks

    echo -e "\n=== Mapping Centralized Emulation Folders ==="
    readonly local_config="$HOME/.config"
    readonly local_share="$HOME/.local/share"

    # RetroArch Overrides
    safe_symlink "$EMULATION_BASE_DIR/Saves" "$local_config/retroarch/saves"
    safe_symlink "$EMULATION_BASE_DIR/States" "$local_config/retroarch/states"
    safe_symlink "$EMULATION_BASE_DIR/BIOS/system" "$local_config/retroarch/system"

    # Standalone Emulator BIOS Overrides (forces native apps to share RetroArch's BIOS pool)
    safe_symlink "$EMULATION_BASE_DIR/BIOS/system" "$local_share/duckstation/bios"
    # - scph5500.bin (Japan)
    # - scph5501.bin (North America) (old: scph1001.bin)
    # - scph5502.bin (Europe) (old: scph7502.bin)
    safe_symlink "$EMULATION_BASE_DIR/BIOS/system/pcsx2/bios" "$local_config/PCSX2/bios"
    # - SCPH-39001.bin (or SCPH-70012.bin)
    safe_symlink "$EMULATION_BASE_DIR/BIOS/xbox" "$local_share/xemu/xemu/flash"
    # - mcpx_1.0.bin (Boot ROM)
    # - Complex_4627.bin (Flash ROM / BIOS)
    # - eeprom.bin (System EEPROM)
    # - xbox_hdd.qcow2 (Formatted hard drive image - placed in the same folder)

    echo -e "\n[INFO] ES-DE Environment Setup Complete!"
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/esde-setup.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/games/esde-setup.sh
