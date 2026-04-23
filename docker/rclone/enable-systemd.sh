#!/bin/bash
set -euo pipefail

# ================================================================
# Provision rclone bisync services using one-shot Docker containers
# ================================================================
# This script is idempotent. It can be run multiple times safely.

# --- Configuration ---

# An array defining the bisync jobs.
# Format: "remote_name;sync_directory_name;OnCalendar_schedule"
# OnCalendar format: https://www.freedesktop.org/software/systemd/man/systemd.time.html#OnCalendar=
declare -a BISYNC_JOBS=(
    # "onedrive;OneDrive;daily"
    # "pcloud;pCloud;daily"
    # "gdrive;ObsidianVaults;daily"
    # "onedrive;OneDrive;*-*-* 06:00:00"
    "pcloud;pCloud;*-*-* 06:05:00"
    "gdrive;GoogleDrive;*-*-* 06:10:00"
)

# --- Script Setup ---

# Ensure the script is run with sudo privileges
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# Ensure SUDO_USER is set
if [[ -z "${SUDO_USER:-}" ]]; then
    echo "❌ SUDO_USER is not set.  Please run with 'sudo' instead of as root.  Exiting..."
    exit 1
fi

# Define key paths
SYSTEMD_DIR="/etc/systemd/system"
USER_HOME_DIR=$(getent passwd "$SUDO_USER" | cut -d: -f6)
echo "⚠️  USER_HOME_DIR: ${USER_HOME_DIR}"
DEV_PROJECT_DIR="$USER_HOME_DIR/Repos/pc-env/docker/rclone"
RCLONE_CONFIG_DIR="$USER_HOME_DIR/.config/rclone"
RCLONE_CACHE_DIR="$USER_HOME_DIR/.cache/rclone"
LOG_DIR="$USER_HOME_DIR/logs/rclone"

# --- Helper Functions ---

# Creates a directory if it doesn't exist and ensures it's owned by the user
ensure_dir() {
    local dir_path="$1"
    mkdir -p "$dir_path"
    chown -R "$SUDO_USER:$SUDO_USER" "$dir_path"
}

# Checks if a remote is configured for the user
check_remote_configured() {
    local remote_name="$1"
    if sudo -u "$SUDO_USER" rclone listremotes 2>/dev/null | grep -q "^${remote_name}:"; then
        return 0
    else
        return 1
    fi
}

# Prints instructions for manual configuration
print_config_instructions() {
    local remote_name="$1"
    echo "⚠️  Remote '${remote_name}' is not configured. Please run as user '$SUDO_USER':"
    echo "    rclone config"
    echo "   After configuring, re-run this script to enable the service."
}

# Creates a systemd service file for a one-shot Docker bisync
create_docker_bisync_service() {
    local remote_name="$1"
    local sync_dir_name="$2"
    local service_name="rclone-bisync-$remote_name"

    cat <<EOF >"$SYSTEMD_DIR/$service_name.service"
[Unit]
Description=Rclone Bisync for $remote_name via Docker
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
User=$SUDO_USER
Group=$SUDO_USER
Environment="HOME=/home/$SUDO_USER"

# Change to the docker-compose project directory first
WorkingDirectory=$DEV_PROJECT_DIR

# Run the one-shot container, passing the remote and sync directory name
# The '--rm' flag ensures the container is deleted after the job completes
ExecStart=/usr/bin/docker compose run --rm rclone "$remote_name" "$sync_dir_name"

StandardOutput=journal
StandardError=journal
EOF
    echo "✅ Created/Updated service: $service_name.service"
    echo "  - $SYSTEMD_DIR/$service_name.service"
}

# Creates a systemd timer file to trigger the bisync service
create_bisync_timer() {
    local remote_name="$1"
    local schedule="$2"
    local service_name="rclone-bisync-$remote_name"

    cat <<EOF >"$SYSTEMD_DIR/$service_name.timer"
[Unit]
Description=Run rclone bisync for $remote_name on a schedule

[Timer]
OnCalendar=$schedule
# Add a random delay to avoid all jobs starting at once on boot
RandomizedDelaySec=15min
# Run job if it was missed due to downtime
Persistent=true

[Install]
WantedBy=timers.target
EOF
    echo "✅ Created/Updated timer: $service_name.timer"
    echo "  - $SYSTEMD_DIR/$service_name.timer"
}

# --- Main Execution ---

main() {
    echo "🚀 Starting rclone bisync provisioning..."

    # --- Automated Environment Setup ---
    echo "🔧 Ensuring host directories exist and have correct permissions..."
    ensure_dir "$LOG_DIR"
    ensure_dir "$RCLONE_CONFIG_DIR"
    ensure_dir "$RCLONE_CACHE_DIR"
    # Also handle the sync directories
    for job in "${BISYNC_JOBS[@]}"; do
        IFS=';' read -r _ sync_dir_name _ <<< "$job"
        ensure_dir "$USER_HOME_DIR/$sync_dir_name"
    done
    # Sync the filter file to the host's rclone config directory
    # (rsync will only copy the file if source is newer than destination)
    echo "🔧 Syncing dev 'bisync-filters.txt' to host config..."
    rsync -u "${DEV_PROJECT_DIR}/config/bisync-filters.txt" "${RCLONE_CONFIG_DIR}/bisync-filters.txt"
    chown "$SUDO_USER:$SUDO_USER" "${RCLONE_CONFIG_DIR}/bisync-filters.txt"
    echo "✅ Host directories are ready."

    # Build the Docker image if it doesn't exist
    # (Docker's layer caching makes this fast and efficient)
    echo "📦 Building rclone Docker image..."
    # Run build as the original user to avoid permission issues on docker context
    sudo -u "$SUDO_USER" bash -c "cd '$DEV_PROJECT_DIR' && docker compose build"
    echo "✅ Docker image built."

    # Loop through the defined jobs
    for job in "${BISYNC_JOBS[@]}"; do
        IFS=';' read -r remote_name sync_dir_name schedule <<< "$job"
        
        echo ""
        echo "🔧 Processing job for: $remote_name"

        # Check if the remote is configured before setting up the service
        if ! check_remote_configured "$remote_name"; then
            print_config_instructions "$remote_name"
            echo "⏭️  Skipping setup for $remote_name."
            continue
        fi

        # Create the service and timer files
        create_docker_bisync_service "$remote_name" "$sync_dir_name"
        create_bisync_timer "$remote_name" "$schedule"

        # Enable the timer
        echo "Enabling timer for $remote_name..."
        systemctl enable "rclone-bisync-$remote_name.timer"
    done

    echo ""
    echo "🔄 Reloading systemd daemon to apply changes..."
    systemctl daemon-reload

    # Restart timers to ensure they are active with the new schedule
    for job in "${BISYNC_JOBS[@]}"; do
        IFS=';' read -r remote_name _ _ <<< "$job"
        if check_remote_configured "$remote_name"; then
            echo "Restarting timer for $remote_name..."
            systemctl restart "rclone-bisync-$remote_name.timer"
        fi
    done

    echo ""
    echo "✅ rclone provisioning complete!"
    echo "   Run 'systemctl list-timers rclone-bisync-*' to check status."
}

main

# chmod +x ~/Repos/pc-env/docker/rclone/enable-systemd.sh
# sudo bash ~/Repos/pc-env/docker/rclone/enable-systemd.sh
