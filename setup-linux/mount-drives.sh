#!/usr/bin/env bash
set -euo pipefail # Exit immediately on error

DRIVES=(
    "/dev/sda2|/media/$USER/HDD-01"
    "/dev/sdb2|/media/$USER/HDD-02"
)

# Prefer the invoking user when run with sudo, fallback to root
USER="${SUDO_USER:-${USER:-root}}"
# Look up numeric uid/gid for the chosen user
MOUNT_UID="$(id -u "$USER")"
MOUNT_GID="$(id -g "$USER")"

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Ensure the script is running as root (or sudo privileges)
require_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "❌ This script must be run as root or with sudo.  Exiting..."
        exit 1
    fi
}

# Ensure the mount point directory exists (and is owned by the user)
create_mount_point() {
    local mount_point="$1"
    if [[ ! -d "$mount_point" ]]; then
        echo "Creating mount point: $mount_point"
        mkdir -p "$mount_point"
        chown "$USER":"$USER" "$mount_point" || true
    else
        echo "Mount point already exists: $mount_point"
    fi
}

# Function to mount the drives
mount_drive() {
    local device mount_point
    device="$1"
    mount_point="$2"

    # Check if the device is already mounted
    if ! mount | grep -q -- "$mount_point"; then
        echo "Mounting $device to $mount_point..."
        mount -t ntfs-3g -o uid="$MOUNT_UID",gid="$MOUNT_GID",allow_other "$device" "$mount_point" || {
            echo "Failed to mount $device"
            exit 1
        }
    else
        echo "$device is already mounted at $mount_point."
    fi
}

# Function to add a mount entry to fstab
add_to_fstab() {
    local device mount_point
    device="$1"
    mount_point="$2"

    # Check if it's already in fstab
    if ! grep -q "$device" /etc/fstab; then
        echo "Adding $device to /etc/fstab for persistent mounting..."
        echo "$device $mount_point ntfs-3g defaults,uid=${MOUNT_UID},gid=${MOUNT_GID},umask=0022 0 0" >>/etc/fstab
    else
        echo "$device $mount_point is already listed in /etc/fstab."
    fi
}

main () {
    require_root

    # Mount and add drives to fstab
    for drive in "${DRIVES[@]}"; do
        # Split the drive string into device and mount point
        IFS="|" read -r device mount_point <<<"$drive"
        # Mount the drive
        create_mount_point "$mount_point"
        mount_drive "$device" "$mount_point"
        # Add the mount to fstab
        add_to_fstab "$device" "$mount_point"
    done

    # Reload systemd to pick up the new fstab changes (if applicable)
    echo "Reloading systemd daemon to update fstab..."
    systemctl daemon-reload || {
        echo "Failed to reload systemd"
        exit 1
    }

    echo "Mount setup complete!"
}

main "$@"

# chmod +x ~/Repos/pc-env/setup-linux/mount-drives.sh
# sudo bash ~/Repos/pc-env/setup-linux/mount-drives.sh

# - Other -
# sudo ntfsfix /dev/sda2        # Check the NTFS partition status
# sudo umount /dev/sda2         # Unmount the drive
