#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Plex Desktop (Flatpak) Installer for Linux Mint
# ============================================================
#
# DESCRIPTION:
# This script installs Plex Desktop via Flatpak (Flathub) in a
# fully idempotent and repeatable way.
#
# Compared to Plex Web (browser-based playback), this client:
# - Improves media compatibility (especially H.265 / HEVC)
# - Reduces or eliminates browser codec limitations and black-screen issues
# - Provides more consistent Direct Play behavior
# - Offers better handling of local/network file access (SMB/NAS)
# - Avoids browser rendering overhead and tab instability
#
# In practice, this results in:
# - More reliable playback for high-bitrate media
# - Fewer unexpected transcodes
# - Smoother performance for large media libraries
# ============================================================

APP_ID="tv.plex.PlexDesktop"
FLATPAK_REMOTE="flathub"

# =========================
# LOGGING HELPERS
# =========================
log() {
  echo -e "\n==> $1"
}

info() {
  echo "    $1"
}

# =========================
# CHECK FLATPAK INSTALLED
# =========================
ensure_flatpak_installed() {
  log "Checking Flatpak installation"

  if command -v flatpak >/dev/null 2>&1; then
    info "Flatpak is installed"
  else
    info "Flatpak not found — installing"
    sudo apt-get update -y
    sudo apt-get install -y flatpak
  fi
}

# =========================
# ENSURE FLATHUB ENABLED
# =========================
ensure_flathub_enabled() {
  log "Checking Flathub remote"

  if flatpak remotes | grep -q "^${FLATPAK_REMOTE}"; then
    info "Flathub already enabled"
  else
    info "Adding Flathub remote"
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
  fi
}

# =========================
# INSTALL PLEX DESKTOP
# =========================
install_plex() {
  log "Checking Plex Desktop Flatpak"

  if flatpak list | grep -q "${APP_ID}"; then
    info "Plex Desktop already installed"
  else
    info "Installing Plex Desktop"
    flatpak install -y flathub "${APP_ID}"
  fi
}

# =========================
# VERIFY INSTALL
# =========================
verify_install() {
  log "Verifying installation"

  if flatpak list | grep -q "${APP_ID}"; then
    info "Plex Desktop installed successfully"
    info "Run with: flatpak run ${APP_ID}"
  else
    echo "    WARNING: Installation may have failed"
  fi
}

# =========================
# MAIN
# =========================
main() {
  log "Starting Plex Desktop Flatpak installation"

  ensure_flatpak_installed
  ensure_flathub_enabled
  install_plex
  verify_install

  log "Done"
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/plex-desktop.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/plex-desktop.sh

# Step if ever wanting to remove config/, cache/, & data/
# sudo rm ~/.var/app/tv.plex.PlexDesktop/
