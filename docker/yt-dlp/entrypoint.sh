#!/bin/sh

# Update required packages
pip install pip -U
pip install yt-dlp -U

# Define aliases for audio and video downloads
echo 'alias ytv="yt-dlp"' >>/root/.shrc
echo 'alias yta="yt-dlp -x"' >>/root/.shrc

# Ensure aliases are sourced for interactive shells
echo '[ -f /root/.shrc ] && . /root/.shrc' >/root/.profile

exec /bin/sh -l # Keeps the container running interactively
