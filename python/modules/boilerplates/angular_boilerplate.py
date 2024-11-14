#!/usr/bin/env python
"""Common logic for Angular commands"""

import argparse
from typing import List

import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Global Methods ------------------------
# https://requests.readthedocs.io
# https://realpython.com/python-requests


# --- Project ---


def project_new(name: str) -> bool:
    """Method that creates an Angular project"""
    command: List[str] = ["ng", "new", name, "--routing", "--style=css"]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    # LOG.debug("process: {process}")
    return process.returncode == 0


# ------------------------ Main Program ------------------------

ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
BASENAME = "angular_boilerplate"
LOG: log.Logger = log.get_logger(BASENAME)  # Initialize the logger

if __name__ == "__main__":
    # Returns argparse.Namespace; to pass into function, use **vars(self.ARGS)
    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        return parser.parse_args()

    ARGS = parse_arguments()

    #  Configure the main logger
    LOG_HANDLERS: List[log.LogHandlerOptions] = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)
    if ARGS.debug:
        # Configure the shell_boilerplate logger
        _sh_log = log.get_logger("shell_boilerplate")
        log.set_handlers(_sh_log, LOG_HANDLERS)
        sh.ARGS.debug = ARGS.debug

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("------------------------------------------------")

    # LOG.debug(f'RESPONSE status code: {RES.status_code}')
    # RESPONSE_SUCCEEDED = bool(RES.status_code == req.codes.ok)
    # LOG.debug(f'RESPONSE status code OK: {RESPONSE_SUCCEEDED}')

    # If we get to this point, assume all went well
    LOG.debug("--------------------------------------------------------")
    LOG.debug("--- end point reached :3 ---")
    sh.exit_process()


# :: Usage Example ::
# app --debug --project="Templates-Angular14-NgrxData" create
