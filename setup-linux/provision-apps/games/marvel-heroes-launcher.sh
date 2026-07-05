#!/usr/bin/env bash
set -euo pipefail  # Exit immediately on error

# --- Configuration ---
# Path to the docker-compose file for the server
SERVER_COMPOSE_FILE="$HOME/Repos/pc-env/docker/marvel-heroes/docker-compose.yml"
# Path to the client launcher script (created by the setup script)
CLIENT_LAUNCHER_SCRIPT="$HOME/.local/bin/play-marvel-heroes.sh"
# Name of the docker container
CONTAINER_NAME="mhserveremu"

# --- Functions ---

ensure_user_space() {
    if [[ "$(id -u)" -eq 0 ]]; then
        if [[ -n "${SUDO_USER:-}" ]]; then
            echo "[INFO] Root execution detected. Dropping privileges to user: $SUDO_USER"
            exec sudo -H -u "$SUDO_USER" bash "$(realpath "$0")" "$@"
        else
            echo "[ERROR] Run as root without SUDO_USER." >&2
            exit 1
        fi
    fi
}

# Function to check if the server container is running
is_server_running() {
    # Check if a container with the exact name is running
    [ "$(docker ps -q -f name=^/${CONTAINER_NAME}$)" ]
}

build_server() {
    echo -e "🛠️  Building server image..."
    docker compose -f "$SERVER_COMPOSE_FILE" --project-directory "$(dirname "$SERVER_COMPOSE_FILE")" build
}

# Function to start the server
start_server() {
    echo "🚀 Starting Marvel Heroes server..."
    if is_server_running; then
        echo "✅ Server is already running."
        return 0
    fi

    echo "Starting container..."
    # Build the image and start the container in the background
    # Use the full path to the compose file and specify the project directory
    docker compose -f "$SERVER_COMPOSE_FILE" --project-directory "$(dirname "$SERVER_COMPOSE_FILE")" build
    docker compose -f "$SERVER_COMPOSE_FILE" --project-directory "$(dirname "$SERVER_COMPOSE_FILE")" up -d
    # Test build command (verbose for dev):
    # docker compose -f "$SERVER_COMPOSE_FILE" --project-directory "$(dirname "$SERVER_COMPOSE_FILE")" build --no-cache --progress=plain

    echo "⏳ Waiting for server to initialize..."
    # A simple sleep is often enough for local startup
    sleep 10

    if is_server_running; then
        echo "✅ Server started successfully."
    else
        echo "❌ Error: Server failed to start. Check logs with 'docker logs ${CONTAINER_NAME}'."
        return 1
    fi
}

# Function to stop the server
stop_server() {
    echo "🛑 Stopping Marvel Heroes server..."
    if ! is_server_running; then
        echo "✅ Server is not running."
        return 0
    fi
    docker compose -f "$SERVER_COMPOSE_FILE" down
    echo "✅ Server stopped."
}

# Function to launch the game client
launch_client() {
    echo "🎮 Launching Marvel Heroes client..."
    if [ ! -f "$CLIENT_LAUNCHER_SCRIPT" ]; then
        echo "❌ Error: Client launcher not found at $CLIENT_LAUNCHER_SCRIPT"
        echo "Please run the client setup script first."
        return 1
    fi
    # Run the client in the background so this script can exit
    nohup "$CLIENT_LAUNCHER_SCRIPT" > /dev/null 2>&1 &
    echo "✅ Client launched."
}

# --- Main Script ---

ensure_user_space

case "${1:-}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        stop_server
        start_server
        ;;
    build)
        build_server
        ;;
    play)
        start_server && launch_client
        ;;
    client)
        launch_client
        ;;
    logs)
        echo "📋 Tailing server logs (Press Ctrl+C to stop)..."
        docker logs -f "$CONTAINER_NAME"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|build|play|client|logs}"
        echo "  start    - Starts the server."
        echo "  stop     - Stops the server."
        echo "  restart  - Restarts the server."
        echo "  build    - Rebuild the server."
        echo "  play     - Starts the server (if needed) and launches the game."
        echo "  client   - Launches the game client only."
        echo "  logs     - View live server logs."
        exit 1
        ;;
esac

# sudo chmod +x ~/Repos/pc-env/setup-linux/provision-apps/games/marvel-heroes-launcher.sh
# bash ~/Repos/pc-env/setup-linux/provision-apps/games/marvel-heroes-launcher.sh start

# bash ~/Repos/pc-env/setup-linux/provision-apps/games/marvel-heroes-launcher.sh play
