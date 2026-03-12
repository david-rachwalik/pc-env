#!/bin/bash
set -euo pipefail

# ----------------------------------------------------------------
# Generic rclone bisync script for any cloud platform
# filepath: /workspaces/pc-env/setup-linux/provision-apps/rclone/rclone-bisync.sh
# Usage: rclone-bisync.sh <remote_name> <sync_dir>
# ----------------------------------------------------------------

REMOTE_NAME="${1:-}"
SYNC_DIR_NAME="${2:-}"

if [[ -z "$REMOTE_NAME" ]] || [[ -z "$SYNC_DIR_NAME" ]]; then
    echo "❌ Usage: $0 <remote_name> <sync_dir>"
    echo "   Example: $0 onedrive OneDrive"
    exit 1
fi

BISYNC_DIR="$HOME/$SYNC_DIR_NAME"
CONFIG_DIR="$HOME/.config/rclone"
FILTERS_FILE="$CONFIG_DIR/bisync-filters.txt"

# Our bash script lock file
SCRIPT_LOCK_FILE="$CONFIG_DIR/rclone-bisync-${REMOTE_NAME}.lock"
SCRIPT_LOCK_TIMEOUT_HOURS=6  # Consider stale if older than 6 hours

# rclone's internal bisync lock file
RCLONE_CACHE_DIR="$HOME/.cache/rclone/bisync"
BISYNC_DIR_ESCAPED=$(echo "$BISYNC_DIR" | sed 's|/|..|g')
RCLONE_LOCK_FILE="$RCLONE_CACHE_DIR/${REMOTE_NAME}_${BISYNC_DIR_ESCAPED}.lck"

# ----------------------------------------------------------------
# Lock Management (prevent concurrent runs)
# ----------------------------------------------------------------

# Our bash script lock - prevents multiple systemd timers from running
acquire_script_lock() {
    if [[ -f "$SCRIPT_LOCK_FILE" ]]; then
        local lock_pid
        lock_pid=$(cat "$SCRIPT_LOCK_FILE" 2>/dev/null || echo "")
        
        # Check if process is still running
        if [[ -n "$lock_pid" ]] && kill -0 "$lock_pid" 2>/dev/null; then
            # Check if lock is stale (older than timeout)
            local lock_age
            lock_age=$(( $(date +%s) - $(stat -c %Y "$SCRIPT_LOCK_FILE" 2>/dev/null || echo 0) ))
            local lock_timeout_seconds=$((SCRIPT_LOCK_TIMEOUT_HOURS * 3600))
            
            if (( lock_age > lock_timeout_seconds )); then
                echo "⚠️  Script lock file is stale (${lock_age}s old, PID: $lock_pid). Force removing."
                rm -f "$SCRIPT_LOCK_FILE"
            else
                echo "⚠️  Another bisync is running (PID: $lock_pid, age: ${lock_age}s). Exiting."
                exit 0
            fi
        else
            echo "ℹ️  Removing stale script lock file (PID $lock_pid no longer exists)"
            rm -f "$SCRIPT_LOCK_FILE"
        fi
    fi
    
    echo $$ > "$SCRIPT_LOCK_FILE"
}

release_script_lock() {
    rm -f "$SCRIPT_LOCK_FILE"
}

trap release_script_lock EXIT

# rclone's bisync lock - check and clean if stale
check_rclone_lock() {
    if [[ ! -f "$RCLONE_LOCK_FILE" ]]; then
        return 0  # No lock file, all good
    fi
    
    echo "🔍 Found rclone lock file, checking if stale..."
    
    # Extract PID from JSON lock file
    local lock_pid
    lock_pid=$(grep -oP '"PID": "\K[0-9]+' "$RCLONE_LOCK_FILE" 2>/dev/null || echo "")
    
    if [[ -z "$lock_pid" ]]; then
        echo "⚠️  Malformed rclone lock file, removing..."
        rm -f "$RCLONE_LOCK_FILE"
        return 0
    fi
    
    # Check if that process is still running
    if ! kill -0 "$lock_pid" 2>/dev/null; then
        echo "⚠️  Stale rclone lock (PID $lock_pid not running), removing..."
        rm -f "$RCLONE_LOCK_FILE"
        return 0
    fi
    
    # Check for unreasonably far future expiration (bug in rclone)
    # Year 2100 = 4102444800 epoch seconds
    local lock_expires
    lock_expires=$(grep -oP '"TimeExpires": "\K[^"]+' "$RCLONE_LOCK_FILE" 2>/dev/null || echo "")
    
    if [[ -n "$lock_expires" ]]; then
        local expires_epoch
        expires_epoch=$(date -d "$lock_expires" +%s 2>/dev/null || echo "0")
        
        if (( expires_epoch > 4102444800 )); then
            echo "⚠️  Rclone lock has invalid expiration ($lock_expires), removing..."
            rm -f "$RCLONE_LOCK_FILE"
            return 0
        fi
    fi
    
    echo "❌ Valid rclone lock exists (active process $lock_pid)"
    return 1
}

# ----------------------------------------------------------------
# Pre-flight Checks
# ----------------------------------------------------------------

preflight_checks() {
    echo "🔍 Running pre-flight checks for $REMOTE_NAME..."
    
    # Check if remote exists
    if ! rclone listremotes 2>/dev/null | grep -q "^${REMOTE_NAME}:$"; then
        echo "❌ Remote '$REMOTE_NAME' is not configured."
        echo "   Run: rclone config create \"$REMOTE_NAME\" <storage_type>"
        exit 1
    fi

    # Check if filters file exists
    if [[ ! -f "$FILTERS_FILE" ]]; then
        echo "⚠️  Filters file not found at: $FILTERS_FILE"
        echo "   Creating default filters..."
        mkdir -p "$CONFIG_DIR"
        cat <<'EOF' > "$FILTERS_FILE"
- Personal Vault/
- Personal Vault/**
- node_modules/
- node_modules/**
- .Trash-*
- .DS_Store
- *.tmp
- .obsidian/workspace.json
- *conflicted copy*
- *.onedrive
EOF
        echo "✅ Created default filters"
    fi
    
    # Test remote connectivity
    echo "🔗 Testing connectivity to $REMOTE_NAME..."
    if ! rclone lsf "$REMOTE_NAME:" --max-depth 1 &>/dev/null; then
        echo "❌ Cannot connect to $REMOTE_NAME. Check authentication/network."
        exit 1
    fi
    
    echo "✅ Pre-flight checks passed"
}

# ----------------------------------------------------------------
# Filter Change Detection
# ----------------------------------------------------------------

check_filters_changed() {
    local filters_hash_file="$CONFIG_DIR/.${REMOTE_NAME}-filters-hash"
    local current_hash
    current_hash=$(md5sum "$FILTERS_FILE" 2>/dev/null | cut -d' ' -f1)
    
    if [[ -f "$filters_hash_file" ]]; then
        local stored_hash
        stored_hash=$(cat "$filters_hash_file" 2>/dev/null || echo "")
        if [[ "$current_hash" != "$stored_hash" ]]; then
            echo "⚠️  Filters changed since last sync - will trigger resync"
            return 0  # Changed
        fi
    fi
    
    # Store hash for next time
    echo "$current_hash" > "$filters_hash_file"
    return 1  # Not changed
}

# ----------------------------------------------------------------
# Bisync Operations
# ----------------------------------------------------------------

run_bisync() {
    local resync_needed=false
    
    # Determine if we need --resync
    if [[ -z "$(ls -A "$BISYNC_DIR" 2>/dev/null)" ]]; then
        echo "📂 Target directory is empty - initial sync required"
        resync_needed=true
    elif check_filters_changed; then
        echo "🔄 Filters changed - resync required"
        resync_needed=true
    fi
    
    # Prepare directory
    mkdir -p "$BISYNC_DIR"
    
    # Build rclone command
    local rclone_cmd=(
        rclone bisync
        "$REMOTE_NAME:"
        "$BISYNC_DIR"
        --filters-file "$FILTERS_FILE"
        --create-empty-src-dirs
        --log-level INFO
    )
    
    if [[ "$resync_needed" == true ]]; then
        echo "🔄 Running bisync with --resync..."
        rclone_cmd+=(--resync)
    else
        echo "🔄 Running routine bisync..."
        rclone_cmd+=(
            --check-access
            --track-renames
            --resilient
            --recover
        )
    fi
    
    # Execute bisync
    if "${rclone_cmd[@]}"; then
        echo "✅ Bisync completed successfully!"
        return 0
    else
        local exit_code=$?
        echo "❌ Bisync failed with exit code: $exit_code"
        echo ""
        echo "Common fixes:"
        echo "  1. Network issues - will auto-retry on next scheduled run"
        echo "  2. Sync conflicts - manually resolve and run:"
        echo "     rclone bisync \"$REMOTE_NAME:\" \"$BISYNC_DIR\" --resync --filters-file \"$FILTERS_FILE\""
        echo "  3. Check logs: journalctl -u rclone-bisync-${REMOTE_NAME} -n 50"
        return $exit_code
    fi
}


initial_bisync() {
    echo "🔄 Starting initial bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    mkdir -p "$BISYNC_DIR"

    rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR" \
        --resync \
        --filters-file "$FILTERS_FILE" \
        --create-empty-src-dirs \
        --log-level INFO || {
        echo "❌ Initial bisync failed."
        exit 1
    }
    
    echo "✅ Initial bisync for $REMOTE_NAME ($BISYNC_DIR) completed!"
}

routine_bisync() {
    echo "🔄 Running routine bisync for $REMOTE_NAME ($BISYNC_DIR)..."
    
    # Check if filters changed (would invalidate bisync state)
    local filters_changed=false
    local filters_hash_file="$CONFIG_DIR/.${REMOTE_NAME}-filters-hash"
    local current_hash
    current_hash=$(md5sum "$FILTERS_FILE" | cut -d' ' -f1)
    
    if [[ -f "$filters_hash_file" ]]; then
        local stored_hash
        stored_hash=$(cat "$filters_hash_file")
        if [[ "$current_hash" != "$stored_hash" ]]; then
            filters_changed=true
            echo "⚠️  Filters file changed since last sync!"
            echo "   This requires a --resync. Running initial bisync instead..."
        fi
    fi
    
    if [[ "$filters_changed" == "true" ]]; then
        initial_bisync
        echo "$current_hash" > "$filters_hash_file"
        return
    fi
    
    # Store filters hash for first run
    if [[ ! -f "$filters_hash_file" ]]; then
        echo "$current_hash" > "$filters_hash_file"
    fi
    
    # Run routine bisync
    rclone bisync "$REMOTE_NAME:" "$BISYNC_DIR" \
        --track-renames \
        --check-access \
        --filters-file "$FILTERS_FILE" \
        --create-empty-src-dirs \
        --resilient \
        --recover \
        --log-level INFO || {
        echo "❌ Bisync failed."
        echo "   You may need to run a manual --resync:"
        echo "   rclone bisync \"$REMOTE_NAME:\" \"$BISYNC_DIR\" --resync --filters-file \"$FILTERS_FILE\""
        exit 1
    }
    
    echo "✅ Bisync for $REMOTE_NAME ($BISYNC_DIR) completed!"
}


# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------

main() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 rclone bisync: $REMOTE_NAME → $BISYNC_DIR"
    echo "   Started: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    acquire_script_lock
    preflight_checks

    # Check and clean rclone's internal lock if stale
    if ! check_rclone_lock; then
        echo "❌ Another bisync is currently running. Exiting to avoid conflicts."
        exit 1
    fi
    
    # # Check if this is initial sync or routine
    # if [[ -z "$(ls -A "$BISYNC_DIR" 2>/dev/null)" ]]; then
    #     echo "📂 Target directory is empty - running initial sync"
    #     initial_bisync
    # else
    #     routine_bisync
    # fi

    run_bisync
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "   Finished: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

main

# :: Usage Examples ::

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync.sh

# Manual runs:
# ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync.sh onedrive OneDrive
# ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync.sh gdrive ObsidianVaults
# ~/Repos/pc-env/setup-linux/provision-apps/rclone/rclone-bisync.sh pcloud pCloud


# View logs:
# journalctl -u rclone-bisync-onedrive.service -n 50                    # Last 50 lines
# journalctl -u rclone-bisync-onedrive.service --since today            # Today's logs
# journalctl -u rclone-bisync-onedrive.service --since "6:00" -f        # Follow from 6am
# journalctl -u rclone-bisync-onedrive.service --no-pager --output=cat  # Clean output

# Check timer status:
# systemctl status rclone-bisync-onedrive.timer
# systemctl list-timers rclone-bisync-*

# Manual trigger (bypass timer):
# sudo systemctl start rclone-bisync-onedrive.service
