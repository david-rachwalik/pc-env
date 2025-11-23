#!/usr/bin/env bash
set -euo pipefail # Exit immediately on error

# Manage mounts between PC & NAS

# ========= CONFIGURATION =========
declare -A SHARE_MOUNT_POINTS=(
    ["Portal"]="/mnt/Portal"
    ["NekoGooVideos"]="/mnt/NekoGooVideos"
    ["Main"]="/mnt/Main"
    ["PervyVR"]="/mnt/X"
    ["Emulation"]="/mnt/Z"
)
NAS_IP="${NAS_IP:-192.168.1.194}"
SYSTEMD_DIR="/etc/systemd/system"
IDLE_TIMEOUT="${IDLE_TIMEOUT:-600}" # seconds (10 min)
PROTOCOL="${PROTOCOL:-smb}" # or nfs (multi-user NFS requires Kerberos)
# Ensure credentials exist when using SMB protocol
CREDENTIALS_FILE="${1:-/home/$SUDO_USER/.config/nas_credentials}"

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Expand credentials path (avoid ~ expansion issues under sudo)
if [[ -n "$CREDENTIALS_FILE" ]]; then
    if command -v readlink >/dev/null 2>&1; then
        CREDENTIALS_FILE="$(readlink -f "$CREDENTIALS_FILE" 2>/dev/null || printf '%s' "$CREDENTIALS_FILE")"
    elif command -v realpath >/dev/null 2>&1; then
        CREDENTIALS_FILE="$(realpath -m "$CREDENTIALS_FILE" 2>/dev/null || printf '%s' "$CREDENTIALS_FILE")"
    fi
fi

declare -a COMMON_OPTS=(
    "_netdev"                # delay mount until network is ready
    "noatime"                # don't update access times
)
# protocol-specific extra options
declare -a NFS_OPTS=(
    "nfsvers=4.1"            # force NFS v4.1 (QNAP supports 4.1)
    "proto=tcp"              # use TCP for reliability/perf on LAN
    "rsize=1048576"          # read buffer size (LAN tuned)
    "wsize=1048576"          # write buffer size (LAN tuned)
    "timeo=600"              # RPC timeout; tuned for LAN responsiveness
    "retrans=2"              # retry attempts
    "hard"                   # prefer hard mounts (reliable data integrity)
)
declare -a SMB_OPTS=(
    "vers=3.1.1"             # SMB protocol version (server supported)
    "credentials=${CREDENTIALS_FILE}" # credentials file path
    "iocharset=utf8"         # filename charset (correct filename encoding)
    "uid=1000"               # map files to local user
    "gid=1000"               # map files to local group
    "file_mode=0644"         # file perms mapping
    "dir_mode=0755"          # dir perms mapping
    "noserverino"            # avoid server inode issues (DFS)
    "nounix"                 # disable unix ext (if problematic)
    "noperm"                 # let server enforce perms where needed
    # "cache=none"             # reduces local caching/stale metadata issues (less speed but more consistency)
    "sec=ntlmssp"            # auth mechanism (match your server)
)

join_opts() {
    local -n arr=$1
    local IFS=, # comma-separated
    echo "${arr[*]}"
}

# Protocol-specific mount options (comma as the field separator)
if [[ $PROTOCOL == "nfs" ]]; then
    MOUNT_TYPE="nfs"
    # MOUNT_OPTIONS="nfsvers=4.1,rsize=1048576,wsize=1048576,noatime"
    MOUNT_OPTIONS="$(join_opts COMMON_OPTS),$(join_opts NFS_OPTS)"
elif [[ $PROTOCOL == "smb" ]]; then
    MOUNT_TYPE="cifs"
    # MOUNT_OPTIONS="vers=3.0,credentials=$CREDENTIALS_FILE,iocharset=utf8,uid=1000,gid=1000"
    MOUNT_OPTIONS="$(join_opts COMMON_OPTS),$(join_opts SMB_OPTS)"
else
    echo "❌ Unsupported protocol: $PROTOCOL"
    exit 1
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
    if [[ "$PROTOCOL" != "smb" ]]; then
        return 0
    fi
    if [[ -z "$CREDENTIALS_FILE" ]]; then
        echo "❌ path to credentials file required for SMB.  Command Usage: $0 /path/to/creds"
        exit 1
    fi
    if [[ ! -f "$CREDENTIALS_FILE" ]]; then
        echo "❌ credentials file not found: $CREDENTIALS_FILE"
        exit 1
    fi
    # chmod 600 "$CREDENTIALS_FILE" || echo "chmod 600 on credentials failed"
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

write_mount_unit() {
    local share="$1"
    local mount_point="$2"
    local unit_name="$3"
    local entry

    if [[ "${MOUNT_TYPE:-}" == "cifs" ]]; then
        entry="//${NAS_IP}/${share}"
    else
        entry="${NAS_IP}:/${share}"
    fi

    # Compose mount unit without fstab-only flags like `noauto` or `x-systemd.automount`
    # .automount unit will provide automount behavior; include idle timeout and _netdev
    cat <<EOF >"$SYSTEMD_DIR/$unit_name.mount"
[Unit]
Description=Mount for $share
After=network-online.target
Wants=network-online.target

[Mount]
What=${entry}
Where=${mount_point}
Type=${MOUNT_TYPE}
Options=${MOUNT_OPTIONS},x-systemd.idle-timeout=${IDLE_TIMEOUT}
TimeoutSec=30

[Install]
WantedBy=multi-user.target
EOF
    echo "Created: $unit_name.mount"
}

write_automount_unit() {
    local mount_point="$1"
    local unit_name="$2"

    cat <<EOF >"$SYSTEMD_DIR/$unit_name.automount"
[Unit]
Description=Automount for $mount_point
After=network-online.target
Wants=network-online.target

[Automount]
Where=${mount_point}
TimeoutIdleSec=${IDLE_TIMEOUT}

[Install]
WantedBy=multi-user.target
EOF
    echo "Created: $unit_name.automount"
}

get_unit_name() {
    local mount_point="$1"
    systemd-escape --path "$mount_point" | sed 's|^-||'
}

# ========== MAIN ==========

main() {
    require_root
    verify_credentials

    echo "MOUNT_TYPE: $MOUNT_TYPE"
    echo "MOUNT_OPTIONS: $MOUNT_OPTIONS"
    echo "CREDENTIALS_FILE: $CREDENTIALS_FILE"

    # Create mount unit configurations
    for share_name in "${!SHARE_MOUNT_POINTS[@]}"; do
        local mount_point="${SHARE_MOUNT_POINTS[$share_name]}"
        local unit_name=$(get_unit_name "$mount_point")
        echo "🔧 Generating systemd units for $share_name => $mount_point"
        create_mount_point "$mount_point"
        write_mount_unit "$share_name" "$mount_point" "$unit_name"
        write_automount_unit "$mount_point" "$unit_name"
    done
    echo ""

    # Reload systemd and enable automounts
    echo "🔄 Reloading systemd and enabling automounts..."
    systemctl daemon-reload
    for share_name in "${!SHARE_MOUNT_POINTS[@]}"; do
        local mount_point="${SHARE_MOUNT_POINTS[$share_name]}"
        local unit_name=$(get_unit_name "$mount_point")
        echo "🚀 Enabling + starting: $unit_name.automount"
        systemctl enable --now "$unit_name.automount"
    done
    echo ""

    echo "✅ All NAS shares configured with systemd .mount and .automount"
}

main "$@"

# :: Credential file format ::
# username=<username>
# password=<password>
# domain=QNAP

# Using domain for Domain Controller users (instead of QNAP/<username>)
# Verify credentials: smbclient -L //192.168.1.194 -A ~/.config/nas_credentials
# Verify file permissions (chmod 600): stat -c %a "/path/to/file"
# Verify `What` path: showmount -e 192.168.1.194

# Verify the mount and contents
# findmnt /mnt/<share>
# ls -la /mnt/<share> | head -n 40

# If needing changes to take effect immediately, make sure mount is not busy and run
# `sudo umount /mnt/<share>` before the script

# systemctl disable mnt-<share>.automount

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# chmod +x ~/Repos/pc-env/setup-linux/mount-nas-systemd.sh
# sudo bash ~/Repos/pc-env/setup-linux/mount-nas-systemd.sh

# systemctl status mnt-<share>.automount mnt-<share>.mount
# journalctl -u mnt-<share>.mount
# journalctl -u mnt-Main.automount -n 200
