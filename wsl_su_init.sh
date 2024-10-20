#!/bin/sh
wsl_ssh=${HOME}/.ssh
win_project=/mnt/f/Repos/pc-env
wsl_project=${HOME}/pc-env
win_vault=${win_project}/ansible_playbooks/group_vars/windows/main_vault.yml
wsl_vault=${wsl_project}/ansible_playbooks/group_vars/windows/main_vault.yml

# --- This file only to be run as user ---

# --- Git Steps ---
# https://help.github.com/en/articles/checking-for-existing-ssh-keys
# Generate SSH keys if they don't exist
if ! test -d ${wsl_ssh}; then
    mkdir ${wsl_ssh}
    chmod 755 ${wsl_ssh}
    # https://help.github.com/en/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent
    ssh-keygen -q -f ${wsl_ssh}/id_rsa -t rsa -b 4096 -N ""
    # Start the ssh-agent in the background
    eval $(ssh-agent -s)
    ssh-add ${wsl_ssh}/id_rsa
    # Add the contents of your local public key to authorized_keys
    if ! test -f ${wsl_ssh}/authorized_keys; then
        cat ${wsl_ssh}/id_rsa.pub >${wsl_ssh}/authorized_keys
    fi
    # Add GitHub to known_hosts if it doesn't exist
    if ! test -f ${wsl_ssh}/known_hosts; then
        touch ${wsl_ssh}/known_hosts
    fi
    ssh-keygen -F github.com || ssh-keyscan -H github.com >>${wsl_ssh}/known_hosts
    # Above must be run once, copy public SSH key to GitHub Settings, and run again
    echo "Copy this SSH key to your GitHub Settings:"
    cat ${wsl_ssh}/id_rsa.pub
    ssh_response=""
    while [ "${ssh_response}" != "y" ]; do
        read -p "Enter (y) after SSH key has been added to GitHub: " ssh_response
    done

    # Testing sed command to update SSH config
    # sed 's/^PasswordAuthentication.*/PasswordAuthentication yes/i' /etc/ssh/sshd_config | grep '^PasswordAuthentication.*'
    # sudo sed -i 's/^PasswordAuthentication.*/PasswordAuthentication yes/i' /etc/ssh/sshd_config
    # sudo sed -i 's/^#PermitRootLogin.*/PermitRootLogin yes/i' /etc/ssh/sshd_config
    # sudo sed -i 's/.*PubkeyAuthentication.*/PubkeyAuthentication yes/i' /etc/ssh/sshd_config
    # sudo service ssh restart
fi

if ! test -d ${wsl_project}; then
    # https://git-scm.com/book/en/v2/Getting-Started-First-Time-Git-Setup
    git config --global user.name "David Rachwalik"
    git config --global user.email "david.rachwalik@outlook.com"
    # https://git-scm.com/book/en/v2/Appendix-C%3A-Git-Commands-Setup-and-Config#_core_editor
    git config --global core.editor "code --wait"
    # View Git settings
    git config --list --show-origin
    git clone git@github.com:david-rachwalik/pc-env.git ${wsl_project}
fi

if test -d ${wsl_project}; then
    # Fetch the vault file if it exists
    # TODO: test whether creating a file symlink with Ansible will retroactively win_ping in the same playbook
    # --- TODO: more importantly, change following to a 3-var-prompt for win connect info ---
    if test -f ${win_vault}; then
        cp -f ${win_vault} ${wsl_vault}
    fi

    # Update all systems; shutdown=false is default - prevents Windows restarts
    cd ${wsl_project}
    git pull

    # Ansible ignores ansible.cfg in a world-writable directory
    # https://docs.ansible.com/ansible/devel/reference_appendices/config.html#cfg-in-world-writable-dir
    find ${wsl_project} -type d -print0 | xargs -0 chmod 755
    find ${wsl_project} -type f -print0 | xargs -0 chmod 644

    cd ${wsl_project}/ansible_playbooks
    ansible-playbook system_setup.yml
fi
