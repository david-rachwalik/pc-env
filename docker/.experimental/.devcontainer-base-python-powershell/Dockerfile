# Use the minimal Debian-based image from the devcontainers registry
# https://mcr.microsoft.com/artifact/mar/devcontainers/python/about
FROM mcr.microsoft.com/devcontainers/base:debian

# Copy requirements files to the image
COPY apt-requirements.txt /tmp/
# COPY pip-requirements.txt .

# Install Python, Node.js, npm, and PowerShell
RUN apt-get update \
    # --- APT Steps ---
    && xargs -a /tmp/apt-requirements.txt apt-get install -y \
    # # --- Python Steps ---
    # # Create virtual environment and install necessary packages inside
    # && python3 -m venv /workspaces/pc-env/.venv \
    # && /workspaces/pc-env/.venv/bin/pip install -r pip-requirements.txt \
    # --- PowerShell Steps ---
    # Download Microsoft's GPG key and add it to trusted keys for verifying packages being installed
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    # Add Microsoft's package repository (for Debian), allowing apt-get to download PowerShell from Microsoft's servers
    && echo "deb [arch=amd64] https://packages.microsoft.com/debian/10/prod buster main" > /etc/apt/sources.list.d/microsoft.list \
    && apt-get update && apt-get install -y powershell \
    # --- Cleanup ---
    # Clear the apt cache to reduce image size
    && apt-get clean \
    # Remove package list metadata after initial setup to save space
    && rm -rf /var/lib/apt/lists/*

# Set up a default working directory
WORKDIR /workspaces/pc-env

# # Set the default Python interpreter to the virtual environment's Python
# ENV VIRTUAL_ENV=/workspaces/pc-env/.venv
# ENV PATH="$VIRTUAL_ENV/bin:$PATH"
