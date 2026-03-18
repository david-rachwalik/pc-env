# ==============================================================================
# BUILDER STAGE
# Compile the Subtitle Edit CLI from source
# (contents of this stage are DISCARDED after the build)
# ==============================================================================
# Use the official .NET SDK image to build C# projects
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS dotnet-builder

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Build subtitleedit-cli
ARG SE_CLI_REPO=https://github.com/SubtitleEdit/subtitleedit-cli.git
ARG SE_CLI_VERSION=main
RUN git clone --depth 1 --branch ${SE_CLI_VERSION} ${SE_CLI_REPO} /tmp/se-cli
WORKDIR /tmp/se-cli
# Publish as a self-contained application so it doesn't need the .NET runtime in the final image
RUN dotnet publish src/se-cli/seconv.csproj -c Release -o /opt/subtitleedit-cli --self-contained true -r linux-x64

# NOTE: other approaches tried were: sup2srt, vobsub2srt
# These tools are unmaintained and should no longer be considered


# ==============================================================================
# FINAL STAGE
# Create the lean, final runtime image with Python and our compiled tools
# ==============================================================================
# Start from our original Python image
FROM python:3.12-slim

# --- Build-time Arguments & Environment Variables ---
ENV DEBIAN_FRONTEND=noninteractive

# --- Base System & Python Dependencies ---
# Install all RUNTIME dependencies, including OCR tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    mkvtoolnix \
    jq \
    locales \
    wget \
    # Runtime libs for Subtitle Edit's OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract5 \
    libleptonica6 \
    && rm -rf /var/lib/apt/lists/*

# Install runtime Python dependencies globally
RUN python3 -m pip install --no-cache-dir --upgrade pip
RUN python3 -m pip install --no-cache-dir pysubs2

# --- Install OCR & Conversion Tools ---
# Copy pre-built binaries from the builder stage
COPY --from=dotnet-builder /opt/subtitleedit-cli /opt/subtitleedit-cli

# Create the symlink for subtitleedit
RUN ln -s /opt/subtitleedit-cli/seconv /usr/local/bin/subtitleedit

# Verify tool installation (date busts cache to always run)
RUN echo "--- Verifying tool versions ($(date)) ---" && \
    subtitleedit --version

# --- Application Setup ---
# Set the working directory in the container
WORKDIR /app

# Copy scripts into the image
COPY convert-subtitles.py /app/convert-subtitles.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /app/convert-subtitles.py /entrypoint.sh

# Use ENTRYPOINT to update container on every run
ENTRYPOINT ["/entrypoint.sh"]
