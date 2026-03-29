#!/bin/sh
set -e

# This runs each time the container starts to set up the shell environment

# --- Configuration ---
# Create a shell configuration file if it doesn't exist
if [ ! -f /root/.shrc ]; then
    echo '# Custom shell configuration' > /root/.shrc
    # Define convenient aliases for the conversion script
    echo 'alias audio-normal="python /app/convert-audio.py --profile normal"' >> /root/.shrc
    echo 'alias audio-book="python /app/convert-audio.py --profile audiobook"' >> /root/.shrc
    echo 'alias audio-comp="python /app/convert-audio.py --profile audiobook-compressed"' >> /root/.shrc
fi

# --- Main Actions ---
# Ensure the custom aliases are sourced for interactive shells
if ! grep -q ". /root/.shrc" /root/.profile; then
    echo '\n[ -f /root/.shrc ] && . /root/.shrc' >> /root/.profile
fi

# Execute the command passed to `docker run` or `docker compose run`
exec "$@"
