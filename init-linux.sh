#!/usr/bin/env bash
set -euo pipefail # Exit immediately on error

# Linux Mint/Ubuntu system provisioning

# --- Global Read-only Variables ---
readonly SCRIPT_NAME="$(basename "$0")"
readonly SUDO_USER_NAME="${SUDO_USER:-}"
readonly USER_HOME_DIR="$(getent passwd "$SUDO_USER_NAME" | cut -d: -f6)"

# --- Script Configuration ---
readonly -a ALIASES=(
    # "alias <alias-name>='docker compose -f <configuration-file> run --rm <service-name>'"
    "alias ytdl='docker compose -f \"${USER_HOME_DIR}/Repos/pc-env/docker/yt-dlp/docker-compose.yml\" run --rm yt-dlp'"
    "alias subs='docker compose -f \"${USER_HOME_DIR}/Repos/pc-env/docker/pysubs2/docker-compose.yml\" run --rm pysubs2'"
    "alias rclone='docker compose -f \"${USER_HOME_DIR}/Repos/pc-env/docker/rclone/docker-compose.yml\" run --rm rclone'"
)
readonly -a PROVISIONING_SCRIPTS=("apt.sh" "onedrive.sh" "obsidian.sh")
readonly PROVISIONING_SCRIPTS_URL="https://raw.githubusercontent.com/david-rachwalik/pc-env/master/setup-linux/provision-apps"


# ----------------------------------------------------------------
# ----------------------------------------------------------------

# --- Helper Functions ---

# Log messages with a timestamp and script name
log() {
    # echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S') - $*"
    echo "[${SCRIPT_NAME}] [INFO] $(date +'%Y-%m-%d %H:%M:%S') - $*"
}

# Log error messages and exit
die() {
    echo "[${SCRIPT_NAME}] [ERROR] $*" >&2
    exit 1
}

# Helper to run a command as the original user
run_as_user() {
    sudo -u "$SUDO_USER_NAME" "$@"
}

# --- Pre-flight Checks ---

# Ensure the script is run as root and that we can identify the original user
ensure_root() {
    log "Verifying execution context..."
    if [[ "$(id -u)" -ne 0 ]]; then
        die "This script must be run as root or with sudo."
    fi

    if [[ -z "$SUDO_USER_NAME" ]]; then
        die "Cannot determine the original user.  Please run with 'sudo'."
    fi

    if [[ ! -d "$USER_HOME_DIR" ]]; then
        die "Could not find home directory for user '$SUDO_USER_NAME'."
    fi
    log "Running as root for user '$SUDO_USER_NAME'."
}
 
# --- Setup Functions ---

# Update package list and install essential packages
setup_core_system() {
    log "Updating package list and upgrading system..."
    apt-get update && apt-get upgrade -y
    log "Installing essential packages..."
    apt-get install -y curl wget git build-essential
}
# (apt-get is the reliable choice for automated scripts)
# (apt is preferred for interactive use as the "porcelain", user-friendly tool)

# Configure shell aliases
setup_aliases() {
    log "Setting up shell aliases..."
    local alias_file="${USER_HOME_DIR}/.bash_aliases"

    # Ensure alias file exists and is owned by the correct user
    if [ ! -f "$alias_file" ]; then
        log "Creating ${alias_file}..."
        touch "$alias_file"
        chown "${SUDO_USER_NAME}:${SUDO_USER_NAME}" "$alias_file"
    fi

    # Add each alias if missing from file
    for alias_cmd in "${ALIASES[@]}"; do
        if ! grep -Fxq "$alias_cmd" "$alias_file"; then
            log "Adding alias: ${alias_cmd%%=*}"
            echo "$alias_cmd" >>"$alias_file"
        fi
    done
    log "Alias setup complete. Please run 'source ~/.bashrc' or restart your shell."
}

# Generate SSH keys if not present
setup_ssh() {
    log "Checking for SSH keys..."
    local ssh_key_path="${USER_HOME_DIR}/.ssh/id_rsa"
    local ssh_dir
    ssh_dir=$(dirname "$ssh_key_path")

    if [ ! -f "$ssh_key_path" ]; then
        log "Generating SSH keys for $SUDO_USER_NAME..."
        run_as_user mkdir -p "$ssh_dir"
        run_as_user chmod 700 "$ssh_dir"
        run_as_user ssh-keygen -q -f "$ssh_key_path" -t rsa -b 4096 -N ""
        log "SSH keys generated."
    else
        log "SSH key already exists."
    fi
}

# Update Cinnamon panel clock settings as the user
# Note: This requires the user to be in an active desktop session
setup_panel_clock() {
    log "Configuring Cinnamon panel clock..."
    local schema="org.cinnamon.desktop.interface"
    local date_format="%b %d, %Y %H:%M"
    local tooltip_format="%A, %B %d, %Y, %-I:%M %p"

    # This must be run as the user to access their D-Bus session
    set_gsetting() {
        local key="$1"
        local value="$2"
        local current_value
        current_value=$(run_as_user gsettings get "$schema" "$key")

        if [[ "$current_value" != "'$value'" ]]; then
            run_as_user gsettings set "$schema" "$key" "$value"
            log "Updated gsetting '$key'."
        fi
    }

    # > gsettings list-keys org.cinnamon.desktop.interface
    set_gsetting "clock-use-24-hour" "$date_format"
    set_gsetting "clock-show-seconds" "$tooltip_format"
    echo "Panel clock settings are set."
}

# Run remote provisioning scripts for applications
run_provisioning_scripts() {
    log "Running remote provisioning scripts..."
    for script in "${PROVISIONING_SCRIPTS[@]}"; do
        log "Executing remote script: $script"
        # Download to a temporary file and execute, which is safer
        local tmp_script
        tmp_script=$(mktemp)
        if curl -sL "${PROVISIONING_SCRIPTS_URL}/${script}" -o "$tmp_script"; then
            bash "$tmp_script"
            log "Completed $script process."
        else
            log "Failed to download $script. Skipping." >&2
        fi
        rm -f "$tmp_script"
    done
}

# Setup scheduled cron jobs
setup_cron() {
    echo "Setting up cron jobs..."
    # Example cron job that runs a script periodically
    # (crontab -l; echo "0 0 * * * /usr/bin/python3 /path/to/script.py") | crontab -
    echo "Cron jobs configured."
}

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# --- Main Execution ---
main() {
    ensure_root
    log "Starting Linux provisioning..."
    # --- Core System Setup ---
    setup_core_system
    setup_aliases
    # setup_panel_clock # handled manually
    # setup_ssh         # handled by another script
    # --- TODO: Software Installation ---
    # run_provisioning_scripts
    # --- Developer Environment Setup ---
    # (these are now handled via Docker containers: NodeJS, Python, .NET, C#)
    # --- TODO: Automation & Background Tasks ---
    # setup_cron # app & game backups
    log "--- Successfully completed Linux provisioning! ---"
}

main

# chmod +x ~/Repos/pc-env/init-linux.sh
# sudo bash ~/Repos/pc-env/init-linux.sh
