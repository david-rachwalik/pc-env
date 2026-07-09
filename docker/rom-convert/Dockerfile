# ================================================================
# BUILDER STAGE
# Compile extract-xiso from source
# ================================================================
FROM debian:13-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Clone and build extract-xiso (Standard for stripping padding from Xbox 360 ISOs)
# https://github.com/XboxDev/extract-xiso
RUN git clone --depth 1 https://github.com/XboxDev/extract-xiso.git /tmp/extract-xiso \
    && mkdir -p /tmp/extract-xiso/build \
    && cd /tmp/extract-xiso/build \
    && cmake .. \
    && make

# ================================================================
# FINAL STAGE
# Lean Python Runtime + CLI Tools
# ================================================================
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    mame-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled extract-xiso binary from the builder
COPY --from=builder /tmp/extract-xiso/build/extract-xiso /usr/local/bin/extract-xiso

WORKDIR /app

# Verify installations
RUN extract-xiso -v || true
RUN chdman -version || true

COPY convert-roms.py /app/convert-roms.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /app/convert-roms.py /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
