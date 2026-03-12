# rclone-manager Docker Setup

This runs the `rclone-manager` web UI in Docker, allowing you to manage your rclone remotes and schedule automatic `bisync` operations. It replaces the need for systemd timers and manual scripts.

## Quick Start

### 1. Initial Setup

- Create your `.env` file from the example:

  ```bash
  cp .env.example .env
  ```

- Edit `.env` and set your `TZ` and local directory paths (`ONEDRIVE_DIR`, etc.).

  ```bash
  nano .env
  ```

### 2. Start the Container

```bash
docker compose up -d
```

The container will now start automatically whenever you boot your computer.

### 3. Configure rclone Remotes

If you don't have a `./config/rclone.conf` file yet, configure your cloud remotes:

```bash
docker exec -it rclone-manager rclone config
```

Follow the prompts to add your `onedrive`, `pcloud`, or `gdrive` remotes. The configuration will be saved to `./config/rclone.conf`.

### 4. Set Up Scheduled Syncs

1.  Open the web UI in your browser: **http://localhost:8686** (or your custom port).
2.  Go to the **"Scheduler"** tab.
3.  Click **"Add New Task"**.
4.  Configure a `bisync` task:
    - **Task Type:** `Bisync`
    - **Path 1:** Select your remote (e.g., `onedrive:`).
    - **Path 2:** Enter the **exact same absolute path** you used in your `.env` file (e.g., `/home/your-user/OneDrive`).
    - **Schedule:** Set your desired cron schedule (e.g., `0 */4 * * *` for every 4 hours).
    - **Save** the task.

Repeat for each remote you want to sync automatically. The web UI will handle all scheduling.

## Managing the Service

```bash
# Start the service
docker compose up -d

# Stop the service
docker compose down

# View logs
docker compose logs -f

# Update to the latest version
docker compose pull
docker compose up -d
```
