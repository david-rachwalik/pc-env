# Use the Python image from devcontainers registry
# https://mcr.microsoft.com/artifact/mar/devcontainers/python/about
FROM mcr.microsoft.com/devcontainers/python:3.12

# Install PowerShell
# Download Microsoft's GPG key and add it to trusted keys (verifies packages being installed)
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    # # Add Microsoft's package repository
    # && echo "deb [arch=amd64] https://packages.microsoft.com/debian/10/prod buster main" > /etc/apt/sources.list.d/microsoft.list \
    && echo "deb [arch=amd64] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/microsoft.list \
    && apt-get update && apt-get install -y powershell \
    # --- Cleanup ---
    # Clear the apt cache to reduce image size
    && apt-get clean \
    # Remove package list metadata after initial setup to save space
    && rm -rf /var/lib/apt/lists/*

# Set up a default working directory
WORKDIR /workspaces/pc-env
