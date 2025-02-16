#!/bin/bash

# Ensure the script is being run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please rerun with 'sudo'."
    exit 1
fi

# Set the username from the environment, fall back to 'root' if not found
USER="${USER:-root}"
DRIVES=(
    "/dev/sda2|/media/$USER/HDD-01"
    "/dev/sdb2|/media/$USER/HDD-02"
)

# Function to mount the drives
mount_drive() {
    local device mount_point
    device="$1"
    mount_point="$2"

    # Check if the device is already mounted
    if ! mount | grep -q "$mount_point"; then
        echo "Mounting $device to $mount_point..."
        mount -t ntfs-3g "$device" "$mount_point" || {
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
        echo "$device $mount_point ntfs-3g defaults,uid=1000,gid=1000,umask=0022 0 0" >>/etc/fstab
    else
        echo "$device $mount_point is already listed in /etc/fstab."
    fi
}

# Mount and add drives to fstab
for drive in "${DRIVES[@]}"; do
    # Split the drive string into device and mount point
    IFS="|" read -r device mount_point <<<"$drive"

    # Create the mount point directory if it doesn't exist
    if [ ! -d "$mount_point" ]; then
        echo "Creating mount point $mount_point..."
        mkdir -p "$mount_point" || {
            echo "Failed to create directory $mount_point"
            exit 1
        }
    fi

    # Mount the drive
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

# cd ~/Repos/pc-env/setup-linux/
# sudo bash ./mount_drives.sh

# - Other -
# sudo umount /dev/sda2         # Unmount the drive
# sudo ntfsfix /dev/sda2        # Check the NTFS partition status
