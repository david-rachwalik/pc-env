#!/usr/bin/env python
"""Data models for system backups"""

from dataclasses import dataclass

import shell_boilerplate as sh


# https://realpython.com/python-data-classes
@dataclass
class BackupProfile:
    """Class model of backup details for applications and games.

    Attributes:
        id (str): Arbitrary identifier given for ad hoc commands (filter_id).
        root (str): Install directory path without title.
        name (str): Directory for the title (mirrored by backup target).
        options (dict | None): Provide additional options [only, exclude, include].
        screenshot (str | None): Directory specifically for game screenshots.
        win_root (str | None): Windows-specific directory root override.
        win_name (str | None): Windows-specific application directory name override.
    """

    id: str
    root: str
    name: str
    options: dict | None = None
    screenshot: str | None = None
    win_root: str | None = None
    win_name: str | None = None


def filter_active_profiles(
    profiles: list[BackupProfile], active_ids: list[str], is_windows: bool
) -> list[BackupProfile]:
    """Filters and maps a list of backup profiles based on active IDs and current OS."""
    results: list[BackupProfile] = []

    for profile in profiles:
        if profile.id not in active_ids:
            continue

        # Evaluate Windows overrides
        if is_windows:
            profile.root = (
                profile.win_root if profile.win_root is not None else profile.root
            )
            profile.name = (
                profile.win_name if profile.win_name is not None else profile.name
            )

        # Skip profile if it lacks a valid root/name for the current OS platform
        if not profile.root or not profile.name:
            continue

        results.append(profile)

    return results


@dataclass(frozen=True)
class SystemPaths:
    """Class model for common cross-platform system paths"""

    is_windows: bool
    home: str
    roaming: str
    local: str
    docs: str
    games: str
    cloud: str
    backups: str
    game_c: str
    game_d: str


def get_system_paths() -> SystemPaths:
    """Evaluates cross-platform environment variables into a single path configuration."""
    is_win = sh.system_platform() == "windows"

    if is_win:
        # Windows native paths
        home = sh.environment_get("USERPROFILE")
        roaming = sh.environment_get("APPDATA")  # C:\Users\name\AppData\Roaming
        local = sh.environment_get("LOCALAPPDATA")  # C:\Users\name\AppData\Local
        docs = sh.join_path(home, "Documents")
        game_c = "C:\\Program Files"
        game_d = "D:\\GameFiles"
    else:
        # Linux native paths
        home = sh.environment_get("HOST_USER_HOME") or sh.expand_path("~")
        roaming = sh.join_path(home, ".config")
        local = sh.join_path(home, ".local", "share")
        docs = sh.join_path(home, "Documents")
        game_c = sh.join_path(home, "Games")
        game_d = sh.join_path(home, "Games")

    cloud = sh.join_path(home, "pCloud")

    return SystemPaths(
        is_windows=is_win,
        home=home,
        roaming=roaming,
        local=local,
        docs=docs,
        games=sh.join_path(docs, "My Games"),
        cloud=cloud,
        backups=sh.join_path(cloud, "Backups"),
        game_c=game_c,
        game_d=game_d,
    )


# Compute paths at module load for immediate availability
PATHS = get_system_paths()
