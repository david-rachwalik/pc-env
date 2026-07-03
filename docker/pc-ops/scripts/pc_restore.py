#!/usr/bin/env python
"""Command to restore important files on the system platform"""

import argparse

import logging_boilerplate as log
import shell_boilerplate as sh
from data_apps import app_backups
from data_games import game_backups
from models import PATHS

APP_IDS: list[str] = [app.id for app in app_backups]
GAME_IDS: list[str] = [game.id for game in game_backups]
ALL_IDS: list[str] = [*APP_IDS, *GAME_IDS]
ALL_TASKS: list[str] = ["apps", "games"]


def what_to_run() -> list[str]:
    """Method that determines which task categories to execute based on arguments"""
    if ARGS.only_apps:
        return ["apps"]
    elif ARGS.only_games:
        return ["games"]
    else:
        return ALL_TASKS


def restore_system(tasks: list[str], run_ids: list[str]):
    """Method that restores important application and game files"""

    # Ensure backup drive is actually mounted/accessible
    if not sh.path_exists(PATHS.backups, "d"):
        LOG.error(f"Backup root directory not found: {PATHS.backups}")
        LOG.error(
            "Please ensure your external drive or OneDrive is mounted before restoring."
        )
        return

    # --- Restore important application files (settings) ---
    if "apps" in tasks:
        for app in app_backups:
            if app.id not in run_ids:
                continue
            LOG.info(f"--- Restoring app: {app.id} ---")

            # SRC & DEST flipped from 'pc_clean'
            src = sh.join_path(PATHS.backups, "Apps", app.name)
            dest = sh.join_path(app.root, app.name)
            LOG.info(f"SRC path: {src}")
            LOG.info(f"DEST path: {dest}")

            if ARGS.dry_run:
                sh.sync_directory(src, dest, "diff", options=app.options)
                continue

            # Perform full restore of apps
            sh.sync_directory(src, dest, options=app.options)

    # --- Restore important game files (screenshots, settings, addons) ---
    if "games" in tasks:
        # Ignore screenshots during restore
        # (dirsync ignore accepts regular expressions, not globs)
        ignore_opts = [r".*[Ss]creenshots.*"]

        for game in game_backups:
            if game.id not in run_ids:
                continue  # skip id's not provided
            if not game.options:
                continue  # skip games without backup options
            LOG.info(f"--- Restoring game: {game.id} ---")

            src = sh.join_path(PATHS.backups, "Games", game.name)
            dest = sh.join_path(game.root, game.name)
            LOG.info(f"SRC path: {src}")
            LOG.info(f"DEST path: {dest}")

            if ARGS.dry_run:
                sh.sync_directory(
                    src, dest, "diff", options=game.options, ignore=ignore_opts
                )
                continue

            # Perform full restore of games
            sh.sync_directory(src, dest, options=game.options, ignore=ignore_opts)

            # NEVER clear source screenshot directory for restore


# ------------------------ Main program ------------------------


def parse_arguments():
    """Method that parses arguments provided"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-path", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only-apps", action="store_true")
    parser.add_argument("--only-games", action="store_true")
    parser.add_argument(
        "--id-filter", action="append", choices=ALL_IDS
    )  # most reliable list approach
    return parser.parse_args()


def main():
    """Method that handles command logic"""
    tasks = what_to_run()
    run_ids = ARGS.id_filter if ARGS.id_filter else ALL_IDS

    # -------- Restore the system platform --------
    restore_system(tasks, run_ids)


# Initialize the logger
BASENAME = "pc_restore"
LOG = log.get_logger(BASENAME)
ARGS = argparse.Namespace()  # for external modules

if __name__ == "__main__":
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
# restore --debug
# restore --only-apps
# restore --id-filter=elite_dangerous --id-filter=terraria
