#!/bin/bash

# alias rclone='cd ~/Repos/pc-env/docker/rclone && docker compose run --remove-orphans --rm rclone'
rclone() {
    cd ~/Repos/pc-env/docker/rclone
    # docker compose run --remove-orphans --rm rclone "$@"
    # Pass $USER ID to the container
    local _UID=$(id -u)
    local _GID=$(id -g)
    docker compose run \
        --rm \
        --remove-orphans \
        -e UID=$_UID -e GID=$_GID -e PUID=$_UID -e PGID=$_GID \
        --user $_UID:$_GID \
        rclone "$@"
}
