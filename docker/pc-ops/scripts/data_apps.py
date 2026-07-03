#!/usr/bin/env python
"""Data for important application files to backup"""

import shell_boilerplate as sh
from models import PATHS, BackupProfile, filter_active_profiles

active_apps = [
    "continue",
    "handbrake",
    "obs",
    "qbittorrent",
    "qbittorrent_data",
    "voicemeeter",
    # "vscode",
    # "yt_dlp",
]


app_backups_full: list[BackupProfile] = [
    BackupProfile(
        id="continue",
        root=PATHS.home,
        name=".continue",
        options={
            "only": ["config.yaml", ".continueignore", "rules/*"],
        },
    ),
    BackupProfile(
        id="handbrake",
        root=PATHS.roaming,
        name="ghb",
        win_name="HandBrake",
        options={
            "only": ["presets.json", "settings.json"],
        },
    ),
    BackupProfile(
        id="obs",
        root=PATHS.roaming,
        name="obs-studio",
        options={
            "only": ["global.ini", "basic/*"],
        },
    ),
    BackupProfile(
        id="qbittorrent",
        root=PATHS.roaming,
        name="qBittorrent",
        options={
            "only": ["qBittorrent.ini", "qBittorrent-data.ini"],
        },
    ),
    BackupProfile(
        id="qbittorrent_data",
        root=PATHS.local,
        name="qBittorrent",
        options={
            "only": ["BT_backup/*"],
        },
    ),
    BackupProfile(
        id="voicemeeter",
        root="",
        win_root=sh.join_path(PATHS.home, "Documents"),  # Windows only
        name="Voicemeeter",
        options={
            "only": ["VoicemeeterProfile.xml"],
        },
    ),
    BackupProfile(
        id="vscode",
        root=PATHS.roaming,
        name=sh.join_path("Code", "User"),
        options={
            # 'only': ['settings.json', 'snippets/*'],
            "only": ["settings.json"],
        },
    ),
    BackupProfile(
        id="yt_dlp",
        root=PATHS.roaming,
        name="yt-dlp",
        options={
            "only": ["config"],
        },
    ),
]

# Filter backup details to only the active apps, evaluating OS roots
app_backups: list[BackupProfile] = filter_active_profiles(
    app_backups_full, active_apps, PATHS.is_windows
)
