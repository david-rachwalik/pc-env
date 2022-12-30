#!/usr/bin/env python
"""Command to backup & clean the system platform"""

import argparse
import os
from typing import List

import logging_boilerplate as log
import shell_boilerplate as sh
from app_backup_data import app_backups
from game_backup_data import game_backups

APP_IDS: List[str] = [app.id for app in app_backups]
GAME_IDS: List[str] = [game.id for game in game_backups]
ALL_IDS: List[str] = [*APP_IDS, *GAME_IDS]
ALL_TASKS: List[str] = ['apps', 'games', 'clean']


def what_to_run() -> List[str]:
    """Method that ensures second path provided keeps the same directory name as the first.  This may add an extra directory level."""
    if ARGS.only_apps:
        return ['apps']
    elif ARGS.only_games:
        return ['games']
    elif ARGS.only_clean:
        return ['clean']
    else:
        return ALL_TASKS


def keep_dir_name(path1: str, path2: str) -> str:
    """Method that ensures second path provided keeps the same directory name as the first.  This may add an extra directory level."""
    basename = sh.path_basename(path1)
    if keep_dir_name and sh.path_basename(path2) != basename:
        return sh.join_path(path2, basename)
    return path2


# https://stackoverflow.com/questions/47093561/remove-empty-folders-python
def remove_empty_directories(root) -> List[str]:
    """Method that recursively walks backward through subdirectories to remove empty directories"""
    removed_dirs: List[str] = []

    for (current_dir, subdirs, files) in os.walk(root, topdown=False):
        if files:
            continue  # skip directory with files
        # LOG.debug(f'current_dir: {current_dir}')

        still_has_subdirs = False
        for subdir in subdirs:
            # LOG.debug(f'subdir: {subdir}')
            if os.path.join(current_dir, subdir) not in removed_dirs:
                still_has_subdirs = True
            # LOG.debug(f'still_has_subdirs: {still_has_subdirs}')

        if not still_has_subdirs:
            os.rmdir(current_dir)
            removed_dirs.append(current_dir)

    # LOG.debug(f'empty directories removed: {removed_dirs}')
    return removed_dirs


def run_ccleaner():
    """Method that runs CCleaner silently, using the current set of saved options in Custom Clean to clean the PC.  Does not run the Registry Cleaner."""
    # https://www.ccleaner.com/docs/ccleaner/advanced-usage/command-line-parameters
    # https://gist.github.com/theinventor/7b9f2e1f96420291db28592727ede8d3
    app_dir = sh.environment_variable('ProgramFiles')  # C:\Program Files
    ccleaner_exe = sh.join_path(app_dir, 'CCleaner', 'CCleaner64.exe')
    command = [
        'Start-Process',
        '-FilePath',
        f'\'{ccleaner_exe}\'',  # apostrophe wrapper for space in 'Program Files'
        '-ArgumentList',
        '/AUTO'
    ]
    LOG.debug(f'command: {command}')
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, ARGS.debug)


# ------------------------ Main program ------------------------

def main():
    """Method that handles command logic"""
    allowed_ids = ARGS.id_filter if ARGS.id_filter else ALL_IDS
    backup_root = sh.join_path('D:\\', 'OneDrive', 'Backups')
    tasks = what_to_run()

    # -------- Backup the system platform --------

    # --- Backup important application files (settings) ---
    if 'apps' in tasks:
        # LOG.debug(f'app_ids: {app_ids}')
        for APP in app_backups:
            if APP.id not in allowed_ids:
                continue
            LOG.info(f'--- Backing up app: {APP.name} ---')

            SRC = sh.join_path(APP.root, APP.name)
            DEST = sh.join_path(backup_root, 'Apps_test', APP.name)  # TODO: change after testing
            LOG.info(f'SRC path: {SRC}')
            LOG.info(f'DEST path: {DEST}')
            # RESULT = sh.sync_directory(SRC, DEST, 'diff', options=APP.options)
            RESULT = sh.sync_directory(SRC, DEST, options=APP.options)
            # LOG.debug(f'sync_directory RESULT: {RESULT}')

            # NOTE: if sync_directory() action is 'diff', comment out line below
            DIR_REMOVED = remove_empty_directories(DEST)
            LOG.debug(f'empty directories removed: {DIR_REMOVED}')

    # --- Backup important game files (screenshots, settings, addons) ---
    if 'games' in tasks:
        # LOG.debug(f'game_ids: {game_ids}')
        for GAME in game_backups:
            if GAME.id not in allowed_ids:
                continue  # skip id's not provided to 'filter_id' (or in the backup data)
            if not GAME.options:
                continue  # skip games listed without backup options
            LOG.info(f'--- Backing up game: {GAME.name} ---')

            SRC = sh.join_path(GAME.root, GAME.name)
            DEST = sh.join_path(backup_root, 'Games_test', GAME.name)  # TODO: change after testing
            LOG.info(f'SRC path: {SRC}')
            LOG.info(f'DEST path: {DEST}')
            # RESULT = sh.sync_directory(SRC, DEST, 'diff', options=GAME.options)
            RESULT = sh.sync_directory(SRC, DEST, options=GAME.options)
            # LOG.debug(f'sync_directory RESULT: {RESULT}')

            # NOTE: if sync_directory() action is 'diff', comment out line below
            DIR_REMOVED = remove_empty_directories(DEST)
            LOG.debug(f'empty directories removed: {DIR_REMOVED}')

            # Clear source screenshot directory
            if GAME.screenshot:
                ss_path = sh.join_path(SRC, GAME.screenshot)
                sh.delete_directory(ss_path)

    # --- Clean the system platform / health check ---
    if 'clean' in tasks:
        LOG.info('--- Cleaning system platform ---')
        run_ccleaner()

    # TODO: work on script to restore settings and addons


# Initialize the logger
BASENAME = 'pc_clean'
LOG: log.Logger = log.get_logger(BASENAME)
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules

if __name__ == '__main__':
    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--log-path', default='')
        parser.add_argument('--id-filter', action='append', choices=ALL_IDS)  # most reliable list approach
        parser.add_argument('--only-apps', action='store_true')
        parser.add_argument('--only-games', action='store_true')
        parser.add_argument('--only-clean', action='store_true')
        return parser.parse_args()
    ARGS = parse_arguments()

    # Configure the logger
    LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)

    LOG.debug(f'ARGS: {ARGS}')
    LOG.debug('------------------------------------------------')

    main()

    # If we get to this point, assume all went well
    LOG.debug('------------------------------------------------')
    LOG.debug('--- end point reached :3 ---')
    sh.exit_process()

    # --- Usage Example ---
    # pc_clean --filter_id=elite_dangerous --filter_id=terraria
    # pc_clean --only-apps
