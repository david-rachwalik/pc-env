#!/bin/bash
set -e

REMOTE_NAME="onedrive"
BISYNC_DIR="$HOME/OneDrive"
CONFIG_DIR="$HOME/.config/rclone"
FILTERS_FILE="$CONFIG_DIR/bisync-filters.txt"
BACKUP_DIR="$CONFIG_DIR/rclone-bisync-onedrive-backups"
TEMP_ERROR_LOG="/tmp/rclone-bisync-onedrive-error-$$.log"

# Command Options to avoid with rclone:
# `--log-file` so stdout/stderr goes to `journalctl` with systemd

# Perform initial bisync
initial_bisync() {
    echo "Starting initial bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    mkdir -p "$BISYNC_DIR" "$BACKUP_DIR"

    rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR" \
        --resync \
        --filters-file $FILTERS_FILE \
        --log-level INFO || {
        echo "❗ Initial bisync encountered an issue."
        exit 1
    }
    echo "✅ Initial bisync for $REMOTE_NAME ($BISYNC_DIR) completed!"
}

routine_bisync() {
    echo "🔄 Running rclone bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    
    # Attempt normal bisync, capture ALL output
    rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR" \
        --track-renames \
        --check-access \
        --filters-file "$FILTERS_FILE" \
        --log-level INFO 2>&1 | tee "$TEMP_ERROR_LOG"
    
    # Check output for errors (rclone bisync doesn't always use proper exit codes)
    if grep -q "filters file has changed" "$TEMP_ERROR_LOG" || \
       grep -q "Bisync critical error" "$TEMP_ERROR_LOG" || \
       grep -q "Bisync aborted" "$TEMP_ERROR_LOG"; then
        
        echo "⚠️  Bisync requires resync. Running --resync to recover..."
        
        rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR" \
            --resync \
            --filters-file "$FILTERS_FILE" \
            --log-level INFO || {
            echo "❗ Resync failed."
            rm -f "$TEMP_ERROR_LOG"
            exit 1
        }
        echo "✅ Resync completed successfully!"
        rm -f "$TEMP_ERROR_LOG"
        
    elif grep -q "Failed to bisync" "$TEMP_ERROR_LOG"; then
        echo "❗ Bisync failed with unknown error."
        cat "$TEMP_ERROR_LOG"
        rm -f "$TEMP_ERROR_LOG"
        exit 1
    else
        echo "✅ Bisync for $REMOTE_NAME ($BISYNC_DIR) completed!"
        rm -f "$TEMP_ERROR_LOG"
    fi
}

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Check if target directory is empty
if [ -z "$(ls -A "$BISYNC_DIR" 2>/dev/null)" ]; then
    echo "📂 Target directory is empty."
    initial_bisync
else
    routine_bisync
fi

# :: Usage Commands ::

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync-onedrive.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync-onedrive.sh


# View last 50 lines of OneDrive sync logs:
# journalctl -u rclone-bisync-onedrive.service -n 50

# View logs from today:
# journalctl -u rclone-bisync-onedrive.service --since today

# View logs from last sync:
# journalctl -u rclone-bisync-onedrive.service --since "6:00" --until "6:30"

# Follow logs in real-time:
# journalctl -u rclone-bisync-onedrive.service -f

# View all logs with timestamps:
# journalctl -u rclone-bisync-onedrive.service --no-pager
