#!/bin/bash
set -e          # Exit immediately on error
set -o pipefail # Ensure piped commands fail properly

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ "$(id -u)" -ne 0 ]]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# https://www.filebot.net/download.html
# https://www.filebot.net/forums/viewtopic.php?t=6028

# URLs
GPG_KEY_URL="https://raw.githubusercontent.com/filebot/plugins/master/gpg/maintainer.pub"
REPO_LIST_FILE="/etc/apt/sources.list.d/filebot.list"
GPG_KEY_FILE="/usr/share/keyrings/filebot.gpg"

# Required packages
PREREQ_PACKAGES=("dirmngr" "gnupg" "apt-transport-https")
DEPENDENCIES=("default-jre" "openjfx" "zenity" "mediainfo" "libchromaprint-tools" "p7zip-full" "unrar")
FILEBOT_PACKAGE="filebot"

# Function to check if a package is installed
is_installed() {
    dpkg -l | grep -q "^ii  $1 "
}

# ----------------------------------------------------------------
# ----------------------------------------------------------------

uname -a # Print system info
echo "Starting installation of FileBot..."

# Install required pre-requisites if missing
echo "Installing pre-requisite packages..."
for pkg in "${PREREQ_PACKAGES[@]}"; do
    if ! is_installed "$pkg"; then
        apt-get install -y --install-recommends "$pkg"
    else
        echo "  - $pkg is already installed."
    fi
done

# Import signing key if not already imported
if [ ! -f "$GPG_KEY_FILE" ]; then
    echo "Importing FileBot GPG key..."
    curl -fsSL "$GPG_KEY_URL" | gpg --dearmor --output "$GPG_KEY_FILE"
else
    echo "FileBot GPG key already exists. Skipping..."
fi

# Add repository if not already present
if ! grep -q "^deb .*filebot.net" "$REPO_LIST_FILE" 2>/dev/null; then
    echo "Adding FileBot repository..."
    echo "deb [arch=all signed-by=$GPG_KEY_FILE] https://get.filebot.net/deb/ universal main" | tee "$REPO_LIST_FILE"
else
    echo "FileBot repository already added. Skipping..."
fi

# Update package index
echo "Updating package index..."
apt-get update -y

# Install dependencies
echo "Installing required dependencies..."
for dep in "${DEPENDENCIES[@]}"; do
    if ! is_installed "$dep"; then
        apt-get install -y --install-recommends "$dep"
    else
        echo "  - $dep is already installed."
    fi
done

# Install FileBot if not already installed
if ! is_installed "$FILEBOT_PACKAGE"; then
    echo "Installing FileBot..."
    apt-get install -y --install-recommends "$FILEBOT_PACKAGE"
else
    echo "FileBot is already installed. Skipping..."
fi

# Test Run
echo "Running FileBot system info test..."
filebot -script fn:sysinfo

echo "Installation complete!"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/filebot.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/filebot.sh
