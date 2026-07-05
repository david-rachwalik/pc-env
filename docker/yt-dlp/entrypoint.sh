#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# Update required packages
pip install -U --root-user-action=ignore pip
pip install -U --root-user-action=ignore yt-dlp
pip install -U --root-user-action=ignore yt-dlp-ejs

# Define aliases for audio and video downloads
{
    echo 'alias ytv="yt-dlp"'
    echo 'alias ytvr="yt-dlp -f \"bv*+ba/b\""' # Best video (no resolution limit)
    # Placed audio formats first so `--extract-audio|-x` only attempts to download audio when possible
    echo 'alias yta="yt-dlp -x -f \"ba[abr<=128k]/ba/b[abr<=128k]/b\""'
} >> /root/.bashrc

exec /bin/bash -l # Keeps the container running interactively
