#!/usr/bin/env bash
set -euo pipefail # Exit immediately on error

# Manage NAS mounts in /etc/fstab with x-systemd.automount

# -------- CONFIGURATION --------
declare -A SHARE_MOUNT_POINTS=(
  ["Portal"]="/mnt/Portal"
  ["NekoGooVideos"]="/mnt/NekoGooVideos"
  ["Main"]="/mnt/Main"
  ["PervyVR"]="/mnt/X"
  ["Emulation"]="/mnt/Z"
)

NAS_IP="${NAS_IP:-192.168.1.194}"
PROTOCOL="${PROTOCOL:-smb}" # or "nfs"

CREDENTIALS_FILE="${1:-}"
# Expand credentials path (avoid ~ expansion issues under sudo)
if [[ -n "$CREDENTIALS_FILE" ]]; then
  if command -v readlink >/dev/null 2>&1; then
    CREDENTIALS_FILE="$(readlink -f "$CREDENTIALS_FILE" 2>/dev/null || printf '%s' "$CREDENTIALS_FILE")"
  elif command -v realpath >/dev/null 2>&1; then
    CREDENTIALS_FILE="$(realpath -m "$CREDENTIALS_FILE" 2>/dev/null || printf '%s' "$CREDENTIALS_FILE")"
  fi
fi

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Ensure the script is running as root (or sudo privileges)
require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root or with sudo.  Exiting..."
    exit 1
  fi
}

# Check for SMB credentials file
verify_credentials() {
  # echo "credentials path: $CREDENTIALS_FILE"
  if [[ "$PROTOCOL" == "smb" ]]; then
    if [[ -z "$CREDENTIALS_FILE" ]]; then
      echo "❌ path to credentials file required for SMB.  Command Usage: $0 /path/to/creds"
      exit 1
    fi
    if [[ ! -f "$CREDENTIALS_FILE" ]]; then
      echo "❌ credentials file not found: $CREDENTIALS_FILE"
      exit 1
    fi
    # chmod 600 "$CREDENTIALS_FILE" || echo "chmod 600 on credentials failed"
  fi
}

# Backup /etc/fstab once
backup_fstab() {
  local backup_path="/etc/fstab.bak.$(date +%s)"
  if ! grep -q "^# pc-env-managed-backup" /etc/fstab 2>/dev/null; then
    cp /etc/fstab "$backup_path"
    printf '\n# pc-env-managed-backup %s\n' "$(date -Is)" >> /etc/fstab
    echo "Backed up /etc/fstab to $backup_path"
  fi
}

# Safe atomic removal of lines containing a literal pattern from /etc/fstab
safe_remove_lines_containing() {
  local pattern="$1"
  awk -v pat="$pattern" 'index($0,pat)==0 {print}' /etc/fstab > /tmp/fstab.$$ && mv /tmp/fstab.$$ /etc/fstab
}

# Remove any /etc/fstab lines that use the same mount point (field 2)
safe_remove_entries_for_mountpoint() {
  local mount_point="$1"
  awk -v mp="$mount_point" '($2 != mp) { print }' /etc/fstab > /tmp/fstab.$$ && mv /tmp/fstab.$$ /etc/fstab
}

# Append entry only if exact line not present
append_if_missing() {
  local line="$1"
  if grep -qxF "$line" /etc/fstab; then
    echo "fstab entry already present (skipping): $line"
  else
    printf '%s\n' "$line" >> /etc/fstab
    echo "Appended fstab entry: $line"
  fi
}

# Build and add fstab entry for a share (preserves original intent)
add_to_fstab() {
  local share="$1"
  local mount_point="$2"
  local mount_opts # Mount options per-protocol
  local entry

  # remove old entry for this share
  safe_remove_entries_for_mountpoint "$mount_point"
  
  if [[ "$PROTOCOL" == "nfs" ]]; then
    mount_opts="x-systemd.automount,_netdev,defaults,nfsvers=4.1,rsize=1048576,wsize=1048576,noatime"
    entry="${NAS_IP}:/${share} ${mount_point} nfs ${mount_opts} 0 0"
  elif [[ "$PROTOCOL" == "smb" ]]; then
    # credentials=/path     -> credentials file with username=...,password=...,domain=...
    # x-systemd.automount   -> create a systemd automount unit so the share mounts on access
    # _netdev               -> delay mount until network is available (systemd/network friendly)
    # iocharset=utf8        -> charset for filenames (UTF-8)
    # vers=3.1.1            -> SMB protocol version (pin to server-supported version)
    # sec=ntlmssp           -> authentication method (NTLMSSP / NTLMv2); avoids kernel auth mismatches
    # --- Other Conditional Options ---
    # uid=1000,gid=1000     -> map all files to this local user/group (useful for single-user desktop)
    # file_mode=0644        -> map file permissions (octal) for non-POSIX servers
    # dir_mode=0755         -> map directory permissions (octal)
    # noserverino           -> don't trust server inode numbers (fixes DFS/inode mismatches)
    # nounix                -> disable Unix extensions (stop server from sending unix attrs)
    # noperm                -> don't do local client-side permission checks (defer to server)
    # mfsymlinks            -> emulate POSIX symlinks for Windows reparse points/junctions
    mount_opts="x-systemd.automount,_netdev,iocharset=utf8,vers=3.1.1,sec=ntlmssp,uid=1000,gid=1000,file_mode=0644,dir_mode=0755,noserverino,nounix,noperm"
    entry="//${NAS_IP}/${share} ${mount_point} cifs credentials=${CREDENTIALS_FILE},${mount_opts} 0 0"
  else
    # TODO: exit early on error with empty entry
    mount_opts=""
    entry=""
  fi

  append_if_missing "$entry"
}

create_mount_point() {
  local mount_point="$1"
  if [[ ! -d "$mount_point" ]]; then
    echo "Creating mount point: $mount_point"
    mkdir -p "$mount_point"
    # chown 1000:1000 "$mount_point" || true
  else
    echo "Mount point already exists: $mount_point"
  fi
}

mount_share() {
  local mount_point="$1"
  if mountpoint -q "$mount_point"; then
    echo "$mount_point already mounted"
    return
  fi
  if mount "$mount_point"; then
    echo "Mounted $mount_point"
  else
    echo "Mount failed for $mount_point; x-systemd.automount will still automount on access if present"
  fi
}

# -------- main flow --------
main() {
  require_root
  verify_credentials
  # backup_fstab

  # First pass: ensure mount points & fstab entries
  for share in "${!SHARE_MOUNT_POINTS[@]}"; do
    local mount_point="${SHARE_MOUNT_POINTS[$share]}"
    echo ""
    echo "Processing share: $share -> $mount_point"

    create_mount_point "$mount_point"
    add_to_fstab "$share" "$mount_point"
  done
  echo ""

  # Tell systemd we changed /etc/fstab so subsequent mount() uses new entries
  echo "Reloading systemd fstab units..."
  systemctl daemon-reload || true

  # Second pass: attempt mounts (automount units now visible to systemd)
  for share in "${!SHARE_MOUNT_POINTS[@]}"; do
    local mount_point="${SHARE_MOUNT_POINTS[$share]}"
    mount_share "$mount_point"
  done
  echo ""

  echo "Mount setup complete!"
}

main "$@"

# :: Credential file format ::
# username=<username>
# password=<password>
# domain=QNAP

# Using domain for Domain Controller users (instead of QNAP/<username>)
# Verify credentials: smbclient -L //192.168.1.194 -A ~/.config/nas_credentials
# Verify file permissions (chmod 600): stat -c %a "/path/to/file"

# Verify the mount and contents
# findmnt /mnt/Portal
# ls -la /mnt/Portal | head -n 40

# If needing changes to take effect immediately, make sure mount is not busy and run
# `sudo umount /mnt/name` before the script

# chmod +x ~/Repos/pc-env/setup-linux/mount-nas-fstab.sh
# sudo bash ~/Repos/pc-env/setup-linux/mount-nas-fstab.sh ~/.config/nas_credentials
