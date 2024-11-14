#!/usr/bin/env python
"""Common business logic for Git interactions"""

# --- Global Git Commands ---
# Repository (bare/work):       repo_exists, repo_create
# Working Directory:            work_remote, work_status, work_commit, work_push
# - meta reference:             ref_head, ref_heads, ref_remotes, ref_tags
# - branch:                     branch_validate, branch_exists, branch_create, branch_switch, branch_delete
# - pull methods:               work_fetch, work_merge, work_rebase, work_reset

import argparse
from typing import List, Optional, Tuple

import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Global Commands ------------------------

# --- Repository (bare/work) Commands ---


def repo_exists(path: str, bare: bool = False) -> bool:
    """Method that verifies repository exists"""
    result: bool = False
    if bare:
        if sh.path_exists(path, "d"):
            command: List[str] = ["git", "rev-parse", "--is-bare-repository"]
            sh.print_command(command)
            process = sh.run_subprocess(command, path)
            # sh.log_subprocess(LOG, process, debug=ARGS.debug)
            result = process.returncode == 0 and process.stdout == "true"
    else:
        work_repo_dir = sh.join_path(path, ".git")
        result = sh.path_exists(work_repo_dir, "d")
    return result


# Initialize the repository
def repo_create(path: str, bare: bool = False) -> Tuple[bool, bool]:
    """Method that creates a repository"""
    command: List[str] = ["git", "init"]
    if bare:
        sh.create_directory(path)  # Directory must exist prior
        command.append("--bare")
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed: bool = (
        process.returncode != 0
        and "Reinitialized existing Git repository" not in process.stdout
    )
    changed: bool = not failed and "skipped, since" not in process.stdout
    return (not failed, changed)


# --- Repository (work) Commands ---


# Ensure remote path links to bare repository
def work_remote(path: str, remote_path: str, remote_alias: str = "origin") -> bool:
    """Method that sets a remote path for the repository"""
    failed: bool = False
    # Check local repository for remote alias
    command: List[str] = ["git", "config", "--get", f"remote.{remote_alias}.url"]
    process = sh.run_subprocess(command, path)
    if not process.stdout:
        # Repository is missing remote path, adding...
        LOG.warning(
            f"Remote ({remote_alias}) for local repository is missing, adding..."
        )
        command = ["git", "remote", "add", remote_alias, remote_path]

        sh.print_command(command)
        process = sh.run_subprocess(command, path)
        failed = (
            process.returncode != 0
            and f"remote {remote_alias} already exists" not in process.stderr
        )
        LOG.info("Successfully added remote path for local repository!")

    elif process.stdout != remote_path:
        # Repository has outdated remote path, updating...
        LOG.warning(
            f"Remote ({remote_alias}) for local repository is outdated, updating..."
        )
        command = ["git", "remote", "set-url", remote_alias, remote_path]

        sh.print_command(command)
        process = sh.run_subprocess(command, path)
        failed = (
            process.returncode != 0
            and f"remote {remote_alias} already exists" not in process.stderr
        )
        LOG.info("Successfully updated remote path for local repository!")

    # don't be tempted to remove the copy-paste job above; they only occur in 2/3 conditionals, not the else condition
    return not failed


def work_status(path: str) -> bool:
    """Method that checks the working directory status of a repository"""
    command: List[str] = ["git", "status"]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    is_clean: bool = "nothing to commit, working directory clean" in process.stdout
    return is_clean


def work_commit(
    path: str, message: str = "auto-commit", initial: bool = False
) -> Tuple[bool, bool]:
    """Method that commits the working directory of a repository"""
    if not initial:
        # Stage working directory; copies files into '.git' directory
        # 'git add' detects all changes; 'git commit -a' only detects modified/deleted
        command = ["git", "add", "--all", "."]
        sh.print_command(command)
        process = sh.run_subprocess(command, path)
        # sh.log_subprocess(LOG, process, debug=ARGS.debug)

        # Commit the staged files
        command = ["git", "commit", f"-m '{message}'"]
        sh.print_command(command)
        process = sh.run_subprocess(command, path)
        # sh.log_subprocess(LOG, process, debug=ARGS.debug)
        failed = (
            process.returncode != 0
            and "nothing to commit (working directory clean)" not in process.stdout
        )
        changed = (
            not failed
            and "nothing to commit (working directory clean)" not in process.stdout
        )
        return (not failed, changed)  # (succeeded, changed)
    else:
        # Initial commit so 'master' branch exists; helps prevent dangling HEAD refs
        # - HEAD points to 'refs/heads/master' after 'git init'
        # - however, there's no true 'master' branch until the first commit
        command = ["git", "commit", "--allow-empty", f"-m 'Initial {message}'"]
        sh.print_command(command)
        process = sh.run_subprocess(command, path)
        return (True, True)  # (succeeded, changed)


# TODO: Set upstream (-u) on initial push; streamlines fetch
def work_push(path: str, version: str = "master", remote_alias: str = "origin"):
    """Method that pushes the commits of a repository"""
    command: List[str] = ["git", "push", remote_alias, version]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed = process.returncode != 0 and "Everything up-to-date" not in process.stderr
    changed = not failed and "Everything up-to-date" not in process.stderr
    return (not failed, changed)


# --- Repository Metadata Reference Commands ---


# Trim extra apostrophes; expected format to validate against
def _ref_formatter(in_list: List[str]) -> List[str]:
    # LOG.debug(f"(_ref_formatter): in_list: {in_list}")
    results: List[str] = [i.strip("'") for i in in_list]
    # LOG.debug(f"(_ref_formatter): results: {results}")
    return results


def ref_head(path: str) -> str:
    """Method that fetches the branch name of a repository"""
    # command: List[str] = ["git", "show-ref", "--head"]
    command: List[str] = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    result: str = process.stdout if (process.returncode == 0) else ""
    return result


# git for-each-ref --format='%(refname:short)' refs/heads
# git show-ref --heads      # decent but no formatting and rc=1 when empty
def ref_heads(path: str) -> List[str]:
    """Method that lists the branch names of a repository"""
    command: List[str] = [
        "git",
        "for-each-ref",
        "--format='%(refname:short)'",
        "refs/heads",
    ]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    stdout_lines: List[str] = process.stdout.splitlines()
    # LOG.debug(f"(ref_heads): stdout_lines: {stdout_lines}")
    results: List[str] = _ref_formatter(stdout_lines)
    return results


# git for-each-ref --format='%(refname:short)' refs/remotes
# 'git for-each-ref' has better formatting than 'git branch -r'
def ref_remotes(path: str) -> List[str]:
    """Method that lists the remote names of a repository"""
    command: List[str] = [
        "git",
        "for-each-ref",
        "--format='%(refname:short)'",
        "refs/remotes",
    ]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    stdout_lines: List[str] = process.stdout.splitlines()
    # LOG.debug(f"(ref_remotes): stdout_lines: {stdout_lines}")
    results: List[str] = _ref_formatter(stdout_lines)
    return results


# git for-each-ref --format='%(refname:short)' refs/tags
# git show-ref --tags       # decent but no formatting and rc=1 when empty
def ref_tags(path: str) -> List[str]:
    """Method that lists the tags of a repository"""
    command: List[str] = [
        "git",
        "for-each-ref",
        "--format='%(refname:short)'",
        "refs/tags",
    ]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    stdout_lines: List[str] = process.stdout.splitlines()
    # LOG.debug(f"(ref_tags): stdout_lines: {stdout_lines}")
    results: List[str] = _ref_formatter(stdout_lines)
    return results


# --- Repository (work) Branch Commands ---


# Validate version meets Git-allowed reference name rules
def branch_validate(path: str, version: str = "master") -> bool:
    """Method that validates the branch of a repository"""
    failed: bool = False
    if version == "HEAD":
        return failed
    command: List[str] = ["git", "check-ref-format", "--branch", version]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed = process.returncode != 0 and "not a valid branch name" not in process.stderr
    return not failed


# Providing 'remote_alias' will search in remotes instead of heads
def branch_list(path: str, remote_alias: str = "") -> List[str]:
    """Method that lists the branch names of a repository"""
    # Determine which metadata to check for branch list
    ref_method = ref_remotes if remote_alias else ref_heads
    branch_results: List[str] = ref_method(path)
    ref_descriptor: str = "remote" if remote_alias else "local"
    LOG.debug(f"branches: ({ref_descriptor}): {branch_results}")
    return branch_results


# Providing 'remote_alias' will search in remotes instead of heads
# - 'branches' expects list of strings; omit to automatically call branch_list
def branch_exists(
    path: str,
    version: str = "master",
    remote_alias: str = "",
    branches: Optional[List[str]] = None,
) -> bool:
    """Method that verifies whether a branch exists in a repository"""
    remote_branch: str = f"{remote_alias}/{version}"
    branch_use_name: str = remote_branch if remote_alias else version
    # Gather cache of branch names
    if isinstance(branches, list):
        branch_results = branches
    else:
        branch_results = branch_list(path, remote_alias)
    # Check branch version exists in branch list
    # LOG.debug(f"(branch_exists): branches: {branch_results}")
    is_found = branch_use_name in branch_results
    LOG.debug(f"(branch_exists): branch '{branch_use_name}' is found: {is_found}")
    return is_found


def branch_create(path: str, version: str = "master") -> Tuple[bool, bool]:
    """Method that creates a branch in the repository"""
    # 'git branch --force' resets the branch's HEAD (not wanted)
    command: List[str] = ["git", "branch", version]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed: bool = process.returncode != 0 and "already exists" not in process.stderr
    changed: bool = not failed and "already exists" not in process.stderr
    # LOG.debug(f"(branch_create): succeeded: {not failed}, changed: {changed}")
    return (not failed, changed)


# TODO: option to call exists and create
def branch_switch(
    path: str, version: str = "master", remote_alias: str = ""
) -> Tuple[bool, bool]:
    """Method that creates a branch in the repository"""
    remote_branch: str = f"{remote_alias}/{version}"
    branch_use_name: str = remote_branch if remote_alias else version
    command: List[str] = ["git", "checkout", branch_use_name]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed: bool = process.returncode != 0
    changed: bool = not failed and "Already on" not in process.stderr
    return (not failed, changed)


# Supports either local or remote paths
def branch_delete(path: str, version: str = "master") -> Tuple[bool, bool]:
    """Method that deletes a branch from the repository"""
    command: List[str] = ["git", "branch", "-D", version]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed: bool = process.returncode != 0
    changed: bool = not failed and "Deleted branch" in process.stdout
    LOG.debug(f"(branch_delete): succeeded: {not failed}, changed: {changed}")
    return (not failed, changed)


# --- Repository (work) Pull Commands ---


# Fetch the latest meta data; increases '.git' directory size
# Consider 'git fetch --all' https://www.atlassian.com/git/tutorials/syncing/git-fetch
def work_fetch(path: str, remote_alias: str = "origin") -> Tuple[bool, bool]:
    """Method that fetches the contents of a remote repository"""
    command: List[str] = ["git", "fetch", "--prune", remote_alias]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    failed: bool = process.returncode != 0 and "find remote ref" not in process.stdout
    changed: bool = (
        not failed
        and "find remote ref" not in process.stdout
        and "Everything up-to-date" not in process.stderr
    )
    return (not failed, changed)


# other pull_type choice is 'theirs'; message for potential merge commit
def work_merge(
    path: str,
    version: str = "master",
    remote_alias: str = "",
    message: str = "auto-merge",
    fast_forward: bool = True,
    pull_type: str = "ours",
) -> Tuple[bool, bool]:
    """Method that merges commits into the current branch of a remote repository"""
    # Merge pull branch (auto-resolve)
    remote_branch: str = f"{remote_alias}/{version}"
    branch_use_name: str = remote_branch if remote_alias else version
    command: List[str] = ["git", "merge", branch_use_name]
    if not fast_forward:
        command.append("--no-ff")
    command.extend(
        ["--strategy=recursive", f"--strategy-option={pull_type}", f"-m '{message}'"]
    )
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed: bool = process.returncode != 0
    changed: bool = (
        not failed
        and "Already uptodate" not in process.stdout
        and "Already up-to-date" not in process.stdout
    )
    return (not failed, changed)


# Rebase replays commits from currently active branch onto 'version' parameter target branch
# - automatically uses default of --strategy='recursive' --strategy-option='theirs'
# - ours/theirs is reverse of merge; theirs is currently active branch - ours is target branch
# - 'remote_alias' parameter not implemented so rebase is only used for local work (e.g. feature branch)
def work_rebase(path: str, version: str = "master") -> Tuple[bool, bool]:
    """Method that appends a sequence of commits to the current branch of a remote repository"""
    # Merge pull branch (auto-resolve)
    command: List[str] = ["git", "rebase", version]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    failed: bool = process.returncode != 0
    changed: bool = not failed and "is up to date" not in process.stdout
    return (not failed, changed)


# Reset branch to latest (auto-resolve)
def work_reset(path: str, version: str = "master", remote_alias: str = "") -> bool:
    """Method that resets the current branch of a remote repository"""
    remote_branch: str = f"{remote_alias}/{version}"
    branch_use_name: str = remote_branch if remote_alias else version
    command: List[str] = ["git", "reset", "--hard", branch_use_name]
    sh.print_command(command)
    process = sh.run_subprocess(command, path)
    # sh.log_subprocess(LOG, process, debug=ARGS.debug)
    return process.returncode == 0


# ------------------------ Main Program ------------------------

# Initialize the logger
BASENAME = "git_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: log.Logger = log.get_logger(BASENAME)

if __name__ == "__main__":

    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
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
# python ~/.local/lib/python3.6/site-packages/git_boilerplate.py --debug --test=subprocess
