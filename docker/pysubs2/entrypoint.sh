#!/bin/sh
set -e

# This runs each time the container starts to set up the shell environment

# --- Configuration ---
# Create a shell configuration file if it doesn't exist
if [ ! -f /root/.shrc ]; then
    echo '# Custom shell configuration' > /root/.shrc
    # Define a convenient alias for the conversion script
    echo 'alias srt="python /app/convert-subtitles.py"' >> /root/.shrc
fi

# --- Main Actions ---
# Ensure the custom aliases are sourced for interactive shells
# This check prevents adding the line multiple times
if ! grep -q ". /root/.shrc" /root/.profile; then
    echo '\n[ -f /root/.shrc ] && . /root/.shrc' >> /root/.profile
fi

# Execute the command passed to `docker run` or `docker compose run`
# If no command is passed, it defaults to `sh -l` (interactive shell)
exec "$@"
