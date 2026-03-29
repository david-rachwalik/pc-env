# Use the latest Python slim image
FROM python:3.12-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the conversion script and entrypoint
COPY convert-audio.py /app/convert-audio.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /app/convert-audio.py /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
