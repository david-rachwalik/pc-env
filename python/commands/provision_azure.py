#!/usr/bin/env python
"""Command to configure Azure environment defaults"""
# based on /ansible_playbooks/roles/azure/configure/tasks/main.yml
# based on /ansible_playbooks/inventories/main/group_vars/all/configuration.yml
# https://docs.microsoft.com/en-us/cli/azure/authenticate-azure-cli

import argparse
from typing import List

import logging_boilerplate as log
import shell_boilerplate as sh

# -------- Provision Azure --------


# --- Configure Azure environment ---


def default_subscription(subscription: str):
    """Method that sets the currently active Azure subscription"""
    # https://docs.microsoft.com/en-us/cli/azure/account#az-account-set
    command: List[str] = ["az", "account", "set", f'--subscription="{subscription}"']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, ARGS.debug)


# Eliminates the need to pass "--organization" into "az devops" commands
def default_devops_organization(organization: str):
    """Method that sets the default Azure organization"""
    az_repo = f"https://dev.azure.com/{organization}"
    # https://docs.microsoft.com/en-us/cli/azure/devops#az-devops-configure
    command: List[str] = [
        "az",
        "devops",
        "configure",
        "--defaults",
        f'organization="{az_repo}"',
    ]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, ARGS.debug)


def default_location(location: str):
    """Method that sets the default Azure location"""
    # https://docs.microsoft.com/en-us/cli/azure/reference-index#az-configure
    command: List[str] = ["az", "configure", "--defaults", f'location="{location}"']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, ARGS.debug)


def default_resource_group(resource_group: str):
    """Method that sets the default Azure resource group"""
    command: List[str] = ["az", "configure", "--defaults", f'group="{resource_group}"']
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, ARGS.debug)


# ------------------------ Main program ------------------------

ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
BASENAME = "provision_azure"
LOG: log.Logger = log.get_logger(BASENAME)  # Initialize the logger

if __name__ == "__main__":

    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        # --- Account defaults ---
        parser.add_argument("--tenant", "-t", default="davidrachwalikoutlook")
        parser.add_argument("--organization", "-o", default="david-rachwalik")
        parser.add_argument("--subscription", "-s", default="Pay-As-You-Go")
        # az account list-locations
        parser.add_argument("--location", "-l", default="southcentralus")
        parser.add_argument("--resource-group", "-g", default="")
        return parser.parse_args()

    ARGS = parse_arguments()

    # Configure the main logger
    LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)
    # Configure additional loggers
    if ARGS.debug:
        # Configure the shell_boilerplate logger
        _sh_log = log.get_logger("shell_boilerplate")
        log.set_handlers(_sh_log, LOG_HANDLERS)
        sh.ARGS.debug = ARGS.debug

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("--------------------------------------------------------")

    # --- Configure Azure environment ---
    default_subscription(ARGS.subscription)
    default_devops_organization(ARGS.organization)
    default_location(ARGS.location)
    # default_resource_group(ARGS.resource_group)

    # If we get to this point, assume all went well
    LOG.debug("--------------------------------------------------------")
    LOG.info("--- Completed provisioning of Azure ---")
    sh.exit_process()
