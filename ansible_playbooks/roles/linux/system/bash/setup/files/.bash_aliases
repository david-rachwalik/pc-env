# --- Alias: Main Actions ---
# setup         provision system install and configuration
# clean         backup files and scrub system
# shutdown      perform system clean and shutdown

# --- Alias: App Projects ---
# repoc         app repository create
# repod         app repository delete
# azc           azure webapp create
# azd           azure webapp delete
# appc          full app create
# appd          full app delete


# Anytime the aliases are updated, be sure to restart your shell; source (.) has permission errors
# https://linuxize.com/post/bash-functions/
# Able to pass parameters such as --tags or --skip-tags
# Example: inline ternary operator (conditional expression); a=$([ "$b" == 5 ] && echo "$c" || echo "$d")
    # if [ -n "$1" ]; then
    #     ansible-playbook "system_setup.yml $*"
    # else
    #     ansible-playbook "system_setup.yml"
    # fi
setup () {
    cd "$HOME/pc-env/ansible_playbooks"
    ansible-playbook system_setup.yml $*
}
clean () {
    cd "$HOME/pc-/ansible_playbooks"
    ansible-playbook system_clean.yml $*
}
shutdown () {
    cd "$HOME/pc-env/ansible_playbooks"
    ansible-playbook system_clean.yml -e 'shutdown=true' $*
}

repoc () {
    cd "$HOME/pc-env/ansible_playbooks"
    # play_run=$([ -n "$1" ] && echo "app_create.yml --tags 'repo' $*" || echo "app_create.yml --tags 'repo'")
    # ansible-playbook $play_run
    ansible-playbook app_create.yml --tags 'repo' $*
}
repod () {
    cd "$HOME/pc-env/ansible_playbooks"
    ansible-playbook app_delete.yml --tags 'repo' $*
}
azc () {
    cd "$HOME/pc-env/ansible_playbooks"
    ansible-playbook app_create.yml --tags 'azure' $*
}
azd () {
    cd "$HOME/pc-env/ansible_playbooks"
    ansible-playbook app_delete.yml --tags 'azure' $*
}
appc () {
    cd "$HOME/pc-env/ansible_playbooks"
    ansible-playbook app_create.yml $*
}
appd () {
    cd "$HOME/pc-env/ansible_playbooks"
    ansible-playbook app_delete.yml $*
}

test_args () {
    echo $?
    echo $*
    echo $0
    echo $1
}

# alias update='( cd "$HOME/pc-env/ansible_playbooks" && ansible-playbook system_setup.yml )'
# alias shutdown='( cd "$HOME/pc-/ansible_playbooks" && ansible-playbook system_clean.yml -e "shutdown=true" )'
# alias clean='( cd "$HOME/pc-env/ansible_playbooks" && ansible-playbook system_clean.yml )'
# alias win_up='( cd "$HOME/pc-env/ansible_playbooks" && ansible-playbook system_setup.yml --tags "windows" )'
# alias wsl_up='( cd "$HOME/pc-env/ansible_playbooks" && ansible-playbook system_setup.yml --tags "linux" )'
# alias win_clean='( cd "$HOME/pc-env/ansible_playbooks" && ansible-playbook system_clean.yml --tags "windows" )'
# alias wsl_clean='( cd "$HOME/pc-env/ansible_playbooks" && ansible-playbook system_clean.yml --tags "linux" )'

# ansible-playbook system_setup.yml --tags "alias"
# setup --tags alias
