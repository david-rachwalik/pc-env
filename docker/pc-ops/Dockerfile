FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY docker/pc-ops/pip-requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/pip-requirements.txt

WORKDIR /app

# --- Application Setup (Snapshot) ---
# Copy the shared python modules
COPY python /app/python
# Copy the pc-ops scripts directly into working directory
COPY docker/pc-ops/scripts/ /app/

# Bake aliases system-wide so any runtime user can access them
COPY docker/pc-ops/aliases.sh /etc/profile.d/aliases.sh
ENV ENV="/etc/profile.d/aliases.sh"

CMD ["sh", "-l"]
