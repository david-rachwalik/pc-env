#!/bin/bash
set -euo pipefail

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# === Proton GE Config ===
PROTON_VERSION="9-27"
SUDO_USER_HOME="/home/${SUDO_USER:-$USER}"
STEAM_DIR="$SUDO_USER_HOME/.steam/root"
STEAM_COMPAT_DIR="$STEAM_DIR/compatibilitytools.d"
PROTON_DIR="$STEAM_COMPAT_DIR/GE-Proton${PROTON_VERSION}"

# Proton GE download URLs
GITHUB_DIRECT_URL="https://github.com/GloriousEggroll/proton-ge-custom/releases/download/GE-Proton${PROTON_VERSION}"
TARBALL_NAME="GE-Proton${PROTON_VERSION}.tar.gz"
CHECKSUM_NAME="GE-Proton${PROTON_VERSION}.sha512sum"

# https://github.com/GloriousEggroll/proton-ge-custom?tab=readme-ov-file#native
install_proton_ge() {
    echo "\n=== Installing Proton GE ==="

    local proton_temp_dir="/tmp/proton-ge-custom"
    local tarball_url="$GITHUB_DIRECT_URL/$TARBALL_NAME"
    local checksum_url="$GITHUB_DIRECT_URL/$CHECKSUM_NAME"

    # Prepare temp working directory
    rm -rf "$proton_temp_dir"
    mkdir -p "$proton_temp_dir"
    cd "$proton_temp_dir"

    # Download working files
    echo "Downloading Proton GE: $TARBALL_NAME"
    curl -# -L "$tarball_url" -o "$TARBALL_NAME" --no-progress-meter
    echo "Downloading checksum: $CHECKSUM_NAME"
    curl -# -L "$checksum_url" -o "$CHECKSUM_NAME" --no-progress-meter

    # Verify file integrity
    echo "Verifying tarball $TARBALL_NAME with checksum $CHECKSUM_NAME..."
    sha512sum -c "$CHECKSUM_NAME"

    # Ensure Proton directory exists and extract Proton GE
    mkdir -p "$STEAM_COMPAT_DIR"
    echo "Extracting Proton GE to $STEAM_COMPAT_DIR..."
    tar -xf "$TARBALL_NAME" -C "$STEAM_COMPAT_DIR"
    sudo chown -R "$SUDO_USER:$SUDO_USER" "$PROTON_DIR"

    echo "Cleaning up temporary files..."
    rm -rf "$proton_temp_dir"

    echo "✅ Proton GE v${PROTON_VERSION} successfully installed!"
}

# Only run install if not already present
if [ ! -d "$PROTON_DIR" ]; then
    install_proton_ge
else
    echo "Proton GE already exists at: $PROTON_DIR"
fi

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/proton-ge.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/proton-ge.sh
