cd ~/Repos/pc-env/docker/yt-dlp
docker compose build --no-cache
docker compose run --remove-orphans yt-dlp

# bash ~/Repos/pc-env/docker/yt-dlp/run.sh

# (run inside container to upgrade)
# pip install yt-dlp -U
