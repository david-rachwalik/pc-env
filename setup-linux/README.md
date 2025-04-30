# Provisioning Linux (Ubuntu)

## Recommended Locations

A good practice is to keep logs and temporary files in directories designated for those purposes.&nbsp; Here are some common locations for Linux systems:

1. **Logs** (`$HOME/.local/share/logs` or `/var/log`)

   For personal scripts, storing logs under a folder in your home directory (e.g., `$HOME/.local/share/logs`) is appropriate.&nbsp; If the script is system-wide or managed by a service, use `/var/log` (requires sudo permissions).

2. **Temporary Files** (`$HOME/.cache` or `/tmp`)

   System-wide temporary files typically go to `/tmp`.&nbsp; These files are cleared on reboot.&nbsp; Personal temp files can go under `$HOME/.cache`.

## [Connecting to GitHub with SSH](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)

Connect and authenticate to remote servers and services using the Secure Shell Protocol (SSH) protocol.&nbsp; SSH keys enable connecting to GitHub without supplying a username and personal access token at each visit.
