#!/bin/bash
set -euo pipefail

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# Proton GE config
PROTON_VERSION="9-27"
PROTON_NAME="GE-Proton${PROTON_VERSION}" # extracted folder name
SUDO_USER_HOME="/home/${SUDO_USER:-$USER}"
TEMP_DIR="${TEMP_DIR:-/tmp/proton-ge-custom}" # can override for debugging
# Accept INSTALL_DIR as first argument (default: Steam's compat tools path)
INSTALL_DIR="${1:-$SUDO_USER_HOME/.steam/root/compatibilitytools.d}"
PROTON_DIR="$INSTALL_DIR/$PROTON_NAME"

download_file() {
    local url="$1"
    local output="$2"

    if command -v wget >/dev/null 2>&1; then
        wget -q --show-progress "$url" -O "$output"
    elif command -v curl >/dev/null 2>&1; then
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

# https://github.com/GloriousEggroll/proton-ge-custom?tab=readme-ov-file#native
install_proton_ge() {
    echo "\n=== Installing Proton GE ==="

    # Proton GE download URLs
    local github_direct_url="https://github.com/GloriousEggroll/proton-ge-custom/releases/download/$PROTON_NAME"
    local tarball_name="$PROTON_NAME.tar.gz"
    local checksum_name="$PROTON_NAME.sha512sum"
    local tarball_url="$github_direct_url/$tarball_name"
    local checksum_url="$github_direct_url/$checksum_name"

    # Prepare temp working directory
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"

    # Download working files
    download_file "$tarball_url" "$tarball_name"
    download_file "$checksum_url" "$checksum_name"

    # Verify file integrity
    echo "Verifying tarball $tarball_name with checksum $checksum_name..."
    verify_checksum "$checksum_name"

    # Ensure Proton directory exists and extract Proton GE
    mkdir -p "$INSTALL_DIR"
    echo "Extracting Proton GE to $INSTALL_DIR..."
    tar -xf "$tarball_name" -C "$INSTALL_DIR"
    chown -R "$SUDO_USER:$SUDO_USER" "$PROTON_DIR"

    echo "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"

    echo "✅ Proton GE v${PROTON_VERSION} successfully installed!"
}

# Help/usage output
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [INSTALL_DIR]"
    echo "Example: sudo bash $0 $INSTALL_DIR"
    exit 0
fi

# Only run install if not already present
if [ ! -d "$PROTON_DIR" ]; then
    install_proton_ge
else
    echo "Proton GE already exists at: $PROTON_DIR"
fi

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/proton-ge.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/proton-ge.sh
