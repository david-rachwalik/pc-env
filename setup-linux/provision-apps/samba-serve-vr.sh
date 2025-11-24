#!/bin/bash
set -eu

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Define shares as name:path pairs
SHARES=(
    "vrporn_downloads:/media/root/HDD-01/_Downloads/_VR Porn"
    "vrporn_encodes:/media/root/HDD-02/_Encodes/PervyVR"
    "torrents_done:/media/root/HDD-01/_Downloads/_Torrents/Done"
)
SAMBA_CONF="/etc/samba/smb.conf"
USER="vruser"
PASSWORD="yourpassword" # Change this!

backup_conf() {
    cp "$SAMBA_CONF" "$SAMBA_CONF.bak.$(date +%Y%m%d%H%M%S)"
}

install_samba() {
    if ! command -v smbd &>/dev/null; then
        apt update
        apt install -y samba
    fi
}

create_user() {
    if ! pdbedit -L | /usr/bin/grep -q "^$USER:"; then
        useradd -M -s /usr/sbin/nologin $USER || true
        (
            echo "$PASSWORD"
            echo "$PASSWORD"
        ) | smbpasswd -a $USER
    fi
}

add_share() {
    local NAME="$1"
    local PATH="$2"

    if [ ! -d "$PATH" ]; then
        echo "Warning: $PATH does not exist, skipping $NAME"
        return
    fi

    if ! /usr/bin/grep -q "^\[$NAME\]" $SAMBA_CONF; then
        echo "Adding Samba share $NAME..."
        /usr/bin/tee -a "$SAMBA_CONF" >/dev/null <<EOF

[$NAME]
   path = $PATH
   browseable = yes
   writable = yes
   guest ok = no
   valid users = $USER
   create mask = 0644
   directory mask = 0755
EOF
    fi
}

main() {
    # echo "Backing up $SAMBA_CONF..."
    # backup_conf

    echo "Ensuring Samba is installed..."
    install_samba

    echo "Ensuring Samba user exists..."
    create_user

    # Add shares to smb.conf if not present
    SHARE_NAMES=()
    for SHARE in "${SHARES[@]}"; do
        NAME="${SHARE%%:*}"
        PATH="${SHARE#*:}"
        add_share "$NAME" "$PATH"
        SHARE_NAMES+=("$NAME")
    done

    echo "Restarting Samba service..."
    /usr/bin/systemctl restart smbd

    echo "✅ SMB shares are now available: ${SHARE_NAMES[@]}"
    echo "Use user: $USER, password: $PASSWORD in Skybox or DeoVR."
}

main "$@"

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/samba-serve-vr.sh
# sudo bash ~/Repos/pc-env/setup-linux/provision-apps/samba-serve-vr.sh

# sudo rm /etc/samba/smb.conf
