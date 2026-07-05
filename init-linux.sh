#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error
# -e: Exits immediately if any command fails
# -u: Exits immediately if an undefined variable was used
# -o pipefail: Ensures the whole pipe crashes if any part crashes

# :: Linux Mint (Ubuntu) system provisioning ::
# NOTE: This orchestrator is designed for manual, on-demand execution (e.g., initial
# setup or manual state syncing).  Do not run this on a scheduled background timer.

# ================================================================
# --- Constants ---
# ================================================================

readonly -a CORE_PACKAGES=("curl" "wget" "git" "build-essential" "jq")
readonly SCRIPT_NAME="$(basename "$0")"
readonly SUDO_USER_NAME="${SUDO_USER:-}"
readonly USER_HOME_DIR="$(getent passwd "$SUDO_USER_NAME" | cut -d: -f6)"

# ================================================================
# --- Configuration ---
# ================================================================

readonly PROJECT_DIR="${USER_HOME_DIR}/Repos/pc-env"
readonly -a ALIASES=(
    # "alias <alias-name>='docker compose -f <configuration-file> run --rm <service-name>'"
    "alias ops='docker compose -f \"${PROJECT_DIR}/docker/pc-ops/docker-compose.yml\" run --rm pc-ops'"
    "alias rclone='docker compose -f \"${PROJECT_DIR}/docker/rclone/docker-compose.yml\" run --rm rclone'"
    "alias subs='docker compose -f \"${PROJECT_DIR}/docker/pysubs2/docker-compose.yml\" run --rm pysubs2'"
    "alias ytdl='docker compose -f \"${PROJECT_DIR}/docker/yt-dlp/docker-compose.yml\" run --rm yt-dlp'"
)

readonly -a BASE_SCRIPTS=(
    "appimage.sh"
    "apt.sh"
)
readonly -a FULL_SCRIPTS=(
    "${BASE_SCRIPTS[@]}"
    "filebot.sh"
    "plex-desktop.sh"
    "samba-serve-vr.sh"
    "subtitleedit.sh"
)

# ================================================================
# --- Helper Functions ---
# ================================================================

# Log messages with timestamp and script name
log() {
    # echo "[INFO] $(date +'%Y-%m-%d %H:%M:%S') - $*"
    # echo "[${SCRIPT_NAME}] [INFO] $(date +'%Y-%m-%d %H:%M:%S') - $*"
    echo "[${SCRIPT_NAME}] $(date +'%Y-%m-%d %H:%M:%S') | $*"
}

# Log error messages and exit securely
die() {
    echo "[${SCRIPT_NAME}] [ERROR] $*" >&2
    exit 1
}

# Helper to run command as original user
run_as_user() {
    sudo -u "$SUDO_USER_NAME" "$@"
}

atomic_write() {
    local dest="$1"
    local mode="$2"
    local tmp
    tmp="$(mktemp "${dest}.XXXXXXXX")"
    cat > "$tmp"
    chmod "$mode" "$tmp"

    if [[ -f "$dest" ]] && cmp -s "$tmp" "$dest"; then
        rm -f "$tmp"
        return 0
    fi
    mv -f "$tmp" "$dest"
}

# Ensure script is run as root and can identify original user
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

# Simultaneously prints output to both log file and terminal
setup_pipeline_logging() {
    local log_dir="${USER_HOME_DIR}/logs/provisioning"
    local log_file="${log_dir}/init-$(date +'%Y-%m').log" # Monthly rolling log
    # Ensure directories exist and belong to the user
    if [[ ! -d "$log_dir" ]]; then
        mkdir -p "$log_dir"
        chown "${SUDO_USER_NAME}:${SUDO_USER_NAME}" "$log_dir" 2> /dev/null || true
    fi
    # Ensure file exists and belongs to the user without needlessly updating timestamps
    if [[ ! -f "$log_file" ]]; then
        touch "$log_file"
        chown "${SUDO_USER_NAME}:${SUDO_USER_NAME}" "$log_file" 2> /dev/null || true
    fi
    # Redirect all stdout (1) and stderr (2) to 'tee', safely appending to the log file
    exec > >(tee -a "$log_file") 2>&1
    log "Pipeline logging initialized. Tracking this run in: $log_file"
}

# ================================================================
# --- Provisioning Functions ---
# ================================================================

# Update package list and install essential packages
setup_core_system() {
    log "Ensuring core system packages are installed..."
    local packages_to_install=()
    for pkg in "${CORE_PACKAGES[@]}"; do
        if ! dpkg-query -W -f='${Status}' "$pkg" 2> /dev/null | grep -q "install ok installed"; then
            packages_to_install+=("$pkg")
        fi
    done

    # apt-get is required for automated scripts; apt is preferred for interactive CLI
    if [ ${#packages_to_install[@]} -gt 0 ]; then
        log "Updating APT and installing missing packages: ${packages_to_install[*]}..."
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y "${packages_to_install[@]}"
    else
        log "All core packages are already installed."
    fi
}

# Configure Git identities and ensure an SSH key exists for GitHub access
setup_github_and_ssh() {
    log "Checking for SSH keys & Git configuration..."
    local ssh_dir="${USER_HOME_DIR}/.ssh"

    # Git globals
    local -A git_configs
    git_configs["user.name"]="David Rachwalik"
    git_configs["user.email"]="david.rachwalik@outlook.com"
    git_configs["core.editor"]="code --wait"
    # (shfmt struggles with multi-line associative arrays)

    for key in "${!git_configs[@]}"; do
        local expected_val="${git_configs[$key]}"
        local current_val
        current_val=$(run_as_user git config --global --get "$key" || true)

        if [[ "$current_val" != "$expected_val" ]]; then
            run_as_user git config --global "$key" "$expected_val"
            log "Configured Git global: $key (${git_configs[$key]})"
        fi
    done

    # Ensure SSH directory and GitHub known_hosts entry exist
    run_as_user mkdir -p "$ssh_dir"
    run_as_user chmod 700 "$ssh_dir"  # to fulfill SSH's security requirements
    run_as_user touch "${ssh_dir}/known_hosts"

    # Use ssh-keygen -F to properly search for hashed hostnames
    if ! run_as_user ssh-keygen -F github.com -f "${ssh_dir}/known_hosts" > /dev/null 2>&1; then
        log "Adding github.com to known_hosts..."
        run_as_user ssh-keyscan -H github.com >> "${ssh_dir}/known_hosts" 2> /dev/null
    fi
}

# Delegate further installation steps to explicit remote scripts
run_provisioning_scripts() {
    log "Running provisioning scripts..."
    readonly provisioning_scripts_dir="${PROJECT_DIR}/setup-linux/provision-apps"
    readonly provisioning_scripts_url="https://raw.githubusercontent.com/david-rachwalik/pc-env/master/setup-linux/provision-apps"

    local active_scripts=()
    local script_opts=()

    if [ "$MINIMAL_MODE" = true ]; then
        log "Minimal Mode:  Running ONLY base scripts."
        active_scripts=("${BASE_SCRIPTS[@]}")
        script_opts+=("--minimal") # Pass down for base scripts like apt.sh that have internal splits
    else
        log "Standard Mode:  Running FULL script suite."
        active_scripts=("${FULL_SCRIPTS[@]}")
    fi

    local use_local=false
    if [[ -d "$provisioning_scripts_dir" ]]; then
        use_local=true
        log "Local repository detected at '${PROJECT_DIR}'.  Executing local scripts..."
    else
        log "Local repository not found.  Executing remote scripts from GitHub..."
    fi

    for script in "${active_scripts[@]}"; do
        if [[ "$use_local" == true ]]; then
            local local_script="${provisioning_scripts_dir}/${script}"
            if [[ -f "$local_script" ]]; then
                log "Executing local script: $local_script"
                bash "$local_script" "${script_opts[@]}"
                log "Completed $script process."
            else
                log "Failed to find local script: $local_script.  Skipping." >&2
            fi
        else
            log "Fetching remote script: $script"
            local tmp_script
            tmp_script=$(mktemp)
            # Added '-f' switch to fail silently on HTTP errors
            if curl -sLf "${provisioning_scripts_url}/${script}" -o "$tmp_script"; then
                bash "$tmp_script" "${script_opts[@]}"
                log "Completed $script process."
            else
                log "Failed to download $script from URL.  Skipping." >&2
            fi
            rm -f "$tmp_script"
        fi
    done
}

# Configure shell aliases (command shortcuts)
setup_aliases() {
    log "Checking shell aliases..."
    local alias_file="${USER_HOME_DIR}/.bash_aliases"
    local added=false

    # Safely ensure target file exists mapped to user
    run_as_user touch "$alias_file"

    # Iterate and append only missing lines
    for alias_cmd in "${ALIASES[@]}"; do
        if ! grep -Fxq "$alias_cmd" "$alias_file"; then
            echo "$alias_cmd" >> "$alias_file"
            log "Adding alias: ${alias_cmd%%=*}"
            added=true
        fi
    done

    if [ "$added" = true ]; then
        log "Alias check complete.  If changes were made, run 'source ~/.bashrc' or restart your shell."
    else
        log "All aliases are already present."
    fi
}

# Keep Cinnamon applets and standard settings harmonized
setup_panel_clock() {
    log "Checking Cinnamon panel clock settings..."

    # --- System-wide Display Settings (via gsettings) ---

    if command -v gsettings &> /dev/null; then
        local schema="org.cinnamon.desktop.interface"

        # Safely wrap setting manipulation allowing for headless fallbacks
        set_gsetting() {
            local key="$1"
            local value="$2"
            local current_value
            # Suppress errors if D-Bus session is completely unavailable during headless execution
            current_value=$(run_as_user gsettings get "$schema" "$key" 2> /dev/null || true)

            if [[ -n "$current_value" && "$current_value" != "'$value'" && "$current_value" != "$value" ]]; then
                run_as_user gsettings set "$schema" "$key" "$value" 2> /dev/null || true
                log "Updated gsetting '$key'."
            fi
        }

        # > gsettings list-keys org.cinnamon.desktop.interface
        set_gsetting "clock-use-24h" "true"
    fi

    # --- Cinnamon Calendar Applet Settings (via JSON) ---

    local config_dir="${USER_HOME_DIR}/.config/cinnamon/spices/calendar@cinnamon.org"

    if [[ ! -d "$config_dir" ]]; then
        return  # Skip if config directory doesn't exist
    fi

    # Find config file dynamically (not always '13.json')
    local config_file
    # Take first .json file in the directory
    config_file=$(find "$config_dir" -name '*.json' -print -quit)

    if [[ -z "$config_file" ]]; then
        log "No JSON config file found in '$config_dir'.  Skipping."
        return
    fi

    # Define desired state of the settings
    local date_format='%b %d, %Y %H:%M'
    local tooltip_format='%A, %B %d, %Y, %-I:%M %p'

    # Read current values
    local current_use_custom current_format current_tooltip
    current_use_custom=$(jq -r '."use-custom-format".value' "$config_file" 2> /dev/null || echo "null")
    current_format=$(jq -r '."custom-format".value' "$config_file" 2> /dev/null || echo "null")
    current_tooltip=$(jq -r '."custom-tooltip-format".value' "$config_file" 2> /dev/null || echo "null")

    # Update file if any value is incorrect
    if [[ "$current_use_custom" != "true" || "$current_format" != "$date_format" || "$current_tooltip" != "$tooltip_format" ]]; then
        log "Updating calendar applet configuration..."
        local tmp_file
        tmp_file=$(mktemp)

        # Utilize JQ to modify JSON component values
        if jq '."use-custom-format".value = true' \
            | jq --arg df "$date_format" '."custom-format".value = $df' \
            | jq --arg tf "$tooltip_format" '."custom-tooltip-format".value = $tf' \
                "$config_file" > "$tmp_file"; then

            # Replace original file and set ownership
            mv "$tmp_file" "$config_file"
            chown "${SUDO_USER_NAME}:${SUDO_USER_NAME}" "$config_file"
            log "Calendar applet configuration has been successfully updated!"
        else
            log "Failed to parse calendar configurations." >&2
            rm -f "$tmp_file"
        fi
    else
        log "Calendar applet settings are already good."
    fi
}

# Run automated backup tasks with native Linux process supervision
setup_backup_timer() {
    log "Configuring systemd timer for 'pc_backup.py'..."
    local systemd_dir="/etc/systemd/system"
    local service_file="${systemd_dir}/pc-backup.service"
    local timer_file="${systemd_dir}/pc-backup.timer"

    atomic_write "$service_file" 644 << EOF
[Unit]
Description=PC Backup Service
After=network.target docker.service
Requires=docker.service
# SAFETY LOCK: Abort backup if the system has not been explicitly restored first
ConditionPathExists=${USER_HOME_DIR}/.config/pc-env/.system_restored

[Service]
Type=oneshot
User=${SUDO_USER_NAME}
WorkingDirectory=${PROJECT_DIR}/docker/pc-ops
ExecStart=/usr/bin/docker compose -f ${PROJECT_DIR}/docker/pc-ops/docker-compose.yml run --rm pc-ops python3 /app/pc_backup.py
EOF

    atomic_write "$timer_file" 644 << EOF
[Unit]
Description=Run PC Backup daily at 06:45 AM

[Timer]
OnCalendar=*-*-* 06:45:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
    systemctl enable --now pc-backup.timer
    log "Systemd timer activated (will remain safely dormant until restore sentinel exists)."
}

# Run automated cleanup for unused Docker data
setup_docker_prune_timer() {
    log "Configuring systemd timer for Docker prune..."
    local systemd_dir="/etc/systemd/system"
    local service_file="${systemd_dir}/docker-prune.service"
    local timer_file="${systemd_dir}/docker-prune.timer"

    atomic_write "$service_file" 644 << EOF
[Unit]
Description=Prune unused Docker data

[Service]
Type=oneshot
ExecStart=/usr/bin/docker system prune -af --filter "until=720h"
EOF

    atomic_write "$timer_file" 644 << EOF
[Unit]
Description=Run Docker prune monthly

[Timer]
OnCalendar=monthly
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl daemon-reload
    systemctl enable --now docker-prune.timer
    log "Docker prune timer activated."
}

# ================================================================
# --- Main Execution ---
# ================================================================

MINIMAL_MODE=false

# Modern Bash argument parsing
while [[ $# -gt 0 ]]; do
    case "$1" in
        -m | --minimal)
            MINIMAL_MODE=true
            shift
            ;;
        *)
            echo "[ERROR] Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Main Orchestrator
main() {
    ensure_root
    setup_pipeline_logging
    log "Starting Linux provisioning..."

    setup_core_system
    setup_github_and_ssh
    run_provisioning_scripts
    setup_aliases
    setup_panel_clock
    setup_backup_timer
    setup_docker_prune_timer

    log "--- Successfully completed Linux provisioning! ---"
}

main

# chmod +x ~/Repos/pc-env/init-linux.sh
# sudo bash ~/Repos/pc-env/init-linux.sh
