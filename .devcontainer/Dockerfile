# Use the Python image from devcontainers registry
# https://mcr.microsoft.com/artifact/mar/devcontainers/python/about
FROM mcr.microsoft.com/devcontainers/python:3.12

# Install PowerShell (modern Debian-compatible method)
RUN apt-get update \
    && apt-get install -y wget ca-certificates apt-transport-https gnupg shfmt \
    \
    # Determine the latest PowerShell release dynamically
    && LATEST_PWSH=$(wget -qO- https://api.github.com/repos/PowerShell/PowerShell/releases/latest | grep browser_download_url | grep linux-x64.tar.gz | cut -d '"' -f 4) \
    \
    # Create directory and download/extract PowerShell
    && mkdir -p /opt/microsoft/powershell/7 \
    && wget "$LATEST_PWSH" -O /tmp/powershell.tar.gz \
    && tar -xzf /tmp/powershell.tar.gz -C /opt/microsoft/powershell/7 \
    && ln -s /opt/microsoft/powershell/7/pwsh /usr/bin/pwsh \
    \
    # --- Cleanup ---
    && rm /tmp/powershell.tar.gz \
    # Clear the apt cache to reduce image size
    && apt-get clean \
    # Remove package list metadata after initial setup to save space
    && rm -rf /var/lib/apt/lists/*


# Default working directory
WORKDIR /workspaces/pc-env
