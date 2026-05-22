#!/usr/bin/env python3

import argparse
import logging
import os
import pwd
import shutil
import subprocess
import sys
import time

# Configuration
TARGET = "8.8.8.8"  # Using Google's DNS to test outside local network
INTERVAL_SEC = 1.0  # Seconds between checks
HIGH_LATENCY_MS = 100.0
HEARTBEAT_SEC = 3600.0  # Log a status message every hour (3600 sec) to prove it's alive


def get_actual_home() -> str:
    """Returns the true user's home directory, even if executed via sudo."""
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            return pwd.getpwnam(sudo_user).pw_dir
        except KeyError:
            pass
    return os.path.expanduser("~")


# Dynamically resolve log file path safely
LOGFILE = os.path.join(get_actual_home(), "logs", "network_events.log")


def setup_logging(log_to_file: bool):
    """Sets up logging format. Only hooks up the FileHandler if requested."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]

    # Only write to log file if explicitly requested via flag
    if log_to_file:
        log_dir = os.path.dirname(LOGFILE)
        os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(LOGFILE))

    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", handlers=handlers)


def ping_target(target: str) -> tuple[bool, float | None]:
    """
    Pings the target once.
    Returns a tuple of (success_boolean, latency_in_ms).
    """
    try:
        # -c 1 = count 1, -W 1 = timeout 1 second
        result = subprocess.run(["ping", "-c", "1", "-W", "1", target], capture_output=True, text=True)
        success = result.returncode == 0
        latency = None

        if success:
            for part in result.stdout.split():
                if part.startswith("time="):
                    latency = float(part.split("=")[1])
                    break

        return success, latency
    except Exception as e:
        logging.error(f"Ping execution error: {e}")
        return False, None


def install_systemd_service():
    """
    Copies the script to /usr/local/bin and installs it as a systemd service.
    """
    if os.geteuid() != 0:
        print("Error: Installation requires root privileges.  Please run with sudo:")
        print(f"sudo python3 {os.path.basename(__file__)} --install")
        sys.exit(1)

    user = os.environ.get("SUDO_USER", "root")
    user_home = get_actual_home()
    expected_log_path = os.path.join(user_home, "logs/network_events.log")

    # Copy script to "production" location
    source_script_path = os.path.abspath(__file__)
    target_script_path = "/usr/local/bin/net_monitor.py"

    print(f"Copying script to {target_script_path}...")
    shutil.copy2(source_script_path, target_script_path)
    os.chmod(target_script_path, 0o755)

    # Create and Write the systemd service
    service_name = "net_monitor.service"
    service_path = f"/etc/systemd/system/{service_name}"

    service_content = f"""[Unit]
Description=Network Connectivity Monitor
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={user_home}
ExecStart={sys.executable} {target_script_path} --log-to-file
Restart=always
RestartSec=5
MemoryMax=50M

[Install]
WantedBy=multi-user.target
"""
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        print(f"Created systemd service file at {service_path}")

        # Reload systemd, enable, and start service
        print("Enabling and starting service...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        subprocess.run(["systemctl", "enable", service_name], check=True)
        subprocess.run(["systemctl", "restart", service_name], check=True)

        print("\nService installed/updated and started successfully!")
        print(f"Status check:    sudo systemctl status {service_name}")
        print(f"Background logs: sudo journalctl -u {service_name} -f")
        print(f"App Log file:    {expected_log_path}")

    except Exception as e:
        print(f"Failed to install systemd service: {e}")
        sys.exit(1)


def main(log_to_file: bool):
    setup_logging(log_to_file)

    if log_to_file:
        logging.info(f"=== Network monitor [FILE LOGGING] started against {TARGET} ===")
    else:
        logging.info(f"=== Network monitor [LOCAL_TEST] started against {TARGET} ===")

    was_up = True
    down_since = None
    total_outages = 0
    total_downtime = 0.0
    last_heartbeat = time.time()

    while True:
        try:
            start_time = time.time()
            success, latency = ping_target(TARGET)

            # Transition: DOWN -> UP
            if success and not was_up:
                if down_since is not None:
                    outage_time = time.time() - down_since
                    total_outages += 1
                    total_downtime += outage_time
                    logging.info(f"UP after {outage_time:.1f}s " f"(total outages: {total_outages}, total downtime: {total_downtime:.1f}s)")
                else:
                    logging.info("UP (Initial connection established)")

                was_up = True
                down_since = None

            # Transition: UP -> DOWN
            elif not success and was_up:
                down_since = time.time()
                logging.info("DOWN")
                was_up = False

            # High latency logging
            if success and latency is not None and latency > HIGH_LATENCY_MS:
                logging.info(f"HIGH_LATENCY {latency:.1f}ms")

            # Heartbeat logging
            if time.time() - last_heartbeat >= HEARTBEAT_SEC:
                status_msg = "HEARTBEAT - Monitor active"
                if total_outages > 0:
                    status_msg += f" | Total Outages: {total_outages} | Total Downtime: {total_downtime:.1f}s"
                logging.info(status_msg)
                last_heartbeat = time.time()

            # Sleep only for the remaining time in the interval to maintain consistent checks
            elapsed = time.time() - start_time
            sleep_time = max(0.0, INTERVAL_SEC - elapsed)
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            logging.info("=== Network monitor stopped by user ===")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Network Connectivity Monitor")
    parser.add_argument("--install", action="store_true", help="Install and start as a systemd service")
    parser.add_argument("--log-to-file", action="store_true", help="Enable writing logs to the permanent log file")
    args = parser.parse_args()

    if args.install:
        install_systemd_service()
    else:
        main(log_to_file=args.log_to_file)


# :: Usage ::
# cd ~/Repos/pc-env/python/commands

# Run normally in terminal (for testing):
# python3 net_monitor.py

# Install/Update as a permanent background service:
# sudo python3 net_monitor.py --install

# Systemctl Service Commands:
# sudo systemctl status net_monitor.service    # Check if running
# sudo systemctl stop net_monitor.service      # Stop the background process
# sudo systemctl start net_monitor.service     # Start the background process
# sudo systemctl restart net_monitor.service   # Restart the background process
# sudo systemctl disable net_monitor.service   # Stop starting automatically on boot
