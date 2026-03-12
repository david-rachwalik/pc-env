FROM debian:bookworm-slim

# Install necessary dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        fuse3 \
        curl \
        unzip && \
    rm -rf /var/lib/apt/lists/*

# Install the latest stable version of rclone
RUN curl -O https://downloads.rclone.org/rclone-current-linux-amd64.zip && \
    unzip rclone-current-linux-amd64.zip && \
    mv rclone-*-linux-amd64/rclone /usr/local/bin/ && \
    chown root:root /usr/local/bin/rclone && \
    chmod 755 /usr/local/bin/rclone && \
    rm -rf rclone-*

# --- Configuration ---
# Copy your custom bisync script into the image
COPY rclone-bisync.sh /usr/local/bin/rclone-bisync.sh
RUN chmod +x /usr/local/bin/rclone-bisync.sh

# Set a default entrypoint (can be overridden)
ENTRYPOINT ["/usr/local/bin/rclone-bisync.sh"]
