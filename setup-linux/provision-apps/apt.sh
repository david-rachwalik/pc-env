#!/bin/bash

# Array of packages to install
packages=(
    # --- System Requirements / Core ---
    libfuse2  # FUSE 2 to run AppImages

    # --- Productivity ---
    # firefox
    # opera-stable           # Opera, Opera GX is available as browser extension (GX mode)
    hardinfo  # similar to speccy
    bleachbit # similar to ccleaner

    # --- Development ---
    code # Visual Studio Code
    gh
    git-lfs

    # --- Media ---
    # Required for ALVR
    mesa-va-drivers:amd64
    # mesa-va-drivers
    # libva-drm2
    # libva-x11-2
    vainfo

    # --- Videogames ---
    steam
    lutris

    # --- Streaming ---
    obs-studio

    # --- Video Editing ---
    handbrake
    mkvtoolnix
    mkvtoolnix-gui
    # Lossless Cut, MakeMKV, etc., can be installed via Flatpak or Snap

    # --- Other Editing ---
    gimp
    blender
)

# Commands, packages, and applications for Docker dev containers
packages_container=(
    # --- Development ---
    git # Source Control
    python3
    nodejs # NodeJS comes with Node Package Manager (npm)
    # mongodb-org           # requires additional setup for the MongoDB repo
    # dotnet-sdk-6.0
    azure-cli
    # terraform
    # ruby
    # Additional setups (e.g., oh-my-posh) can be done post-installation

    # --- Video Editing ---
    handbrake
)

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------

# -------- Run with bash (as root or sudo) --------

# Check if the script is being run as root (user ID 0)
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# Update package lists and upgrade existing packages
echo "[INFO] Updating package lists and upgrading existing packages..."
apt-get update -qq && apt-get upgrade -y

# Install required packages
echo "[INFO] Installing required core packages..."
for package in "${packages[@]}"; do
    if ! dpkg -l | grep -q "^ii\s*$package"; then
        echo "[INFO] Installing $package..."
        apt-get install -y "$package"
    else
        echo "[INFO] $package is already installed."
    fi
done

# --- Additional package installations from Flatpak, Snap, or other sources ---
# e.g., Spotify, GitHub Desktop can be handled separately since they are not directly available via apt

# Install Discord via Linux deb file installer
if ! command -v discord &>/dev/null; then
    DISCORD_INSTALLER_URL="https://discord.com/api/download?platform=linux&format=deb"
    echo "[INFO] Discord was not found.  Installing..."
    curl -L -o /tmp/discord.deb $DISCORD_INSTALLER_URL
    apt-get install -y /tmp/discord.deb
else
    # dpkg-query is safer for scripts than 'apt list'
    DISCORD_VERSION=$(dpkg-query --show --showformat='${Version}' discord 2>/dev/null || echo "Unknown")
    echo "[INFO] Discord is already installed.  Version: $DISCORD_VERSION"
fi

# Install Docker CE via official convenience script
if ! command -v docker &>/dev/null; then
    echo "[INFO] Docker was not found.  Installing official Docker CE..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    # Optional: Add user to docker group so sudo isn't needed for docker commands
    # usermod -aG docker "$SUDO_USER"
else
    echo "[INFO] Docker is already installed.  Version: $(docker --version | tr -d '\n')"
fi

# Install NordVPN on Linux distributions
# https://support.nordvpn.com/hc/en-us/articles/20196094470929-Installing-NordVPN-on-Linux-distributions
if ! command -v nordvpn &>/dev/null; then
    echo "[INFO] NordVPN was not found.  Installing..."
    # https://nordvpn.com/download/linux/#install-nordvpn
    sh <(curl -sSf https://downloads.nordcdn.com/apps/linux/install.sh)
    nordvpn login
    nordvpn connect United_States
    nordvpn set autoconnect on United_States # automatically connect on boot
    nordvpn set lan-discovery enabled
    # nordvpn status
    # nordvpn settings
else
    echo "[INFO] NordVPN is already installed.  Version: $(nordvpn --version | tr -d '\n')"
fi

# Install qBittorrent on Linux distributions
# https://www.qbittorrent.org/download
if ! command -v qbittorrent &>/dev/null; then
    echo "[INFO] qBittorrent was not found.  Installing..."
    add-apt-repository -y ppa:qbittorrent-team/qbittorrent-stable
    apt-get update -qq && apt-get install -y qbittorrent
else
    echo "[INFO] qBittorrent is already installed.  Version: $(qbittorrent --version)"
fi

# Cleaning up
echo "[INFO] Cleaning up unnecessary files..."
apt-get autoremove -y && apt-get clean

echo "[INFO] --- Completed provisioning of Linux via apt ---"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/apt.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/apt.sh

# ------------------------------------------------------------------------------------------------

# Standard Removal:     apt-get remove <package>
# - This command removes the package but leaves behind configuration files. These files are usually stored in /etc, /var, or the user's home directory,
#   depending on the application.

# Complete Removal:     apt-get purge <package>
# Use this command to remove both the package and its configuration files. This is equivalent to a "clean uninstall" and prevents most leftovers.
# Even after purging, some files (like logs or user-specific data) might still be left behind in non-standard directories.

# Autoremove:           apt-get autoremove
# This command helps clean up dependencies that were installed along with a package but are no longer needed once the package is removed.

# Autoclean:            apt-get autoclean
# This command helps clean up the local repository of retrieved package files no longer needed.
# - directories: /var/cache/apt/archives, /var/cache/apt/archives/partial
# Removes only the cached package files that are no longer available in the repositories or are outdated.
# It’s less aggressive than apt-get clean because it keeps the most recent versions of package files in the cache.

# Manual Clean-Up:
# Occasionally, manual intervention is needed to delete user data or logs that are not managed by apt.

# - For cleaner uninstalls, always use `purge` instead of `remove` when uninstalling software with apt-get.
# - Use `autoremove` regularly to keep your system tidy by removing unnecessary dependencies.
