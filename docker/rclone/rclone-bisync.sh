#!/bin/bash
set -euo pipefail

# ================================================================
# Generic rclone bisync script - designed to run inside Docker
# https://rclone.org/commands/rclone_bisync
# ================================================================
# Usage: rclone-bisync.sh <remote_name> <sync_dir_name>

# Use 'declare -r' to make them readonly after initial assignment
declare -r REMOTE_NAME="${1:-}"
declare -r SYNC_DIR_NAME="${2:-}"

# Define paths relative to the user's home directory inside the container
declare -r BISYNC_DIR="/data/$SYNC_DIR_NAME"
declare -r CONFIG_FILE="/etc/rclone/rclone.conf"
declare -r FILTERS_FILE="/etc/rclone/bisync-filters.txt"
declare -r LOG_FILE="/logs/bisync-${REMOTE_NAME}.log"
declare -r LOCK_FILE="/cache/rclone-bisync-${REMOTE_NAME}.lock"


# --- Function Definitions ---

# Validates that the required script arguments have been provided
validate_arguments() {
    if [[ -z "$REMOTE_NAME" ]] || [[ -z "$SYNC_DIR_NAME" ]]; then
        # Write error to stderr
        echo "❌ Usage: $0 <remote_name> <sync_dir_name>" >&2
        exit 1
    fi
}

# Sets up logging to redirect all output to a log file and stdout
setup_logging() {
    mkdir -p "$(dirname "$LOG_FILE")"
    # Redirect all subsequent output (stdout and stderr) to a process substitution
    # that tees to the log file and also prints to the original stdout
    exec > >(tee -a "$LOG_FILE") 2>&1
    # (superior to using `--log-file` in command)
}

# Handles lock file creation and cleanup to prevent concurrent runs
handle_locking() {
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE")
        # Check if process holding the lock is still running
        if ps -p "$lock_pid" > /dev/null; then
            echo "⚠️  Lock file found and process $lock_pid is still running.  Aborting."
            exit 0 # Exit gracefully, not as an error
        else
            echo "🧹 Stale lock file found for PID $lock_pid.  Removing."
            rm -f "$LOCK_FILE"
        fi
    fi
    # Create new lock file (with current PID) that removes on exit
    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT
}

# Executes the main bisync command with intelligent error handling and one-time retry
run_bisync() {
    echo "🚀 Running bisync check..."

    # Build the base command in an array for robustness
    local cmd=(
        rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR"
        --config "$CONFIG_FILE"
        --cache-dir "/cache"
        --workdir "/cache/bisync_workdir/${REMOTE_NAME}"
        --filters-file "$FILTERS_FILE"
        --track-renames
        --resilient
        # --verbose
        -vv # debug-level messages
    )
    # --resilient: Helps with intermittent network errors
    # --verbose: Provides detailed output for logging

    # --- First Attempt ---
    local stderr_output
    local exit_code
    set +e # Temporarily disable exit-on-error
    stderr_output=$("${cmd[@]}" 2>&1)
    exit_code=$?
    set -e # Re-enable exit-on-error

    # Always print the output, whether it was an error or not
    echo "$stderr_output"

    # --- Analyze Result and Potentially Retry ---
    if [ "$exit_code" -eq 0 ]; then
        echo "✅ Bisync completed successfully."
        return 0
    # Exit code 9: "resync is required" (e.g., missing listings, first run)
    # Exit code 7: Fatal error (e.g., filter hash mismatch on first run)
    # Exit code 1 + specific message: "Safety abort: too many deletes" (e.g., large rename)
    elif [[ "$exit_code" -eq 9 || "$exit_code" -eq 7 || ("$exit_code" -eq 1 && $(echo "$stderr_output" | grep -c "Safety abort: too many deletes") -gt 0) ]]; then
        echo "⚠️  Bisync requires resync (Exit Code: $exit_code). This may be due to a large rename or first-time sync. Attempting --resync now..."

        # Add the --resync flag and run again
        cmd+=(--resync)
        
        local resync_stderr_output
        local resync_exit_code
        set +e
        resync_stderr_output=$("${cmd[@]}" 2>&1)
        resync_exit_code=$?
        set -e
        echo "$resync_stderr_output"

        if [ "$resync_exit_code" -eq 0 ]; then
            echo "✅ Resync completed successfully."
            return 0
        else
            echo "❌ Resync attempt failed with exit code: $resync_exit_code"
            return "$resync_exit_code"
        fi
    else
        echo "❌ Bisync failed with a critical, non-recoverable error (Exit Code: $exit_code)."
        return "$exit_code"
    fi
}

# --- Main Execution ---
main() {
    validate_arguments
    setup_logging

    echo "================================================================"
    echo "🔄 Starting bisync for '$REMOTE_NAME' at $(date)"
    echo "   Local Dir: $BISYNC_DIR"
    echo "================================================================"

    handle_locking
    run_bisync

    echo "================================================================"
    echo ""
}

# Call the main function with all script arguments
main "$@"

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
