#!/usr/bin/env bash
set -euo pipefail # Exit immediately on error

# Linux Mint (Ubuntu) system provisioning

# --- Global Read-only Variables ---
readonly SCRIPT_NAME="$(basename "$0")"
readonly SUDO_USER_NAME="${SUDO_USER:-}"
readonly USER_HOME_DIR="$(getent passwd "$SUDO_USER_NAME" | cut -d: -f6)"

# --- Script Configuration ---
readonly -a CORE_PACKAGES=("curl" "wget" "git" "build-essential")
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
    # echo "[${SCRIPT_NAME}] [INFO] $(date +'%Y-%m-%d %H:%M:%S') - $*"
    echo "[${SCRIPT_NAME}] $(date +'%Y-%m-%d %H:%M:%S') | $*"
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
    log "Checking core system packages..."
    local packages_to_install=()
    for pkg in "${CORE_PACKAGES[@]}"; do
        # dpkg-query is a stable way to check for installed packages
        if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "install ok installed"; then
            log "Package '$pkg' not found.  Marking for installation."
            packages_to_install+=("$pkg")
        fi
    done

    if [ ${#packages_to_install[@]} -gt 0 ]; then
        log "Updating package list..."
        apt-get update
        log "Installing missing packages: ${packages_to_install[*]}..."
        apt-get install -y "${packages_to_install[@]}"
    else
        log "All core packages are already installed."
    fi
}
# (apt-get is the reliable choice for automated scripts)
# (apt is preferred for interactive use as the "porcelain", user-friendly tool)

# Configure shell aliases
setup_aliases() {
    log "Checking shell aliases..."
    local alias_file="${USER_HOME_DIR}/.bash_aliases"

    # Ensure alias file exists and is owned by the correct user
    if [ ! -f "$alias_file" ]; then
        log "Creating ${alias_file}..."
        run_as_user touch "$alias_file"
    fi
    
    # Verify and correct ownership if necessary
    if [[ "$(stat -c '%U' "$alias_file")" != "$SUDO_USER_NAME" ]]; then
        log "Correcting ownership of ${alias_file}..."
        chown "${SUDO_USER_NAME}:${SUDO_USER_NAME}" "$alias_file"
    fi

    # Add each alias if missing from file
    for alias_cmd in "${ALIASES[@]}"; do
        if ! grep -Fxq "$alias_cmd" "$alias_file"; then
            log "Adding alias: ${alias_cmd%%=*}"
            echo "$alias_cmd" >>"$alias_file"
        fi
    done
    log "Alias check complete.  If changes were made, run 'source ~/.bashrc' or restart your shell."
}

# Generate SSH keys for user if not present
setup_ssh() {
    log "Checking for SSH keys..."
    local ssh_key_path="${USER_HOME_DIR}/.ssh/id_rsa"
    
    # Check if key exists
    if [ ! -f "$ssh_key_path" ]; then
        log "No SSH key found.  Generating for $SUDO_USER_NAME..."
        local ssh_dir
        ssh_dir=$(dirname "$ssh_key_path")
        run_as_user mkdir -p "$ssh_dir"
        run_as_user chmod 700 "$ssh_dir"
        run_as_user ssh-keygen -q -f "$ssh_key_path" -t rsa -b 4096 -N ""
        log "SSH keys generated."
    else
        log "SSH key already exists."
    fi
}

# Update Cinnamon panel clock settings as the user (must be in active desktop session)
setup_panel_clock_old() {
    # Pre-flight check that gsettings command exists
    if ! command -v gsettings &> /dev/null; then
        log "gsettings command not found. Skipping panel clock setup."
        return
    fi

    log "Checking Cinnamon panel clock settings..."
    local schema="org.cinnamon.desktop.interface"

    # Must be run as user to access their D-Bus session
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

    # local date_format="%b %d, %Y %H:%M"
    # local tooltip_format="%A, %B %d, %Y, %-I:%M %p"
    # set_gsetting "clock-use-24-hour" "$date_format"
    # set_gsetting "clock-show-seconds" "$tooltip_format"

    # > gsettings list-keys org.cinnamon.desktop.interface
    set_gsetting "clock-use-24h" "true"
    set_gsetting "clock-show-seconds" "true"
    echo "Panel clock settings are set."
}

# Update Cinnamon panel clock settings by modifying its JSON config file
setup_panel_clock() {
    log "Checking Cinnamon panel clock settings..."
    local config_dir="${USER_HOME_DIR}/.config/cinnamon/spices/calendar@cinnamon.org"

    # 1) Pre-flight check: Only run if the applet's config directory exists
    if [[ ! -d "$config_dir" ]]; then
        log "Calendar applet config directory not found.  Skipping."
        return
    fi

    # 2) Find config file dynamically (not always '13.json')
    local config_file
    # Take first .json file in the directory
    config_file=$(find "$config_dir" -name '*.json' -print -quit)

    if [[ -z "$config_file" ]]; then
        log "No JSON config file found in '$config_dir'.  Skipping."
        return
    fi

    # 3) Define the desired state of the settings
    local date_format='%b %d, %Y %H:%M'
    local tooltip_format='%A, %B %d, %Y, %-I:%M %p'

    # 4) Read current values
    local current_use_custom
    local current_format
    local current_tooltip
    current_use_custom=$(jq -r '."use-custom-format".value' "$config_file")
    current_format=$(jq -r '."custom-format".value' "$config_file")
    current_tooltip=$(jq -r '."custom-tooltip-format".value' "$config_file")

    # 5) Update file if any value is incorrect
    if [[ "$current_use_custom" != "true" || "$current_format" != "$date_format" || "$current_tooltip" != "$tooltip_format" ]]; then
        log "Updating calendar applet configuration..."
        
        # Use jq to update the values and write to temporary file
        local tmp_file
        tmp_file=$(mktemp)
        
        jq \
          '."use-custom-format".value = true' \
          | jq --arg df "$date_format" '."custom-format".value = $df' \
          | jq --arg tf "$tooltip_format" '."custom-tooltip-format".value = $tf' \
          "$config_file" > "$tmp_file"

        # Safely replace the original file and set correct ownership
        mv "$tmp_file" "$config_file"
        chown "${SUDO_USER_NAME}:${SUDO_USER_NAME}" "$config_file"
        log "Calendar applet configuration updated."
    else
        log "Calendar applet settings are already correct."
    fi
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
    setup_panel_clock # handled manually
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
