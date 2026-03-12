#!/bin/bash
set -e

REMOTE_NAME="gdrive"
BISYNC_DIR="$HOME/ObsidianVaults"
CONFIG_DIR="$HOME/.config/rclone"
FILTERS_FILE="$CONFIG_DIR/bisync-filters.txt"
BACKUP_DIR="$CONFIG_DIR/rclone-bisync-gdrive-backups"

# Command Options to avoid with rclone:
# `--log-file` so stdout/stderr goes to `journalctl` with systemd

# Perform initial bisync
initial_bisync() {
    echo "Starting initial bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    mkdir -p "$BISYNC_DIR" "$BACKUP_DIR"
    # chown "$SUDO_USER":"$SUDO_USER" "$BISYNC_DIR" "$BACKUP_DIR"

    rclone bisync "$REMOTE_NAME:$(basename $BISYNC_DIR)" "$BISYNC_DIR" \
        --resync \
        --filters-file $FILTERS_FILE \
        --log-level INFO || {
        # --workdir /workdir \
        # --check-access \
        # --log-file "$LOG_FILE" \
        # --log-level INFO || {
        # echo "Bisync encountered an issue.  Check logs: $LOG_FILE"
        echo "❗ Initial bisync encountered an issue."
        exit 1
    }
    # rm /workdir/*.lst-err /workdir/*.lst-new # clean out stale error files
    echo "✅ Initial bisync for $REMOTE_NAME ($BISYNC_DIR) completed!"
}

routine_bisync() {
    echo "🔄 Running rclone bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    rclone bisync "$REMOTE_NAME:$(basename "$BISYNC_DIR")" "$BISYNC_DIR" \
        --track-renames \
        --check-access \
        --filters-file $FILTERS_FILE \
        --log-level INFO || {
        # --workdir /workdir \
        # --backup-dir "$BACKUP_DIR" \
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

# mkdir -p "$BISYNC_DIR" "$BACKUP_DIR" "$(dirname "$LOG_FILE")"
# mkdir -p "$BISYNC_DIR" "$BACKUP_DIR"

# echo "🔄 Running rclone bisync..."
# rclone bisync "$REMOTE_NAME:$(basename "$BISYNC_DIR")" "$BISYNC_DIR" \
#     --track-renames \
#     --check-access \
#     --filters-file $FILTERS_FILE \
#     --backup-dir "$BACKUP_DIR" \
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

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync-gdrive.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync-gdrive.sh
