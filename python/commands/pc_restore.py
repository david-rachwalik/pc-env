#!/usr/bin/env python
"""Command to restore important files on the system platform"""

import argparse
from typing import List

import logging_boilerplate as log
import shell_boilerplate as sh
from app_backup_data import app_backups
from game_backup_data import game_backups

APP_IDS: List[str] = [app.id for app in app_backups]
GAME_IDS: List[str] = [game.id for game in game_backups]
ALL_IDS: List[str] = [*APP_IDS, *GAME_IDS]
ALL_TASKS: List[str] = ["apps", "games"]


def what_to_run() -> List[str]:
    """Method that ensures second path provided keeps the same directory name as the first.  This may add an extra directory level."""
    if ARGS.only_apps:
        return ["apps"]
    elif ARGS.only_games:
        return ["games"]
    else:
        return ALL_TASKS


def keep_dir_name(path1: str, path2: str) -> str:
    """Method that ensures second path provided keeps the same directory name as the first.  This may add an extra directory level."""
    basename = sh.path_basename(path1)
    if keep_dir_name and sh.path_basename(path2) != basename:
        return sh.join_path(path2, basename)
    return path2


# ------------------------ Main program ------------------------


def main():
    """Method that handles command logic"""
    tasks = what_to_run()
    run_ids = ARGS.id_filter if ARGS.id_filter else ALL_IDS

    # -------- Backup the system platform --------

    # --- Backup important application files (settings) ---
    if "apps" in tasks:
        # LOG.debug(f'app_ids: {app_ids}')
        for APP in app_backups:
            if APP.id not in run_ids:
                continue
            LOG.info(f"--- Restoring app: {APP.name} ---")

            # SRC & DEST flipped from 'pc_clean'
            SRC = sh.join_path(ARGS.backup_root, "Apps", APP.name)
            DEST = sh.join_path(APP.root, APP.name)
            LOG.info(f"SRC path: {SRC}")
            LOG.info(f"DEST path: {DEST}")
            if ARGS.test_run:
                RESULT = sh.sync_directory(SRC, DEST, "diff", options=APP.options)
            else:
                RESULT = sh.sync_directory(SRC, DEST, options=APP.options)
            # LOG.debug(f'sync_directory RESULT: {RESULT}')

    # --- Backup important game files (screenshots, settings, addons) ---
    if "games" in tasks:
        # LOG.debug(f'game_ids: {game_ids}')
        for GAME in game_backups:
            if GAME.id not in run_ids:
                continue  # skip id's not provided to 'filter_id' (or in the backup data)
            if not GAME.options:
                continue  # skip games listed without backup options
            LOG.info(f"--- Restoring game: {GAME.name} ---")

            # Ignore screenshots during restore
            ignore_options = ["Screenshots/*", "screenshots/*"]

            # SRC & DEST flipped from 'pc_clean'
            SRC = sh.join_path(ARGS.backup_root, "Games", GAME.name)
            DEST = sh.join_path(GAME.root, GAME.name)
            LOG.info(f"SRC path: {SRC}")
            LOG.info(f"DEST path: {DEST}")
            if ARGS.test_run:
                RESULT = sh.sync_directory(SRC, DEST, "diff", options=GAME.options, ignore=ignore_options)
            else:
                RESULT = sh.sync_directory(SRC, DEST, options=GAME.options, ignore=ignore_options)
            # LOG.debug(f'sync_directory RESULT: {RESULT}')

            # NEVER clear source screenshot directory for restore


# Initialize the logger
BASENAME = "pc_restore"
LOG = log.get_logger(BASENAME)
ARGS = argparse.Namespace()  # for external modules

if __name__ == "__main__":

    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        # parser.add_argument('--backup-root', default='D:\\OneDrive\\Backups')
        parser.add_argument("--backup-root", default="/mnt/d/OneDrive/Backups")
        parser.add_argument("--test-run", action="store_true")
        parser.add_argument("--only-apps", action="store_true")
        parser.add_argument("--only-games", action="store_true")
        parser.add_argument("--id-filter", action="append", choices=ALL_IDS)  # most reliable list approach
        return parser.parse_args()

    ARGS = parse_arguments()

    # Configure the logger
    LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("------------------------------------------------")

    main()

    # If we get to this point, assume all went well
    LOG.debug("------------------------------------------------")
    LOG.debug("--- end point reached :3 ---")
    sh.exit_process()


# :: Usage Example ::
# pc_restore --debug
# pc_restore --only-apps
# pc_restore --id-filter=elite_dangerous --id-filter=terraria
