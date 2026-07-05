#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# Proton GE
# https://github.com/gloriouseggroll/proton-ge-custom/releases

# --- CONFIG ---
PROTON_VERSION="10-26"
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

download_file() {
    local url="$1"
    local output="$2"
    if command -v wget > /dev/null 2>&1; then
        wget -q --show-progress "$url" -O "$output"
    elif command -v curl > /dev/null 2>&1; then
        curl -# -L "$url" -o "$output"
    else
        echo "Error: Neither wget nor curl is installed." >&2
        return 1
    fi
}

verify_checksum() {
    local checksum_file="${1:-}"
    if [[ "$checksum_file" == *.sha512sum ]]; then
        sha512sum -c "$checksum_file"
    elif [[ "$checksum_file" == *.sha256sum ]]; then
        sha256sum -c "$checksum_file"
    else
        echo "Unknown checksum file format: $checksum_file" >&2
        return 1
    fi
}

# ----------------------------------------------------------------
# --- Worker Functions ---
# ----------------------------------------------------------------

install_proton_ge() {
    local install_dir="$1"

    echo -e "\n=== Installing Proton GE ==="

    local github_direct_url="https://github.com/GloriousEggroll/proton-ge-custom/releases/download/$PROTON_NAME"
    local tarball_name="$PROTON_NAME.tar.gz"
    local checksum_name="$PROTON_NAME.sha512sum"
    local tarball_url="$github_direct_url/$tarball_name"
    local checksum_url="$github_direct_url/$checksum_name"
    local temp_dir="/tmp/proton-ge-custom"

    # Prepare temp working directory
    rm -rf "$temp_dir"
    mkdir -p "$temp_dir"
    pushd "$temp_dir" > /dev/null

    # Download working files
    download_file "$tarball_url" "$tarball_name"
    download_file "$checksum_url" "$checksum_name"

    # Verify file integrity
    echo "Verifying tarball $tarball_name with checksum $checksum_name..."
    verify_checksum "$checksum_name"

    # Ensure Proton directory exists and extract
    mkdir -p "$install_dir"
    echo "Extracting Proton GE to $install_dir..."
    tar -xf "$tarball_name" -C "$install_dir"

    echo "Cleaning up temporary files..."
    popd > /dev/null
    rm -rf "$temp_dir"

    echo "✅ Proton GE v${PROTON_VERSION} successfully installed!"
}

# ----------------------------------------------------------------
# --- Main Orchestrator ---
# ----------------------------------------------------------------

main() {
    # Help/usage output
    if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
        echo "Usage: $0 [INSTALL_DIR]"
        echo "Example: bash $0 ~/.steam/root/compatibilitytools.d"
        exit 0
    fi

    ensure_user_space

    local default_install_dir="$HOME/.steam/root/compatibilitytools.d"
    local install_dir="${1:-$default_install_dir}"
    local proton_dir="$install_dir/$PROTON_NAME"

    if [ ! -d "$proton_dir" ]; then
        install_proton_ge "$install_dir"
    else
        echo "Proton GE already exists at: $proton_dir"
    fi
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/proton-ge.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/proton-ge.sh
