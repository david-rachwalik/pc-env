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


app_root_dir = sh.environment_get('AppData')  # %UserProfile%/AppData/Roaming

app_backups: List[AppBackup] = [
    AppBackup(
        id='handbrake',
        root=app_root_dir,
        name='HandBrake',
        # setting_opts=['--include=presets.json', '--include=settings.json', '--exclude=*'],
        options={
            'only': ['presets.json', 'settings.json'],
        },
    ),
    AppBackup(
        id='obs',
        root=app_root_dir,
        name='obs-studio',
        # Test Command: rsync -a --dry-run --verbose --exclude=*.bak --include=global.ini --include=basic/ --include=basic/**/ --include=basic/**/* --exclude=* /mnt/c/Users/david/AppData/Roaming/obs-studio/ /mnt/d/OneDrive/Backups/Apps/obs-studio
        # setting_opts=['--exclude=*.bak', '--include=global.ini', '--include=basic/',
        #               '--include=basic/**/', '--include=basic/**/*', '--exclude=*'],
        options={
            'only': ['global.ini', 'basic/*'],
        },
    ),
    AppBackup(
        id='voicemeeter',
        root=sh.join_path(sh.environment_get('Home'), 'Documents'),
        name='Voicemeeter',
        options={
            'only': ['VoicemeeterProfile.xml'],
        },
    ),
    AppBackup(
        id='vscode',
        root=app_root_dir,
        name=sh.join_path('Code', 'User'),
        # setting_opts=['--include=settings.json', '--include=snippets/', '--exclude=*'],
        options={
            # 'only': ['settings.json', 'snippets/*'],
            'only': ['settings.json'],
        },
    ),
]
