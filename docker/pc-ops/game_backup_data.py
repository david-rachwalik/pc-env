#!/usr/bin/env python
"""Data for important game files to backup"""

from dataclasses import dataclass, field

import shell_boilerplate as sh


# https://realpython.com/python-data-classes
@dataclass
class GameBackup:
    """Class model of game backup details.

    Attributes:
        id (str): Arbitrary 'game_id' given for ad hoc commands (filter_id).
        root (str): Install directory path without game title.
        name (str): Directory for the game title (mirrored by backup target).
        options (dict | None): Provide additional options [only, exclude, include].
        screenshot (str | None): Directory specifically for screenshots.
        win_root (str | None): Windows-specific directory root override.
        win_name (str | None): Windows-specific application directory name override.
    """

    id: str
    root: str
    name: str
    win_root: str | None = field(default=None)
    win_name: str | None = field(default=None)
    options: dict | None = field(default=None)
    screenshot: str | None = field(default=None)


active_games = [
    # 'diablo_iii',
    # 'elder_scrolls_online',
    # 'elite_dangerous',
    # "final_fantasy_xiv",
    # "hotline_miami",
    # "killing_floor_2",
    "marvel_rivals",
    # "rocket_league",
    # 'skyrim_se',
    # "skyrim_vr",
    # "stardew_valley",
    # 'wow_retail',
    # 'wow_classic',
    # 'wow_weakauras',
    # "wow_project_ascension",
    # "yiffalicious",
]


# --- Cross-Platform Roots ---
is_windows = sh.system_platform() == "windows"

if is_windows:
    # Windows native paths
    game_c_dir = "C:\\Program Files"
    game_d_dir = "D:\\GameFiles"
    user_roaming_dir = sh.environment_get("APPDATA")
    user_local_dir = sh.environment_get("LOCALAPPDATA")
    user_docs_dir = sh.join_path(sh.environment_get("USERPROFILE"), "Documents")
    user_games_dir = sh.join_path(user_docs_dir, "My Games")
else:
    # Linux native paths
    user_home = sh.expand_path("~")
    game_c_dir = sh.join_path(user_home, "Games")
    game_d_dir = sh.join_path(user_home, "Games")
    user_roaming_dir = sh.join_path(user_home, ".config")
    user_local_dir = sh.join_path(user_home, ".local", "share")
    user_docs_dir = sh.join_path(user_home, "Documents")
    user_games_dir = sh.join_path(user_docs_dir, "My Games")
    steam_dir = sh.join_path(
        user_home, ".steam", "debian-installation", "steamapps", "common"
    )


game_backups_full: list[GameBackup] = [
    GameBackup(
        id="diablo_iii",
        root=user_docs_dir,
        name="Diablo III",
        screenshot="Screenshots",
        options={
            "only": [
                "Screenshots/*",
                "D3Prefs.txt",  # settings
            ],
        },
    ),
    GameBackup(
        id="elder_scrolls_online",
        root=user_docs_dir,
        name=sh.join_path("Elder Scrolls Online", "live"),
        screenshot="Screenshots",
        options={
            "only": [
                "Screenshots/*",
                r".*\.txt$",  # settings ('.txt' extension)
                "SavedVariables/*",  # settings
                "AddOns/*",
            ],
        },
    ),
    GameBackup(
        id="elite_dangerous",
        root=user_local_dir,
        name=sh.join_path("Frontier Developments", "Elite Dangerous"),
        screenshot="Screenshots",
        options={
            "only": [
                "Screenshots/*",
                sh.join_path("Options", "Bindings", "*"),  # settings
            ],
            "filter": [
                r".*\.log$",  # ignore setting files with '.log' extension
            ],
        },
    ),
    GameBackup(
        id="final_fantasy_xiv",
        root=user_games_dir,
        name="FINAL FANTASY XIV - A Realm Reborn",
        screenshot="screenshots",
        options={
            "only": [
                "screenshots/*",
                r".*\.cfg$",  # settings ('.cfg' extension)
                r".*\.dat$",  # settings ('.dat' extension)
                "FFXIV_CHR004000174BCC982B/*",  # Goo Clone settings
                "FFXIV_CHR0040002E933812EA/*",  # Zaiba Igawa settings
                "FFXIV_CHR004000174B3A4759/*",  # Callia Denma settings
            ],
            "exclude": [
                r".*/log.*",  # ignore the settings log directory
            ],
        },
    ),
    GameBackup(
        id="hotline_miami",
        root=steam_dir,
        win_root=user_games_dir,
        # user_home, ".steam", "debian-installation", "steamapps", "common"
        # /media/root/HDD-01/GameFiles/SteamLibrary/steamapps/common/hotline_miami
        name="HotlineMiami",
        options={
            "only": [
                r".*\.sav$",  # settings ('.sav' extension)
            ],
        },
    ),
    GameBackup(
        id="killing_floor_2",
        root=user_games_dir,
        name="KillingFloor2",
        options={
            "only": [
                "KFGame/Config/*",  # settings
            ],
        },
    ),
    GameBackup(
        id="marvel_rivals",
        root=steam_dir,
        name="MarvelRivals",
        options={
            "only": [
                "KFGame/Config/*",  # settings
            ],
        },
    ),
    GameBackup(
        id="rocket_league",
        root=user_games_dir,
        name="Rocket League",
        options={
            "only": [
                "TAGame/Config/*",  # settings
            ],
        },
    ),
    # GameBackup(
    #     id='sims_iii',
    #     # Sims 3 [archive screenshots/settings/addons, run memory cleanup]
    # ),
    GameBackup(
        id="skyrim_se",
        root=user_games_dir,
        name="Skyrim Special Edition",
        options={
            "only": [
                r".*\.ini$",  # settings ('.ini' extension)
                "Saves/*",  # settings (save states)
            ],
        },
    ),
    GameBackup(
        id="skyrim_vr",
        root=user_games_dir,
        name="Skyrim VR",
        options={
            "only": [
                r".*\.ini$",  # settings ('.ini' extension)
                "Saves/*",  # settings (save states)
            ],
        },
    ),
    GameBackup(
        id="stardew_valley",
        root=user_roaming_dir,
        name="StardewValley",
        options={
            "only": [r".*"],  # settings
        },
    ),
    GameBackup(
        id="wow_retail",
        root=game_d_dir,
        name=sh.join_path("World of Warcraft", "_retail_"),
        screenshot="Screenshots",
        options={
            "only": [
                "Screenshots/*",
                "WTF/*",  # settings (save states)
                "Interface/AddOns/*",  # addons
            ],
            "exclude": [
                r".*\.bak$",  # ignore setting files with '.bak' extension
                r".*\.old$",  # ignore setting files with '.old' extension
                r".*Blizzard_.*",  # ignore the 'Blizzard_*' addon directories
                r".*DataStore.*",  # ignore the 'DataStore*' addon directory
                r".*/TradeSkillMaster_AppHelper.*",  # ignore the 'TradeSkillMaster_AppHelper' addon directory
            ],
        },
    ),
    GameBackup(
        id="wow_classic",
        root=game_d_dir,
        name=sh.join_path("World of Warcraft", "_classic_"),
        screenshot="Screenshots",
        options={
            "only": [
                "Screenshots/*",
                "WTF/*",  # settings (save states)
                "Interface/AddOns/*",  # addons
            ],
            "exclude": [
                r".*\.bak$",  # ignore setting files with '.bak' extension
                r".*\.old$",  # ignore setting files with '.old' extension
                r".*Blizzard_.*",  # ignore the 'Blizzard_*' addon directories
                r".*DataStore.*",  # ignore the 'DataStore*' addon directory
                r".*/TradeSkillMaster_AppHelper.*",  # ignore the 'TradeSkillMaster_AppHelper' addon directory
            ],
        },
    ),
    GameBackup(
        id="wow_weakauras",
        root=user_roaming_dir,
        name="weakauras-companion",
        options={
            "only": [
                "config.json",  # settings
            ],
        },
    ),
    GameBackup(
        id="wow_project_ascension",
        root=sh.join_path(game_c_dir, "ascension-wow", "drive_c", "Program Files"),
        win_root=game_c_dir,
        name=sh.join_path("Ascension Launcher", "resources", "client"),
        screenshot="Screenshots",
        options={
            "only": [
                "Screenshots/*",
                "WTF/*",  # settings (save states)
                "Interface/AddOns/*",  # addons
            ],
            "exclude": [
                r".*\.bak$",  # ignore setting files with '.bak' extension
                r".*\.old$",  # ignore setting files with '.old' extension
                r".*Blizzard_.*",  # ignore the 'Blizzard_*' addon directories
            ],
        },
    ),
    GameBackup(
        id="yiffalicious",
        root=user_roaming_dir,
        name="yiffalicious",
        screenshot="screenshots",
        options={
            "only": [
                "screenshots/*",
                "interactions/favorites/*",  # settings
            ],
        },
    ),
]

# Filter backup details to only the active games
game_backups: list[GameBackup] = [
    game for game in game_backups_full if game.id in active_games
]
