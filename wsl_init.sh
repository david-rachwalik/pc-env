#!/bin/sh

# tested for Linux Ubuntu versions: [18.04, 20.04]
distro=$(lsb_release --id --short)       # Ubuntu
release=$(lsb_release --release --short) # [18.04, 20.04]

if test "${distro}" != "Ubuntu"; then
    echo "This script currently only supports Ubuntu distributions"
    exit 1
fi

if test "${SUDO_USER}" != ""; then
    run_user="${SUDO_USER}"
else
    run_user="${USER}"
    echo "This script must be run using 'sudo'"
    exit 1
fi

# Grant user nopasswd sudo access
# https://gist.github.com/carlessanagustin/922711701b1cfcc5c7a056c7018e8fe2
if ! test -f /etc/sudoers.d/${run_user}; then
    # touch /etc/sudoers.d/${run_user}
    usermod -a -G sudo ${run_user} # add user to sudoers group
    bash -c "echo '%${run_user} ALL=NOPASSWD:ALL' > /etc/sudoers.d/${run_user}"
    chmod 440 /etc/sudoers.d/${run_user}
fi

# Upgrade Linux distribution
export DEBIAN_FRONTEND=noninteractive
apt-get update && apt-get dist-upgrade -y

# Install Ansible and dependencies
apt-get install -y python3
apt-get install -y python3-pip
apt-get install -y python3-winrm
pip3 install -U ansible=2.9.27

# Register Microsoft to trusted keys and add package repository (for .NET SDK and Azure CLI)
# https://docs.microsoft.com/en-us/dotnet/core/install/linux-ubuntu
$microsoft_repository_src="https://packages.microsoft.com/config/ubuntu/${release}/packages-microsoft-prod.deb"
$microsoft_repository_tmp="/var/cache/apt/archives/packages-microsoft-prod.deb"
if ! test -f ${microsoft_repository_tmp}; then
    wget -q ${microsoft_repository_src} -O ${microsoft_repository_tmp}
    dpkg -i ${microsoft_repository_tmp}
fi

# Install .NET SDK
dotnet_install_path=https://raw.githubusercontent.com/dotnet/runtime/master/eng/common/dotnet-install.sh
# version="3.1" # default is 'Current'
version="5.0" # default is 'Current'
curl -sSL $dotnet_install_path | bash /dev/stdin -c $version

# Install Azure CLI
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt
curl -sL https://aka.ms/InstallAzureCLIDeb | bash

# Run remaining commands as user
su -c "curl -s https://raw.githubusercontent.com/david-rachwalik/pc-env/master/wsl_su_init.sh | bash" ${run_user}
