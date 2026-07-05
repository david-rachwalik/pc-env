#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# Ensure a GitHub username is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <github-username> <system>"
    exit 1
fi

GITHUB_USER="$1"

SSH_KEY_PATH="$HOME/.ssh/github_$GITHUB_USER"
SSH_CONFIG_MANAGER="$(dirname "$0")/ssh-config-manager.sh"

# ----------------------------------------------------------------
# --- Worker Functions ---
# ----------------------------------------------------------------

remove_local_keys() {
    if [[ -f "$SSH_KEY_PATH" ]]; then
        echo "Removing local private SSH key file..."
        rm -f "$SSH_KEY_PATH"
    fi
    if [[ -f "$SSH_KEY_PATH.pub" ]]; then
        echo "Removing local public SSH key file..."
        rm -f "$SSH_KEY_PATH.pub"
    fi
}

unlink_ssh_config() {
    local github_host="github.com-$GITHUB_USER"
    bash "$SSH_CONFIG_MANAGER" remove "$github_host"
}

remove_from_github() {
    # Get the existing key ID by matching the key content
    local pub_key_content
    # Using NF "number of fields" (columns) instead of fixed field positions because key contains spaces
    if [[ -f "$SSH_KEY_PATH.pub" ]]; then
        pub_key_content=$(cat "$SSH_KEY_PATH.pub")
    fi

    local github_key_id
    github_key_id=$(gh ssh-key list | grep "^${GITHUB_USER}[[:space:]]" | awk '{print $(NF-1)}')

    # Ensure SSH public key is removed from GitHub (https://github.com/settings/keys)
    if [[ -n "$github_key_id" ]]; then
        echo "Removing SSH key from GitHub (ID: $github_key_id)..."
        # https://cli.github.com/manual/gh_ssh-key_add
        gh ssh-key delete "$github_key_id" -y
    else
        echo "SSH key (ID: $github_key_id) does not exist on GitHub.  Skipping..."
    fi
}

# ----------------------------------------------------------------
# --- Main Orchestrator ---
# ----------------------------------------------------------------

main() {
    echo "Starting SSH key removal for $GITHUB_USER..."

    remove_local_keys
    unlink_ssh_config
    remove_from_github

    echo "✅ SSH key removed for $GITHUB_USER."
}

main "$@"

# --- Run the script once per GitHub user (do NOT use sudo) ---

# chmod +x ~/Repos/pc-env/setup-linux/ssh/remove-ssh.sh
# bash ~/Repos/pc-env/setup-linux/ssh/remove-ssh.sh <USER>
# bash ~/Repos/pc-env/setup-linux/ssh/remove-ssh.sh david-rachwalik
