#!/bin/bash
set -e

# Provision cloud storage sync using `rclone` and `systemd`

# Ensure the script is run as root (or sudo privileges)
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# ----------------------------------------------------------------
# ----------------------------------------------------------------

CONFIG_DIR="/home/$SUDO_USER/.config/rclone"
# SYSTEMD_DIR="/home/$SUDO_USER/.config/systemd/user"
SYSTEMD_DIR="/etc/systemd/system"
# SCRIPT_DIR="/home/$SUDO_USER/Repos/pc-env/docker/rclone/scripts"
SCRIPT_DIR="/home/$SUDO_USER/Repos/pc-env/setup-linux/provision-apps/rclone"

REMOTE_NAME="gdrive"
STORAGE_TYPE="drive" # Google Drive (https://rclone.org/drive)
BACKUP_DIR="$CONFIG_DIR/bisync-backups"

# Install rclone if not present
install_rclone() {
    if ! command -v rclone &>/dev/null; then
        echo "Installing rclone..."
        # apt-get update -q
        # apt-get install -y --no-install-recommends --no-install-suggests rclone
        curl https://rclone.org/install.sh | sudo bash
    else
        echo "rclone is already installed.  Skipping."
    fi
}

# Configure rclone for Google Drive
configure_rclone() {
    local config_file="$CONFIG_DIR/rclone.conf"

    mkdir -p "$CONFIG_DIR"

    # Check if rclone is configured
    if [ ! -f "$config_file" ]; then
        echo "Running initial rclone setup for Google Drive.  Follow authentication steps."
        # Configure rclone manually
        # rclone config

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

        # To test your connection (first use has a delay)
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
[Unit]
Description=Rclone Mount Google Drive for $SUDO_USER
After=network-online.target
Wants=network-online.target

[Service]
User=$SUDO_USER
Group=$SUDO_USER
ExecStart=$SCRIPT_DIR/$service_name.sh
ExecStop=/usr/bin/fusermount -u /home/$SUDO_USER/GoogleDrive
Restart=on-failure
RestartSec=10
Type=simple
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd, enable, and start service
    systemctl daemon-reload
    systemctl enable --now "$service_name.service"

    # Check status of service:
    # systemctl status rclone-mount-gdrive

    # View real-time logs (add `-f` to follow):
    # journalctl -u rclone-mount-gdrive
}

# Set up systemd services for bisync
auto_bisync_gdrive() {
    local service_name="rclone-bisync-$REMOTE_NAME"

    # Create systemd service for bisync
    cat <<EOF >"$SYSTEMD_DIR/$service_name.service"
[Unit]
Description=Rclone Bisync Google Drive
After=network-online.target
Wants=network-online.target

[Service]
User=$SUDO_USER
Group=$SUDO_USER
ExecStart=$SCRIPT_DIR/$service_name.sh
Restart=on-failure
RestartSec=30s
Type=simple
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Create systemd timer to run every 30 minutes
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

    # Reload systemd, enable, and start service and timer
    systemctl daemon-reload
    systemctl enable --now "$service_name.timer"

    # Check status of service:
    # systemctl status rclone-bisync-gdrive.timer

    # View real-time logs (add `-f` to follow):
    # journalctl -u rclone-bisync-gdrive.timer
}

# WebDAV for local files
auto_serve_webdav() {
    local service_name="rclone-serve-webdav"

    # Create systemd service for webdav
    cat <<EOF >"$SYSTEMD_DIR/$service_name.service"
[Unit]
Description=Rclone WebDAV Service for Local Media
After=network-online.target
Wants=network-online.target

[Service]
User=$SUDO_USER
Group=$SUDO_USER
ExecStart=$SCRIPT_DIR/$service_name.sh
ExecStop=/bin/kill -SIGINT $MAINPID
Restart=on-failure
RestartSec=10
Type=simple
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd, enable, and start service
    systemctl daemon-reload
    systemctl enable --now "$service_name.service"

    # Check status of service:
    # systemctl status rclone-serve-webdav

    # View real-time logs (add `-f` to follow):
    # journalctl -u rclone-serve-webdav
}

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Main function: sets up rclone environment and systemd services
main() {
    echo "Starting rclone provisioning..."

    # [0] Set up environment
    install_rclone
    configure_rclone
    create_filters

    # [1] mount Google Drive (on reboot) to ~/GoogleDrive
    auto_mount_gdrive

    # [2] bisync Google Drive (every 30m) to ~/ObsidianVaults
    auto_bisync_gdrive

    # [3] bisync Microsoft OneDrive (every 1h) to ~/OneDrive

    # [4] serve WebDAV local media (on reboot) from /mnt
    auto_serve_webdav

    echo -e "\n"
    echo "🚀 rclone provisioning complete!"
}

main

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/rclone/enable-systemd.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/rclone/enable-systemd.sh
