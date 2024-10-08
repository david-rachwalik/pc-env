#!/bin/bash

# -------- Run with bash (as root or sudo) --------

# Array of packages to install
packages=(
    # --- Productivity ---
    # firefox
    # opera-stable           # Opera, Opera GX is available only as a browser extension (GX mode)
    # google-chrome-stable
    # p7zip-full              # 7zip alternative    * already installed
    hardinfo                # similar to speccy
    bleachbit               # similar to ccleaner
    # ChatGPT doesn't have a native Linux package, consider using the web app or Flatpak options

    # --- Development ---
    code                    # Visual Studio Code
    docker.io
    docker-compose

    # --- Media ---
    gimp
    blender

    # --- Video Editing ---
    handbrake
    mkvtoolnix
    # Lossless Cut, MakeMKV, etc., can be installed via Flatpak or Snap

    # --- Streaming ---
    # obs-studio

    # --- Videogames ---
    steam
    # DirectX not required, use Wine for Windows compatibility
)


# Update package lists and upgrade existing packages
echo "Updating package lists and upgrading existing packages..."
sudo apt update && sudo apt upgrade -y

# Install required packages
echo "Installing required packages..."
for package in "${packages[@]}"; do
    if ! dpkg -l | grep -q "^ii\s*$package"; then
        echo "Installing $package..."
        sudo apt install -y $package
    else
        echo "$package is already installed."
    fi
done


# Additional package installations from Flatpak, Snap, or other sources
# e.g., Spotify, GitHub Desktop can be handled separately since they are not directly available via apt

# Install Discord via Linux deb file installer
url="https://discord.com/api/download?platform=linux&format=deb"
curl -L -o /tmp/discord.deb $url
sudo apt install /tmp/discord.deb

# Install NordVPN on Linux distributions
# https://support.nordvpn.com/hc/en-us/articles/20196094470929-Installing-NordVPN-on-Linux-distributions
sh <(curl -sSf https://downloads.nordcdn.com/apps/linux/install.sh)


# Cleaning up
echo "Cleaning up unnecessary files..."
sudo apt autoremove -y && sudo apt clean

echo "--- Completed provisioning of Linux Mint ---"



# Standard Removal:     sudo apt remove <package>
# - This command removes the package but leaves behind configuration files. These files are usually stored in /etc, /var, or the user's home directory,
#   depending on the application.

# Complete Removal:     sudo apt purge <package>
# Use this command to remove both the package and its configuration files. This is equivalent to a "clean uninstall" and prevents most leftovers.
# Even after purging, some files (like logs or user-specific data) might still be left behind in non-standard directories.

# Autoremove:           sudo apt autoremove
# This command helps clean up dependencies that were installed along with a package but are no longer needed once the package is removed.

# Autoclean:           sudo apt autoclean
# This command helps clean up the local repository of retrieved package files no longer needed.
# - directories: /var/cache/apt/archives, /var/cache/apt/archives/partial
# Removes only the cached package files that are no longer available in the repositories or are outdated.
# It’s less aggressive than apt clean because it keeps the most recent versions of package files in the cache.

# Manual Clean-Up:
# Occasionally, manual intervention is needed to delete user data or logs that are not managed by apt.


# - For cleaner uninstalls, always use `purge` instead of `remove` when uninstalling software with apt.
# - Use `autoremove` regularly to keep your system tidy by removing unnecessary dependencies.
