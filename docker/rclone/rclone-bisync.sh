#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# ================================================================
# Generic rclone bisync script - designed to run inside Docker
# https://rclone.org/commands/rclone_bisync
# ================================================================
# Usage: rclone-bisync.sh <remote_name> <sync_dir_name>

# Use 'declare -r' for readonly variables to prevent accidental reassignment
declare -r REMOTE_NAME="${1:-}"
declare -r SYNC_DIR_NAME="${2:-}"

# --- Container Paths ---
# These are mapped via Docker volumes to the host's actual folders
declare -r BISYNC_DIR="/data/$SYNC_DIR_NAME"
declare -r CONFIG_FILE="/etc/rclone/rclone.conf"
declare -r FILTERS_FILE="/etc/rclone/bisync-filters.txt"
declare -r LOCK_FILE="/cache/rclone-bisync-${REMOTE_NAME}.lock"

# --- Logging Paths ---
# Log files kept inside the mounted /logs volume
declare -r SUMMARY_LOG="/logs/summary.log"
declare -r DAILY_DIR="/logs/daily"
declare -r DAILY_LOG="${DAILY_DIR}/bisync-${REMOTE_NAME}-$(date +%Y-%m-%d).log"

# A temporary workspace file just for active script execution
# Used to analyze exact output of the current run before appending to daily log
declare -r RUN_LOG="/tmp/rclone-run-${REMOTE_NAME}.log"

# --- Function Definitions ---

validate_arguments() {
    # Ensure the script wasn't called blindly without targets
    if [[ -z "$REMOTE_NAME" ]] || [[ -z "$SYNC_DIR_NAME" ]]; then
        echo "❌ Usage: $0 <remote_name> <sync_dir_name>" >&2
        exit 1
    fi
}

setup_logging() {
    # Ensure base logging directory exists
    mkdir -p "$DAILY_DIR"

    # # Housekeeping: Delete daily logs older than 30 days
    # find "$DAILY_DIR" -type f -name "bisync-*.log" -mtime +30 -delete 2>/dev/null || true
}

log_summary() {
    # Appends a single, clean timestamped line to a tracking file
    # Ex: [2026-05-22 08:00:00] [pcloud] SUCCESS
    local message="$1"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [${REMOTE_NAME}] ${message}" >> "$SUMMARY_LOG"
}

handle_locking() {
    # Check if a previous run is still executing to prevent data corruption
    if [ -f "$LOCK_FILE" ]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE")
        # Check if the process indicated by the lock file is actively executing
        if ps -p "$lock_pid" > /dev/null 2>&1; then
            echo "⚠️  Lock file found and process $lock_pid is still running.  Aborting."
            log_summary "IGNORED - Process already running (PID $lock_pid)"
            exit 0
        else
            # Process died cleanly but left the lock file behind (safe to clean)
            echo "🧹 Stale lock file found for PID $lock_pid.  Removing."
            rm -f "$LOCK_FILE"
        fi
    fi

    # Create new lock file containing current Process ID ($$)
    # The trap ensures that when script exits (normally or via crash), the lock is deleted
    echo $$ > "$LOCK_FILE"
    trap 'rm -f "$LOCK_FILE"' EXIT
}

run_bisync() {
    echo "🚀 Running bisync check... (Verbose logs: $DAILY_LOG)"

    # Write daily log header for run clarity
    echo -e "\n=== Run Started: $(date +'%Y-%m-%d %H:%M:%S') ===" >> "$DAILY_LOG"

    local cmd=(
        rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR"
        --config "$CONFIG_FILE"
        --cache-dir "/cache"
        --workdir "/cache/bisync_workdir/${REMOTE_NAME}"
        --filters-file "$FILTERS_FILE"
        --track-renames
        --resilient   # Retries operations if the network falters
        -vv           # Verbose output for debug-level messages
    )

    # First Attempt: Write execution data to temporary file (RUN_LOG)
    set +e  # Temporarily disable standard error crashing
    "${cmd[@]}" > "$RUN_LOG" 2>&1
    local exit_code=$?
    set -e

    # Pipe data from temp execution into permanent daily log wrapper
    cat "$RUN_LOG" >> "$DAILY_LOG"

    # Analyze completion status using rclone standard Exit Codes
    if [ "$exit_code" -eq 0 ]; then
        echo "✅ Bisync completed successfully."
        log_summary "SUCCESS"
        return 0
    # Exit code 9: "resync is required" (e.g., missing listings, first run)
    # Exit code 7: Fatal error (e.g., filter hash mismatch on first run)
    # Exit code 1: "Safety abort: too many deletes" (e.g., large rename)
    # (grep from RUN_LOG, not DAILY_LOG, to avoid reading past executions)
    elif [[ "$exit_code" -eq 9 || "$exit_code" -eq 7 || ("$exit_code" -eq 1 && $(grep -c "Safety abort: too many deletes" "$RUN_LOG") -gt 0) ]]; then
        echo "⚠️  Bisync requires resync (Exit Code: $exit_code).  Attempting --resync now..."
        log_summary "WARNING - Require Resync (Exit $exit_code)"

        # Add --resync flag and execute again
        cmd+=(--resync)

        echo -e "\n=== RESYNC Started: $(date +'%Y-%m-%d %H:%M:%S') ===" >> "$DAILY_LOG"

        set +e
        "${cmd[@]}" > "$RUN_LOG" 2>&1
        local resync_exit_code=$?
        set -e

        cat "$RUN_LOG" >> "$DAILY_LOG"

        if [ "$resync_exit_code" -eq 0 ]; then
            echo "✅ Resync completed successfully."
            log_summary "SUCCESS (Recovered via --resync)"
            return 0
        else
            echo "❌ Resync attempt failed with exit code: $resync_exit_code"
            log_summary "FAILED - Resync attempt failed (Exit $resync_exit_code)"
            return "$resync_exit_code"
        fi
    else
        # The script hit an error code outside recovery protocols
        echo "❌ Bisync failed with a critical, non-recoverable error (Exit Code: $exit_code)."
        log_summary "FAILED - Critical error (Exit $exit_code)"
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

    log_summary "STARTED"
    handle_locking
    run_bisync

    echo "================================================================"
    echo ""
}

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
