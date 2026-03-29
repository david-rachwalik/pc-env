#!/bin/sh
set -e

# This runs each time the container starts to set up the shell environment

# --- Configuration ---
# Create a shell configuration file if it doesn't exist
if [ ! -f /root/.shrc ]; then
    echo '# Custom shell configuration' > /root/.shrc
    # Define convenient aliases for the conversion script
    echo 'alias music="python /app/convert-audio.py --profile music"' >> /root/.shrc
    echo 'alias music-clean="python /app/convert-audio.py --profile music-clean"' >> /root/.shrc
    echo 'alias vocal="python /app/convert-audio.py --profile vocal"' >> /root/.shrc
    echo 'alias vocal-clean="python /app/convert-audio.py --profile vocal-clean"' >> /root/.shrc
fi

# --- Main Actions ---
# Ensure the custom aliases are sourced for interactive shells
if ! grep -q ". /root/.shrc" /root/.profile; then
    echo '\n[ -f /root/.shrc ] && . /root/.shrc' >> /root/.profile
fi

# Execute the command passed to `docker run` or `docker compose run`
exec "$@"
