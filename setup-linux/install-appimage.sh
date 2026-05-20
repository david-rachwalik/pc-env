#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Generic AppImage Installer
#
# Downloads an AppImage, generates an executable wrapper, creates a .desktop 
# shortcut, and optionally extracts the app's embedded icon. 
# 
# Supports user-space (default) or system-wide (--system) installations.
# Run with -h or --help for full usage instructions.
# ==============================================================================

progname="$(basename "$0")"

# --- Defaults ---
NAME=""
ID=""
URL=""
EXTRACT_ICON=false
SYSTEM=false
FORCE=false
ICON="applications-games"
INSTALL_DIR=""
WRAPPER=""
DESKTOP=""
CATEGORIES="Utility;Network;FileTransfer;"  # Game;Emulator;

usage() {
  cat <<EOF
Generic AppImage Installer

Usage:
  $progname --name "App Name" --id <short-id> --url <URL> [OPTIONS]

Required Arguments:
  --name "Nice Name"      Human-readable name used in the desktop file.
  --id <app-id>           Short internal identifier used for filenames and paths.
  --url <URL>             Direct download URL for the AppImage binary.

Optional Actions:
  --extract-icon          Attempt to extract an icon directly from the AppImage.
  --force                 Force redownload and rewrite even if the app exists.
  --system                Install system-wide (requires root/sudo). 
                          Target paths: /opt/, /usr/local/bin, /usr/share/applications
                          (If omitted, defaults to user-space: ~/.local/...)

Path Overrides (Optional):
  --install-dir <DIR>     Custom directory to store the AppImage.
  --wrapper <PATH>        Custom path for the executable shell wrapper.
  --desktop <PATH>        Custom path for the .desktop launcher.
  --icon <ICON>           Theme icon name or absolute path (default: applications-games).
  --categories <CATS>     Desktop file categories (default: Utility;Network;FileTransfer;).
  -h, --help              Show this help message and exit.

Example to test locally:
  $progname --name "My App" --id myapp --url "https://..." --extract-icon
EOF
  exit 1
}

# --- Parse args ---
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
    --system) SYSTEM=true; shift ;;
    --force) FORCE=true; shift ;;
    -h|--help) usage ;;
    *) echo "[ERROR] Unknown arg: $1"; usage ;;
  esac
done

if [[ -z "$NAME" || -z "$ID" || -z "$URL" ]]; then
  echo "[ERROR] Missing required arguments."
  usage
fi

# --- Apply standard path defaults based on mode ---
if $SYSTEM; then
  : "${INSTALL_DIR:="/opt/$ID"}"
  : "${WRAPPER:="/usr/local/bin/$ID"}"
  : "${DESKTOP:="/usr/share/applications/${ID}.desktop"}"
else
  # Respect XDG Base Directory Specification
  XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
  XDG_BIN_HOME="${HOME}/.local/bin"  # Standard user executable path
  
  : "${INSTALL_DIR:="$XDG_DATA_HOME/$ID"}"
  : "${WRAPPER:="$XDG_BIN_HOME/$ID"}"
  : "${DESKTOP:="$XDG_DATA_HOME/applications/${ID}.desktop"}"
fi

APPIMAGE_PATH="$INSTALL_DIR/${ID}.AppImage"
ICON_PATH="${INSTALL_DIR}/icon.png"

# ----------------------------------------------------------------
# --- Helpers ---
# ----------------------------------------------------------------

ensure_dirs() {
  mkdir -p "$INSTALL_DIR" "$(dirname "$WRAPPER")" "$(dirname "$DESKTOP")"
}

download_appimage() {
  if [[ -f "$APPIMAGE_PATH" ]] && ! $FORCE; then
    echo "[INFO] AppImage already present.  Use --force to redownload."
    return
  fi

  echo "[INFO] Downloading AppImage..."
  local tmp
  tmp="$(mktemp "${APPIMAGE_PATH}.XXXXXX")"
  
  # Ensure temp files are cleaned up on download failure
  trap 'rm -f "$tmp"' EXIT INT TERM
  
  if command -v curl >/dev/null 2>&1; then
    curl --location --fail --show-error --output "$tmp" "$URL"
  elif command -v wget >/dev/null 2>&1; then
    wget -q -O "$tmp" "$URL"
  else
    echo "[ERROR] Neither curl nor wget available"; exit 1
  fi
  
  chmod +x "$tmp"
  mv -f "$tmp" "$APPIMAGE_PATH"
  trap - EXIT INT TERM  # Remove trap after successful move
  echo "[INFO] Downloaded to $APPIMAGE_PATH"
}

extract_icon_best_effort() {
  if [[ ! -f "$APPIMAGE_PATH" ]]; then return 0; fi
  if [[ -f "$ICON_PATH" ]] && ! $FORCE; then 
    echo "[INFO] Icon already exists.  Skipping extraction."
    return 0
  fi

  echo "[INFO] Attempting to extract icon..."
  local tmpd
  tmpd="$(mktemp -d)"
  
  # Ensure dir is cleaned up no matter how extraction exits
  trap 'rm -rf "$tmpd"' EXIT INT TERM
  
  pushd "$tmpd" >/dev/null || return 1
  
  if "$APPIMAGE_PATH" --appimage-extract >/dev/null 2>&1; then
    if [[ -f squashfs-root/.DirIcon ]]; then
      cp squashfs-root/.DirIcon "$ICON_PATH" 2>/dev/null || true
    else
      local found
      found="$(find squashfs-root -type f \( -iname '*.png' -o -iname '*.ico' \) | head -n1 || true)"
      [[ -n "$found" ]] && cp "$found" "$ICON_PATH" 2>/dev/null || true
    fi
  elif command -v bsdtar >/dev/null 2>&1; then
    local candidate
    candidate="$(bsdtar -tf "$APPIMAGE_PATH" | grep -Ei '\.png$|\.ico$' | head -n1 || true)"
    if [[ -n "$candidate" ]]; then
      bsdtar -xf "$APPIMAGE_PATH" "$candidate"
      mv "$candidate" "$ICON_PATH" 2>/dev/null || true
    fi
  fi

  if [[ -f "$ICON_PATH" ]] && file "$ICON_PATH" | grep -iq 'ico' && command -v convert >/dev/null 2>&1; then
    convert "$ICON_PATH[0]" -resize 256x256 "${ICON_PATH%.ico}.png" && ICON_PATH="${ICON_PATH%.ico}.png"
  fi

  popd >/dev/null || return 1
  rm -rf "$tmpd"  # Normal cleanup
  trap - EXIT INT TERM # Remove trap after success
  
  [[ -f "$ICON_PATH" ]] && echo "[INFO] Extracted icon to $ICON_PATH" || echo "[WARN] No icon extracted."
}

atomic_write() {
  local dest="$1"
  local mode="$2"
  local tmp
  tmp="$(mktemp "${dest}.XXXXXXXX")"
  cat > "$tmp"
  chmod "$mode" "$tmp"
  mv -f "$tmp" "$dest"
}

create_wrapper() {
  atomic_write "$WRAPPER" 755 <<EOF
#!/usr/bin/env sh
exec "$APPIMAGE_PATH" "\$@"
EOF
  echo "[INFO] Wrapper written: $WRAPPER"
}

create_desktop_entry() {
  local icon_field="$ICON"
  if [[ -f "$ICON_PATH" ]]; then icon_field="$ICON_PATH"; fi

  atomic_write "$DESKTOP" 644 <<EOF
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
  echo "[INFO] Desktop entry written: $DESKTOP"
}

update_databases() {
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$(dirname "$DESKTOP")" || true
  fi
}

post_install_notes() {
  echo
  echo "✅ Installed $NAME"
  echo " - AppImage: $APPIMAGE_PATH"
  echo " - Wrapper:  $WRAPPER"
  echo " - Desktop:  $DESKTOP"
  if [[ -f "$ICON_PATH" ]]; then echo " - Icon:     $ICON_PATH"; fi
}

# ----------------------------------------------------------------
# --- Main Execution ---
# ----------------------------------------------------------------

main() {
  echo "[INFO] Started provisioning of $NAME..."
  ensure_dirs
  download_appimage
  if $EXTRACT_ICON; then extract_icon_best_effort; fi
  create_wrapper
  create_desktop_entry
  update_databases
  post_install_notes
}

main "$@"

# chmod +x ~/Repos/pc-env/setup-linux/install-appimage.sh
# bash ~/Repos/pc-env/setup-linux/install-appimage.sh
