#!/bin/bash
set -euo pipefail

# Subtitle Edit installer for Linux Mint
# https://github.com/SubtitleEdit/subtitleedit

SE_VERSION="4.0.13"
SE_FILENAME="SE4013.zip"
SE_URL="https://github.com/SubtitleEdit/subtitleedit/releases/download/${SE_VERSION}/${SE_FILENAME}"
APP_NAME="Subtitle Edit"
USER_NAME="${SUDO_USER:-$USER}"
SUDO_USER_HOME="/home/$USER_NAME"
INSTALL_DIR="$SUDO_USER_HOME/.local/share/subtitleedit"
APP_DIR="$INSTALL_DIR/SubtitleEdit"
DESKTOP_ENTRY="$SUDO_USER_HOME/.local/share/applications/subtitleedit.desktop"

install_mono() {
  echo "[INFO] Checking for Mono..."
  if ! command -v mono >/dev/null 2>&1; then
    echo "[INFO] Installing mono-complete..."
    sudo apt update
    sudo apt install -y mono-complete
  else
    echo "[INFO] Mono already installed."
  fi
}

download_subtitle_edit() {
  echo "[INFO] Downloading $APP_NAME $SE_VERSION..."
  mkdir -p "$INSTALL_DIR"
  chmod +x "$DESKTOP_ENTRY"
  chown $USER_NAME:$USER_NAME "$DESKTOP_ENTRY"
  cd "$INSTALL_DIR"

  if [ ! -f "$SE_FILENAME" ]; then
    wget -q "$SE_URL" -O "$SE_FILENAME"
  else
    echo "[INFO] Archive already downloaded."
  fi
}

extract_subtitle_edit() {
  echo "[INFO] Extracting $APP_NAME..."
  cd "$INSTALL_DIR"

  # if [ ! -d "SubtitleEdit" ]; then
  #   unzip -q "$SE_FILENAME" -d SubtitleEdit
  # else
  #   echo "[INFO] SubtitleEdit already extracted."
  # fi

  if [ ! -d "$APP_DIR" ]; then
    unzip -q "$SE_FILENAME" -d "$APP_DIR"
  else
    echo "[INFO] SubtitleEdit already extracted."
  fi

  chown -R "$USER_NAME":"$USER_NAME" "$INSTALL_DIR" || true
}

create_launcher() {
  # echo "[INFO] Creating launcher..."
  echo -e "\n=== Creating Desktop Launcher ==="

  # Add desktop entry for start menu
  mkdir -p "$(dirname "$DESKTOP_ENTRY")"
  cat > "$DESKTOP_ENTRY" <<EOF
[Desktop Entry]
Name=$APP_NAME
Comment=Open Source Subtitle Editor
Exec=mono "$APP_DIR/SubtitleEdit.exe"
# Icon=accessories-text-editor
Icon=$APP_DIR/Icons/mpc-hc.png
Terminal=false
Type=Application
Categories=AudioVideo;Video;Utility;
EOF

    chmod +x "$DESKTOP_ENTRY"
    chown $USER_NAME:$USER_NAME "$DESKTOP_ENTRY"
    echo "✅ Desktop entry created at: $DESKTOP_ENTRY"

    # Validate desktop entry
    if command -v desktop-file-validate &>/dev/null; then
        echo "Validating desktop entry..."
        desktop-file-validate "$DESKTOP_ENTRY" && echo "✅ Desktop entry validation passed." || echo "⚠️ Desktop entry validation failed."
    else
        echo "ℹ️ 'desktop-file-validate' not found.  Skipping validation."
    fi
}

main() {
  install_mono
  download_subtitle_edit
  extract_subtitle_edit
  create_launcher
  echo -e "\n🎉 All done!  You can now launch '$APP_NAME' from your applications menu."
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/subtitleedit.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/subtitleedit.sh
