#!/bin/bash
set -e

REMOTE_NAME="gdrive"
BISYNC_DIR="$HOME/ObsidianVaults"
CONFIG_DIR="$HOME/.config/rclone"
BACKUP_DIR="$CONFIG_DIR/rclone-bisync-gdrive-backups"

# Docker Container Paths
IMG_BISYNC_DIR="/ObsidianVaults"
IMG_CONFIG_DIR="/config"
IMG_BACKUP_DIR="$IMG_CONFIG_DIR/rclone-bisync-gdrive-backups"
# LOG_FILE="$IMG_CONFIG_DIR/logs/rclone-bisync-gdrive.log"
IMG_FILTERS_FILE="$IMG_CONFIG_DIR/bisync-filters.txt"

# Command Options to avoid with rclone:
# `--log-file` so stdout/stderr goes to `journalctl` with systemd

SCRIPT_DIR="$HOME/Repos/pc-env/docker/rclone/scripts"
source "$SCRIPT_DIR/rclone-alias.sh"

# Perform initial bisync
initial_bisync() {
    echo "Starting initial bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    mkdir -p "$BISYNC_DIR" "$BACKUP_DIR"
    # chown "$SUDO_USER":"$SUDO_USER" "$BISYNC_DIR" "$BACKUP_DIR"

    rclone bisync "$REMOTE_NAME:$(basename "$BISYNC_DIR")" "$IMG_BISYNC_DIR" \
        --resync \
        --workdir /workdir \
        --filters-file $IMG_FILTERS_FILE \
        --log-level INFO || {
        # --check-access \
        # --log-file "$LOG_FILE" \
        # --log-level INFO || {
        # echo "Bisync encountered an issue.  Check logs: $LOG_FILE"
        echo "❗ Initial bisync encountered an issue."
        exit 1
    }
    rm /workdir/*.lst-err /workdir/*.lst-new # clean out stale error files
    echo "✅ Initial bisync for $REMOTE_NAME ($BISYNC_DIR) completed!"
}

routine_bisync() {
    echo "🔄 Running rclone bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    rclone bisync "$REMOTE_NAME:$(basename "$BISYNC_DIR")" "$IMG_BISYNC_DIR" \
        --track-renames \
        --check-access \
        --workdir /workdir \
        --filters-file $IMG_FILTERS_FILE \
        --log-level INFO || {
        # --backup-dir "$IMG_BACKUP_DIR" \
        # --log-file "$LOG_FILE" \
        # --log-level INFO || {
        # echo "❗ Bisync failed. Check logs: $LOG_FILE"
        echo "❗ Bisync failed."
        exit 1
    }
    # echo "✅ Bisync completed! Logs: $LOG_FILE"
    echo "✅ Bisync for $REMOTE_NAME ($BISYNC_DIR) completed!"
}

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# mkdir -p "$BISYNC_DIR" "$IMG_BACKUP_DIR" "$(dirname "$LOG_FILE")"
# mkdir -p "$BISYNC_DIR" "$IMG_BACKUP_DIR"

# echo "🔄 Running rclone bisync..."
# rclone bisync "$REMOTE_NAME:$(basename "$BISYNC_DIR")" "$BISYNC_DIR" \
#     --track-renames \
#     --check-access \
#     --filters-file $IMG_FILTERS_FILE \
#     --backup-dir "$IMG_BACKUP_DIR" \
#     --log-level INFO
# # --log-file "$LOG_FILE" \

# Check if target directory is empty
if [ -z "$(ls -A "$BISYNC_DIR" 2>/dev/null)" ]; then
    echo "📂 Target directory is empty."
    initial_bisync
else
    routine_bisync
fi

# if [ $? -eq 0 ]; then
#     echo "✅ Bisync completed!  Logs: $LOG_FILE"
# else
#     echo "❗ Bisync failed.  Check logs: $LOG_FILE"
#     exit 1
# fi

# # Check the exit status directly
# if [ $? -eq 0 ]; then
#     echo "✅ Bisync completed!"
# else
#     echo "❗ Bisync failed."
#     exit 1
# fi

# :: Usage Commands ::

# chmod +x ~/Repos/pc-env/docker/rclone/scripts/rclone-bisync-gdrive.sh
# bash ~/Repos/pc-env/docker/rclone/scripts/rclone-bisync-gdrive.sh

# Check status of Google Drive sync:
# systemctl --user status rclone-bisync-gdrive

# systemctl --user restart rclone-bisync-gdrive

# View real-time logs:
# journalctl --user -u rclone-bisync-gdrive -f
