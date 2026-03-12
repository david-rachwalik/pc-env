#!/usr/bin/env bash
set -euo pipefail

# Generic AppImage installer
# Usage:
#   sudo ./install-appimage.sh --name "EmulationStation DE" --id emulationstation-de \
#     --url "https://..." --system
#
# Runs as root for system installs (/opt + /usr/local/bin + /usr/share/applications)
# Can be run as normal user for user-local install (HOME/.local/...).
#
# Flags:
#   --name "Nice Name"         Human name used in desktop file
#   --id app-id                short id (used for filenames and desktop id)
#   --url URL                  AppImage download URL
#   --install-dir DIR          where to place app (defaults: /opt/<id> for --system, $HOME/.local/share/<id> for user)
#   --wrapper PATH             wrapper path (defaults: /usr/local/bin/<id> for system, $HOME/.local/bin/<id> for user)
#   --desktop PATH             desktop file path (defaults as above)
#   --icon ICON                theme icon name or absolute path (default: applications-games)
#   --extract-icon             attempt best-effort icon extraction (optional)
#   --no-deps                 skip libfuse2 installation attempt (default = install when root)
#   --system                  install system-wide (requires root)
#
# Minimal, robust and idempotent.

progname="$(basename "$0")"

# defaults
NAME=""
ID=""
URL=""
EXTRACT_ICON=false
NO_DEPS=false
SYSTEM=false
ICON="applications-games"
INSTALL_DIR=""
WRAPPER=""
DESKTOP=""
CATEGORIES="Utility;Network;FileTransfer;" # Game;Emulator;

usage() {
  cat <<EOF
Usage: $progname --name "Nice Name" --id short-id --url <AppImage-URL> [--system] [--extract-icon] [--no-deps]
EOF
  exit 1
}

# parse args (simple)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2;;
    --id) ID="$2"; shift 2;;
    --url) URL="$2"; shift 2;;
    --install-dir) INSTALL_DIR="$2"; shift 2;;
    --wrapper) WRAPPER="$2"; shift 2;;
    --desktop) DESKTOP="$2"; shift 2;;
    --icon) ICON="$2"; shift 2;;
    --categories) CATEGORIES="$2"; shift 2;;
    --extract-icon) EXTRACT_ICON=true; shift ;;
    --no-deps) NO_DEPS=true; shift ;;
    --system) SYSTEM=true; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown arg: $1"; usage ;;
  esac
done

if [[ -z "$NAME" || -z "$ID" || -z "$URL" ]]; then
  echo "Missing required arguments."
  usage
fi

# defaults based on mode
if $SYSTEM; then
  : ${INSTALL_DIR:="/opt/$ID"}
  : ${WRAPPER:="/usr/local/bin/$ID"}
  : ${DESKTOP:="/usr/share/applications/${ID}.desktop"}
else
  REAL_HOME="${HOME}"
  : ${INSTALL_DIR:="$REAL_HOME/.local/share/$ID"}
  : ${WRAPPER:="$REAL_HOME/.local/bin/$ID"}
  : ${DESKTOP:="$REAL_HOME/.local/share/applications/${ID}.desktop"}
fi

APPIMAGE_PATH="$INSTALL_DIR/${ID}.AppImage"
ICON_PATH="${INSTALL_DIR}/icon.png"

# helpers
ensure_dirs() {
  mkdir -p "$INSTALL_DIR"
  if ! $SYSTEM; then
    mkdir -p "$(dirname "$DESKTOP")" "$(dirname "$WRAPPER")"
  fi
}

install_deps_if_needed() {
  if $NO_DEPS; then
    return 0
  fi
  # only try when root (system) or when user requests; for system installs usually run as root
  if $SYSTEM && command -v apt-get >/dev/null 2>&1; then
    if ! dpkg -s libfuse2 >/dev/null 2>&1; then
      echo "[INFO] Installing libfuse2 (AppImage runtime) via apt..."
      DEBIAN_FRONTEND=noninteractive apt-get update -qq || echo "[WARN] apt-get update had issues; attempting install"
      DEBIAN_FRONTEND=noninteractive apt-get install -y libfuse2 || echo "[WARN] apt-get install libfuse2 failed; continuing"
    fi
  fi
}

download_appimage() {
  if [[ -f "$APPIMAGE_PATH" ]]; then
    echo "[INFO] AppImage already present at $APPIMAGE_PATH"
    return
  fi

  tmp="$(mktemp "${APPIMAGE_PATH}.XXXXXX")"
  if command -v curl >/dev/null 2>&1; then
    curl --location --fail --show-error --output "$tmp" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$tmp" "$URL"
  else
    echo "[ERROR] No curl or wget available"; exit 1
  fi
  chmod +x "$tmp"
  mv -f "$tmp" "$APPIMAGE_PATH"
  echo "[INFO] Downloaded $APPIMAGE_PATH"
}

extract_icon_best_effort() {
  # best-effort: use embedded extractor if available
  if [[ ! -f "$APPIMAGE_PATH" ]]; then
    return 0
  fi
  tmpd="$(mktemp -d)"
  pushd "$tmpd" >/dev/null
  if "$APPIMAGE_PATH" --appimage-extract >/dev/null 2>&1; then
    if [[ -f squashfs-root/.DirIcon ]]; then
      cp squashfs-root/.DirIcon "$ICON_PATH" 2>/dev/null || true
    else
      found="$(find squashfs-root -type f \( -iname '*.png' -o -iname '*.ico' \) | head -n1 || true)"
      [[ -n "$found" ]] && cp "$found" "$ICON_PATH" 2>/dev/null || true
    fi
    rm -rf squashfs-root
  else
    # best-effort fallback with bsdtar (if installed)
    if command -v bsdtar >/dev/null 2>&1; then
      candidate="$(bsdtar -tf "$APPIMAGE_PATH" | grep -Ei '\.png$|\.ico$' | head -n1 || true)"
      if [[ -n "$candidate" ]]; then
        bsdtar -xf "$APPIMAGE_PATH" "$candidate"
        mkdir -p "$(dirname "$ICON_PATH")"
        mv "$candidate" "$ICON_PATH" 2>/dev/null || true
      fi
    fi
  fi

  # convert ico->png if needed and convert is available
  if [[ -f "$ICON_PATH" ]] && file "$ICON_PATH" | grep -iq 'ico'; then
    if command -v convert >/dev/null 2>&1; then
      convert "$ICON_PATH[0]" -resize 256x256 "${ICON_PATH%.ico}.png" && ICON_PATH="${ICON_PATH%.ico}.png"
    fi
  fi

  popd >/dev/null
  rm -rf "$tmpd" || true
  [[ -f "$ICON_PATH" ]] && echo "[INFO] extracted icon to $ICON_PATH" || echo "[INFO] no icon extracted"
}

atomic_write() {
  # atomic_write <dest> <mode> <<EOF ... EOF
  dest="$1"; mode="$2"; shift 2
  tmp="$(mktemp "${dest}.XXXXXXXX")"
  cat > "$tmp" "$@"
  chmod "$mode" "$tmp"
  mv -f "$tmp" "$dest"
}

create_wrapper() {
  mkdir -p "$(dirname "$WRAPPER")"
  tmp="$(mktemp "${WRAPPER}.XXXXXXXX")"
  cat > "$tmp" <<EOF
#!/usr/bin/env sh
exec "$APPIMAGE_PATH" "\$@"
EOF
  chmod 755 "$tmp"
  mv -f "$tmp" "$WRAPPER"
  echo "[INFO] wrapper written: $WRAPPER"
}

create_desktop_entry() {
  mkdir -p "$(dirname "$DESKTOP")"
  tmp="$(mktemp "${DESKTOP}.XXXXXXXX")"
  # icon field: absolute path if we extracted, otherwise theme name
  local icon_field="$ICON"
  if [[ -f "$ICON_PATH" ]]; then
    icon_field="$ICON_PATH"
  fi

  cat > "$tmp" <<EOF
[Desktop Entry]
Name=$NAME
Comment=$NAME
TryExec=$WRAPPER
Exec=$WRAPPER %U
Icon=$icon_field
Terminal=false
Type=Application
Categories=$CATEGORIES
StartupNotify=true
EOF
  chmod 644 "$tmp"
  mv -f "$tmp" "$DESKTOP"
  echo "[INFO] desktop entry written: $DESKTOP"
}

# main
ensure_dirs
if $SYSTEM; then
  install_deps_if_needed
fi
download_appimage
if $EXTRACT_ICON; then
  extract_icon_best_effort || true
fi
create_wrapper
create_desktop_entry

echo
echo "✅ Installed $NAME"
echo " - AppImage: $APPIMAGE_PATH"
echo " - Wrapper: $WRAPPER"
echo " - Desktop: $DESKTOP"
if [[ -f "$ICON_PATH" ]]; then echo " - Icon: $ICON_PATH"; fi
