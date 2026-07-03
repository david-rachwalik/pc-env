# Use the latest Python slim image (Debian-based)
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# - ffmpeg: standard media tooling
# - curl & unzip: required to install Deno
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
        unzip \
    # Install Deno (for secure JavaScript-based YouTube throttling bypass)
    && curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr sh \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration settings to the container
COPY config /root/.config/yt-dlp/config

# Use ENTRYPOINT to update container on every run
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Set the default command to run your Python script with arguments
# CMD ["python", "/root/.local/bin/pc_restore", "--debug"]
# CMD ["yt-dlp", "--version"]
