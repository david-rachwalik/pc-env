#!/usr/bin/env python
"""Data for important application files to backup"""

from dataclasses import dataclass, field

import shell_boilerplate as sh


# https://realpython.com/python-data-classes
@dataclass
class AppBackup:
    """Class model of application backup details.

    Attributes:
        id (str): Arbitrary 'app_id' given for ad hoc commands (filter_id).
        root (str | None): Install directory path without app title.
        name (str | None): Directory for the app title (mirrored by backup target).
        options (dict | None): Provide additional options [only, exclude, include].
        win_root (str | None): Windows-specific directory root override.
        win_name (str | None): Windows-specific application directory name override.
    """

    id: str
    root: str
    name: str
    win_root: str | None = field(default=None)
    win_name: str | None = field(default=None)
    options: dict | None = field(default=None)


active_apps = [
    "continue",
    "handbrake",
    "obs",
    "qbittorrent",
    "qbittorrent_data",
    # "voicemeeter",
    # "vscode",
    # "yt_dlp",
]


# --- Cross-Platform Roots ---
is_windows = sh.system_platform() == "windows"
if is_windows:
    # Windows native paths
    user_home = sh.environment_get("USERPROFILE")
    user_roaming_dir = sh.environment_get("APPDATA")  # C:\Users\name\AppData\Roaming
    user_local_dir = sh.environment_get("LOCALAPPDATA")  # C:\Users\name\AppData\Local
else:
    # Linux native paths
    user_home = sh.expand_path("~")
    user_roaming_dir = sh.join_path(user_home, ".config")
    user_local_dir = sh.join_path(user_home, ".local", "share")

CLOUD_ROOT_DIR = sh.join_path(user_home, "pCloud")
BACKUP_ROOT_DIR = sh.join_path(CLOUD_ROOT_DIR, "Backups")


app_backups_full: list[AppBackup] = [
    AppBackup(
        id="continue",
        root=user_home,
        name=".continue",
        options={
            "only": ["config.yaml", ".continueignore", "rules/*"],
        },
    ),
    AppBackup(
        id="handbrake",
        root=user_roaming_dir,
        name="HandBrake",
        options={
            "only": ["presets.json", "settings.json"],
        },
    ),
    AppBackup(
        id="obs",
        root=user_roaming_dir,
        name="obs-studio",
        options={
            "only": ["global.ini", "basic/*"],
        },
    ),
    AppBackup(
        id="qbittorrent",
        root=user_roaming_dir,
        name="qBittorrent",
        options={
            "only": ["qBittorrent.ini", "qBittorrent-data.ini"],
        },
    ),
    AppBackup(
        id="qbittorrent_data",
        root=user_local_dir,
        name="qBittorrent",
        options={
            "only": ["BT_backup/*"],
        },
    ),
    AppBackup(
        id="voicemeeter",
        root="",
        win_root=sh.join_path(user_home, "Documents"),  # Windows only
        name="Voicemeeter",
        options={
            "only": ["VoicemeeterProfile.xml"],
        },
    ),
    AppBackup(
        id="vscode",
        root=user_roaming_dir,
        name=sh.join_path("Code", "User"),
        options={
            # 'only': ['settings.json', 'snippets/*'],
            "only": ["settings.json"],
        },
    ),
    AppBackup(
        id="yt_dlp",
        root=user_roaming_dir,
        name="yt-dlp",
        options={
            "only": ["config"],
        },
    ),
]

# # Filter backup details to only the active apps
# app_backups: list[AppBackup] = [
#     app for app in app_backups_full if app.id in active_apps
# ]

# Filter backup details to only the active apps, evaluating OS roots
app_backups: list[AppBackup] = []
for app in app_backups_full:
    if app.id not in active_apps:
        continue

    # Evaluate Windows overrides
    if is_windows:
        app.root = app.win_root if app.win_root is not None else app.root
        app.name = app.win_name if app.win_name is not None else app.name

    # Skip application if it lacks a valid root/name for the current OS platform
    if not app.root or not app.name:
        continue

    app_backups.append(app)
