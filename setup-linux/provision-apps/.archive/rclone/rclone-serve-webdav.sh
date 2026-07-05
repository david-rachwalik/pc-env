#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

WEBDAV_DIRS=(
    "/mnt"
    "/media/root/HDD-01"
    # "/media/root/HDD-02"
)
JOINED_DIRS=$(
    IFS=:
    echo "${WEBDAV_DIRS[*]}"
)

REMOTE_NAME="localmedia"
STORAGE_TYPE="local" # Local Disk
ADDR="0.0.0.0:8181"
CONFIG_DIR="$HOME/.config/rclone"
# LOG_FILE="$CONFIG_DIR/logs/rclone-serve-webdav.log"

# Command Options to avoid with rclone:
# `--log-file` so stdout/stderr goes to `journalctl` with systemd

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# mkdir -p "$(dirname "$LOG_FILE")"

# echo "📂 Serving files over WebDAV..."
echo "🌐 Serving WebDAV on $ADDR with directories: $JOINED_DIRS"
# https://rclone.org/commands/rclone_serve_webdav
# Verify port is not in use: sudo lsof -i :8181
rclone serve webdav "$REMOTE_NAME:$JOINED_DIRS" \
    --addr $ADDR \
    --read-only \
    --log-level INFO
# --filters-file "$CONFIG_DIR/webdav-filters.txt" \
# --log-file "$LOG_FILE" \

# if [ $? -eq 0 ]; then
#     echo "✅ Serve WebDAV successful!  Logs: $LOG_FILE"
# else
#     echo "❗ Serve WebDAV failed.  Check logs: $LOG_FILE"
#     exit 1
# fi

if [ $? -eq 0 ]; then
    echo "✅ Serve WebDAV successful!"
else
    echo "❗ Serve WebDAV failed."
    exit 1
fi

# :: Usage Commands ::

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-serve-webdav.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-serve-webdav.sh
