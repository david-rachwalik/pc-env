#!/bin/bash
set -e

# https://github.com/abraunegg/onedrive/blob/master/docs/usage.md

# -------- Run with bash (as root or sudo) --------

# Check if the script is being run as root (user ID 0)
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# -------- Ensure system has latest version of curl --------

# Check if curl is already up-to-date
CURL_VERSION="8.11.0"
if ! curl --version | grep -q "${CURL_VERSION}"; then
    echo "Upgrading curl to v${CURL_VERSION}..."

    # Install necessary dependencies
    apt-get update
    apt-get install -y nghttp2 libnghttp2-dev libssl-dev libpsl-dev build-essential wget

    # Download, extract, and build curl
    CURL_SOURCE_URL="https://curl.se/download/curl-${CURL_VERSION}.tar.xz"
    wget -q "$CURL_SOURCE_URL" -O "curl.tar.xz"
    tar -xf curl.tar.xz
    rm curl.tar.xz
    cd "curl-${CURL_VERSION}"

    ./configure --prefix=/usr/local --with-ssl --with-nghttp2 --enable-versioned-symbols
    make -j"$(nproc)"
    make install

    # Update library links
    ldconfig

    # Clean up source directory
    cd ..
    rm -rf "curl-${CURL_VERSION}"

    # Verify installation
    echo "curl successfully upgraded to:"
    curl --version
else
    echo "curl is already up-to-date (v${CURL_VERSION}). No action needed."
    exit 0
fi

# -------- Installation of OneDrive client --------

echo "Starting installation of OneDrive client on Linux Mint v22 (Ubuntu 24.04)..."

# Step 1: Add the OpenSuSE Build Service repository release key
REPO_KEY_URL="https://download.opensuse.org/repositories/home:/npreining:/debian-ubuntu-onedrive/xUbuntu_24.04/Release.key"
KEYRING_PATH="/usr/share/keyrings/obs-onedrive.gpg"

if [ ! -f "$KEYRING_PATH" ]; then
    echo "Adding repository release key..."
    wget -qO - "$REPO_KEY_URL" | gpg --dearmor | tee "$KEYRING_PATH" >/dev/null
    echo "Repository release key added."
else
    echo "Repository release key already exists.  Skipping."
fi

# Step 2: Add the OpenSuSE Build Service repository
REPO_FILE="/etc/apt/sources.list.d/onedrive.list"
REPO_LINE="deb [arch=$(dpkg --print-architecture) signed-by=$KEYRING_PATH] https://download.opensuse.org/repositories/home:/npreining:/debian-ubuntu-onedrive/xUbuntu_24.04/ ./"

if grep -Fxq "$REPO_LINE" "$REPO_FILE" 2>/dev/null; then
    echo "Repository already exists.  Skipping."
else
    echo "Adding repository..."
    echo "$REPO_LINE" | tee "$REPO_FILE" >/dev/null
    echo "Repository added."
fi

# Step 3: Update system and install dependencies
echo "Updating package lists..."
apt-get update -q

echo "Installing dependencies..."
apt install -y --no-install-recommends --no-install-suggests python3 python3-pip

# Step 4: Install 'onedrive' CLI client
if dpkg -l | grep -q '^ii.*onedrive'; then
    echo "'onedrive' is already installed.  Skipping."
else
    echo "Installing 'onedrive'..."
    apt install -y --no-install-recommends --no-install-suggests onedrive
fi

# Step 5: Configure OneDrive
CONFIG_DIR="$HOME/.config/onedrive"
CONFIG_FILE="$CONFIG_DIR/config"

if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Running initial OneDrive setup.  Please follow the authentication steps."
    onedrive
    echo "OneDrive setup complete."
else
    echo "OneDrive is already configured."
fi

# Step 6: Enable and start OneDrive sync as a systemd service
if ! systemctl --user is-enabled onedrive &>/dev/null; then
    echo "Enabling OneDrive sync service..."
    systemctl --user enable onedrive
    systemctl --user start onedrive
else
    echo "OneDrive service is already enabled and running."
fi

echo -e "\nInstallation complete!  You can manage OneDrive using the 'onedrive' CLI command"

# chmod +x ~/Repos/pc-env/setup-linux/provision_onedrive.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision_onedrive.sh

# systemctl --user status onedrive

# To tail the OneDrive log in real-time:
# journalctl --user -u onedrive -f
