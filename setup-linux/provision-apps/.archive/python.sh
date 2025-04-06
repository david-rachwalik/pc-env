#!/bin/bash

# Ensure the script is being run as root (POSIX-compliant test)
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root"
    exit 1
fi

# --- Third-Party Modules ---
pip_packages=(
    # --- Development ---
    autopep8
    colorlog
    pytest
    pytz
    python-dotenv # https://pypi.org/project/python-dotenv
    pylint-quotes
    dirsync     # https://github.com/tkhyn/dirsync
    pyinstaller # https://pyinstaller.org/en/stable
    requests    # https://requests.readthedocs.io
    watchdog

    # --- Projects ---
    # Azure SDKs and tools
    # https://learn.microsoft.com/en-us/azure/developer/python/configure-local-development-environment
    # https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-overview#connect-to-and-use-azure-resources-with-client-libraries
    azure-identity
    # azure.mgmt.subscription
    azure-mgmt-resource
    azure-keyvault-secrets # https://pypi.org/project/azure-keyvault-secrets
    # https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-db
    # https://learn.microsoft.com/en-us/azure/developer/python/sdk/examples/azure-sdk-example-database
    azure-cosmos
    azure-mgmt-cosmosdb
    # https://github.com/Azure-Samples/azure-cosmos-db-mongodb-python-getting-started
    pymongo # https://www.mongodb.com/docs/drivers/pymongo
)

# --- Custom Modules ---
python_user_modules=(
    file_backup
    app_backup_data
    game_backup_data
)

python_user_boilerplate_modules=(
    logging_boilerplate
    shell_boilerplate
    http_boilerplate
    azure_boilerplate
    azure_devops_boilerplate
    dotnet_boilerplate
    git_boilerplate
    # xml_boilerplate
    # multiprocess_boilerplate
    # daemon_boilerplate
    # socket_boilerplate
)

python_user_commands=(
    app
    # mygit
    pc_clean
    pc_restore
    provision_vscode
    provision_azure
)

# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------

# --- Validate file hashes ---
test_file_hashes() {
    local src="$1"
    local dest="$2"
    if [[ ! -f "$dest" ]]; then
        return 1
    fi
    local src_hash=$(sha256sum "$src" | awk '{print $1}')
    local dest_hash=$(sha256sum "$dest" | awk '{print $1}')
    [[ "$src_hash" == "$dest_hash" ]]
}

# --- Copy files ---
copy_source_files() {
    local src_dir="$1"
    local dest_dir="$2"
    shift 2
    local files=("$@")

    echo "Copying files: ${files[*]}"
    for file in "${files[@]}"; do
        local src_path="${src_dir%/}/${file}.py"
        local dest_path="${dest_dir%/}/${file}.py"

        if test_file_hashes "$src_path" "$dest_path"; then
            echo "No changes needed for: $dest_path"
        else
            echo "Copying: $src_path to $dest_path"
            cp "$src_path" "$dest_path"
            chmod +x "$dest_path"
        fi
    done
}

# --- Main script logic ---
# Update pip to the latest version
echo "Upgrading pip..."
python3 -m pip install --upgrade pip

# Install required pip packages
echo "Installing pip packages..."
for package in "${pip_packages[@]}"; do
    echo "Installing: $package"
    python3 -m pip install --upgrade "$package"
done

# Handle custom modules
custom_modules_dir="/path/to/custom/modules"
python_scripts_dir="/usr/local/bin"
copy_source_files "$custom_modules_dir" "$python_scripts_dir" "${python_user_modules[@]}"
copy_source_files "$custom_modules_dir" "$python_scripts_dir" "${python_user_boilerplate_modules[@]}"
copy_source_files "$custom_modules_dir" "$python_scripts_dir" "${python_user_commands[@]}"

echo "Successfully completed Python provisioning!"
