#!/usr/bin/env bash
set -euo pipefail

# Installs the pCloud Drive AppImage for the current user
# https://www.pcloud.com/how-to-install-pcloud-drive-linux.html

echo "### Installing pCloud Drive AppImage... ###"
# INSTALL_SCRIPT_PATH="/workspaces/pc-env/setup-linux/install-appimage.sh"
# INSTALL_SCRIPT_PATH="../install-appimage.sh"
INSTALL_SCRIPT_PATH="$HOME/Repos/pc-env/setup-linux/install-appimage.sh"

if [[ ! -f "$INSTALL_SCRIPT_PATH" ]]; then
    echo "ERROR: install-appimage.sh not found at $INSTALL_SCRIPT_PATH"
    exit 1
fi

# The script will install to ~/.local/... for the current user
bash "$INSTALL_SCRIPT_PATH" \
    --name "pCloud Drive" \
    --id "pcloud" \
    --url "https://p-lux2.pcloud.com/cBZ3NEL1X7ZbOFyPC7ZZZqner0kZ2ZZ4o4ZkZ8QnszZhRZlRZ3TZwpZGFZL4ZnYZXYZI8Z9RZiHZHQZqTZm4Z8opl5ZpLtsjLYoQRQXrCGRySYJR5k8fsgy/pCloud.AppImage" \
    --categories "Network;FileTransfer;Cloud;" \
    --extract-icon

echo ""
echo "✅ pCloud Drive installation script finished."
echo "You may need to log out and log back in for the application to appear in your menu."

# chmod +x ~/Repos/pc-env/setup-linux/provision-apps/pcloud-drive.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/pcloud-drive.sh
