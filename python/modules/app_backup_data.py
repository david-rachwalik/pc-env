#!/usr/bin/env python
"""Data for important application files to backup"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import shell_boilerplate as sh


# https://realpython.com/python-data-classes
@dataclass
class AppBackup:
    """Class model of application backup details"""

    id: str  # arbitrary 'app_id' given for ad hoc commands (filter_id)
    root: str  # install directory path without app title
    name: str  # directory for the app title (mirrored by backup target)
    # setting_opts: Optional[List[str]] = field(default=None)
    options: Optional[Dict[str, Any]] = field(default=None)  # provide additional options [only, exclude, include]


active_apps = [
    "handbrake",
    "obs",
    "qbittorrent",
    "qbittorrent_data",
    "voicemeeter",
    "vscode",
    "yt_dlp",
]


# user_roaming_dir = sh.environment_get('AppData')  # %UserProfile%/AppData/Roaming
# user_local_dir = sh.environment_get('LocalAppData')  # %UserProfile%/AppData/Local

user_roaming_dir = "/mnt/c/Users/david/AppData/Roaming"  # %AppData%
user_local_dir = "/mnt/c/Users/david/AppData/Local"  # %LocalAppData%
user_docs_dir = "/mnt/c/Users/david/Documents"

app_backups_full: List[AppBackup] = [
    AppBackup(
        id="handbrake",
        root=user_roaming_dir,
        name="HandBrake",
        # setting_opts=['--include=presets.json', '--include=settings.json', '--exclude=*'],
        options={
            "only": ["presets.json", "settings.json"],
        },
    ),
    AppBackup(
        id="obs",
        root=user_roaming_dir,
        name="obs-studio",
        # Test Command: rsync -a --dry-run --verbose --exclude=*.bak --include=global.ini --include=basic/ --include=basic/**/ --include=basic/**/* --exclude=* /mnt/c/Users/david/AppData/Roaming/obs-studio/ /mnt/d/OneDrive/Backups/Apps/obs-studio
        # setting_opts=['--exclude=*.bak', '--include=global.ini', '--include=basic/',
        #               '--include=basic/**/', '--include=basic/**/*', '--exclude=*'],
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
        # root=sh.join_path(sh.environment_get('Home'), 'Documents'),
        root=user_docs_dir,
        name="Voicemeeter",
        options={
            "only": ["VoicemeeterProfile.xml"],
        },
    ),
    AppBackup(
        id="vscode",
        root=user_roaming_dir,
        name=sh.join_path("Code", "User"),
        # setting_opts=['--include=settings.json', '--include=snippets/', '--exclude=*'],
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

# Filter backup details to only the active apps
app_backups: List[AppBackup] = [app for app in app_backups_full if app.id in active_apps]
