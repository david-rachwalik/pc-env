#!/bin/bash
set -euo pipefail

# ================================================================
# Generic rclone bisync script - designed to run inside Docker
# https://rclone.org/commands/rclone_bisync
# ================================================================
# Usage: rclone-bisync.sh <remote_name> <sync_dir_name>

REMOTE_NAME="${1:-}"
SYNC_DIR_NAME="${2:-}"

if [[ -z "$REMOTE_NAME" ]] || [[ -z "$SYNC_DIR_NAME" ]]; then
    echo "❌ Usage: $0 <remote_name> <sync_dir_name>"
    exit 1
fi

# Define paths relative to the user's home directory inside the container
BISYNC_DIR="/data/$SYNC_DIR_NAME"
CONFIG_FILE="/etc/rclone/rclone.conf"
FILTERS_FILE="/etc/rclone/bisync-filters.txt"
LOG_FILE="/logs/bisync-${REMOTE_NAME}.log"
LOCK_FILE="/cache/rclone-bisync-${REMOTE_NAME}.lock"

# --- Logging Setup ---
mkdir -p "$(dirname "$LOG_FILE")"
exec > >(tee -a "$LOG_FILE") 2>&1 # instead of --log-file
# tee command redirects all output to both journalctl and log file

echo "================================================================"
echo "🔄 Starting bisync for '$REMOTE_NAME' at $(date)"
echo "   Local Dir: $BISYNC_DIR"
echo "================================================================"

# --- Lock File Handling ---
if [ -f "$LOCK_FILE" ]; then
    # Check if the process holding the lock is still running
    LOCK_PID=$(cat "$LOCK_FILE")
    if ps -p "$LOCK_PID" > /dev/null; then
        echo "⚠️  Lock file found and process $LOCK_PID is still running.  Aborting."
        exit 0
    else
        echo "🧹 Stale lock file found for PID $LOCK_PID.  Removing."
        rm -f "$LOCK_FILE"
    fi
fi
# Create a new lock file and ensure it's removed on exit
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# --- Pre-flight Debugging ---
echo "🔎 Performing pre-flight checks..."
echo "⚠️  Running as user:group → $(id -u):$(id -g)" # verify is not root
echo "Listing /etc/rclone contents:"
ls -la /etc/rclone || echo "Could not list /etc/rclone"
echo ""
# echo "Checking rclone.conf owner:"
# ls -ld "$CONFIG_FILE" || echo "Could not read rclone.conf"
# echo "---"
# echo "Checking bisync-filters.txt owner:"
# ls -ld "$FILTERS_FILE" || echo "Could not read bisync-filters.txt"
# echo "---"
# --- End Debugging ---

# --- Execute Bisync ---
echo "🚀 Running bisync check..."

# Build the command in an array
cmd=(
    rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR"
    --config "$CONFIG_FILE"
    --cache-dir "/cache"
    --workdir "/cache/bisync_workdir/${REMOTE_NAME}"
    --filters-file "$FILTERS_FILE"
    --track-renames
    --resilient
    # --verbose
    -vv # shows debug-level messages
    # --log-file="$LOG_FILE" # redundant and conflicts with the 'exec' redirection above
)
# --resilient: Helps with intermittent network errors
# --verbose: Provides detailed output for logging
# --log-file: Ensures rclone's output also goes to the log file

# Run the command and capture the exit code
# (use `set +e` to prevent the script from exiting if rclone returns a non-zero code)
set +e
"${cmd[@]}"
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Bisync completed successfully."
# Exit code 9: "resync is required" (e.g. missing listings)
# Exit code 7: Fatal error, which for bisync can mean a filter hash mismatch on first run
elif [ $EXIT_CODE -eq 9 ] || [ $EXIT_CODE -eq 7 ]; then
    echo "⚠️  Bisync requires resync (Exit Code: $EXIT_CODE).  Attempting now..."
    
    # Add the --resync flag and run again
    cmd+=(--resync)
    
    set +e
    "${cmd[@]}"
    RESYNC_EXIT_CODE=$?
    set -e

    if [ $RESYNC_EXIT_CODE -eq 0 ]; then
        echo "✅ Resync completed successfully."
    else
        echo "❌ Resync failed with exit code: $RESYNC_EXIT_CODE"
        exit $RESYNC_EXIT_CODE
    fi
else
    echo "❌ Bisync failed with a critical error (Exit Code: $EXIT_CODE)."
    exit $EXIT_CODE
fi

echo "================================================================"
echo ""

# :: Usage Examples ::
# chmod +x ~/Repos/pc-env/docker/rclone/rclone-bisync.sh
# ~/Repos/pc-env/docker/rclone/rclone-bisync.sh onedrive OneDrive
# ~/Repos/pc-env/docker/rclone/rclone-bisync.sh gdrive ObsidianVaults
# ~/Repos/pc-env/docker/rclone/rclone-bisync.sh pcloud pCloud


# View logs:
# journalctl -u rclone-bisync-pcloud.service --since "3 days ago"
# journalctl -u rclone-bisync-pcloud.service -n 50                    # Last 50 lines
# journalctl -u rclone-bisync-pcloud.service --since today            # Today's logs
# journalctl -u rclone-bisync-pcloud.service --since "6:00" -f        # Follow from 6am
# journalctl -u rclone-bisync-pcloud.service --no-pager --output=cat  # Clean output

# Check timer status:
# systemctl status rclone-bisync-pcloud.timer
# systemctl list-timers rclone-bisync-*

# Manual trigger (bypass timer):
# sudo systemctl start rclone-bisync-pcloud.service
