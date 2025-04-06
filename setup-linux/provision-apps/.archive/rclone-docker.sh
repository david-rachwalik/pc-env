#!/bin/bash
set -e

# # Provision Google Drive sync using rclone and systemd
# https://drive.google.com

# Notes on systemd [Service] configuration:
# - avoid `User` (e.g. User=$SUDO_USER) because service started with --user
# - if logs don't appear in journalctl, can explicitly direct output there
#     `StandardOutput=journal`
#     `StandardError=journal`

# Ensure the script is NOT run as root
if [[ "$(id -u)" -eq 0 ]]; then
    echo "This script should NOT be run with sudo.  Exiting..."
    exit 1
fi

# ----------------------------------------------------------------
# ----------------------------------------------------------------

CONFIG_DIR="$HOME/.config/rclone"
SYSTEMD_DIR="$HOME/.config/systemd/user"
SCRIPT_DIR="$HOME/Repos/pc-env/docker/rclone/scripts"
BISYNC_WORK_DIR="$HOME/.local/share/rclone-bisync-workdir"

MOUNT_DIR="$HOME/GoogleDrive"
BISYNC_DIR_NAME="ObsidianVaults"
BISYNC_DIR="$HOME/$BISYNC_DIR_NAME"
REMOTE_NAME="gdrive"
STORAGE_TYPE="drive" # Google Drive (https://rclone.org/drive)
BACKUP_DIR="$CONFIG_DIR/bisync-backups"

# Install rclone if not present
install_rclone() {
    if ! command -v rclone &>/dev/null; then
        echo "Installing rclone..."
        apt-get update -q
        apt-get install -y --no-install-recommends --no-install-suggests rclone
    else
        echo "rclone is already installed.  Skipping."
    fi
}

# Configure rclone for Google Drive
configure_rclone() {
    local config_file="$CONFIG_DIR/rclone.conf"

    # Ensure configuration directory exists
    mkdir -p "$CONFIG_DIR"

    # Check if rclone is configured
    if [ ! -f "$config_file" ]; then
        echo "Running initial rclone setup for Google Drive.  Follow authentication steps."
        # rclone config # interactive config

        # Follow the prompts to set up access to Google Drive
        # https://rclone.org/drive/#making-your-own-client-id
        # https://console.cloud.google.com

        # rclone config create "$REMOTE_NAME" "$STORAGE_TYPE" \
        #     scope="drive" \
        #     file="$HOME/.config/rclone/rclone.conf"
        #     service_account_file="/path/to/service_account.json"

        # NOTE: This step is mostly automated but will open the
        # browser to authenticate once and produce an access token
        rclone config create "$REMOTE_NAME" "$STORAGE_TYPE"

        echo "Google Drive setup complete."
        # rclone listremotes

        # To test your connection (delay on first use)
        # rclone lsf <remote-name>:
    else
        echo "Google Drive is already configured."
    fi
}

# Create sync filters (https://rclone.org/bisync/#filtering)
create_filters() {
    local filters_file="$CONFIG_DIR/bisync-filters.txt"

    cat <<EOF >"$filters_file"
- node_modules/
- .Trash-*
- .DS_Store
- *.tmp
- .obsidian/workspace.json
EOF
    echo "Created rclone exclude filters."
}

# Create mount for root files
auto_mount_gdrive() {
    local service_name="rclone-mount-$REMOTE_NAME"

    # Create systemd service for mount
    cat <<EOF >"$SYSTEMD_DIR/$service_name.service"
# This service mounts Google Drive using rclone
[Unit]
Description=Rclone Mount Google Drive
After=network-online.target
Wants=network-online.target

# Service configuration
[Service]
# ExecStart=/usr/bin/docker run --rm \
#   -v ~/.config/rclone:/config \
#   --device /dev/fuse \
#   --cap-add SYS_ADMIN \
#   rclone/rclone mount $REMOTE_NAME: $MOUNT_DIR \
#   --allow-other \
#   --vfs-cache-mode full
ExecStart=$SCRIPT_DIR/$service_name.sh
Restart=on-failure
RestartSec=10
Type=simple

# Enable this service to run on boot
[Install]
# WantedBy=multi-user.target
WantedBy=default.target
EOF

    systemctl --user daemon-reload # source/reload systemd
    systemctl --user enable --now $service_name.service
}

# Set up systemd services
auto_bisync_gdrive() {
    local service_name="rclone-bisync-$REMOTE_NAME"

    # Create systemd service
    cat <<EOF >"$SYSTEMD_DIR/$service_name.service"
[Unit]
Description=Rclone Bisync Google Drive
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=$SCRIPT_DIR/$service_name.sh
Restart=on-failure
RestartSec=30s
Type=simple

[Install]
WantedBy=default.target
EOF

    # Create systemd timer
    cat <<EOF >"$SYSTEMD_DIR/$service_name.timer"
[Unit]
Description=Run Rclone Bisync Every 30 Minutes

[Timer]
OnBootSec=2m
OnUnitActiveSec=30m
Persistent=true
Unit=$service_name.service

[Install]
WantedBy=timers.target
EOF

    systemctl --user daemon-reload # source/reload systemd
    systemctl --user enable --now $service_name.service $service_name.timer
}

# WebDAV for local files
auto_serve_webdav() {
    local service_name="rclone-serve-webdav"

    # Create systemd service for webdav
    cat <<EOF >"$SYSTEMD_DIR/$service_name.service"
# This serves WebDAV files for Local Media
[Unit]
Description=Rclone WebDAV Service for Local Media
After=network-online.target
Wants=network-online.target

# Service configuration
[Service]
ExecStart=$SCRIPT_DIR/$service_name.sh
Restart=on-failure
RestartSec=10
Type=simple

# Enable this service to run on boot
[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload # source/reload systemd
    systemctl --user enable --now $service_name.service

    # Check its status
    # systemctl --user status rclone-serve-webdav.service

    # View the logs for issues
    # journalctl --user -u rclone-serve-webdav.service
}

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Main function: sets up rclone environment and systemd services
main() {
    echo "Starting rclone provisioning..."

    # [0] Set up environment
    # install_rclone
    # configure_rclone
    # create_filters
    mkdir -p "$SYSTEMD_DIR" "$BISYNC_WORK_DIR"

    # [1] mount (on reboot) to ~/GoogleDrive
    auto_mount_gdrive

    # [2] bisync (every 30m) to ~/ObsidianVaults
    auto_bisync_gdrive

    # [3] bisync (every 1h) to ~/OneDrive

    # [4] serve webdav local media from /mnt
    # auto_serve_webdav

    echo "\n🚀 rclone provisioning complete!"
}

main

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/rclone.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/rclone.sh
