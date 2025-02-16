#!/bin/bash
set -e # Exit immediately on error

# Ensure a GitHub username is provided
if [[ -z "$1" ]]; then
    echo "Usage: $0 <github-username> <system>"
    exit 1
fi
# Ensure a system description is provided
if [[ -z "$2" ]]; then
    echo "Usage: $0 <github-username> <system>"
    exit 1
fi

GITHUB_USER="$1"
SYSTEM_ALIAS="$2"

SSH_DIR="$HOME/.ssh"
SSH_KEY_PATH="$SSH_DIR/github_$GITHUB_USER"
SSH_CONFIG_MANAGER="$(dirname "$0")/ssh-config-manager.sh"

# -------- Create SSH Key for GitHub User --------

# --- What This Script Does ---
# :Step:                        :What It Does:
# Ensure ~/.ssh/ exists         Creates the SSH directory if missing
# Set correct permissions       Ensures ~/.ssh is 700 and private key is 600
# Generate SSH key              Creates the key only if it doesn't exist
# Add key to GitHub             Uses gh ssh-key list to check if key exists before adding
# Configure SSH for GitHub      Adds a SSH config entry per-user only if missing

# Ensure the SSH directory exists with correct permissions
if [[ ! -d "$SSH_DIR" ]]; then
    echo "Creating SSH directory: $SSH_DIR"
    mkdir -p "$SSH_DIR"
fi
if [[ "$(stat -c '%a' "$SSH_DIR")" != "700" ]]; then
    echo "Updating SSH directory permissions: $SSH_DIR"
    chmod 700 "$SSH_DIR"
fi

# Ensure SSH key exists with correct permissions
if [[ ! -f "$SSH_KEY_PATH" ]]; then
    echo "Generating SSH key for $GITHUB_USER..."
    ssh-keygen -t ed25519 -C "$GITHUB_USER@github.com" -f "$SSH_KEY_PATH" -N ""
else
    echo "SSH key already exists: $SSH_KEY_PATH"
fi
if [[ "$(stat -c '%a' "$SSH_KEY_PATH")" != "600" ]]; then
    echo "Fixing SSH key permissions: $SSH_KEY_PATH"
    chmod 600 "$SSH_KEY_PATH"
fi

# Ensure SSH key is referenced in config
GITHUB_HOST="github.com-$GITHUB_USER"
# bash "$SSH_CONFIG_MANAGER" add "$GITHUB_HOST" "github.com" "$SSH_KEY_PATH"
bash "$SSH_CONFIG_MANAGER" add "$GITHUB_HOST" "github.com" "~/.ssh/github_$GITHUB_USER"

# Get the existing key ID by matching the key content
PUB_KEY_CONTENT=$(cat "$SSH_KEY_PATH.pub")
# GITHUB_KEY_ID=$(gh ssh-key list | grep "$PUB_KEY_CONTENT" | awk '{print $1}')
# Using NF "number of fields" (columns) instead of fixed field positions because key contains spaces
GITHUB_KEY_ID=$(gh ssh-key list | grep "^${GITHUB_USER}[[:space:]]" | awk '{print $(NF-1)}')

# Ensure SSH public key is added to GitHub (https://github.com/settings/keys)
if [[ -z "$GITHUB_KEY_ID" ]]; then
    echo "Adding SSH key to GitHub..."
    # https://cli.github.com/manual/gh_ssh-key_add
    gh ssh-key add "$SSH_KEY_PATH.pub" --title "[$SYSTEM_ALIAS] $GITHUB_USER"
else
    echo "SSH key already exists on GitHub (ID: $GITHUB_KEY_ID)"
fi

echo "✅ SSH setup complete for $GITHUB_USER!"

# --- Verify GitHub CLI is authenticated to the correct account ---

# gh auth status
# gh auth logout
# gh auth login --hostname github.com --git-protocol ssh --web

# --- Run the script once per GitHub user (do NOT use sudo) ---

# chmod +x ~/Repos/pc-env/setup-linux/ssh/add_ssh.sh
# bash ~/Repos/pc-env/setup-linux/ssh/add_ssh.sh <USER> <SYSTEM>
# bash ~/Repos/pc-env/setup-linux/ssh/add_ssh.sh david-rachwalik Mint-22

# --- Update each Git repository's remote to SSH path ---

# git remote -v
# EXAMPLE HTTPS PATH:   https://github.com/<USER>/<REPO>
# EXAMPLE SSH PATH:     git@github.com-<ALIAS>:<USER><REPO>.git

# git remote set-url <ALIAS> <PATH>
# OLD: git remote set-url origin https://github.com/david-rachwalik/pc-env
# NEW: git remote set-url origin git@github.com-david-rachwalik:david-rachwalik/pc-env.git
# NEW: git remote set-url origin git@github.com-david-rachwalik:david-rachwalik/david-rachwalik.github.io.git

# --- Before making commits, verify correct email is configured ---

# git config user.name "David Rachwalik"
# git config user.email "david.rachwalik@outlook.com"
