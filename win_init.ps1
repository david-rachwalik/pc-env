# -------- Run with PowerShell (as Administrator) --------

# --- Manually ensure PowerShell is updated first (MSI package) ---
# https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows
# PowerShell 7.2+ has the option to enable Microsoft Update to handle PowerShell updates

# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_variables
# Variable names in PowerShell are NOT case-sensitive and can include spaces and special characters
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_comparison_operators


# -------- STAGE 1: Configure PowerShell --------

# --- Allow execution of PowerShell scripts (.ps1) on machine ---
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies
# - RemoteSigned policy: allows running scripts created locally but downloaded scripts must be digitally signed by a trusted publisher
# - Unrestricted policy: carries no restrictions at all and allows unsigned scripts from any source (default for non-Windows)
$execution_policy = Get-ExecutionPolicy
$expected_policy = "RemoteSigned"
if ($execution_policy -ne $expected_policy)
{
    Write-Host "PowerShell execution policy is '$execution_policy', changing to '$expected_policy'..."
    # https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies
    # https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-executionpolicy
    Set-ExecutionPolicy -ExecutionPolicy $expected_policy -Force
    Write-Host "PowerShell execution policy successfully changed to '$expected_policy'!" -ForegroundColor Green
}
# can verify policy by scope using 'Get-ExecutionPolicy -List'


# -- Set SSH default to PowerShell (instead of Command, cmd.exe) ---
# https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_server_configuration
# New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force
# Generate public/private keys
# ssh-keygen -q -f %UserProfile%/.ssh/id_rsa -t rsa -b 4096 -N ""


# -------- STAGE 2: Provision Chocolatey --------

Write-Host "Calling 'provision_chocolatey.ps1' from remote..."
$provision_chocolatey_url = "https://raw.githubusercontent.com/david-rachwalik/pc-env/master/powershell/provision_chocolatey.ps1"
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/invoke-webrequest
$provision_chocolatey_script = Invoke-WebRequest $provision_chocolatey_url
Invoke-Expression $provision_chocolatey_script.Content
Write-Host "Completed 'provision_chocolatey.ps1' process"


# -------- STAGE 3: Provision Python --------

Write-Host "Calling 'provision_python.ps1' from remote..."
$provision_python_url = "https://raw.githubusercontent.com/david-rachwalik/pc-env/master/powershell/provision_python.ps1"
$provision_python_script = Invoke-WebRequest $provision_python_url
Invoke-Expression $provision_python_script.Content
Write-Host "Completed 'provision_python.ps1' process"

# --- Set Environmental Variable for custom Python commands ---
# https://stackoverflow.com/questions/9546324/adding-a-directory-to-the-path-environment-variable-in-windows
# https://learn.microsoft.com/en-us/powershell/scripting/developer/cmdlet/approved-verbs-for-windows-powershell-commands
function Add-EnvPath
{
    param(
        [Parameter(Mandatory)]
        [string]$Dir
    )
    
    if ( !(Test-Path $Dir) )
    {
        Write-Warning "Supplied directory was not found! ($($Dir))" -ForegroundColor Yellow
        return
    }
    $PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    if ( $PATH -notlike "*$($Dir)*" )
    {
        [Environment]::SetEnvironmentVariable("PATH", "$PATH;$Dir", "Machine")
    }
}

$user_py_dir = python -m site --user-base
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/join-path
$user_py_command_dir = Join-Path -Path $user_py_dir -ChildPath "bin"
# Write-Host "user_py_command_dir: $user_py_command_dir"
Add-EnvPath $user_py_command_dir

# https://webinstall.dev/pathman
# curl.exe https://webi.ms/pathman | powershell


# -------- STAGE 4: Running Python script --------

# --- Run Python script from PowerShell ---
# Start-Process -FilePath "C:\Program Files\Python\python.exe" -ArgumentList '"c:\scripts\simulate.py" "abcd"';
pc_setup --debug


# # -------- STAGE 5: Establishing Scheduled Tasks --------

# Write-Host "Calling 'scheduled_tasks.ps1' from remote..."
# $scheduled_tasks_url = "https://raw.githubusercontent.com/david-rachwalik/pc-env/master/powershell/scheduled_tasks.ps1"
# $scheduled_tasks_script = Invoke-WebRequest $scheduled_tasks_url
# Invoke-Expression $scheduled_tasks_script.Content
# Write-Host "Completed 'scheduled_tasks.ps1' process"


Write-Host "--- Windows provisioning has completed ---" -ForegroundColor Green
Exit



# -------------------------------------------------------------------------------------
# -------------------------------------------------------------------------------------

# -------- STAGE ?: Install WSL (Windows Subsystem Linux) --------

# https://docs.microsoft.com/en-us/windows/wsl/install-manual
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux

# --- NOT READY FOR WSL-2 YET... SOON (depends on Ansible) ---
# # Install WSL (*nix kernel) - restart system when prompted - update to WSL 2
# # https://docs.microsoft.com/en-us/windows/wsl/install-manual
# Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
# Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
# wsl --set-default-version 2

# Install RemoteRM (leftover commands from ./ansible_playbooks/roles/powershell/files/provision_pc.ps1)
$url = "https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1"
$file = "${env:temp}\ConfigureRemotingForAnsible.ps1"
(New-Object -TypeName System.Net.WebClient).DownloadFile($url, $file)
powershell.exe -ExecutionPolicy ByPass -File $file
# Verify existing WinRM listeners
# winrm enumerate winrm/config/Listener           # displays IP address and port for HTTP(S)
# Toggle WinRM authentications
# Set-Item -Path WSMan:\localhost\Service\Auth\Basic -Value true
# Set-Item -Path WSMan:\localhost\Service\Auth\Kerberos -Value false
# Verify changes
# winrm get winrm/config/Service
# winrm get winrm/config/Winrs


# Ensure correct network connection type for remoting (possibly not needed for Auth\Basic)
# Set-NetConnectionProfile -NetworkCategory Private
# winrm quickconfig -quiet
# Verify Windows IP Configuration
# winrs -r:DESKTOP-U8ATCTC ipconfig /all

# --- List all installed packages
# Get-AppxPackage -AllUsers
# Get-AppxPackage -Name "CanonicalGroupLimited.UbuntuonWindows" -AllUsers
# Get-AppxPackage -Name "CanonicalGroupLimited.Ubuntu18.04onWindows" -AllUsers
# --- Remove package by name
# Get-AppxPackage *CanonicalGroupLimited.UbuntuonWindows* | Remove-AppxPackage

# Download and install Ubuntu LTS - the preferred, stable release
# $wsl_distro = https://aka.ms/wsl-ubuntu-1804
$wsl_distro = "https://aka.ms/wslubuntu2004"
$wsl_package = "${env:temp}\wsl-ubuntu-2004.appx"
if (-not (Test-Path $wsl_package))
{
    Write-Host "Downloading Ubuntu package (${wsl_package})"
    Invoke-WebRequest -Uri "${wsl_distro}" -OutFile "${wsl_package}"
}
else
{
    Write-Host "Ubuntu package already in temp (${wsl_package})"
}
Add-AppxPackage "${wsl_package}"
# Note: If you reset/uninstall the app, be sure to fix the registry with CCleaner before installing again

# Launch Ubuntu (using WSL)


# -------- STAGE ?: Configure System --------

# --- Provision PowerShell Profile (required for OhMyPosh) ---

$psUserProfile = (Write-Output $PROFILE) # 'echo $PROFILE' command
# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.management/split-path
$psUserDir = Split-Path -Path $psUserProfile
$psUserProfileFilename = Split-Path -Path $psUserProfile -Leaf # 'Microsoft.PowerShell_profile.ps1'

$repoDir = $PSScriptRoot
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/join-path
$repoPsDir = Join-Path -Path $repoDir -ChildPath "powershell"
$repoUserProfile = Join-Path -Path $repoPsDir -ChildPath $psUserProfileFilename

# Verify integrity based on the file hashes
$psProfileSrc = Get-FileHash $repoUserProfile
$psProfileDest = Get-FileHash $psUserProfile
if ($psProfileSrc.Hash -ne $psProfileDest.Hash)
{
    Write-Host "Hash check failed, preparing to update '$psUserProfileFilename'.."
    # https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/robocopy
    # https://adamtheautomator.com/robocopy
    robocopy $repoPsDir $psUserDir $psUserProfileFilename /mt /z
    Write-Host "Successfully updated '$psUserProfileFilename'!"
}
else
{
    Write-Host "Hash passed: $psUserProfileFilename is up-to-date."
}
