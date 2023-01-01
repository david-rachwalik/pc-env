# -------- Run with PowerShell (as Administrator) --------
# based on /ansible_playbooks/inventories/main/group_vars/windows/python.yml

$pip_packages = @(
    # 'pip'
    'pytest'
    'autopep8'
    'pytz'
    'colorlog'
    'pylint-quotes'
    'pyinstaller'  # https://pyinstaller.org/en/stable
    'yt-dlp'
    'dirsync'  # https://github.com/tkhyn/dirsync
    # https://learn.microsoft.com/en-us/azure/developer/python/configure-local-development-environment
    # https://learn.microsoft.com/en-us/azure/developer/python/sdk/azure-sdk-overview#connect-to-and-use-azure-resources-with-client-libraries
    'azure-identity'
    'azure-mgmt-resource'
    # https://learn.microsoft.com/en-us/python/api/overview/azure/cosmos-db
    # https://learn.microsoft.com/en-us/azure/developer/python/sdk/examples/azure-sdk-example-database
    'azure-cosmos'
    'azure-mgmt-cosmosdb'
    # https://github.com/Azure-Samples/azure-cosmos-db-mongodb-python-getting-started
    # https://www.mongodb.com/docs/drivers/pymongo
    'pymongo'
    # https://pypi.org/project/python-dotenv
    'python-dotenv'
)
# https://learn.microsoft.com/en-us/azure/cosmos-db/mongodb/quickstart-nodejs

$python_user_modules = @(
    # --- Misc. ---
    'file_backup'
    # 'mytest'
    'app_backup_data'
    'game_backup_data'
)

$python_user_boilerplate_modules = @(
    'logging_boilerplate'
    'shell_boilerplate'
    'azure_boilerplate'
    'azure_devops_boilerplate'
    'dotnet_boilerplate'
    'git_boilerplate'
    # 'xml_boilerplate'
    # 'multiprocess_boilerplate'
    # 'daemon_boilerplate'
    # 'socket_boilerplate'
)

$python_user_commands = @(
    # 'app'
    # 'mygit'
    # 'provision_vscode'
    'pc_clean'
)


# ------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------


# -------- Provision PIP (Python package-management system) --------

# --- Upgrade PIP installation ---
Write-Host "Checking for PIP (package manager) upgrades.."
python -m pip install --upgrade pip


# --- Fetch list of installed and out-of-date pip packages ---
# https://stackoverflow.com/questions/62964466/upgrade-outdated-python-packages-by-pip-in-powershell-in-one-line
$pip_packages_installed = (pip list --format=json | ConvertFrom-Json).name
Write-Host "pip_packages_installed: $pip_packages_installed"
$pip_packages_to_install = $pip_packages | Where-Object { $pip_packages_installed -notcontains $_ }
Write-Host "pip_packages_to_install: $pip_packages_to_install"
$pip_packages_outdated = ((pip list --outdated --format=json | ConvertFrom-Json).name | Out-String).replace("`r`n", " ")
Write-Host "pip_packages_outdated: $pip_packages_outdated"


# --- Install missing PIP packages ---

# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_foreach
foreach ($package in $pip_packages_to_install)
{
    Write-Host "Attempting to install PIP package '$package'.."
    pip install $package
}


# --- Upgrade all PIP packages ---
if ($pip_packages_outdated)
{
    Write-Host "Attempting to upgrade PIP package '$package'.."
    pip install --upgrade $pip_packages_outdated
}

Write-Host "--- Completed provisioning of PIP (package manager) ---"


# -------- Provision Python user modules --------

# Write-Host "python_user_modules:"
# Write-Host ($python_user_modules | Out-String).Trim()
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/out-string

# Write-Host "python_user_boilerplate_modules:"
# Write-Host ($python_user_boilerplate_modules | Out-String).Trim()

# Write-Host "python_user_commands:"
# Write-Host ($python_user_commands | Out-String).Trim()


# --- Determine Python (source) module locations ---

$script_root = $PSScriptRoot
[bool]$script_is_remote = 0
if ($script_root -ne "")
{
    # Use local repository when called directly
    $repo_dir = Split-Path $script_root -Parent
    $repo_py_dir = Join-Path -Path $repo_dir -ChildPath "python"
    $repo_py_module_dir = Join-Path -Path $repo_py_dir -ChildPath "modules"
    $repo_py_boilerplate_dir = Join-Path -Path $repo_py_module_dir -ChildPath "boilerplates"
    $repo_py_command_dir = Join-Path -Path $repo_py_dir -ChildPath "commands"
}
else
{
    # Use remote repository when called indirectly (another script)
    $script_is_remote = 1
    $repo_url = "https://raw.githubusercontent.com/david-rachwalik/pc-setup/master/"
    $repo_py_dir = $repo_url + "python"
    $repo_py_module_dir = $repo_py_dir + "modules"
    $repo_py_boilerplate_dir = $repo_py_module_dir + "boilerplates"
    $repo_py_command_dir = $repo_py_dir + "commands"
}
Write-Host "source directory: $repo_py_dir"


# --- Determine Python (destination) site locations ---

$user_py_dir = python -m site --user-base
# Write-Host "user_py_dir: $user_py_dir"

$user_py_module_dir = python -m site --user-site
# Write-Host "user_py_module_dir: $user_py_module_dir"
# $user_py_boilerplate_dir = Join-Path -Path $user_py_module_dir -ChildPath "boilerplates"

# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/join-path
$user_py_command_dir = Join-Path -Path $user_py_dir -ChildPath "bin"
# Write-Host "user_py_command_dir: $user_py_command_dir"

Write-Host "destination directory: $user_py_dir"


# --- Ensure Python (destination) site directories exist ---
# NO LONGER NECESSARY THANKS TO 'ROBOCOPY'
# https://stackoverflow.com/questions/16906170/create-directory-if-it-does-not-exist
# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/test-path
# if (!(Test-Path -PathType Container -Path $user_py_module_dir))
# {
#     Write-Host "Python user-site directory not found, preparing to create.."
#     # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item
#     New-Item -ItemType Directory -Path $user_py_module_dir
#     Write-Host "Python user-site directory was successfully created!"
# }
# # else
# # {
# #     Write-Host "Found the Python user-site directory"
# # }

# if (!(Test-Path -PathType Container -Path $user_py_boilerplate_dir))
# {
#     Write-Host "Python user-site boilerplate directory not found, preparing to create.."
#     # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item
#     New-Item -ItemType Directory -Path $user_py_boilerplate_dir
#     Write-Host "Python user-site boilerplate directory was successfully created!"
# }

# if (!(Test-Path -PathType Container -Path $user_py_command_dir))
# {
#     Write-Host "Python command directory not found, preparing to create.."
#     # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/new-item
#     New-Item -ItemType Directory -Path $user_py_command_dir
#     Write-Host "Python command directory was successfully created!"
# }


# --- Method to validate files exist and are identical versions ---

# https://learn.microsoft.com/en-us/powershell/scripting/learn/ps101/09-functions
# https://learn.microsoft.com/en-us/powershell/scripting/developer/cmdlet/approved-verbs-for-windows-powershell-commands

# Returns true if both files are found and the hashes match
function Test-FileHashes
{
    param (
        [Parameter(Mandatory)]
        [string]$SourcePath,
        [Parameter(Mandatory)]
        [string]$DestinationPath,
        [bool]$IsRemote = 0
    )

    [bool]$result = 0

    if (!(Test-Path -Path $DestinationPath -PathType Leaf))
    {
        return $result
    }

    if ($IsRemote)
    {
        # https://stackoverflow.com/questions/71975539/how-do-i-check-the-filehash-of-a-file-thats-online-in-powershell
        try
        {
            $content = Invoke-RestMethod $SourcePath
            $memstream = [System.IO.MemoryStream]::new($content.ToCharArray())
            $src = Get-FileHash -InputStream $memstream
            $dest = Get-FileHash $DestinationPath
            # Compare the hashes
            if ($src.Hash -eq $dest.Hash)
            {
                $result = 1
            }
        }
        finally
        {
            $memstream.foreach('Dispose')
        }
    }
    else
    {
        # Ensure that local files exist before attempting to hash
        # https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/test-path
        if ((Test-Path -Path $SourcePath -PathType Leaf))
        {
            $src = Get-FileHash $SourcePath
            $dest = Get-FileHash $DestinationPath
            # Compare the hashes
            if ($src.Hash -eq $dest.Hash)
            {
                $result = 1
            }
        }
    }

    # https://stackoverflow.com/questions/10286164/function-return-value-in-powershell
    return $result
}

# Copies file from local or remote repository
function Copy-SourceFile
{
    param (
        [Parameter(Mandatory)]
        [string]$SourcePath,
        [Parameter(Mandatory)]
        [string]$DestinationPath,
        [Parameter(Mandatory)]
        [string]$FileName,
        [bool]$IsRemote = 0
    )

    if ($IsRemote)
    {
        # https://stackoverflow.com/questions/71975539/how-do-i-check-the-filehash-of-a-file-thats-online-in-powershell
        try
        {
            # Copy file from remote repository into Temp directory, then robocopy from there
            Invoke-WebRequest "$($SourcePath)/$($FileName)" -OutFile "$($Env:Temp)\$($FileName)"
            robocopy $Env:Temp $DestinationPath $FileName /mt /z /mov  # /mov (cut instead of copy)
        }
        catch [System.Net.WebException], [System.IO.IOException]
        {
            Write-Host "Unable to download '$($SourcePath)/$($FileName)'." -ForegroundColor Red
        }
    }
    else
    {
        # Copy file from local repository
        # https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy
        # https://adamtheautomator.com/robocopy
        robocopy $SourcePath $DestinationPath $FileName /mt /z
    }
}


# --- Deploy Python user modules & commands ---

[System.Collections.ArrayList]$PythonFilesPassed = @()
[System.Collections.ArrayList]$PythonFilesUpdated = @()

# Provision the latest Python modules
foreach ($module in $python_user_modules)
{
    $filename = "$($module).py"
    $src_path = Join-Path -Path $repo_py_module_dir -ChildPath $filename
    $dest_path = Join-Path -Path $user_py_module_dir -ChildPath $filename
    $match = Test-FileHashes $src_path $dest_path $script_is_remote
    if ($match)
    {
        $PythonFilesPassed.Add($filename) | Out-Null
    }
    else
    {
        $PythonFilesUpdated.Add($filename) | Out-Null
        # robocopy $repo_py_module_dir $user_py_module_dir $filename /mt /z
        Copy-SourceFile $repo_py_module_dir $user_py_module_dir $filename $script_is_remote
    }
}

# Provision the latest Python modules (boilerplate)
foreach ($module in $python_user_boilerplate_modules)
{
    $filename = "$($module).py"
    $src_path = Join-Path -Path $repo_py_boilerplate_dir -ChildPath $filename
    $dest_path = Join-Path -Path $user_py_module_dir -ChildPath $filename
    $match = Test-FileHashes $src_path $dest_path $script_is_remote
    if ($match)
    {
        $PythonFilesPassed.Add($filename) | Out-Null
    }
    else
    {
        $PythonFilesUpdated.Add($filename) | Out-Null
        # robocopy $repo_py_boilerplate_dir $user_py_module_dir $filename /mt /z
        Copy-SourceFile $repo_py_boilerplate_dir $user_py_module_dir $filename $script_is_remote
    }
}

# Provision the latest Python commands
foreach ($module in $python_user_commands)
{
    $filename = "$($module).py"
    $src_path = Join-Path -Path $repo_py_command_dir -ChildPath $filename
    $dest_path = Join-Path -Path $user_py_command_dir -ChildPath $filename
    $match = Test-FileHashes $src_path $dest_path $script_is_remote
    if ($match)
    {
        $PythonFilesPassed.Add($filename) | Out-Null
    }
    else
    {
        $PythonFilesUpdated.Add($filename) | Out-Null
        # robocopy $repo_py_command_dir $user_py_command_dir $filename /mt /z
        Copy-SourceFile $repo_py_command_dir $user_py_command_dir $filename $script_is_remote
        
        # --- Make the command executable from CLI ---
        $dest_bat_content = "py %AppData%\Python\bin\$($filename) %*"
        $dest_bat = "C:\Python311\Scripts\$($module).bat"
        Set-Content -Path $dest_bat -Value $dest_bat_content -Encoding Ascii

        # --- Make a distributeable application (for external users) ---
        # https://pyinstaller.org/en/stable/usage.html
        # https://realpython.com/pyinstaller-python
        # $dest_build_path = Join-Path -Path $user_py_command_dir -ChildPath 'build'
        # $dest_dist_path = Join-Path -Path $user_py_command_dir -ChildPath 'dist'
        # pyinstaller --onefile --specpath=$dest_build_path --workpath=$dest_build_path --distpath='C:\Python311\Scripts' $dest_path
    }
}

# Write-Host "Python files that passed the hash check: $PythonFilesPassed"
Write-Host "Python files updated: $PythonFilesUpdated"

Write-Host "--- Completed provisioning of Python ---" -ForegroundColor Green
