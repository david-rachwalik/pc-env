#!/bin/sh

# Update required packages
pip install pip -U
pip install yt-dlp -U

exec /bin/sh # Keeps the container running interactively
