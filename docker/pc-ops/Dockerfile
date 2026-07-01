FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pip-requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/pip-requirements.txt

WORKDIR /app

# --- Application Setup (Snapshot) ---
# Copy the shared python modules
COPY python /app/python
# Copy the pc-ops scripts
COPY docker/pc-ops /app/docker/pc-ops

# Setup entrypoint
COPY docker/pc-ops/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Use ENTRYPOINT for shell setup, CMD for default behavior
ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-l"]
