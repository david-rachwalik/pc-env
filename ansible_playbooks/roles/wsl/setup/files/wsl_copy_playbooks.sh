#!/bin/bash

# Run command: sudo -H /mnt/d/Repos_Exp/pc-setup/bin/wsl_copy_playbooks.sh

mkdir /etc/ansible/group_vars
mkdir /etc/ansible/host_vars
cp /mnt/d/Repos_Exp/pc-setup/etc/ansible/group_vars/windows.yml /etc/ansible/group_vars/windows.yml
cp /mnt/d/Repos_Exp/pc-setup/etc/ansible/host_vars/localhost.yml /etc/ansible/host_vars/localhost.yml
cp /mnt/d/Repos_Exp/pc-setup/play_test.yml /etc/ansible/play_test.yml

# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-apt
# curl -sL https://aka.ms/InstallAzureCLIDeb | bash
