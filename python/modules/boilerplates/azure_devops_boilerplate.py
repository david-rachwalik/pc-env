#!/usr/bin/env python
"""Common logic for Python Azure DevOps interactions"""

# --- Global Azure Methods ---
# user:                         user_get, user_list, user_logout, user_login, user_set
# devops:                       devops_config
# devops project:               devops_project_list, devops_project_create

# TODO:
# artifacts:                    artifact_set, artifact_get
# boards:                       board_set, board_get
# pipelines:                    pipeline_set, pipeline_get
# repos:                        repo_set, repo_get

import argparse
from typing import List, Tuple

import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Global Methods ------------------------
# https://learn.microsoft.com/en-us/cli/azure/devops
# https://learn.microsoft.com/en-us/azure/devops/cli
# https://learn.microsoft.com/en-us/azure/devops/cli/quick-reference
# https://colinsalmcorner.com/az-devops-like-a-boss


# --- Account Commands for DevOps ---


# NOT USED: only grabs a temporary token for 5-60 minutes
def account_pat() -> str:
    """Method that requests an access token for Azure DevOps"""
    # https://www.dylanberry.com/2021/02/21/how-to-get-a-pat-personal-access-token-for-azure-devops-from-the-az-cli
    # https://learn.microsoft.com/en-us/azure/healthcare-apis/get-access-token
    azureDevopsResourceId = "499b84ac-1321-427f-aa17-267ca6975798"
    # https://learn.microsoft.com/en-us/cli/azure/account?view=azure-cli-latest#az-account-get-access-token
    command: List[str] = [
        "az",
        "account",
        "get-access-token",
        f"--resource={azureDevopsResourceId}",
        "--query=accessToken",
    ]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    token: str = process.stdout if (process.returncode == 0) else ""
    return token


# NOT USED: opted to pipe PAT into 'az devops login' so it persists across terminals
def environment_pat(devops_pat: str):
    """Method that sets environment variable for Azure DevOps PAT"""
    # --- Environment Variables, personal access token (PAT) ---
    if devops_pat:
        # ID of an Azure AD application
        sh.environment_set("AZURE_DEVOPS_EXT_PAT", devops_pat)


def save_pat(path: str, content: str):
    """Method that saves Azure DevOps personal access token (PAT) to file"""
    # Handle previous credentials if found
    if sh.path_exists(path, "f"):
        backup_path = sh.backup_file(path)
    LOG.debug("storing DevOps PAT...")
    sh.write_file(path, content)
    LOG.debug("successfully saved DevOps PAT!")


def logout() -> bool:
    """Method that signs out Azure DevOps"""
    command: List[str] = ["az", "devops", "logout"]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# Login with credential (PAT)
def login(pat: str) -> bool:
    """Method that signs into Azure DevOps"""
    command: List[str] = ["echo", pat, "|", "az", "devops", "login"]
    sh.print_command(command)
    # https://learn.microsoft.com/en-us/azure/devops/cli/log-in-via-pat
    # environment_vars = {'AZURE_DEVOPS_EXT_PAT': pat_data}
    # process = sh.run_subprocess(command, env=environment_vars)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# Maybe can look into using HTTP requests for some actions later
# https://learn.microsoft.com/en-us/rest/api/azure/devops/tokens/pats
# https://learn.microsoft.com/en-us/azure/devops/release-notes/2021/sprint-183-update#pat-lifecycle-management-api-private-preview


# --- DevOps User Commands ---
# https://docs.microsoft.com/en-us/cli/azure/ext/azure-devops/devops (login)
# https://docs.microsoft.com/en-us/cli/azure/ext/azure-devops/devops/user


def user_get(pat_data: str, user: str) -> bool:
    """Method that fetches Azure DevOps user profile"""
    command: List[str] = ["az", "devops", "user", "show", f"--user={user}"]
    environment_vars = {"AZURE_DEVOPS_EXT_PAT": pat_data}
    sh.print_command(command)
    # process = sh.run_subprocess(command)
    process = sh.run_subprocess(command, env=environment_vars)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- DevOps Project Commands ---
# https://learn.microsoft.com/en-us/cli/azure/devops/project
# https://docs.microsoft.com/en-us/cli/azure/ext/azure-devops/devops/project


def devops_project_list() -> Tuple[bool, bool]:
    """Method that lists Azure DevOps projects"""
    command: List[str] = ["az", "devops", "project", "list"]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed = process.returncode != 0
    changed = not failed and "is not authorized to access this resource" not in process.stderr
    return (not failed, changed)


# ------------------------ Main Program ------------------------

ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
BASENAME = "azure_devops_boilerplate"
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


# :: Usage Example ::
# python ~/.local/lib/python3.6/site-packages/azure_devops_boilerplate.py --debug
