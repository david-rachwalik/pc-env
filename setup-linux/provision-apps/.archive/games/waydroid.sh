#!/usr/bin/env bash
set -euo pipefail

#######################################
# Global configuration
#######################################
LOG_FILE="/var/log/waydroid-install.log"
WAYDROID_REPO_CHECK="/etc/apt/sources.list.d/waydroid.list"
REQUIRED_PACKAGES=(
  waydroid
  waydroid-extra-images
)

#######################################
# Logging helpers
#######################################
log() {
  local level="$1"
  local msg="$2"
  echo "$(date '+%Y-%m-%d %H:%M:%S') [$level] $msg" | tee -a "$LOG_FILE"
}

info()  { log "INFO"  "$1"; }
warn()  { log "WARN"  "$1"; }
error() { log "ERROR" "$1"; }

#######################################
# Safety & environment checks
#######################################
require_sudo() {
  if [[ "$EUID" -ne 0 ]]; then
    error "This script must be run with sudo."
    exit 1
  fi
}

detect_real_user() {
  if [[ -z "${SUDO_USER:-}" || "$SUDO_USER" == "root" ]]; then
    error "Unable to determine invoking user. Use: sudo bash script.sh"
    exit 1
  fi

  REAL_USER="$SUDO_USER"
  REAL_HOME="$(getent passwd "$REAL_USER" | cut -d: -f6)"

  info "Detected invoking user: $REAL_USER"
  info "Home directory: $REAL_HOME"
}

#######################################
# Waydroid installation steps
#######################################
add_waydroid_repo() {
  if [[ -f "$WAYDROID_REPO_CHECK" ]]; then
    info "Waydroid repository already present. Skipping."
    return
  fi

  info "Adding Waydroid repository..."
  curl -fsSL https://repo.waydro.id | bash >>"$LOG_FILE" 2>&1
  info "Waydroid repository added."
}

install_packages() {
  info "Ensuring required packages are installed..."

  apt-get update -qq >>"$LOG_FILE" 2>&1

  for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if dpkg -s "$pkg" &>/dev/null; then
      info "Package already installed: $pkg"
    else
      info "Installing package: $pkg"
      apt-get install -y "$pkg" >>"$LOG_FILE" 2>&1
    fi
  done
}

#######################################
# Waydroid runtime setup
#######################################
enable_waydroid_service() {
  info "Enabling Waydroid container service..."
  systemctl enable waydroid-container >>"$LOG_FILE" 2>&1 || true
  systemctl start waydroid-container >>"$LOG_FILE" 2>&1 || true
}

initialize_waydroid() {
  if [[ -d "/var/lib/waydroid" ]]; then
    info "Waydroid already initialized. Skipping init."
    return
  fi

  info "Initializing Waydroid system image..."
  waydroid init >>"$LOG_FILE" 2>&1
}

force_reinit_with_arm_support() {
  info "Ensuring ARM translation support is installed..."

  if [[ -d "/var/lib/waydroid/images" ]]; then
    info "Extra images detected. Reinitializing to ensure ARM support."
    waydroid init --force >>"$LOG_FILE" 2>&1
  else
    warn "Waydroid images directory not found; skipping forced reinit."
  fi
}

#######################################
# User-facing post-install info
#######################################
print_next_steps() {
  info "Installation complete."

  cat <<EOF | tee -a "$LOG_FILE"

Next steps (run as your normal user):

  1. Start Waydroid session:
       waydroid session start

  2. Launch full UI:
       waydroid show-full-ui

  3. Install APK:
       waydroid adb install SyahatasBadDay_v1.0.5.apk

If Waydroid fails to start, try:
  sudo systemctl restart waydroid-container

A reboot is recommended before first launch.

EOF
}

#######################################
# Main execution flow
#######################################
main() {
  require_sudo
  detect_real_user

  info "=== Waydroid installation started ==="
  add_waydroid_repo
  install_packages
  enable_waydroid_service
  initialize_waydroid
  force_reinit_with_arm_support

  info "=== Waydroid installation finished ==="
  print_next_steps
}

main "$@"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/waydroid.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/games/waydroid.sh
