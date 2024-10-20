#!/bin/bash

# -------- Run with Bash (use `sudo` for privileged tasks) --------

# --- Ensure the system is updated first ---
# Update package lists and installed packages
sudo apt update && sudo apt upgrade -y

# --- Install required packages for setup ---
# Install curl, git, and other essential tools
sudo apt install -y curl wget git build-essential


# -------- STAGE 1: Configure Shell --------

# --- Allow execution of scripts (.sh) on machine ---
# Ensure the script is executable using `chmod +x script.sh`
# Execution policies aren't enforced like PowerShell, but permissions are controlled via `chmod`.

# --- Set up SSH (OpenSSH is usually installed on Mint) ---
# Generate SSH keys if not already existing
if [ ! -f "$HOME/.ssh/id_rsa" ]; then
    ssh-keygen -q -f "$HOME/.ssh/id_rsa" -t rsa -b 4096 -N ""
    echo "SSH keys generated."
fi


# -------- STAGE 2: Provision Software Installer (e.g., Apt, Snap, Flatpak) --------

echo "Calling 'provision_apt.sh' from remote..."
# Define the URL of the script
provision_apt_url="https://raw.githubusercontent.com/david-rachwalik/pc-env/master/setup-linux/provision_apt.sh"
# Download and execute the script content directly
curl -s "$provision_apt_url" | bash
echo "Completed 'provision_apt.sh' process"

# echo "Installing essential software via apt..."
# # You can install common tools or software as needed here
# sudo apt install -y vim htop tmux

# Optional: Add software repositories or PPA (Personal Package Archives)
# Example: Adding the PPA for a specific software
# sudo add-apt-repository ppa:some/ppa -y
# sudo apt update


# -------- STAGE 3: Provision Python --------

echo "Setting up Python..."

echo "Calling 'provision_python.sh' from remote..."
# Define the URL of the script
provision_python_url="https://raw.githubusercontent.com/david-rachwalik/pc-env/master/setup-linux/provision_python.sh"
# Download and execute the script content directly
curl -s "$provision_python_url" | bash
echo "Completed 'provision_python.sh' process"


# # Ensure Python and pip are installed
# sudo apt install -y python3 python3-pip
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


# -------- STAGE 4: Running Python script --------

echo "Running Python setup script..."
# Example of running a Python script (replace path as necessary)
# python3 ~/scripts/simulate.py "abcd"


# -------- STAGE 5: Establishing Scheduled Tasks --------

# Schedule tasks using cron
echo "Setting up cron jobs..."
# Example: Add a cron job to run a script periodically
# (crontab -l ; echo "0 0 * * * /usr/bin/python3 /path/to/script.py") | crontab -


# -------- Optional: Configure Additional System Settings --------

# Example: Configure Git
# git config --global user.name "Your Name"
# git config --global user.email "youremail@example.com"


echo "--- Linux Mint provisioning has completed ---"
exit 0
