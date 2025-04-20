#!/bin/bash
set -e

# -------- Run with bash (as root or sudo) --------

# Ensure the script is run as root
if [[ "$(id -u)" -ne 0 ]]; then
    echo "This script must be run as root or with sudo.  Exiting..."
    exit 1
fi

# ----------------------------------------------------------------
# ----------------------------------------------------------------

# Update package list and install essential packages
setup_core_system() {
    apt update && apt upgrade -y
    apt install -y curl wget git build-essential
}

# Configure shell aliases
setup_aliases() {
    local -a aliases=(
        "alias ytdl='cd ~/Repos/pc-env/docker/yt-dlp && docker compose run --remove-orphans yt-dlp'"
        "alias rclone='cd ~/Repos/pc-env/docker/rclone && docker compose run --remove-orphans rclone'"
    )
    local alias_file="$HOME/.bash_aliases"

    # Ensure alias file exists
    if [ ! -f "$alias_file" ]; then
        touch "$alias_file"
    fi

    # Add each alias if missing from file
    for alias_cmd in "${aliases[@]}"; do
        if ! grep -Fxq "$alias_cmd" "$alias_file"; then
            echo "$alias_cmd" >>"$alias_file"
            echo "Added: $alias_cmd"
        fi
    done
    # Reload shell configuration
    source "$HOME/.bashrc"
    echo "Alias setup complete!"
}

# Generate SSH keys if not present
setup_ssh() {
    local ssh_key="$HOME/.ssh/id_rsa"
    if [ ! -f "$ssh_key" ]; then
        ssh-keygen -q -f "$ssh_key" -t rsa -b 4096 -N ""
        echo "SSH keys generated."
    else
        echo "SSH key already exists."
    fi
}

# Update Cinnamon panel settings
setup_panel_clock() {
    local schema="org.cinnamon.desktop.interface"
    local date_format="%b %d, %Y %H:%M"
    local tooltip_format="%A, %B %d, %Y, %-I:%M %p"

    set_gsetting() {
        local key="$1"
        local value="$2"
        # gsettings list-keys org.cinnamon.desktop.interface
        local current_value=$(gsettings get $schema "$key")

        if [[ "$current_value" != "'$value'" ]]; then
            gsettings set $schema "$key" "$value"
            echo "Updated $key to: $value"
        else
            echo "$key is already set correctly."
        fi
    }

    # set_gsetting "clock-format" "$date_format"
    set_gsetting "clock-use-24-hour" "$date_format"
    set_gsetting "clock-show-seconds" "$tooltip_format"
    echo "Panel settings updated."
}

# Run remote provisioning scripts
run_provisioning_scripts() {
    local base_url="https://raw.githubusercontent.com/david-rachwalik/pc-env/master/setup-linux/provision-apps"
    local -a scripts=("apt.sh" "onedrive.sh" "obsidian.sh")

    for script in "${scripts[@]}"; do
        echo "Calling $script from remote..."
        curl -s "$base_url/$script" | bash
        echo "Completed $script process."
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

# Main execution
main() {
    echo "Starting Linux provisioning..."
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
    echo "--- Successfully completed Linux provisioning! ---"
}

main

# chmod +x ~/Repos/pc-env/init-linux.sh
# sudo bash ~/Repos/pc-env/init-linux.sh
