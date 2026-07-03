#!/usr/bin/env python
"""Data for important game files to backup"""

import shell_boilerplate as sh
from models import PATHS, BackupProfile, filter_active_profiles

active_games = [
    # 'diablo_iii',
    # 'elder_scrolls_online',
    # 'elite_dangerous',
    # "final_fantasy_xiv",
    "halls_of_torment",
    "hotline_miami",
    # "killing_floor_2",
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


game_backups_full: list[BackupProfile] = [
    BackupProfile(
        id="diablo_iii",
        root=PATHS.docs,
        name="Diablo III",
        screenshot="Screenshots",
        options={
            "only": [
                "Screenshots/*",
                "D3Prefs.txt",  # settings
            ],
        },
    ),
    BackupProfile(
        id="elder_scrolls_online",
        root=PATHS.docs,
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
    BackupProfile(
        id="elite_dangerous",
        root=PATHS.local,
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
    BackupProfile(
        id="final_fantasy_xiv",
        root=PATHS.games,
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
    BackupProfile(
        id="halls_of_torment",
        root=PATHS.local,
        win_root=PATHS.games,
        name="HallsOfTorment",
        options={
            "only": ["settings.json"],
        },
    ),
    BackupProfile(
        id="hotline_miami",
        root=PATHS.local,
        win_root=PATHS.games,
        name="HotlineMiami",
        options={
            "only": ["SaveData.sav", "hotline.cfg"],
        },
    ),
    BackupProfile(
        id="killing_floor_2",
        root=PATHS.games,
        name="KillingFloor2",
        options={
            "only": [
                "KFGame/Config/*",  # settings
            ],
        },
    ),
    BackupProfile(
        id="rocket_league",
        root=PATHS.games,
        name="Rocket League",
        options={
            "only": [
                "TAGame/Config/*",  # settings
            ],
        },
    ),
    # BackupProfile(
    #     id='sims_iii',
    #     # Sims 3 [archive screenshots/settings/addons, run memory cleanup]
    # ),
    BackupProfile(
        id="skyrim_se",
        root=PATHS.games,
        name="Skyrim Special Edition",
        options={
            "only": [
                r".*\.ini$",  # settings ('.ini' extension)
                "Saves/*",  # settings (save states)
            ],
        },
    ),
    BackupProfile(
        id="skyrim_vr",
        root=PATHS.games,
        name="Skyrim VR",
        options={
            "only": [
                r".*\.ini$",  # settings ('.ini' extension)
                "Saves/*",  # settings (save states)
            ],
        },
    ),
    BackupProfile(
        id="stardew_valley",
        root=PATHS.roaming,
        name="StardewValley",
        options={
            "only": [r".*"],  # settings
        },
    ),
    BackupProfile(
        id="wow_retail",
        root=PATHS.game_d,
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
    BackupProfile(
        id="wow_classic",
        root=PATHS.game_d,
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
    BackupProfile(
        id="wow_weakauras",
        root=PATHS.roaming,
        name="weakauras-companion",
        options={
            "only": ["config.json"],  # settings
        },
    ),
    BackupProfile(
        id="wow_project_ascension",
        root=sh.join_path(PATHS.game_c, "ascension-wow", "drive_c", "Program Files"),
        win_root=PATHS.game_c,
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
    BackupProfile(
        id="yiffalicious",
        root=PATHS.roaming,
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

# Filter backup details to only the active games, evaluating OS roots
game_backups: list[BackupProfile] = filter_active_profiles(
    game_backups_full, active_games, PATHS.is_windows
)
