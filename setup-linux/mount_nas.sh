#!/bin/bash

# Ensure the script is being run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root"
    exit 1
fi

CREDENTIALS_FILE="$1"
SUPPORTED_PROTOCOLS=("cifs" "smb" "nfs")
PROTOCOL="${PROTOCOL:-smb}" # Default to NFS if not set

# NAS IP and shares
NAS_IP="${NAS_IP:-192.168.0.4}"
if [ "$PROTOCOL" = "nfs" ]; then
    MOUNT_OPTS="defaults,nfsvers=4.1,rsize=1048576,wsize=1048576,noatime"
elif [ "$PROTOCOL" = "smb" ]; then
    MOUNT_OPTS="iocharset=utf8,vers=3.0,uid=1000,gid=1000"
else
    MOUNT_OPTS=""
fi
declare -A SHARE_MOUNT_POINTS=(
    ["Portal"]="/mnt/Portal"
    ["NekoGooVideos"]="/mnt/NekoGooVideos"
    ["Main"]="/mnt/Main"
    ["PervyVR"]="/mnt/X"
    ["Emulation"]="/mnt/Z"
)

# Check for credential file argument
if [ "$PROTOCOL" = "smb" ] && [ -z "$1" ]; then
    echo "Error: Please provide the path to the credentials file as an argument."
    exit 1
fi

# Validate the protocol
if [[ ! " ${SUPPORTED_PROTOCOLS[@]} " =~ " ${PROTOCOL} " ]]; then
    echo "Error: Unsupported protocol '$PROTOCOL'. Supported protocols are: ${SUPPORTED_PROTOCOLS[*]}"
    exit 1
fi

# Check if the credentials file exists (only required for SMB)
if [ "$PROTOCOL" = "smb" ] && [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Error: Credentials file '$CREDENTIALS_FILE' not found."
    exit 1
fi

create_mount_point() {
    local mount_point="$1"
    if [ ! -d "$mount_point" ]; then
        echo "Creating mount point: $mount_point"
        mkdir -p "$mount_point"
    else
        echo "Mount point already exists: $mount_point"
    fi
}

# Add fstab entry for the share
add_to_fstab() {
    local share_name="$1"
    local mount_point="$2"
    local fstab_entry="${NAS_IP}:/Share/${share_name} ${mount_point} nfs ${MOUNT_OPTS} 0 0"

    if [ "$PROTOCOL" = "nfs" ]; then
        # Remove old conflicting CIFS/SMB entries if they exist
        if grep -qs "//${NAS_IP}/${share_name}" /etc/fstab; then
            echo "Removing old CIFS entry for ${share_name}"
            sed -i "\|//${NAS_IP}/${share_name}|d" /etc/fstab
            umount "$mount_point"
        fi
    else
        # Remove old conflicting NFS entries if they exist
        if grep -qs "${NAS_IP}:/Share/${share_name}" /etc/fstab; then
            echo "Removing old NFS entry for ${share_name}"
            sed -i "\|${NAS_IP}:/Share/${share_name}|d" /etc/fstab
            umount "$mount_point"
        fi

        # _netdev: Ensures the mount happens only after the network is ready
        # x-systemd.automount: Delays mounting until the share is accessed
        fstab_entry="//${NAS_IP}/${share_name} ${mount_point} cifs credentials=${CREDENTIALS_FILE},iocharset=utf8,vers=3.0,uid=1000,gid=1000,_netdev,x-systemd.automount 0 0"
    fi

    # Check if the fstab entry exists and matches
    # if ! grep -qs "^//${NAS_IP}/${share_name}" /etc/fstab; then
    # if ! grep -qs "${NAS_IP}:/share/${share_name}" /etc/fstab || ! grep -qs "$mount_point" /etc/fstab; then
    if ! grep -qsF "$fstab_entry" /etc/fstab; then
        echo "Updating fstab entry for ${share_name}"
        # # Remove old conflicting entries
        # sed -i "\|//${NAS_IP}/${share_name}|d" /etc/fstab
        # sed -i "\|${NAS_IP}:/share/${share_name}|d" /etc/fstab
        # umount "$mount_point"
        echo "$fstab_entry" >>/etc/fstab
    fi
}

mount_share() {
    local mount_point="$1"
    if mountpoint -q "$mount_point"; then
        echo "$mount_point is already mounted"
    else
        echo "Mounting $mount_point"
        mount "$mount_point"
    fi
}

# Ensure shares are configured and mounted
for SHARE_NAME in "${!SHARE_MOUNT_POINTS[@]}"; do
    MOUNT_POINT="${SHARE_MOUNT_POINTS[$SHARE_NAME]}"
    create_mount_point "$MOUNT_POINT"
    add_to_fstab "$SHARE_NAME" "$MOUNT_POINT"
    mount_share "$MOUNT_POINT"
done

echo "Mount setup complete!"

# chmod +x ~/Repos/pc-env/setup-linux/mount_nas.sh
# sudo bash ~/Repos/pc-env/setup-linux/mount_nas.sh ~/.config/nas_credentials

# :: Credential file format ::
# username=admin
# password=<password>
