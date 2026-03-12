#!/bin/bash
set -euo pipefail

# Provision cloud storage sync using `rclone` and `systemd`

# Ensure the script is run as root (or sudo privileges)
if [[ $EUID -ne 0 ]]; then
    echo "❌ This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# Ensure SUDO_USER is set (catch cases where script is run directly as root)
if [[ -z "${SUDO_USER:-}" ]]; then
    echo "❌ SUDO_USER is not set. Please run with 'sudo' instead of as root. Exiting..."
    exit 1
fi

# ----------------------------------------------------------------
# Parse arguments
# ----------------------------------------------------------------

FORCE_FILTERS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force-filters)
            FORCE_FILTERS=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force-filters    Force recreation of filter files (will reset bisync state)"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------

CONFIG_DIR="/home/$SUDO_USER/.config/rclone"
# SYSTEMD_DIR="/home/$SUDO_USER/.config/systemd/user"
SYSTEMD_DIR="/etc/systemd/system"
# SCRIPT_DIR="/home/$SUDO_USER/Repos/pc-env/docker/rclone/scripts"
SCRIPT_DIR="/home/$SUDO_USER/Repos/pc-env/setup-linux/provision-apps/rclone"

REMOTE_NAME="gdrive"
STORAGE_TYPE="drive" # Google Drive (https://rclone.org/drive)
BACKUP_DIR="$CONFIG_DIR/bisync-backups"

# ----------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------

# Install rclone if not present
install_rclone() {
    if ! command -v rclone &>/dev/null; then
        echo "📦 Installing rclone..."
        curl https://rclone.org/install.sh | sudo bash
        echo "✅ rclone installed successfully"
    else
        echo "✅ rclone is already installed. Skipping."
    fi
}

# Configure rclone for cloud services (Google Drive, OneDrive, pCloud)
configure_rclone_old() {
    # local config_file="$CONFIG_DIR/rclone.conf"
    echo "Configuring rclone remotes..."
    # Ensure config directory exists
    mkdir -p "$CONFIG_DIR"

    # Configure rclone manually:
    # rclone config
    # rclone config <remote-name> <storage-type>

    # Check if rclone is configured
    if [ ! -f "$config_file" ]; then
        echo "Running initial rclone setup for Google Drive.  Follow authentication steps."

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

# Configure rclone for a specific cloud service remote
configure_rclone() {
    local remote_name="$1"
    local storage_type="$2"
    
    # Check if remote already exists
    if sudo -u "$SUDO_USER" rclone listremotes | grep -q "^${remote_name}:$"; then
        echo "${remote_name} is already configured. Skipping..."
        return 0
    fi
    
    echo "Running initial rclone setup for ${remote_name}. Follow authentication steps."
    
    # Configure the remote (must run as actual user to save to correct config location)
    case "$storage_type" in
        drive)
            # NOTE: This step is mostly automated but will open the
            # browser to authenticate once and produce an access token
            # Follow the prompts to set up access to Google Drive
            # https://rclone.org/drive/#making-your-own-client-id
            # https://console.cloud.google.com
            sudo -u "$SUDO_USER" rclone config create "$remote_name" "$storage_type" scope="drive"
            
            # To test your connection (first use has a delay):
            # rclone lsf gdrive:
            ;;
        onedrive)
            # NOTE: This will open a browser window for Microsoft authentication
            # Tokens are stored in ~/.config/rclone/rclone.conf
            # rclone automatically refreshes the access token when needed
            # You won't need to re-authenticate if rclone is used at least once every 90 days
            sudo -u "$SUDO_USER" rclone config create "$remote_name" "$storage_type"
            
            # To test your connection:
            # rclone lsf onedrive: --max-depth 1
            ;;
        pcloud)
            # NOTE: This will open a browser window for pCloud authentication
            sudo -u "$SUDO_USER" rclone config create "$remote_name" "$storage_type"
            ;;
        *)
            echo "❌ Unknown storage type: $storage_type"
            return 1
            ;;
    esac
    
    echo "✅ ${remote_name} setup complete."
}

# Check if a remote is configured
check_remote_configured() {
    local remote_name="$1"
    if sudo -u "$SUDO_USER" rclone listremotes 2>/dev/null | grep -q "^${remote_name}:$"; then
        return 0
    else
        return 1
    fi
}

# Print manual configuration instructions
print_config_instructions() {
    local remote_name="$1"
    local storage_type="$2"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  MANUAL CONFIGURATION REQUIRED FOR: ${remote_name}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Remote '${remote_name}' is not configured yet."
    echo "Please run the following command as the user '$SUDO_USER':"
    echo ""
    echo "    rclone config create \"${remote_name}\" \"${storage_type}\""
    echo ""
    
    case "$storage_type" in
        drive)
            echo "This will open a browser for Google authentication."
            echo "Follow the prompts to authorize rclone access to Google Drive."
            echo ""
            echo "📚 More info: https://rclone.org/drive/"
            ;;
        onedrive)
            echo "This will open a browser for Microsoft authentication."
            echo "Tokens are stored in ~/.config/rclone/rclone.conf"
            echo "rclone will auto-refresh tokens if used at least once every 90 days."
            echo ""
            echo "After configuration, test with:"
            echo "    rclone lsf ${remote_name}: --max-depth 1"
            echo ""
            echo "📚 More info: https://rclone.org/onedrive/"
            ;;
        pcloud)
            echo "This will open a browser for pCloud authentication."
            echo ""
            echo "After configuration, test with:"
            echo "    rclone lsf ${remote_name}: --max-depth 1"
            echo ""
            echo "📚 More info: https://rclone.org/pcloud/"
            ;;
    esac
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Create sync filters (https://rclone.org/bisync/#filtering)
create_filters() {
    local filters_file="$CONFIG_DIR/bisync-filters.txt"

    # Only create if it doesn't exist to avoid invalidating bisync state
    if [[ -f "$filters_file" ]] && [[ "$FORCE_FILTERS" != "true" ]]; then
        echo "ℹ️  Filters file already exists. Skipping..."
        echo "    Use --force-filters to recreate (will invalidate bisync state)"
        return 0
    fi

    if [[ "$FORCE_FILTERS" == "true" ]] && [[ -f "$filters_file" ]]; then
        echo "⚠️  Force mode: Recreating filters file..."
        echo "    ⚠️  This will invalidate bisync state - you'll need to resync!"
        cp "$filters_file" "${filters_file}.bak.$(date +%Y%m%d_%H%M%S)"
    fi

    cat <<EOF >"$filters_file"
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
    
    chown "$SUDO_USER:$SUDO_USER" "$filters_file"
    chmod 644 "$filters_file"
    
    echo "✅ Created rclone exclude filters at: $filters_file"
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

# Create systemd service unit
create_service_unit() {
    local service_name="$1"
    local description="$2"
    local exec_start="$3"
    local exec_stop="${4:-}"
    
    local unit_file="$SYSTEMD_DIR/${service_name}.service"
    
    cat <<EOF >"$unit_file"
[Unit]
Description=${description}
After=network-online.target
Wants=network-online.target

[Service]
User=$SUDO_USER
Group=$SUDO_USER
ExecStart=${exec_start}
${exec_stop:+ExecStop=${exec_stop}}
Restart=on-failure
RestartSec=10
Type=simple
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    echo "✅ Created service: ${service_name}.service"
}

# Create systemd timer unit
create_timer_unit() {
    local service_name="$1"
    local description="$2"
    local on_calendar="$3"
    local on_boot_sec="${4:-2m}"
    local on_unit_active_sec="${5:-}"
    
    local unit_file="$SYSTEMD_DIR/${service_name}.timer"
    
    cat <<EOF >"$unit_file"
[Unit]
Description=${description}

[Timer]
OnBootSec=${on_boot_sec}
${on_calendar:+OnCalendar=${on_calendar}}
${on_unit_active_sec:+OnUnitActiveSec=${on_unit_active_sec}}
Persistent=true
Unit=${service_name}.service

[Install]
WantedBy=timers.target
EOF
    
    echo "✅ Created timer: ${service_name}.timer"
}

# Enable and start a systemd unit
enable_start_unit() {
    local unit_name="$1"
    local unit_type="${2:-.service}"
    
    systemctl daemon-reload
    
    if systemctl is-enabled "${unit_name}${unit_type}" &>/dev/null; then
        echo "ℹ️  ${unit_name}${unit_type} is already enabled"
    else
        systemctl enable "${unit_name}${unit_type}"
        echo "✅ Enabled ${unit_name}${unit_type}"
    fi
    
    if systemctl is-active "${unit_name}${unit_type}" &>/dev/null; then
        echo "ℹ️  ${unit_name}${unit_type} is already running"
        systemctl restart "${unit_name}${unit_type}"
        echo "🔄 Restarted ${unit_name}${unit_type}"
    else
        systemctl start "${unit_name}${unit_type}"
        echo "✅ Started ${unit_name}${unit_type}"
    fi
}

# ----------------------------------------------------------------
# Service Setup Functions
# ----------------------------------------------------------------

# Set up Google Drive mount
setup_mount_gdrive() {
    local remote_name="gdrive"
    local service_name="rclone-mount-${remote_name}"
    
    echo ""
    echo "🔧 Setting up Google Drive mount..."
    
    if ! check_remote_configured "$remote_name"; then
        print_config_instructions "$remote_name" "drive"
        echo "⏭️  Skipping Google Drive mount setup (remote not configured)"
        return 1
    fi
    
    create_service_unit \
        "$service_name" \
        "Rclone Mount Google Drive for $SUDO_USER" \
        "$SCRIPT_DIR/${service_name}.sh" \
        "/usr/bin/fusermount -u /home/$SUDO_USER/GoogleDrive"
    
    enable_start_unit "$service_name"
    
    echo "✅ Google Drive mount configured"
    echo "    Check status: systemctl status ${service_name}"
    echo "    View logs: journalctl -u ${service_name} -f"
}

# Set up Google Drive bisync
setup_bisync_gdrive() {
    local remote_name="gdrive"
    local service_name="rclone-bisync-${remote_name}"
    
    echo ""
    echo "🔧 Setting up Google Drive bisync..."
    
    if ! check_remote_configured "$remote_name"; then
        print_config_instructions "$remote_name" "drive"
        echo "⏭️  Skipping Google Drive bisync setup (remote not configured)"
        return 1
    fi
    
    create_service_unit \
        "$service_name" \
        "Rclone Bisync Google Drive" \
        "$SCRIPT_DIR/${service_name}.sh"
    
    create_timer_unit \
        "$service_name" \
        "Run Rclone Bisync Every 30 Minutes" \
        "" \
        "2m" \
        "30m"
    
    enable_start_unit "$service_name" ".timer"
    
    echo "✅ Google Drive bisync configured"
    echo "    Check status: systemctl status ${service_name}.timer"
    echo "    View logs: journalctl -u ${service_name} -f"
}

# Set up OneDrive bisync
setup_bisync_onedrive() {
    local remote_name="onedrive"
    local service_name="rclone-bisync-${remote_name}"
    
    echo ""
    echo "🔧 Setting up OneDrive bisync..."
    
    if ! check_remote_configured "$remote_name"; then
        print_config_instructions "$remote_name" "onedrive"
        echo "⏭️  Skipping OneDrive bisync setup (remote not configured)"
        return 1
    fi
    
    create_service_unit \
        "$service_name" \
        "Rclone Bisync OneDrive" \
        "$SCRIPT_DIR/${service_name}.sh"
    
    create_timer_unit \
        "$service_name" \
        "Run Rclone OneDrive Bisync Daily at 6am CST" \
        "*-*-* 12:00:00"
    
    enable_start_unit "$service_name" ".timer"
    
    echo "✅ OneDrive bisync configured"
    echo "    Check status: systemctl status ${service_name}.timer"
    echo "    View logs: journalctl -u ${service_name} -f"
}

# Set up pCloud bisync
setup_bisync_pcloud() {
    local remote_name="pcloud"
    local service_name="rclone-bisync-${remote_name}"
    
    echo ""
    echo "🔧 Setting up pCloud bisync..."
    
    if ! check_remote_configured "$remote_name"; then
        print_config_instructions "$remote_name" "pcloud"
        echo "⏭️  Skipping pCloud bisync setup (remote not configured)"
        return 1
    fi
    
    create_service_unit \
        "$service_name" \
        "Rclone Bisync pCloud" \
        "$SCRIPT_DIR/${service_name}.sh"
    
    create_timer_unit \
        "$service_name" \
        "Run Rclone pCloud Bisync Daily at 6am CST" \
        "*-*-* 12:00:00"
    
    enable_start_unit "$service_name" ".timer"
    
    echo "✅ pCloud bisync configured"
    echo "    Check status: systemctl status ${service_name}.timer"
    echo "    View logs: journalctl -u ${service_name} -f"
}

# Set up WebDAV server
setup_serve_webdav() {
    local service_name="rclone-serve-webdav"
    
    echo ""
    echo "🔧 Setting up WebDAV server..."
    
    create_service_unit \
        "$service_name" \
        "Rclone WebDAV Service for Local Media" \
        "$SCRIPT_DIR/${service_name}.sh" \
        "/bin/kill -SIGINT \$MAINPID"
    
    enable_start_unit "$service_name"
    
    echo "✅ WebDAV server configured"
    echo "    Check status: systemctl status ${service_name}"
    echo "    View logs: journalctl -u ${service_name} -f"
}

# ----------------------------------------------------------------
# OLD
# ----------------------------------------------------------------

# Set up systemd services for OneDrive bisync (daily at 6am CST)
auto_bisync_onedrive() {
    local service_name="rclone-bisync-onedrive"

    # Create systemd service for bisync
    cat <<EOF >"$SYSTEMD_DIR/$service_name.service"
[Unit]
Description=Rclone Bisync OneDrive
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

    # Create systemd timer for daily 6am CST (12:00 UTC when CST, 11:00 UTC when CDT)
    cat <<EOF >"$SYSTEMD_DIR/$service_name.timer"
[Unit]
Description=Run Rclone OneDrive Bisync Daily at 6am CST

[Timer]
OnCalendar=*-*-* 12:00:00
Persistent=true
Unit=$service_name.service

[Install]
WantedBy=timers.target
EOF

    # Reload systemd, enable, and start timer
    systemctl daemon-reload
    systemctl enable --now "$service_name.timer"
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
ExecStop=/bin/kill -SIGINT \$MAINPID
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
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 Starting rclone provisioning..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # [0] Set up environment
    install_rclone

    # Ensure config directory exists with correct ownership
    mkdir -p "$CONFIG_DIR"
    chown "$SUDO_USER:$SUDO_USER" "$CONFIG_DIR"

    # [1] Create filter file
    create_filters

    # # Configure cloud service remotes
    # echo ""
    # echo "Configuring rclone remotes..."
    # # configure_rclone "gdrive" "drive"
    # configure_rclone "onedrive" "onedrive"
    # # configure_rclone "pcloud" "pcloud"  # Uncomment when ready to use pCloud

    # [2] List configured remotes
    echo ""
    echo "📋 Currently configured remotes:"
    if sudo -u "$SUDO_USER" rclone listremotes 2>/dev/null | grep -q ":"; then
        sudo -u "$SUDO_USER" rclone listremotes
    else
        echo "    (none configured yet)"
    fi

    # [3] Set up services (skip if remote not configured)
    # mount Google Drive (on reboot) to ~/GoogleDrive
    setup_mount_gdrive || true
    # bisync Google Drive (every 30m) to ~/ObsidianVaults
    setup_bisync_gdrive || true
    # bisync Microsoft OneDrive (daily at 6am CST) to ~/OneDrive
    setup_bisync_onedrive || true
    # bisync pCloud (daily at 6am CST) to ~/pCloud
    # setup_bisync_pcloud || true  # Uncomment when ready
    # serve WebDAV local media (on reboot) from /mnt
    setup_serve_webdav || true
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ rclone provisioning complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Print any remaining manual steps
    local needs_config=false
    
    if ! check_remote_configured "gdrive"; then
        needs_config=true
        print_config_instructions "gdrive" "drive"
    fi
    
    if ! check_remote_configured "onedrive"; then
        needs_config=true
        print_config_instructions "onedrive" "onedrive"
    fi
    
    # if ! check_remote_configured "pcloud"; then
    #     needs_config=true
    #     print_config_instructions "pcloud" "pcloud"
    # fi
    
    if [[ "$needs_config" == "true" ]]; then
        echo ""
        echo "⚠️  Some remotes still need manual configuration (see above)"
        echo "    After configuring, re-run this script to enable services"
    fi



    # # [1] mount Google Drive (on reboot) to ~/GoogleDrive
    # auto_mount_gdrive

    # # [2] bisync Google Drive (every 30m) to ~/ObsidianVaults
    # auto_bisync_gdrive

    # # [3] bisync Microsoft OneDrive (every 1h) to ~/OneDrive
    # # [3] bisync Microsoft OneDrive (daily at 6am CST) to ~/OneDrive
    # auto_bisync_onedrive

    # # [4] serve WebDAV local media (on reboot) from /mnt
    # auto_serve_webdav

    # echo -e "\n"
    # echo "🚀 rclone provisioning complete!"
}

main

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/rclone/enable-systemd.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/rclone/enable-systemd.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/rclone/enable-systemd.sh --force-filters
