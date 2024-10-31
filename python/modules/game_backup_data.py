#!/usr/bin/env python
"""Data for important game files to backup"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import shell_boilerplate as sh


# https://realpython.com/python-data-classes
@dataclass
class GameBackup:
    """Class model of game backup details"""
    id: str  # arbitrary 'game_id' given for ad hoc commands (filter_id)
    root: str  # install directory path without game title
    name: str  # directory for the game title (mirrored by backup target)
    options: Optional[Dict[str, Any]] = field(default=None)  # provide additional options [only, exclude, include]
    screenshot: Optional[str] = field(default=None)
    # addon: Optional[str] = field(default=None)
    # # addon_opts: Optional[List[str]] = field(default=None)
    # addon_opts: Optional[Dict[str, Any]] = field(default=None)  # provide additional options [only, exclude, include]
    # # screenshot_opts: Optional[List[str]] = field(default=None)
    # # screenshot_opts: Optional[Dict[str, Any]] = field(default=None)
    # setting: Optional[str] = field(default=None)
    # # setting_opts: Optional[List[str]] = field(default=None)
    # setting_opts: Optional[Dict[str, Any]] = field(default=None)  # provide additional options [only, exclude, include]


active_games = [
    # 'diablo_iii',
    # 'elder_scrolls_online',
    # 'elite_dangerous',
    'final_fantasy_xiv',
    'hotline_miami',
    'killing_floor_2',
    'rocket_league',
    # 'skyrim_se',
    'skyrim_vr',
    'stardew_valley',
    # 'wow_retail',
    # 'wow_classic',
    # 'wow_weakauras',
    'wow_project_ascension',
    'yiffalicious',
]


game_root_dir = sh.environment_get('AppData')  # %UserProfile%/AppData/Roaming
game_c_root_dir = sh.join_path('C:\\', 'Program Files')
game_d_root_dir = sh.join_path('D:\\', 'GameFiles')

game_backups_full: List[GameBackup] = [
    # GameBackup(
    #     id='blade_and_soul',
    #     root='/mnt/c/Users/david/Documents/My Games',
    #     name='BnS',
    #     setting="NCWEST",
    # ),
    GameBackup(
        id='diablo_iii',
        # root='/mnt/c/Users/david/Documents',
        root=sh.join_path(sh.environment_get('Home'), 'Documents'),  # similar to UserProfile
        name='Diablo III',
        screenshot='Screenshots',
        # screenshot_opts=['--backup', "--backup-dir=backup_{{ lookup('pipe','date +%Y-%m-%d') }}"],
        # setting=' ',
        # setting_opts=['--include=D3Prefs.txt', '--exclude=*'],
        options={
            'only': [
                'Screenshots/*',
                'D3Prefs.txt',  # settings
            ],
        },
    ),
    GameBackup(
        id='elder_scrolls_online',
        # root='/mnt/c/Users/david/Documents',
        root=sh.join_path(sh.environment_get('Home'), 'Documents'),
        name=sh.join_path('Elder Scrolls Online', 'live'),
        # addon='AddOns',
        screenshot='Screenshots',
        # setting=' ',
        # setting_opts=['--include=SavedVariables/', '--include=SavedVariables/*',
        #               '--exclude=*/', '--include=*.txt', '--exclude=*'],
        options={
            'only': [
                'Screenshots/*',
                r'.*\.txt$',  # settings ('.txt' extension)
                'SavedVariables/*',  # settings
                'AddOns/*',
            ],
        },
    ),
    GameBackup(
        id='elite_dangerous',
        # root='/mnt/c/Users/david/AppData/Local',
        root=sh.environment_get('LocalAppData'),
        name=sh.join_path('Frontier Developments', 'Elite Dangerous'),
        screenshot='Screenshots',
        # setting=sh.join_path('Options', 'Bindings'),
        # setting_opts=['--exclude=*.log'],
        # setting_opts={
        #     'exclude': ['*.log'],
        # },
        options={
            'only': [
                'Screenshots/*',
                sh.join_path('Options', 'Bindings', '*'),  # settings
            ],
            'filter':[
                r'.*\.log$',  # ignore setting files with '.log' extension
            ]
        },
    ),
    # GameBackup(
    #     id='elite_dangerous_screenshot',
    #     root='/mnt/c/Users/david/Pictures',
    #     name='Frontier Developments/Elite Dangerous',
    #     screenshot=' ',
    # ),
    GameBackup(
        id='final_fantasy_xiv',
        # root='/mnt/c/Users/david/Documents/My Games',
        root=sh.join_path(sh.environment_get('Home'), 'Documents', 'My Games'),
        name='FINAL FANTASY XIV - A Realm Reborn',
        screenshot='screenshots',
        # setting=' ',
        # setting_opts=['--include=*.cfg', '--exclude=*'],
        # setting_opts=[
        #     '--include=FFXIV_CHR004000174BCC982B/', '--include=FFXIV_CHR004000174BCC982B/*',  # Goo Clone
        #     '--include=FFXIV_CHR0040002E933812EA/', '--include=FFXIV_CHR0040002E933812EA/*',  # Zaiba Igawa
        #     '--include=FFXIV_CHR004000174B3A4759/', '--include=FFXIV_CHR004000174B3A4759/*',  # Callia Denma
        #     '--exclude=log/', '--exclude=log/*', '--exclude=*/'
        # ],
        options={
            'only': [
                'screenshots/*',
                r'.*\.cfg$',  # settings ('.cfg' extension)
                r'.*\.dat$',  # settings ('.dat' extension)
                'FFXIV_CHR004000174BCC982B/*',  # Goo Clone settings
                'FFXIV_CHR0040002E933812EA/*',  # Zaiba Igawa settings
                'FFXIV_CHR004000174B3A4759/*',  # Callia Denma settings
            ],
            'exclude':[
                r'.*/log.*',  # ignore the settings log directory
            ]
        },
    ),
    GameBackup(
        id='hotline_miami',
        # root='/mnt/c/Users/david/Documents/My Games',
        root=sh.join_path(sh.environment_get('Home'), 'Documents', 'My Games'),
        name='HotlineMiami',
        # setting=' ',
        # setting_opts=['--include=*.cfg', '--exclude=*'],
        # setting_opts=['--include=*.sav', '--exclude=*'],
        options={
            'only': [
                r'.*\.sav$',  # settings ('.sav' extension)
            ],
        },
    ),
    GameBackup(
        id='killing_floor_2',
        # root='/mnt/c/Users/david/Documents/My Games',
        root=sh.join_path(sh.environment_get('Home'), 'Documents', 'My Games'),
        name='KillingFloor2',
        # setting='KFGame/Config',
        options={
            'only': [
                'KFGame/Config/*',  # settings
            ],
        },
    ),
    GameBackup(
        id='rocket_league',
        # root='/mnt/c/Users/david/Documents/My Games',
        root=sh.join_path(sh.environment_get('Home'), 'Documents', 'My Games'),
        name='Rocket League',
        # setting='TAGame/Config',
        options={
            'only': [
                'TAGame/Config/*',  # settings
            ],
        },
    ),
    # GameBackup(
    #     id='sims_iii',
    #     # Sims 3 [archive screenshots/settings/addons, run memory cleanup]
    # ),
    GameBackup(
        id='skyrim_se',
        # root='/mnt/c/Users/david/Documents/My Games',
        root=sh.join_path(sh.environment_get('Home'), 'Documents', 'My Games'),
        name='Skyrim Special Edition',
        # setting=' ',
        # setting_opts=['--include=Saves/', '--include=Saves/*', '--exclude=*/', '--include=*.ini', '--exclude=*'],
        options={
            'only': [
                r'.*\.ini$',  # settings ('.ini' extension)
                'Saves/*',  # settings (save states)
            ],
        },
    ),
    GameBackup(
        id='skyrim_vr',
        # root='/mnt/c/Users/david/Documents/My Games',
        root=sh.join_path(sh.environment_get('Home'), 'Documents', 'My Games'),
        name='Skyrim VR',
        # setting=' ',
        # setting_opts=['--include=Saves/', '--include=Saves/*', '--exclude=*/', '--include=*.ini', '--exclude=*'],
        options={
            'only': [
                r'.*\.ini$',  # settings ('.ini' extension)
                'Saves/*',  # settings (save states)
            ],
        },
    ),
    GameBackup(
        id='stardew_valley',
        # root='/mnt/c/Users/david/AppData/Roaming',
        root=game_root_dir,
        name='StardewValley',
        # setting=' ',
        options={
            'only': [r'.*'],  # settings
        },
    ),
    GameBackup(
        id='wow_retail',
        # root='/mnt/e/GameFiles',
        root=game_d_root_dir,
        name=sh.join_path('World of Warcraft', '_retail_'),
        # addon='Interface/AddOns',
        # addon_opts=['--exclude=DataStore*/', '--exclude=TradeSkillMaster_AppHelper/'],
        screenshot='Screenshots',
        # setting='WTF',
        # setting_opts=['--exclude=*.bak', '--exclude=*.old'],
        options={
            'only': [
                'Screenshots/*',
                'WTF/*',  # settings (save states)
                'Interface/AddOns/*',  # addons
            ],
            'exclude':[
                r'.*\.bak$',  # ignore setting files with '.bak' extension
                r'.*\.old$',  # ignore setting files with '.old' extension
                r'.*DataStore.*',  # ignore the 'DataStore*' addon directory
                r'.*/TradeSkillMaster_AppHelper.*',  # ignore the 'TradeSkillMaster_AppHelper' addon directory
            ]
        },
    ),
    GameBackup(
        id='wow_classic',
        # root='/mnt/e/GameFiles',
        root=game_d_root_dir,
        name=sh.join_path('World of Warcraft', '_classic_'),
        # addon='Interface/AddOns',
        # addon_opts=['--exclude=DataStore*/', '--exclude=TradeSkillMaster_AppHelper/'],
        screenshot='Screenshots',
        # setting='WTF',
        # setting_opts=['--exclude=*.bak', '--exclude=*.old'],
        options={
            'only': [
                'Screenshots/*',
                'WTF/*',  # settings (save states)
                'Interface/AddOns/*',  # addons
            ],
            'exclude':[
                r'.*\.bak$',  # ignore setting files with '.bak' extension
                r'.*\.old$',  # ignore setting files with '.old' extension
                r'.*DataStore.*',  # ignore the 'DataStore*' addon directory
                r'.*/TradeSkillMaster_AppHelper.*',  # ignore the 'TradeSkillMaster_AppHelper' addon directory
            ]
        },
    ),
    GameBackup(
        id='wow_weakauras',
        # root='/mnt/c/Users/david/AppData/Roaming',
        root=game_root_dir,
        name='weakauras-companion',
        # setting=' ',
        # setting_opts=['--include=config.json', '--exclude=*'],
        options={
            'only': [
                'config.json',  # settings
            ],
        },
    ),
    GameBackup(
        id='wow_project_ascension',
        root=game_c_root_dir,
        name=sh.join_path('Ascension Launcher', 'resources', 'client'),
        screenshot='Screenshots',
        options={
            'only': [
                'Screenshots/*',
                'WTF/*',  # settings (save states)
                'Interface/AddOns/*',  # addons
            ],
            'exclude':[
                r'.*\.bak$',  # ignore setting files with '.bak' extension
                r'.*\.old$',  # ignore setting files with '.old' extension
                r'.*Blizzard_.*',  # ignore the 'Blizzard_*' addon directory
            ]
        },
    ),
    GameBackup(
        id='yiffalicious',
        # root='/mnt/c/Users/david/AppData/Roaming',
        root=game_root_dir,
        name='yiffalicious',
        screenshot='screenshots',
        # setting='interactions/favorites',
        options={
            'only': [
                'screenshots/*',
                'interactions/favorites/*',  # settings
            ],
        },
    ),

    # --- Covered by OneDrive ---
    # overwatch
    # --- Covered by Steam ---
    # *most other games
]

# Filter backup details to only the active games
game_backups: List[GameBackup] = [game for game in game_backups_full if game.id in active_games]
