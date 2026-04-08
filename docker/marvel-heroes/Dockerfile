# Use the .NET SDK image as it contains both the runtime and build tools
FROM mcr.microsoft.com/dotnet/sdk:8.0

# Install git and sqlite3 as root
RUN apt-get update && apt-get install -y --no-install-recommends git sqlite3 gosu && \
    rm -rf /var/lib/apt/lists/*

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set up a non-root user for security
ENV PUID=1000
ENV PGID=1000
RUN groupadd -g ${PGID} -o serveruser && \
    useradd --shell /bin/bash -u ${PUID} -g ${PGID} -o -c "" -m serveruser

# Create mount points.  Ownership will be handled by the entrypoint.
RUN mkdir -p /app /data

WORKDIR /app
VOLUME ["/app", "/data"]

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
