#!/bin/bash

SSH_CONFIG="$HOME/.ssh/config"

remove_extra_lines() {
    # Remove consecutive blank lines
    sed -i '/^$/N;/^\n$/D' "$SSH_CONFIG"
    # Ensure file doesn't start with a blank line
    sed -i '/./,$!d' "$SSH_CONFIG"
}

add_host() {
    local host_alias="$1"
    local hostname="$2"
    local identity_file="$3"

    if grep -q "Host $host_alias" "$SSH_CONFIG"; then
        echo "Host $host_alias already exists in SSH config."
    else
        echo "Adding Host $host_alias..."
        cat <<EOF >>"$SSH_CONFIG"

Host $host_alias
    HostName $hostname
    User git
    IdentityFile $identity_file
    IdentitiesOnly yes
EOF
        remove_extra_lines
        echo "✅ Host $host_alias added to SSH config!"
    fi
}

remove_host() {
    local host_alias="$1"
    echo "Removing Host $host_alias..."
    # Fixed Length: removes exactly 4 lines
    # sed -i "/Host $host_alias/,+3d" "$SSH_CONFIG"
    # Adaptive: stops at first empty line
    sed -i "/^Host $host_alias$/,/^$/d" "$SSH_CONFIG"
    remove_extra_lines
    echo "✅ Host $host_alias removed from SSH config."
}

list_hosts() {
    grep "^Host " "$SSH_CONFIG" | awk '{print $2}'
}

# -------- MAIN --------

# Ensure SSH config file exists with correct permissions
if [ ! -f "$SSH_CONFIG" ]; then
    echo "Creating SSH config file: $SSH_CONFIG"
    touch "$SSH_CONFIG"
fi
if [ "$(stat -c '%a' "$SSH_CONFIG")" != "600" ]; then
    echo "Fixing SSH config permissions: $SSH_CONFIG"
    chmod 600 "$SSH_CONFIG"
fi

if [[ "$1" == "add" ]]; then
    add_host "$2" "$3" "$4"
elif [[ "$1" == "remove" ]]; then
    remove_host "$2"
elif [[ "$1" == "list" ]]; then
    list_hosts
else
    echo "Usage:"
    echo "  $0 add <host_alias> <hostname> <identity_file>"
    echo "  $0 remove <host_alias>"
    echo "  $0 list"
    exit 1
fi

# 🔹 Usage 🔹
# --- Add a new SSH host ---
# bash ssh-config-manager.sh add <HOST> <HOSTNAME> <PATH>
# bash ssh-config-manager.sh add github.com-rhodair github.com ~/.ssh/github_rhodair
# --- Remove an SSH host ---
# bash ssh-config-manager.sh remove github.com-rhodair
# --- List all configured hosts ---
# bash ssh-config-manager.sh list
