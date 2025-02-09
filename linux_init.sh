#!/bin/bash
set -e

# Ensure the script is being run as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root"
    exit 1
fi

# -------- Ready the system for setup tasks --------

# Update package lists and installed packages
apt update && apt upgrade -y
# Install required packages for setup: curl, git, and other essential tools
apt install -y curl wget git build-essential

# -------- Configure Shell --------

# --- Add Aliases ---

ALIASES=(
    "alias ytdl='bash ~/Repos/pc-env/docker/yt-dlp/run.sh'"
    "alias joplin='~/.joplin/Joplin.AppImage'"
)

# Ensure ~/.bash_aliases exists
if [ ! -f ~/.bash_aliases ]; then
    touch ~/.bash_aliases
fi

# Add each alias only if it’s not already in the file
for ALIAS_CMD in "${ALIASES[@]}"; do
    if ! grep -Fxq "$ALIAS_CMD" ~/.bash_aliases; then
        echo "$ALIAS_CMD" >>~/.bash_aliases
        echo "Added: $ALIAS_CMD"
    else
        echo "Already exists: $ALIAS_CMD"
    fi
done

# # Ensure ~/.bash_aliases is sourced in ~/.bashrc
# if ! grep -q "source ~/.bash_aliases" ~/.bashrc; then
#     echo "source ~/.bash_aliases" >>~/.bashrc
#     echo "Added source command to ~/.bashrc"
# fi

# Reload shell configuration
source ~/.bashrc

echo "Alias setup complete!"

# --- Allow execution of scripts (.sh) on machine ---
# Ensure the script is executable using `chmod +x script.sh`
# Execution policies aren't enforced like PowerShell, but permissions are controlled via `chmod`.

# --- Set up SSH (OpenSSH is usually installed on Mint) ---
# Generate SSH keys if not already existing
if [ ! -f "$HOME/.ssh/id_rsa" ]; then
    ssh-keygen -q -f "$HOME/.ssh/id_rsa" -t rsa -b 4096 -N ""
    echo "SSH keys generated."
fi

# -------- Configure Panel (Taskbar) --------

# Function to update a gsettings key if needed
set_gsetting() {
    local key="$1"
    local value="$2"
    local current_value

    current_value=$(gsettings get org.cinnamon.desktop.interface "$key")

    if [[ "$current_value" != "'$value'" ]]; then
        gsettings set org.cinnamon.desktop.interface "$key" "$value"
        echo "Updated $key to: $value"
    else
        echo "$key is already set correctly."
    fi
}

# Define the desired date formats
DATE_FORMAT="%b %d, %Y %H:%M"
TOOLTIP_FORMAT="%A, %B %d, %Y, %-I:%M %p"

# Apply the settings
set_gsetting "clock-format" "$DATE_FORMAT"
set_gsetting "clock-show-seconds" "$TOOLTIP_FORMAT"

echo "Done setting custom date format."

# -------- Provision Software Installer (e.g., Apt, Snap, Flatpak) --------

echo "Calling 'provision_apt.sh' from remote..."
# Define the URL of the script
provision_apt_url="https://raw.githubusercontent.com/david-rachwalik/pc-env/master/setup-linux/provision_apt.sh"
# Download and execute the script content directly
curl -s "$provision_apt_url" | bash
echo "Completed 'provision_apt.sh' process"

# -------- Provision Python --------

echo "Setting up Python..."

echo "Calling 'provision_python.sh' from remote..."
# Define the URL of the script
provision_python_url="https://raw.githubusercontent.com/david-rachwalik/pc-env/master/setup-linux/provision_python.sh"
# Download and execute the script content directly
curl -s "$provision_python_url" | bash
echo "Completed 'provision_python.sh' process"

# # Ensure Python and pip are installed
# apt install -y python3 python3-pip
# # Optionally install virtual environment tools
# pip3 install --user virtualenv

# # Add Python scripts directory to PATH if needed
# PYTHON_USER_BIN=$(python3 -m site --user-base)/bin
# if [[ ":$PATH:" != *":$PYTHON_USER_BIN:"* ]]; then
#     echo "Adding $PYTHON_USER_BIN to PATH"
#     export PATH="$PYTHON_USER_BIN:$PATH"
#     echo "export PATH=\"$PYTHON_USER_BIN:\$PATH\"" >> ~/.bashrc
#     source ~/.bashrc
# fi

# -------- Establishing Scheduled Tasks --------

# Schedule tasks using cron
echo "Setting up cron jobs..."
# Example: Add a cron job to run a script periodically
# (crontab -l ; echo "0 0 * * * /usr/bin/python3 /path/to/script.py") | crontab -

echo "--- Successfully completed Linux provisioning! ---"
exit 0

# sudo bash ~/Repos/pc-env/linux_init.sh
