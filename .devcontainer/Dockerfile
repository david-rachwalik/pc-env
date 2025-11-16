# Use the Python image from devcontainers registry
# https://mcr.microsoft.com/artifact/mar/devcontainers/python/about
FROM mcr.microsoft.com/devcontainers/python:3.12

# # Install PowerShell (modern Debian-compatible method)
# RUN apt-get update \
#     && apt-get install -y curl gnupg \
#     && curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
#         -o /usr/share/keyrings/microsoft.gpg \
#     # Add Microsoft's package repository & install PowerShell
#     && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" \
#         > /etc/apt/sources.list.d/microsoft.list \
#     && apt-get update \
#     && apt-get install -y powershell \
#     # Clear the apt cache to reduce image size
#     && apt-get clean \
#     # Remove package list metadata after initial setup to save space
#     && rm -rf /var/lib/apt/lists/*


# Install latest PowerShell on Debian 13
RUN apt-get update \
    && apt-get install -y wget ca-certificates apt-transport-https gnupg \
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
