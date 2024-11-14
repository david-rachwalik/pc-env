#!/usr/bin/env python
"""Common business logic for ASP.NET Core"""

# https://docs.microsoft.com/en-us/ef/core/miscellaneous/cli/dotnet

# --- Global Methods ---
# solution:                     solution_new, solution_project_list, solution_project_add
# project:                      project_new, project_package_list, project_package_add
# user-secrets:                 secrets_init, secrets_list, secrets_set
# identity:                     project_identity_scaffold

# import json, time
import argparse
from typing import List

import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Global Methods ------------------------

# --- Solution Commands ---


def solution_new(solution_dir: str, solution: str) -> bool:
    """Method that creates a new solution"""
    # https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-new
    template: str = "sln"
    command: List[str] = [
        "dotnet",
        "new",
        template,
        f"--output={solution_dir}",
        f"--name={solution}",
    ]
    # command.append("--dry-run")
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


def solution_project_add(solution_file: str, project_file: str) -> bool:
    """Method that adds a project to a solution"""
    # https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-sln
    command: List[str] = ["dotnet", "sln", solution_file, "add", project_file]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- Project Commands ---


# 'dotnet new' automatically calls build and restore
# https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-new
def project_new(tenant: str, project_dir: str, strat: str, framework: str) -> bool:
    """Method that creates a new project"""
    template: str = "webapi" if strat == "api" else "webapp"
    client_id: str = ""
    domain: str = "https://localhost:5001"

    command: List[str] = ["dotnet", "new", template]
    command.append(f"--framework={framework}")
    command.append(f"--output={project_dir}")
    if strat == "identity":
        command.append("--auth=MultiOrg")
        command.append(f"--client-id={client_id}")
    # elif strat == "api" and strat == "identity":
    #     command.append("--auth=SingleOrg")
    #     command.append(f"--client-id={client_id}")
    #     command.append("--tenant=tenant")
    #     command.append(f"--domain={domain}")
    else:
        # command.append("--auth=None")
        command.append(f"--domain={domain}")
    command.append("--org-read-access")

    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    # LOG.debug("Successfully created ASP.NET Core project")
    return process.returncode == 0


# Currently difficult to parse - will eventually have --json option: https://github.com/NuGet/Home/issues/7752
# - TODO: skip attempting to add packages each run when this change occurs
def project_package_list(project_dir: str) -> List[str]:
    """Method that lists the packages in a project"""
    results: List[str] = []
    command: List[str] = ["dotnet", "list", project_dir, "package"]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    # Parse project package list
    if process.returncode == 0 and process.stdout:
        stdout_lines = process.stdout.splitlines()
        for line in stdout_lines:
            line_edit = line.lstrip()
            if line_edit.startswith("> "):
                line_edit_list = line_edit.split()
                results.append(line_edit_list[1])
    results.sort()
    # LOG.debug(f"results: {results}")
    return results


# https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-add
def project_package_add(project_dir: str, package: str) -> bool:
    """Method that adds a package to a project"""
    command: List[str] = ["dotnet", "add", project_dir, "package", package]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- User-Secrets Commands ---
# https://docs.microsoft.com/en-us/aspnet/core/security/app-secrets


def secrets_init(dotnet_dir: str, application: str, project: str) -> bool:
    """Method that initializes user secrets in a project"""
    app_dir: str = sh.join_path(dotnet_dir, application)
    project_path: str = sh.join_path(app_dir, project)
    command: List[str] = ["dotnet", "user-secrets", "init", f"--project={project_path}"]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


def secrets_list(dotnet_dir: str, application: str, project: str) -> bool:
    """Method that lists the user secrets in a project"""
    app_dir: str = sh.join_path(dotnet_dir, application)
    project_path: str = sh.join_path(app_dir, project)
    command: List[str] = ["dotnet", "user-secrets", "list", f"--project={project_path}"]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


def secrets_set(
    dotnet_dir: str, application: str, project: str, secret_key: str, secret_value: str
) -> bool:
    """Method that creates a user secret in a project"""
    app_dir: str = sh.join_path(dotnet_dir, application)
    project_path: str = sh.join_path(app_dir, project)
    command: List[str] = [
        "dotnet",
        "user-secrets",
        "set",
        secret_key,
        secret_value,
        f"--project={project_path}",
    ]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# --- Scaffold Commands ---


# https://docs.microsoft.com/en-us/aspnet/core/fundamentals/tools/dotnet-aspnet-codegenerator
def project_identity_scaffold(project_dir: str) -> bool:
    """Method that scaffolds an identity in a project"""
    command: List[str] = [
        "dotnet",
        "aspnet-codegenerator",
        "identity",
        "--useDefaultUI",
        f"--project={project_dir}",
    ]
    sh.print_command(command)
    process = sh.run_subprocess(command)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# ------------------------ Main Program ------------------------
# Initialize the logger
BASENAME = "dotnet_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: log.Logger = log.get_logger(BASENAME)

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
    LOG_HANDLERS: List[log.LogHandlerOptions] = log.default_handlers(
        ARGS.debug, ARGS.log_path
    )
    log.set_handlers(LOG, LOG_HANDLERS)
    if ARGS.debug:
        # Configure the shell_boilerplate logger
        _sh_log = log.get_logger("shell_boilerplate")
        log.set_handlers(_sh_log, LOG_HANDLERS)
        sh.ARGS.debug = ARGS.debug

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("------------------------------------------------")


# :: Usage Example ::
# python ~/.local/lib/python3.6/site-packages/dotnet_boilerplate.py --debug
