# PC Environment Setup

These are the steps I would take to provision a new machine (PC or laptop) for Windows 10/11.

<sup>For a new system, it is recommended to manually install [PowerShell Core](https://github.com/PowerShell/PowerShell/releases/latest) (\*-win-x64.msi) first. Chocolatey can keep it up-to-date from there.</sup>

## Initialization

Run Windows PowerShell (as _Administrator_).

1. Set security to TLS 1.2 (more secure than SystemDefault [TLS 1.0] & required by many sites)

   ```powershell
   [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
   ```

2. Run script to provision Chocolatey and Python

   ```powershell
   iwr https://raw.githubusercontent.com/david-rachwalik/pc-env/master/win_init.ps1 -UseBasicParsing | iex
   ```

---

## Initialization Alternative: Windows Only (No Python, No WSL+Ansible)

> _Most actions are only run the first time except `choco upgrade all`_

1. Run PowerShell (as Administrator) to [install Chocolatey](https://chocolatey.org/install)

   <sub><sup>Install Chocolatey</sup></sub>

   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; iwr https://chocolatey.org/install.ps1 -UseBasicParsing | iex
   ```

   <sub><sup>Set Chocolatey to skip confirmation prompts</sup></sub>

   ```powershell
   choco feature enable -n=allowGlobalConfirmation
   ```

2. Search for [Chocolatey packages](https://chocolatey.org/packages) (apps/programs) - _[examples](https://raw.githubusercontent.com/david-rachwalik/pc-env/master/ansible_playbooks/group_vars/windows/choco.yml)_

3. Install what you like using: `choco install <package>`

4. Upgrade all packages at once using: `choco upgrade all`

---

## Initialization (Old): Installed WSL+Ubuntu with Ansible

1. Run Windows PowerShell (as _Administrator_) to install Linux on Windows

   <sub><sup>Set security to TLS 1.2 (required by many sites; more secure than default TLS 1.0)</sup></sub>

   ```powershell
   [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
   ```

   <sub><sup>Install WSL (\*nix kernel) - restart system when prompted</sup></sub>

   ```powershell
   Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
   ```

   <sub><sup>Run script to install Chocolatey, Ubuntu, and RemoteRM</sup></sub>

   ```powershell
   iwr https://raw.githubusercontent.com/david-rachwalik/pc-env/master/win_init.ps1 -UseBasicParsing | iex
   ```

2. Run script to install Ansible on Linux and call provisioning playbooks

   <sub><sup>Script installs might fail behind VPN</sup></sub>

   ```bash
   curl -s https://raw.githubusercontent.com/david-rachwalik/pc-env/master/wsl_init.sh | sudo -H bash
   ```

## Development & PC Health (Old)

Review aliases/functions to common actions

```bash
view ~/.bash_aliases
```

Open File Explorer in current location (_only "." path is valid_)

```bash
explorer.exe .
```

Open VS Code in current location with [Core CLI](https://code.visualstudio.com/docs/editor/command-line#_core-cli-options)

```bash
code .
```

Review latest logs (_rotated daily_)

```bash
view ~/log/ansible_scheduled_task.log
```
