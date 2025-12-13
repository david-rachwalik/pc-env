# Use the latest Python image
FROM python:3.12-alpine

# Set the working directory in the container
WORKDIR /app

# Install system dependencies, including ffmpeg and Node.js (for YouTube throttling bypass)
RUN apk add --no-cache ffmpeg nodejs

# Copy configuration settings to the container
COPY config /root/.config/yt-dlp/config

# Use ENTRYPOINT to update container on every run
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Update PATH to include /root/.local/bin
# ENV PATH="/root/.local/bin:${PATH}"

# Set the default command to run your Python script with arguments
# CMD ["python", "/root/.local/bin/pc_restore", "--debug"]
# CMD ["yt-dlp", "--version"]


# --- Usage Example (run from project root, build image, and run container) ---
# cd ~/Repos/pc-env/docker/yt-dlp
# docker build -t yt-dlp-runner -f Dockerfile .
# docker run --rm -it -v /media/root/HDD-01:/mnt/d -v ~/.mozilla/firefox:/root/.mozilla/firefox yt-dlp-runner /bin/sh

# docker compose run yt-dlp


# --- Old ---
# cd ~/Repos/pc-env
# docker build -t yt-dlp-runner -f docker/yt-dlp/Dockerfile .
# docker run --rm -it -v ${PWD}:/app -v /media/root/HDD-01:/mnt/d -v ~/.mozilla/firefox:/root/.mozilla/firefox yt-dlp-runner /bin/sh

# --- Test Run (specify command) ---
# docker run --rm --name yt-dlp-runner-container yt-dlp-runner <command>
# --- Test Run (interactive run) ---
# docker run --rm -it --name yt-dlp-runner-container yt-dlp-runner /bin/sh
# --- Test Run (with mounted volumes) ---
# docker run --rm -v ${PWD}:/app -v C:/:/mnt/c -v D:/:/mnt/d yt-dlp-runner
