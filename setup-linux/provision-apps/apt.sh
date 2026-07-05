#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# ================================================================
# --- Configuration ---
# ================================================================

# --- Base Applications (Always Installed) ---
BASE_PACKAGES=(
    # --- System Requirements / Core ---
    libfuse2t64  # FUSE 2 to run AppImages (t64 for Ubuntu 24.04+)
    flatpak  # For Plex Desktop infrastructure
    mono-complete  # For Subtitle Edit

    # --- Productivity ---
    # firefox
    # opera-stable  # Opera, Opera GX is available as browser extension (GX mode)
    hardinfo  # similar to speccy
    bleachbit  # similar to ccleaner

    # --- Development ---
    code  # Visual Studio Code
    gh
    git-lfs

    # --- Media ---
    vainfo
    vulkan-tools

    # --- Videogames ---
    steam
    lutris
)

# --- Heavy Applications (Skipped in Minimal Mode) ---
HEAVY_PACKAGES=(
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

# Development packages (nodejs, python3, etc.) have all been
# migrated into Docker containers & are no longer global

# ================================================================
# --- Helper Functions ---
# ================================================================

# Check if script is being run as root (user ID 0)
ensure_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "[ERROR] This script must be run as root or with sudo.  Exiting..." >&2
        exit 1
    fi
}

# ================================================================
# --- Worker Functions ---
# ================================================================

install_apt_packages() {
    local target_packages=("${BASE_PACKAGES[@]}")

    if [[ "$MINIMAL_MODE" == false ]]; then
        target_packages+=("${HEAVY_PACKAGES[@]}")
    fi

    # Safe to perform full unattended upgrades because this script is executed manually on-demand
    echo "[INFO] Updating package lists and upgrading existing packages..."
    apt-get update -qq && apt-get upgrade -y
    # (Because Linux Mint's native Update Manager safely orchestrates OS updates, security patches,
    # and Flatpak updates in the background, the OS layer is already handled daily.)

    echo "[INFO] Installing required core packages via APT..."
    local missing_packages=()

    for package in "${target_packages[@]}"; do
        if ! dpkg-query -W -f='${Status}' "$package" 2> /dev/null | grep -q "install ok installed"; then
            missing_packages+=("$package")
        fi
    done

    if [ ${#missing_packages[@]} -gt 0 ]; then
        echo "[INFO] Installing missing packages: ${missing_packages[*]}..."
        apt-get install -y "${missing_packages[@]}"
    else
        echo "[INFO] All specified APT packages are already installed."
    fi
}

install_discord() {
    if ! command -v discord &> /dev/null; then
        echo "[INFO] Discord was not found.  Installing..."
        readonly discord_tmp="/tmp/discord.deb"
        local discord_url="https://discord.com/api/download?platform=linux&format=deb"
        curl -L -o "$discord_tmp" "$discord_url"
        apt-get install -y "$discord_tmp"
        rm -f "$discord_tmp"
    else
        local discord_version
        discord_version=$(dpkg-query --show --showformat='${Version}' discord 2> /dev/null || echo "Unknown")
        echo "[INFO] Discord is already installed.  Version: $discord_version"
    fi
}

# Install Docker CE via official convenience script
install_docker() {
    if ! command -v docker &> /dev/null; then
        echo "[INFO] Docker was not found.  Installing official Docker CE..."
        readonly docker_tmp="/tmp/get-docker.sh"
        curl -fsSL https://get.docker.com -o "$docker_tmp"
        sh "$docker_tmp"
        rm -f "$docker_tmp"
        # Optional: Add user to docker group so sudo isn't needed for docker commands
        # usermod -aG docker "$SUDO_USER"
    else
        echo "[INFO] Docker is already installed.  Version: $(docker --version | tr -d '\n')"
    fi
}

install_nordvpn() {
    if ! command -v nordvpn &> /dev/null; then
        echo "[INFO] NordVPN was not found.  Installing..."
        # https://support.nordvpn.com/hc/en-us/articles/20196094470929-Installing-NordVPN-on-Linux-distributions
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
}

install_qbittorrent() {
    if ! command -v qbittorrent &> /dev/null; then
        echo "[INFO] qBittorrent was not found.  Installing..."
        add-apt-repository -y ppa:qbittorrent-team/qbittorrent-stable
        apt-get update -qq
        apt-get install -y qbittorrent
    else
        echo "[INFO] qBittorrent is already installed.  Version: $(qbittorrent --version | tr -d '\n')"
    fi
}

cleanup_system() {
    echo "[INFO] Cleaning up unnecessary files..."
    apt-get autoremove -y && apt-get clean
}

# ================================================================
# --- Main Orchestrator ---
# ================================================================

MINIMAL_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -m | --minimal)
            MINIMAL_MODE=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

main() {
    ensure_root
    echo "[INFO] Starting APT provisioning pipeline..."

    export DEBIAN_FRONTEND=noninteractive

    install_apt_packages
    install_discord
    install_docker
    install_nordvpn
    install_qbittorrent
    cleanup_system

    echo "[INFO] --- Completed provisioning of Linux via apt ---"
}

main "$@"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/apt.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/apt.sh
