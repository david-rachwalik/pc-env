#!/bin/bash
set -euo pipefail

# Ensure the script is run as root (or sudo privileges)
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# ========= CONFIGURATION =========

# Format: ["ShareName"]="/mnt/LocalPath"
declare -A SHARE_MAP=(
    ["Portal"]="/mnt/Portal"
    ["NekoGooVideos"]="/mnt/NekoGooVideos"
    ["Main"]="/mnt/Main"
    ["PervyVR"]="/mnt/X"
    ["Emulation"]="/mnt/Z"
)

PROTOCOL="nfs" # or smb

# Protocol-specific defaults
if [[ $PROTOCOL == "nfs" ]]; then
    TYPE="nfs"
    OPTIONS="nfsvers=4.1,rsize=1048576,wsize=1048576,noatime"
elif [[ $PROTOCOL == "smb" ]]; then
    TYPE="cifs"
    OPTIONS="vers=3.0,credentials=/etc/smb-credentials,iocharset=utf8,uid=1000,gid=1000"
    # TODO: ensure `/etc/smb-credentials` exists (chmod 600) with lines:
    # username=*
    # password=*
else
    echo "❌ Unsupported protocol: $PROTOCOL"
    exit 1
fi

NAS_IP="192.168.0.4"
SYSTEMD_DIR="/etc/systemd/system"
IDLE_TIMEOUT="600" # seconds (10 min)

# ========= FUNCTIONS =============

create_mount_point() {
    local mount_point="$1"
    if [ ! -d "$mount_point" ]; then
        echo "Creating mount point: $mount_point"
        mkdir -p "$mount_point"
        # chown "$SUDO_USER":"$SUDO_USER" "$mount_point"
    fi
}

write_mount_unit() {
    local share="$1"
    local mount_point="$2"
    local unit_name="$3"

    cat <<EOF >"$SYSTEMD_DIR/$unit_name.mount"
[Unit]
Description=Mount for $share
After=network-online.target
Wants=network-online.target

[Mount]
What=${NAS_IP}:/${share}
Where=${mount_point}
Type=${TYPE}
Options=${OPTIONS},noauto,x-systemd.idle-timeout=${IDLE_TIMEOUT}
TimeoutSec=30

[Install]
WantedBy=multi-user.target
EOF
    # Verify `What` path: showmount -e 192.168.0.4
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

# enable_units() {
#     local mount_point="$1"
#     local unit_name="$2"

#     systemctl daemon-reload
#     systemctl enable --now "$unit_name.automount"
#     echo "Enabled + started automount for: $mount_point"
# }

get_unit_name() {
    local mount_point="$1"
    systemd-escape --path "$mount_point" | sed 's|^-||'
}

# ========== MAIN ==========

# Create mount unit configurations
for SHARE_NAME in "${!SHARE_MAP[@]}"; do
    MOUNT_POINT="${SHARE_MAP[$SHARE_NAME]}"
    UNIT_NAME=$(get_unit_name "$MOUNT_POINT")
    echo "🔧 Generating systemd units for $SHARE_NAME => $MOUNT_POINT"

    create_mount_point "$MOUNT_POINT"
    write_mount_unit "$SHARE_NAME" "$MOUNT_POINT" "$UNIT_NAME"
    write_automount_unit "$MOUNT_POINT" "$UNIT_NAME"
    # enable_units "$MOUNT_POINT" "$UNIT_NAME"

    echo ""
done

# Reload systemd and enable automounts
echo "🔄 Reloading systemd and enabling automounts..."
systemctl daemon-reload
for SHARE_NAME in "${!SHARE_MAP[@]}"; do
    MOUNT_POINT="${SHARE_MAP[$SHARE_NAME]}"
    UNIT_NAME=$(get_unit_name "$MOUNT_POINT")
    echo "🚀 Enabling + starting: $UNIT_NAME.automount"
    systemctl enable --now "$UNIT_NAME.automount"
done

echo "✅ All NAS shares configured with systemd .mount and .automount"

# chmod +x ~/Repos/pc-env/setup-linux/mount-nas-systemd.sh
# sudo bash ~/Repos/pc-env/setup-linux/mount-nas-systemd.sh

# systemctl status mnt-NFSShare.mount
# journalctl -u mnt-NFSShare.mount

# systemctl disable mnt-NFSShare.automount
