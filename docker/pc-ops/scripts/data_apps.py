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
    # --- Emulators ---
    # "es_de",
    # "retroarch",
    # "xemu",
    # "pcsx2",
    # "rpcs3",
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
    # ----------------------------------------------------------------
    # --- Emulators ---
    # ----------------------------------------------------------------
    BackupProfile(
        id="es_de",
        root=PATHS.home,
        name=".es-de",
        options={
            "only": ["settings/*", "custom_systems/*"],
        },
    ),
    BackupProfile(
        id="retroarch",
        root=PATHS.roaming,  # ~/.config/retroarch
        name="retroarch",
        options={
            "only": [
                "system/*",  # BIOS / Drivers (e.g. scph5501.bin)
                "saves/*",
                "states/*",
                "config/*",
            ],
        },
    ),
    BackupProfile(
        id="xemu",
        root=sh.join_path(PATHS.local, "xemu"),  # ~/.local/share/xemu/xemu
        name="xemu",
        options={
            "only": [
                "xemu.toml",
                "eeprom/*",  # Xbox config data
                "flash/*",  # Xbox BIOS / Drivers
            ],
        },
    ),
    BackupProfile(
        id="pcsx2",
        root=PATHS.roaming,  # ~/.config/PCSX2
        name="PCSX2",
        options={
            "only": [
                "bios/*",  # BIOS / PS2 Drivers
                "memcards/*",  # Save states
                "sstates/*",
                "inis/*",  # Settings
            ],
        },
    ),
    BackupProfile(
        id="rpcs3",
        root=PATHS.roaming,  # ~/.config/rpcs3
        name="rpcs3",
        options={
            "only": [
                "config/*",
                "dev_hdd0/home/*",  # User profiles
                "dev_hdd0/savedata/*",  # Save data
            ],
        },
    ),
]

# Filter backup details to only the active apps, evaluating OS roots
app_backups: list[BackupProfile] = filter_active_profiles(
    app_backups_full, active_apps, PATHS.is_windows
)
