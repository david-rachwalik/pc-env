# Marvel Heroes: Local Server & Standalone Client

This project provides a complete, automated setup for running a local [`MHServerEmu`](https://github.com/Crypto137/MHServerEmu) server in Docker and playing Marvel Heroes with a standalone client on Linux.&nbsp; It is designed to be efficient and easy to use.

> For a video walkthrough of a similar manual setup, see this [YouTube guide](https://www.youtube.com/watch?v=a1fIxhRZg34).

## Features

- **Automated Server Build**:&nbsp; Builds the _MHServerEmu_ directly from the official source code for the best performance and latest updates.
- **Efficient Caching**:&nbsp; The Docker build process is optimized to only download new source code changes, making subsequent builds very fast.
- **Dockerized Environment**:&nbsp; The server runs in a clean, isolated Docker container as a non-root user for better security.
- **Persistent Data**:&nbsp; Uses Docker named volumes to safely store the account data, server database, and cloned git repository.
- **Standalone Client**:&nbsp; A setup script configures the game client to run independently of Steam using Proton GE.
- **Simple Controls**:&nbsp; A single orchestration script (`marvel-heroes-launcher.sh`) manages starting/stopping the server and launching the game.

---

## Step 1: Prerequisites

Before you begin, ensure you have the following installed and ready on your Linux machine:

1. **Docker and Docker Compose**:&nbsp; Required to build and run the server container.

2. **Marvel Heroes Game Client**:&nbsp; You need a copy of the the game files.&nbsp; The game is still able to be re-installed via Steam (needed to have played when it was live).&nbsp; Otherwise, the standalone client must be the last live copy of the game on PC, version [1.52.0.1700](https://archive.org/details/marvel-heroes-omega-2-16a-steam) (**Omega 2.16a**) released on September 7th, 2017.

3. **Proton GE**:&nbsp; The client setup script uses Proton GE to run the game.&nbsp; The script expects it to be installed in the standard Steam compatibility tools directory.&nbsp; If you don't have it, you can use a script like the one in `setup-linux/provision-apps/proton-ge.sh` to install it.

---

## Step 2: One-Time Client Setup

You only need to do this once. This script will create a launcher for the game that points to your local server.

1. **Edit the Setup Script**:
   Open the client setup script: `setup-linux/provision-apps/games/marvel-heroes.sh`.

   Find this line and **change the path** to match the location of your Marvel Heroes game files:

   ```bash
   # !! IMPORTANT: Update this path to your game installation directory !!
   GAME_DIR="/media/root/HDD-01/GameFiles/Marvel Heroes/UnrealEngine3/Binaries/Win64"
   ```

2. **Run the Script**:
   Execute the script with `sudo`.&nbsp; It needs root permissions to create the launcher in a system-accessible location.

   ```bash
   sudo bash setup-linux/provision-apps/games/marvel-heroes.sh
   ```

   This will create a `play-marvel-heroes.sh` launcher in your `~/.local/bin` directory and a desktop entry so you can find "Marvel Heroes (Local Server)" in your applications menu.

---

## Step 3: How to Play

All actions are performed using the `marvel-heroes-launcher.sh` script located in `setup-linux/provision-apps/games/`.

#### To start the server and launch the game:

This is the command you will use most often. It automatically starts the server (if it's not already running) and then launches the game client.&nbsp; The first time you run this, it will take several minutes to download and compile the server source code.&nbsp; Subsequent runs will be much faster.

```bash
./setup-linux/provision-apps/games/marvel-heroes-launcher.sh play
```

##### Other Commands

View live server logs

```bash
./setup-linux/provision-apps/games/marvel-heroes-launcher.sh logs
```

Start the server only

```bash
./setup-linux/provision-apps/games/marvel-heroes-launcher.sh start
```

Restart the server

```bash
./setup-linux/provision-apps/games/marvel-heroes-launcher.sh restart
```

Stop the server

```bash
./setup-linux/provision-apps/games/marvel-heroes-launcher.sh stop
```

---

### First-Time Account Creation

The first time you connect to your server, you will need to create an account and grant it administrator privileges.

1. **Start the server** using the `marvel-heroes-launcher.sh start` command.
2. **Open a web browser** and navigate to the server's [Dashboard](http://localhost:8088/Dashboard/)
3. **Create an account** using the web interface (e.g., `test@test.com` / `123`).
4. **Promote the account to Admin**: While the server is running, run the following command in your terminal.&nbsp; The single quotes are important!

   ```bash
   # Replace test@test.com with the email you used to register
   docker exec mhserveremu /app/src/MHServerEmu/bin/x64/Release/net8.0/MHServerEmu '!account userlevel test@test.com 2'
   ```

---

### Advanced Configuration

- **Server Options**:&nbsp; To change server settings, you can directly edit the `ConfigOverride.ini` file.&nbsp; You will need to restart the server for changes to take effect.&nbsp; Notable options include:
  - AutoUnlockAvatars
  - AutoUnlockTeamUps
  - DisableMovementPowerChargeCost

- **Live Tuning**:&nbsp; For more advanced real-time changes, you can edit the `LiveTuningDataGlobal.json` file located in the server's `Data/Game/LiveTuning` directory.&nbsp; After making changes, you can apply them without restarting the server by running:

  ```bash
  docker exec mhserveremu /app/src/MHServerEmu/bin/x64/Release/net8.0/MHServerEmu '!server reloadlivetuning'
  ```

- **Server Version**:&nbsp; To use a specific release of _MHServerEmu_ instead of the latest `master` branch, edit `docker-compose.yml` and change the `MH_VERSION` build argument.
