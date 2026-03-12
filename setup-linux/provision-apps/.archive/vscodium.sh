#!/bin/bash
set -euo pipefail # Exit immediately on error

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# https://github.com/VSCodium/vscodium
# https://vscodium.com/#install-on-debian-ubuntu-deb-package

# VSCodium repo variables
KEYRING_PATH="/usr/share/keyrings/vscodium-archive-keyring.gpg"
REPO_FILE="/etc/apt/sources.list.d/vscodium.list"
REPO_URL="https://download.vscodium.com/debs"
REPO_ENTRY="deb [arch=amd64,arm64 signed-by=${KEYRING_PATH}] ${REPO_URL} vscodium main"
GPG_URL="https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg"

install_gpg_key() {
    if [[ ! -f "$KEYRING_PATH" ]]; then
        echo "Adding VSCodium GPG key..."
        wget -qO - "$GPG_URL" | gpg --dearmor | sudo dd of="$KEYRING_PATH" status=none
    else
        echo "GPG key already exists at $KEYRING_PATH"
    fi
}

add_repository() {
    if [[ ! -f "$REPO_FILE" ]] || ! grep -Fxq "$REPO_ENTRY" "$REPO_FILE"; then
        echo "Adding VSCodium APT repository..."
        echo "$REPO_ENTRY" | sudo tee "$REPO_FILE" >/dev/null
    else
        echo "VSCodium repository already configured."
    fi
}

install_vscodium() {
    if ! command -v codium &>/dev/null; then
        echo "Installing VSCodium..."
        apt update
        apt install -y codium
    else
        echo "VSCodium is already installed."
    fi
}

main() {
    install_gpg_key
    add_repository
    install_vscodium
    echo "VSCodium provisioning complete."
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/vscodium.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/vscodium.sh
