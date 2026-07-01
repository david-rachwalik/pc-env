#!/usr/bin/env python

# Basename: dotnet_boilerplate
# Description: Common business logic for ASP.NET Core
# Version: 1.0.2
# VersionDate: 19 Oct 2021
# https://docs.microsoft.com/en-us/ef/core/miscellaneous/cli/dotnet

# --- Global Methods ---
# solution:                     solution_new, solution_project_list, solution_project_add
# project:                      project_new, project_package_list, project_package_add
# user-secrets:                 secrets_init, secrets_list, secrets_set
# identity:                     project_identity_scaffold

# import json, time
from typing import List

import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Global Methods ------------------------

# --- Solution Commands ---


# https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-new
def solution_new(solution_dir: str, solution: str) -> bool:
    if not (solution_dir and isinstance(solution_dir, str)):
        TypeError("'solution_dir' parameter expected as string")
    if not (solution and isinstance(solution, str)):
        TypeError("'solution' parameter expected as string")
    template: str = "sln"

    command: List[str] = [
        "dotnet",
        "new",
        template,
        "--output={0}".format(solution_dir),
        "--name={0}".format(solution),
    ]
    # command.append("--dry-run")
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


# https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-sln
def solution_project_add(solution_file: str, project_file: str) -> bool:
    if not (solution_file and isinstance(solution_file, str)):
        TypeError("'solution_file' parameter expected as string")
    if not (project_file and isinstance(project_file, str)):
        TypeError("'project_file' parameter expected as string")

    command: List[str] = ["dotnet", "sln", solution_file, "add", project_file]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


# --- Project Commands ---


# 'dotnet new' automatically calls build and restore
# https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-new
def project_new(tenant: str, project_dir: str, strat: str, framework: str) -> bool:
    if not (tenant and isinstance(tenant, str)):
        TypeError("'tenant' parameter expected as string")
    if not (project_dir and isinstance(project_dir, str)):
        TypeError("'project_dir' parameter expected as string")
    if not (strat and isinstance(strat, str)):
        TypeError("'strat' parameter expected as string")
    if not (framework and isinstance(framework, str)):
        TypeError("'framework' parameter expected as string")
    template: str = "webapi" if strat == "api" else "webapp"
    client_id: str = ""
    domain: str = "https://localhost:5001"

    command: List[str] = ["dotnet", "new", template]
    command.append("--framework={0}".format(framework))
    command.append("--output={0}".format(project_dir))
    if strat == "identity":
        command.append("--auth={0}".format("MultiOrg"))
        command.append("--client-id={0}".format(client_id))
    # elif strat == "api" and strat == "identity":
    #     command.append("--auth={0}".format("SingleOrg"))
    #     command.append("--client-id={0}".format(client_id))
    #     command.append("--tenant={0}".format("tenant"))
    #     command.append("--domain={0}".format(domain))
    else:
        # command.append("--auth={0}".format("None"))
        command.append("--domain={0}".format(domain))
    command.append("--org-read-access")

    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    # _log.debug("Successfully created ASP.NET Core project")
    return bool(rc == 0)


# Currently difficult to parse - will eventually have --json option: https://github.com/NuGet/Home/issues/7752
# - TODO: skip attempting to add packages each run when this change occurs
def project_package_list(project_dir: str) -> List[str]:
    if not (project_dir and isinstance(project_dir, str)):
        TypeError("'project_dir' parameter expected as string")
    results: List[str] = []
    command: List[str] = ["dotnet", "list", project_dir, "package"]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    # Parse project package list
    if rc == 0 and stdout:
        stdout_lines = stdout.splitlines()
        for line in stdout_lines:
            line_edit = line.lstrip()
            if line_edit.startswith("> "):
                line_edit_list = line_edit.split()
                results.append(line_edit_list[1])
    results.sort()
    # _log.debug("results: {0}".format(results))
    return results


# https://docs.microsoft.com/en-us/dotnet/core/tools/dotnet-add
def project_package_add(project_dir: str, package: str) -> bool:
    if not (project_dir and isinstance(project_dir, str)):
        TypeError("'project_dir' parameter expected as string")
    if not (package and isinstance(package, str)):
        TypeError("'package' parameter expected as string")
    command: List[str] = ["dotnet", "add", project_dir, "package", package]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    # sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


# --- User-Secrets Commands ---
# https://docs.microsoft.com/en-us/aspnet/core/security/app-secrets


def secrets_init(dotnet_dir: str, application: str, project: str) -> bool:
    if not (dotnet_dir and isinstance(dotnet_dir, str)):
        TypeError("'dotnet_dir' parameter expected as string")
    if not (application and isinstance(application, str)):
        TypeError("'application' parameter expected as string")
    if not (project and isinstance(project, str)):
        TypeError("'project' parameter expected as string")
    app_dir: str = sh.path_join(dotnet_dir, application)
    project_path: str = sh.path_join(app_dir, project)
    command: List[str] = [
        "dotnet",
        "user-secrets",
        "init",
        "--project={0}".format(project_path),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


def secrets_list(dotnet_dir: str, application: str, project: str) -> bool:
    if not (dotnet_dir and isinstance(dotnet_dir, str)):
        TypeError("'dotnet_dir' parameter expected as string")
    if not (application and isinstance(application, str)):
        TypeError("'application' parameter expected as string")
    if not (project and isinstance(project, str)):
        TypeError("'project' parameter expected as string")
    app_dir: str = sh.path_join(dotnet_dir, application)
    project_path: str = sh.path_join(app_dir, project)
    command: List[str] = [
        "dotnet",
        "user-secrets",
        "list",
        "--project={0}".format(project_path),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


def secrets_set(
    dotnet_dir: str, application: str, project: str, secret_key: str, secret_value: str
) -> bool:
    if not (dotnet_dir and isinstance(dotnet_dir, str)):
        TypeError("'dotnet_dir' parameter expected as string")
    if not (application and isinstance(application, str)):
        TypeError("'application' parameter expected as string")
    if not (project and isinstance(project, str)):
        TypeError("'project' parameter expected as string")
    if not (secret_key and isinstance(secret_key, str)):
        TypeError("'secret_key' parameter expected as string")
    if not (secret_value and isinstance(secret_value, str)):
        TypeError("'secret_value' parameter expected as string")
    app_dir: str = sh.path_join(dotnet_dir, application)
    project_path: str = sh.path_join(app_dir, project)
    command: List[str] = [
        "dotnet",
        "user-secrets",
        "set",
        secret_key,
        secret_value,
        "--project={0}".format(project_path),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


# --- Scaffold Commands ---


# https://docs.microsoft.com/en-us/aspnet/core/fundamentals/tools/dotnet-aspnet-codegenerator
def project_identity_scaffold(project_dir: str) -> bool:
    if not (project_dir and isinstance(project_dir, str)):
        TypeError("'project_dir' parameter expected as string")
    command: List[str] = [
        "dotnet",
        "aspnet-codegenerator",
        "identity",
        "--useDefaultUI",
        "--project={0}".format(project_dir),
    ]
    sh.print_command(command)
    (stdout, stderr, rc) = sh.subprocess_run(command)
    sh.subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return bool(rc == 0)


# ------------------------ Main Program ------------------------

# Initialize the logger
basename: str = "dotnet_boilerplate"
args = log.LogArgs()  # for external modules
_log: log._logger_type = log.get_logger(basename)

if __name__ == "__main__":
    # Returns argparse.Namespace; to pass into function, use **vars(self.args)
    def parse_arguments():
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        return parser.parse_args()

    args = parse_arguments()

    #  Configure the main logger
    log_handlers: List[log.LogHandlerOptions] = log.gen_basic_handlers(
        args.debug, args.log_path
    )
    log.set_handlers(_log, log_handlers)
    if args.debug:
        # Configure the shell_boilerplate logger
        _sh_log = log.get_logger("shell_boilerplate")
        log.set_handlers(_sh_log, log_handlers)
        sh.args.debug = args.debug

    _log.debug("args: {0}".format(args))
    _log.debug("------------------------------------------------")

    # --- Usage Example ---
    # python ~/.local/lib/python3.6/site-packages/dotnet_boilerplate.py --debug
