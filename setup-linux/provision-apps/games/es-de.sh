#!/usr/bin/env bash
set -euo pipefail # Exit immediately on error

# EmulationStation, Destop Edition (ES-DE) (https://es-de.org)
# (user install of AppImage for proper self-updating)

# Get the actual user when running with sudo
ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(getent passwd "$ACTUAL_USER" | cut -d: -f6)

APPIMAGE_URL="https://gitlab.com/es-de/emulationstation-de/-/package_files/210210324/download"
APP_NAME="es-de"
# INSTALL_DIR="/opt/$APP_NAME"  # system-wide install
# WRAPPER_PATH="/usr/local/bin/$APP_NAME"
# DESKTOP_ENTRY="/usr/share/applications/$APP_NAME.desktop"
INSTALL_DIR="$ACTUAL_HOME/Applications"  # user install
WRAPPER_PATH="$ACTUAL_HOME/.local/bin/$APP_NAME"
DESKTOP_ENTRY="$ACTUAL_HOME/.local/share/applications/$APP_NAME.desktop"
APP_IMAGE_PATH="$INSTALL_DIR/$APP_NAME.AppImage"

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Ensure the script is running as root (or sudo privileges)
require_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "❌ This script must be run as root or with sudo.  Exiting..."
        exit 1
    fi
}

ensure_dirs() {
  # Ensure install directory exists
  if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Creating $APP_NAME directory: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
    chown "$ACTUAL_USER:$ACTUAL_USER" "$INSTALL_DIR"
  fi

  # Ensure .local/bin and .local/share/applications exist
  mkdir -p "$ACTUAL_HOME/.local/bin"
  chown "$ACTUAL_USER:$ACTUAL_USER" "$ACTUAL_HOME/.local/bin"
  
  mkdir -p "$ACTUAL_HOME/.local/share/applications"
  chown "$ACTUAL_USER:$ACTUAL_USER" "$ACTUAL_HOME/.local/share/applications"
}

install_runtime_deps() {
  echo "[INFO] Ensuring libfuse2 is available..."
  if dpkg -s libfuse2 >/dev/null 2>&1; then
    echo "[INFO] libfuse2 already installed."
    return 0
  fi

  if ! command -v apt-get >/dev/null 2>&1; then
    echo "[WARN] apt-get not found; please install libfuse2 manually."
    return 1
  fi

  # Try update, but don't let unrelated repo errors stop us from attempting install.
  if ! apt-get update -qq; then
    echo "[WARN] 'apt-get update' reported errors; attempting install anyway."
  fi

  if DEBIAN_FRONTEND=noninteractive apt-get install -y libfuse2; then
    echo "[INFO] libfuse2 installed."
    return 0
  else
    echo "[ERROR] Failed to install libfuse2. Run 'sudo apt-get update' and fix repository GPG errors, or install libfuse2 manually."
    return 1
  fi
}

download_appimage() {
  if [ -f "$APP_IMAGE_PATH" ]; then
    echo "[INFO] AppImage already present at $APP_IMAGE_PATH"
    return
  fi

  echo "[INFO] Downloading AppImage to $APP_IMAGE_PATH"
  if command -v curl >/dev/null 2>&1; then
    # robust, atomic pattern — avoids partial/corrupt files on failure
    tmp="$(mktemp "${APP_IMAGE_PATH}.XXXXXX")"
    curl -L --fail --show-error -o "$tmp" "$APPIMAGE_URL" \
      && chmod +x "$tmp" \
      && chown "$ACTUAL_USER:$ACTUAL_USER" "$tmp" \
      && mv -f "$tmp" "$APP_IMAGE_PATH"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$APP_IMAGE_PATH" "$APPIMAGE_URL"
    chown "$ACTUAL_USER:$ACTUAL_USER" "$APP_IMAGE_PATH"
  else
    echo "[ERROR] Neither curl nor wget available to download AppImage."
    exit 1
  fi
  chmod +x "$APP_IMAGE_PATH"
  chown "$ACTUAL_USER:$ACTUAL_USER" "$APP_IMAGE_PATH"
  echo "[INFO] Downloaded and made executable: $APP_IMAGE_PATH"
}

create_wrapper() {
  echo "[INFO] Creating system wrapper at $WRAPPER_PATH"
  tmp="$(mktemp "${WRAPPER_PATH}.XXXXXXXX")"
  cat > "$tmp" <<EOF
#!/usr/bin/env sh
exec "$APP_IMAGE_PATH" "\$@"
EOF
  chmod 755 "$tmp"
  chown "$ACTUAL_USER:$ACTUAL_USER" "$tmp"
  mv -f "$tmp" "$WRAPPER_PATH"
  # ensure final perms / ownership
  chmod 755 "$WRAPPER_PATH"
  chown "$ACTUAL_USER:$ACTUAL_USER" "$WRAPPER_PATH"
}

create_desktop_entry() {
  echo "[INFO] Writing system desktop entry at $DESKTOP_ENTRY (overwriting idempotently)"

  tmp="$(mktemp "${DESKTOP_ENTRY}.XXXXXXXX")"
  cat > "$tmp" <<EOF
[Desktop Entry]
Name=EmulationStation DE
Comment=EmulationStation Desktop Edition (ES-DE)
TryExec=$WRAPPER_PATH
Exec=$WRAPPER_PATH %U
Icon=applications-games
Terminal=false
Type=Application
Categories=Game;Emulator;
StartupNotify=true
EOF

  chmod 644 "$tmp"
  chown "$ACTUAL_USER:$ACTUAL_USER" "$tmp"
  mv -f "$tmp" "$DESKTOP_ENTRY"
  chmod 644 "$DESKTOP_ENTRY"
  chown "$ACTUAL_USER:$ACTUAL_USER" "$DESKTOP_ENTRY"
}

post_install_notes() {
  echo
  echo "✅ Installed ES-DE AppImage to: $APP_IMAGE_PATH"
  echo " - Wrapper: $WRAPPER_PATH (on system PATH)"
  echo " - Desktop entry: $DESKTOP_ENTRY"
  echo
  echo "If the new launcher doesn't appear immediately, run:"
  echo "  update-desktop-database ~/.local/share/applications"
  echo "or log out and back in."
}

main() {
    echo "Started provisioning of Emulation Station, Desktop Edition (ES-DE)..."
    require_root
    ensure_dirs
    install_runtime_deps
    download_appimage
    create_wrapper
    create_desktop_entry
    post_install_notes
}

main "$@"

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/es-de.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/games/es-de.sh
