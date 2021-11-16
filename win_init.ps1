# Run with PowerShell as Administrator

# https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_server_configuration
# Set PowerShell as default (instead of Command) for SSH
# New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force
# Generate public/private keys
# ssh-keygen -q -f %userprofile%/.ssh/id_rsa -t rsa -b 4096 -N ""

# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; iwr https://chocolatey.org/install.ps1 -UseBasicParsing | iex
# Configure Chocolatey:- remember params used for upgrades (to verify: choco feature list)
# https://docs.chocolatey.org/en-us/guides/create/parse-packageparameters-argument
choco feature enable -n=useRememberedArgumentsForUpgrades

# https://docs.microsoft.com/en-us/windows/wsl/install-manual
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux

# --- NOT READY FOR WSL-2 YET... SOON (depends on Ansible) ---
# # Install WSL (*nix kernel) - restart system when prompted - update to WSL 2
# # https://docs.microsoft.com/en-us/windows/wsl/install-manual
# Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
# Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
# wsl --set-default-version 2

# Install RemoteRM (leftover commands in D:\Repos\pc-setup\ansible_playbooks\roles\powershell\files\provision_pc.ps1)
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

# To permanently allow .ps1 scripts on machine
# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies
# https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.security/set-executionpolicy
Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Force

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
    Write-Output "Downloading Ubuntu package (${wsl_package})"
    Invoke-WebRequest -Uri "${wsl_distro}" -OutFile "${wsl_package}" -UseBasicParsing
} else {
    Write-Output "Ubuntu package already in temp (${wsl_package})"
}
Add-AppxPackage "${wsl_package}"
# Note: If you reset/uninstall the app, be sure to fix the registry with CCleaner before installing again

# Launch Ubuntu (using WSL)
