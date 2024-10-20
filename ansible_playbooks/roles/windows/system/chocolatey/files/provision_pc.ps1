# Run command example:
# F:\Repos\pc-env\PowerShell\provision_pc.ps1

# -------- Install WinRM for Ansible connection --------
# https://docs.ansible.com/ansible/latest/user_guide/windows_setup.html#winrm-setup
$url = "https://raw.githubusercontent.com/ansible/ansible/devel/examples/scripts/ConfigureRemotingForAnsible.ps1"
$file = "$env:temp\ConfigureRemotingForAnsible.ps1"
(New-Object -TypeName System.Net.WebClient).DownloadFile($url, $file)
powershell.exe -ExecutionPolicy ByPass -File $file
