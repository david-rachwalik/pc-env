#!/bin/bash
set -e

REMOTE_NAME="gdrive"
MOUNT_DIR="$HOME/GoogleDrive"
# CONFIG_DIR="$HOME/.config/rclone"

# Docker Container Paths
IMG_MOUNT_DIR="/GoogleDrive"
# IMG_CONFIG_DIR="/config"
IMG_CACHE_DIR="/cache"
# LOG_FILE="$IMG_CONFIG_DIR/logs/rclone-mount-gdrive.log"

# Command Options to avoid with rclone:
# `--log-file` so stdout/stderr goes to `journalctl` with systemd
# `--dry-run` not supported by `rclone mount`

SCRIPT_DIR="$HOME/Repos/pc-env/docker/rclone/scripts"
source "$SCRIPT_DIR/rclone-alias.sh"

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# mkdir -p "$MOUNT_DIR" "$(dirname "$LOG_FILE")"
mkdir -p "$MOUNT_DIR"

# /usr/bin/rclone mount gdrive: /home/YOUR_USERNAME/GoogleDrive \
#     --vfs-cache-mode full \
#     --vfs-cache-max-age 24h \
#     --vfs-cache-max-size 10G \
#     --dir-cache-time 12h \
#     --poll-interval 5m \

echo "📂 Mounting Google Drive to $MOUNT_DIR..."
# https://rclone.org/commands/rclone_mount
rclone mount "$REMOTE_NAME:" "$IMG_MOUNT_DIR" \
    --allow-other \
    --allow-non-empty \
    --cache-dir $IMG_CACHE_DIR \
    --vfs-cache-mode writes \
    --vfs-cache-max-age 24h \
    --log-level INFO
# --log-file "$LOG_FILE" \
# https://rclone.org/commands/rclone_mount/#vfs-file-caching
# `--filters-file` works to hide stuff, but it will upload if copied to mount

# if [ $? -eq 0 ]; then
#     echo "✅ Mount successful!  Logs: $LOG_FILE"
# else
#     echo "❗ Mount failed.  Check logs: $LOG_FILE"
#     exit 1
# fi

if [ $? -eq 0 ]; then
    echo "✅ Mount for $REMOTE_NAME ($MOUNT_DIR) successful!"
else
    echo "❗ Mount for $REMOTE_NAME ($MOUNT_DIR) failed."
    exit 1
fi

# :: Usage Commands ::

# chmod +x ~/Repos/pc-env/docker/rclone/scripts/rclone-mount-gdrive.sh
# bash ~/Repos/pc-env/docker/rclone/scripts/rclone-mount-gdrive.sh

# Check status of Google Drive sync:
# systemctl --user status rclone-mount-gdrive

# View real-time logs:
# journalctl --user -u rclone-mount-gdrive -f
# journalctl -u rclone-mount-gdrive.service
