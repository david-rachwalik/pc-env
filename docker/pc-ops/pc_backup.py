#!/usr/bin/env python
"""Command to backup & clean the system platform"""

import argparse

import logging_boilerplate as log
import shell_boilerplate as sh
from app_backup_data import BACKUP_ROOT_DIR, app_backups
from game_backup_data import game_backups

APP_IDS: list[str] = [app.id for app in app_backups]
GAME_IDS: list[str] = [game.id for game in game_backups]
ALL_IDS: list[str] = [*APP_IDS, *GAME_IDS]
ALL_TASKS: list[str] = ["apps", "games", "clean"]


def what_to_run() -> list[str]:
    """Method that determines which task categories to execute based on arguments"""
    if ARGS.only_apps:
        return ["apps"]
    elif ARGS.only_games:
        return ["games"]
    elif ARGS.only_clean:
        return ["clean"]
    else:
        return ALL_TASKS


def backup_system(tasks: list[str], run_ids: list[str]):
    """Method that backs up important application and game files"""

    # --- Backup important application files (settings) ---
    if "apps" in tasks:
        for app in app_backups:
            if app.id not in run_ids:
                continue
            LOG.info(f"--- Backing up app: {app.name} ---")

            src = sh.join_path(app.root, app.name)
            dest = sh.join_path(BACKUP_ROOT_DIR, "Apps", app.name)
            LOG.info(f"SRC path: {src}")
            LOG.info(f"DEST path: {dest}")

            if ARGS.dry_run:
                sh.sync_directory(src, dest, "diff", options=app.options)
                continue

            # Perform full backup of apps
            sh.sync_directory(src, dest, options=app.options)
            dirs_removed = sh.remove_empty_directories(dest)
            if dirs_removed:
                LOG.debug(f"empty directories removed: {dirs_removed}")

    # --- Backup important game files (screenshots, settings, addons) ---
    if "games" in tasks:
        for game in game_backups:
            if game.id not in run_ids:
                continue

            # Automatically inject the screenshot path into sync inclusion rules
            if game.screenshot:
                ss_pattern = f"{game.screenshot}/*"
                if not game.options:
                    game.options = {"only": []}
                if "only" not in game.options:
                    game.options["only"] = []

                if ss_pattern not in game.options["only"]:
                    game.options["only"].append(ss_pattern)

            if not game.options:
                continue
            LOG.info(f"--- Backing up game: {game.name} ---")

            src = sh.join_path(game.root, game.name)
            dest = sh.join_path(BACKUP_ROOT_DIR, "Games", game.name)
            LOG.info(f"SRC path: {src}")
            LOG.info(f"DEST path: {dest}")

            if ARGS.dry_run:
                sh.sync_directory(src, dest, "diff", options=game.options)
                continue

            # Perform full backup of games
            sh.sync_directory(src, dest, options=game.options)
            dirs_removed = sh.remove_empty_directories(dest)
            if dirs_removed:
                LOG.debug(f"empty directories removed: {dirs_removed}")

            # # Clear source screenshot directory
            # if game.screenshot:
            #     ss_path = sh.join_path(src, game.screenshot)
            #     sh.delete_directory(ss_path)


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
    # use "--id-filter" arg to only target certain apps
    run_ids = ARGS.id_filter if ARGS.id_filter else ALL_IDS

    # -------- Backup the system platform --------
    backup_system(tasks, run_ids)


# Initialize the logger
BASENAME = "pc_backup"
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
# backup --debug
# backup --only-apps
# backup --id-filter=elite_dangerous --id-filter=terraria

# export PYTHONPATH="$HOME/Repos/pc-env/python/modules:$HOME/Repos/pc-env/python/modules/boilerplates"
# python3 ~/Repos/pc-env/python/commands/pc_backup.py --dry-run --debug
