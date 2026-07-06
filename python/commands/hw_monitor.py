#!/usr/bin/env python3
"""
Hardware Resource Crash Monitor

Purpose:
  To diagnose sudden system crashes during demanding tasks (like gaming).
  This script monitors core system resources (CPU, RAM, AMD GPU) and logs them
  to a CSV file every second.  By immediately flushing data to the disk, it
  ensures the final recorded metrics (temperature, power draw, utilization)
  are saved right up to the exact second the system hard-locks or black-screens.

Usage:
  1. Live Preview (terminal only, no file logging):
     python3 /workspaces/hw_monitor.py

  2. Install the background service (run once, or again to update the script):
     sudo python3 /workspaces/hw_monitor.py --install

  3. Start/Stop background logging (run these when you start/stop gaming):
     sudo systemctl start hw_monitor.service
     sudo systemctl stop hw_monitor.service

Expected Behavior (The Crash Lifecycle):
  1. Setup:         Running the `--install` command registers the service, asleep and using 0 resources.
  2. Launch:        Before playing a game, run `hw-start` (via alias) to spin up the background process.
  3. Silent Watch:  Every 1 second, it reads raw kernel memory (/proc) and direct hardware lanes (/sys).
                    Because paths are cached and subprocesses are bypassed, it uses virtually 0% CPU.
  4. The Crash:     A hard-lock or black-screen occurs.  Standard RAM logs are lost, but because this
                    script forces an instant disk flush, the final metrics are etched to the SSD.
  5. The Aftermath: You force reboot the PC and open ~/logs/hw_metrics_log.csv in a spreadsheet.
  6. The Verdict:   Check the final 3 seconds to find the culprit (e.g., GPU temp spike, RAM OOM).

Optional Setup:
  To make starting/stopping easier, add these aliases to your ~/.bashrc profile:
    alias hw-start="sudo systemctl start hw_monitor.service"
    alias hw-stop="sudo systemctl stop hw_monitor.service"
"""

import argparse
import csv
import logging
import os
import pwd
import shutil
import subprocess
import sys
import time
from datetime import datetime

# --- Configuration ---
INTERVAL_SEC = 1.0  # Log every second to catch spikes right before a crash
LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "hw_metrics_log.csv"


def get_actual_home() -> str:
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            return pwd.getpwnam(sudo_user).pw_dir
        except KeyError:
            pass
    return os.path.expanduser("~")


LOGFILE = os.path.join(get_actual_home(), LOG_DIR_NAME, LOG_FILE_NAME)

# Global state for calculating CPU usage deltas
_last_cpu_total = 0
_last_cpu_idle = 0

# Cached file paths for maximum efficiency
_thermal_zones = []
_amd_paths = {}


def init_hardware_paths():
    """Scans and caches the specific deeply-nested hardware files once at startup."""
    global _thermal_zones, _amd_paths

    # 1. Cache CPU Thermal Zones
    try:
        if os.path.exists("/sys/class/thermal"):
            for zone in os.listdir("/sys/class/thermal"):
                if zone.startswith("thermal_zone"):
                    filepath = f"/sys/class/thermal/{zone}/temp"
                    if os.path.exists(filepath):
                        _thermal_zones.append(filepath)

        # AMD CPUs (and modern Intel) often put CPU temps here instead
        if os.path.exists("/sys/class/hwmon"):
            for hwmon in os.listdir("/sys/class/hwmon"):
                hwmon_dir = os.path.join("/sys/class/hwmon", hwmon)
                name_path = os.path.join(hwmon_dir, "name")
                if os.path.exists(name_path):
                    with open(name_path, "r") as f:
                        sensor_name = f.read().strip()
                    if sensor_name in ["k10temp", "coretemp", "zenpower"]:
                        for file in os.listdir(hwmon_dir):
                            if file.startswith("temp") and file.endswith("_input"):
                                _thermal_zones.append(os.path.join(hwmon_dir, file))
    except Exception:
        pass

    # 2. Cache AMD GPU Files
    try:
        drm_path = "/sys/class/drm"
        if os.path.exists(drm_path):
            for card in os.listdir(drm_path):
                if card.startswith("card") and "-" not in card:
                    card_dir = os.path.join(drm_path, card, "device")
                    if os.path.exists(os.path.join(card_dir, "gpu_busy_percent")):
                        _amd_paths["busy"] = os.path.join(card_dir, "gpu_busy_percent")
                        _amd_paths["mem_used"] = os.path.join(
                            card_dir, "mem_info_vram_used"
                        )
                        _amd_paths["mem_total"] = os.path.join(
                            card_dir, "mem_info_vram_total"
                        )

                        hwmon_dir = os.path.join(card_dir, "hwmon")
                        if os.path.exists(hwmon_dir):
                            for hwmon in os.listdir(hwmon_dir):
                                h_dir = os.path.join(hwmon_dir, hwmon)
                                if os.path.exists(os.path.join(h_dir, "temp1_input")):
                                    _amd_paths["temp"] = os.path.join(
                                        h_dir, "temp1_input"
                                    )
                                if os.path.exists(
                                    os.path.join(h_dir, "power1_average")
                                ):
                                    _amd_paths["power"] = os.path.join(
                                        h_dir, "power1_average"
                                    )
                        break  # Stop after finding the first valid AMD card
    except Exception:
        pass


def get_cpu_temp() -> str:
    """Reads all thermal zones from cached paths to minimize overhead."""
    max_temp = 0.0
    for path in _thermal_zones:
        try:
            with open(path, "r") as f:
                temp = float(f.read().strip()) / 1000.0
                if temp > max_temp and temp < 150:  # Ignore bogus high readings
                    max_temp = temp
        except Exception:
            continue

    return f"{max_temp:.1f}" if max_temp > 0 else "N/A"


def get_cpu_util() -> str:
    """Calculates CPU usage directly from /proc/stat to avoid subprocess fork overhead."""
    global _last_cpu_total, _last_cpu_idle
    try:
        with open("/proc/stat", "r") as f:
            cpu_line = f.readline()

        # Format: cpu  user nice system idle iowait irq softirq steal guest guest_nice
        parts = [int(p) for p in cpu_line.split()[1:]]
        idle = parts[3] + parts[4]  # idle + iowait
        total = sum(parts)

        delta_idle = idle - _last_cpu_idle
        delta_total = total - _last_cpu_total

        _last_cpu_idle = idle
        _last_cpu_total = total

        # Prevent division by zero and ignore the very first calculation
        if delta_total > 0 and _last_cpu_total > 0:
            util = 100.0 * (1.0 - (delta_idle / delta_total))
            return f"{util:.1f}"
    except Exception as e:
        logging.debug(f"CPU stat error: {e}")
    return "N/A"


def get_ram_util() -> str:
    """Reads memory usage directly from /proc/meminfo to avoid subprocess fork overhead."""
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = int(parts[1])

        total_kb = meminfo.get("MemTotal", 0)
        avail_kb = meminfo.get("MemAvailable", 0)

        if total_kb > 0:
            used_mb = (total_kb - avail_kb) // 1024
            percent = (float(total_kb - avail_kb) / float(total_kb)) * 100.0
            return f"{percent:.1f}% ({used_mb}MB)"
    except Exception as e:
        logging.debug(f"RAM stat error: {e}")
    return "N/A"


def get_amd_gpu_stats() -> dict:
    """Reads cached AMD GPU sysfs paths."""
    stats = {"gpu_util": "N/A", "vram_util": "N/A", "temp": "N/A", "power": "N/A"}
    if not _amd_paths:
        return stats

    try:
        if "busy" in _amd_paths:
            with open(_amd_paths["busy"]) as f:
                stats["gpu_util"] = f"{f.read().strip()}%"

        if "mem_used" in _amd_paths and "mem_total" in _amd_paths:
            with open(_amd_paths["mem_used"]) as f:
                used_mb = int(f.read().strip()) // (1024 * 1024)
            with open(_amd_paths["mem_total"]) as f:
                total_mb = int(f.read().strip()) // (1024 * 1024)
            stats["vram_util"] = f"{used_mb}MB / {total_mb}MB"

        if "temp" in _amd_paths:
            with open(_amd_paths["temp"]) as f:
                temp_c = int(f.read().strip()) / 1000.0
                stats["temp"] = f"{temp_c:.1f}C"

        if "power" in _amd_paths:
            with open(_amd_paths["power"]) as f:
                power_w = int(f.read().strip()) / 1000000.0
                stats["power"] = f"{power_w:.1f}W"
    except Exception as e:
        logging.debug(f"AMD stats error: {e}")

    return stats


def install_systemd_service():
    """Installs the script as an on-demand systemd service."""
    if os.geteuid() != 0:
        print("Error: Installation requires root privileges. Please run with sudo:")
        print(f"sudo python3 {os.path.basename(__file__)} --install")
        sys.exit(1)

    user = os.environ.get("SUDO_USER", "root")
    user_home = get_actual_home()

    target_script_path = "/usr/local/bin/hw_monitor.py"
    shutil.copy2(os.path.abspath(__file__), target_script_path)
    os.chmod(target_script_path, 0o755)

    service_name = "hw_monitor.service"
    service_path = f"/etc/systemd/system/{service_name}"

    # We want nice high priority limit so it can write even under heavy system load
    service_content = f"""[Unit]
Description=Hardware Resource Crash Monitor
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={user_home}
ExecStart={sys.executable} {target_script_path} --log-to-file
# Removed 'Restart=always' so it stays stopped when you tell it to stop
OOMScoreAdjust=-900
CPUSchedulingPolicy=rr
CPUSchedulingPriority=1

[Install]
WantedBy=multi-user.target
"""
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        # We intentionally omit 'systemctl enable' so it DOES NOT start on boot
        # We also omit 'systemctl start' so it waits for your manual trigger

        print("\nService installed successfully! (Manual Start Mode)")
        print("To make triggering easy, add these to your ~/.bashrc:")
        print('  alias hw-start="sudo systemctl start hw_monitor.service"')
        print('  alias hw-stop="sudo systemctl stop hw_monitor.service"')
        print("\nOtherwise, run exactly when about to play a game:")
        print(f"  sudo systemctl start {service_name}")
        print("\nWhen you are done playing, stop it:")
        print(f"  sudo systemctl stop {service_name}")
        print(f"\nTo monitor live background logs in terminal: tail -f {LOGFILE}")
    except Exception as e:
        print(f"Install failed: {e}")
        sys.exit(1)


def main(log_to_file: bool):
    file_handle = None
    csv_writer = None

    if log_to_file:
        os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
        # Open in append mode, unbuffered/line-buffered so it writes instantly
        file_handle = open(LOGFILE, "a", newline="")
        csv_writer = csv.writer(file_handle)

        # Write header if file is totally empty
        if os.path.getsize(LOGFILE) == 0:
            csv_writer.writerow(
                [
                    "Timestamp",
                    "CPU Util",
                    "CPU Temp",
                    "RAM Util",
                    "GPU Util",
                    "GPU VRAM",
                    "GPU Temp",
                    "GPU Power",
                ]
            )
            file_handle.flush()

        print(f"Logging actively to {LOGFILE} ...")
    else:
        print(
            "Running in terminal display mode (Not logging to file). Watch stats live:"
        )
        print(
            f"{'Timestamp':<20} | {'CPU %':<6} | {'CPU Temp':<8} | {'RAM Usage':<18} | {'GPU %':<6} | {'GPU VRAM':<18} | {'GPU Temp':<8} | {'GPU Pwr'}"
        )

    # Initialize one-time caches and CPU stat deltas
    init_hardware_paths()
    get_cpu_util()

    try:
        while True:
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cpu_val = get_cpu_util()
            ram_val = get_ram_util()
            cpu_temp = get_cpu_temp()
            gpu = get_amd_gpu_stats()

            row = [
                timestamp,
                cpu_val,
                cpu_temp,
                ram_val,
                gpu["gpu_util"],
                gpu["vram_util"],
                gpu["temp"],
                gpu["power"],
            ]

            if log_to_file and csv_writer and file_handle:
                csv_writer.writerow(row)
                # CRITICAL: Force the file operation to disk immediately
                # (otherwise, python buffers it and a hard crash loses the last few seconds)
                file_handle.flush()
                os.fsync(file_handle.fileno())
            else:
                print(
                    f"{row[0]:<20} | {row[1]:<6} | {row[2]:<8} | {row[3]:<18} | {row[4]:<6} | {row[5]:<18} | {row[6]:<8} | {row[7]}"
                )

            elapsed = time.time() - start_time
            sleep_time = max(0.0, INTERVAL_SEC - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    finally:
        if file_handle:
            file_handle.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--install", action="store_true", help="Install background systemd service"
    )
    parser.add_argument(
        "--log-to-file", action="store_true", help="Write to CSV log file"
    )
    args = parser.parse_args()

    if args.install:
        install_systemd_service()
    else:
        main(log_to_file=args.log_to_file)


# :: Quick Reference Commands ::

# 1. Preview what it looks like before running it in the background (does NOT save to CSV):
# python3 ~/Repos/pc-env/python/commands/hw_monitor.py

# 2. Install to the system to allow consistent background logging:
# sudo python3 ~/Repos/pc-env/python/commands/hw_monitor.py --install

# 3. Start/Stop the background logger (saves to CSV):
# sudo systemctl start hw_monitor.service
# sudo systemctl stop hw_monitor.service
# sudo systemctl status hw_monitor.service
