#!/bin/sh

# Update required packages
pip install pip -U
pip install yt-dlp -U
pip install yt-dlp-ejs -U

# Define aliases for audio and video downloads
echo 'alias ytv="yt-dlp"' >>/root/.shrc
echo 'alias ytvr="yt-dlp -f \"bv*+ba/b\""' >>/root/.shrc # Best video (no resolution limit)
# Placed audio formats first so `--extract-audio|-x` only attempts to download audio when possible
echo 'alias yta="yt-dlp -x -f \"ba[abr<=128k]/ba/b[abr<=128k]/b\""' >>/root/.shrc

# Ensure aliases are sourced for interactive shells
echo '[ -f /root/.shrc ] && . /root/.shrc' >/root/.profile

exec /bin/sh -l # Keeps the container running interactively
