#!/bin/bash
set -e # Exit immediately on error

# Ensure a GitHub username is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <github-username> <system>"
    exit 1
fi

GITHUB_USER="$1"

SSH_KEY_PATH="$HOME/.ssh/github_$GITHUB_USER"
SSH_CONFIG_MANAGER="$(dirname "$0")/ssh-config-manager.sh"

# -------- Remove SSH Key for GitHub User --------

# Remove local SSH key files if they exist
if [[ -f "$SSH_KEY_PATH" ]]; then
    echo "Removing local private SSH key file..."
    rm -f "$SSH_KEY_PATH"
fi
if [[ -f "$SSH_KEY_PATH.pub" ]]; then
    echo "Removing local public SSH key file..."
    rm -f "$SSH_KEY_PATH.pub"
fi

# Ensure SSH key is removed from config
GITHUB_HOST="github.com-$GITHUB_USER"
bash "$SSH_CONFIG_MANAGER" remove "$GITHUB_HOST"

# Get the existing key ID by matching the key content
PUB_KEY_CONTENT=$(cat "$SSH_KEY_PATH.pub")
# GITHUB_KEY_ID=$(gh ssh-key list | grep "$PUB_KEY_CONTENT" | awk '{print $1}')
# Using NF "number of fields" (columns) instead of fixed field positions because key contains spaces
GITHUB_KEY_ID=$(gh ssh-key list | grep "^${GITHUB_USER}[[:space:]]" | awk '{print $(NF-1)}')

# Ensure SSH public key is removed from GitHub (https://github.com/settings/keys)
if [[ -z "$GITHUB_KEY_ID" ]]; then
    echo "Adding SSH key to GitHub..."
    # https://cli.github.com/manual/gh_ssh-key_add
    gh ssh-key delete "$GITHUB_KEY_ID" -y
else
    echo "SSH key already exists on GitHub (ID: $GITHUB_KEY_ID)"
fi

echo "✅ SSH key removed for $GITHUB_USER."

# --- Run the script once per GitHub user (do NOT use sudo) ---

# chmod +x ~/Repos/pc-env/setup-linux/ssh/remove_ssh.sh
# bash ~/Repos/pc-env/setup-linux/ssh/remove_ssh.sh <USER>
# bash ~/Repos/pc-env/setup-linux/ssh/remove_ssh.sh david-rachwalik
