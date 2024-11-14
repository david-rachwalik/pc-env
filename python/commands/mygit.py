#!/usr/bin/env python
"""Command to perform common Git business logic strategies"""

#       *** Actions ***
# push:                 Either pull or create a bare repository; then push
# pull:                 Auto-resolve using 'ours' merge strategy; favors existing changes
# reset:                Disregard existing working directory changes; match files to remote
# status:               Determines whether the work-tree is clean (True) or dirty (False)
# delete:               Removes the specified branch in locl and remote repositories
#       *** Options ***
# --debug:              Enable to display log messages for development
# --force:              Enable to disregard the initialize repository prompt
# --branch:             Arbitrary name of branch to push/pull; default is 'master'
# --remote-alias:       Alias used for bare repo; default is 'origin'
# --remote-path:        Remote, bare repository path (origin)
# --local-path:         Specify where to create work repo; default is current directory
# --gitignore-path:     Location of .gitignore file to use

# from typing import Dict, List, Optional, Tuple
import argparse
from typing import List

import git_boilerplate as bp_git
import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Primary classes/functions ------------------------

# Provide 'remote_path' for bare repo; 'no_create' only applies to bare


class Repository(object):
    """Class to track Git repository actions"""

    def __init__(self, path, remote_path="", no_create=False, force=False):
        # LOG.debug("Init")
        self.path = str(path)
        self.remote_path = str(remote_path) if remote_path else ""
        self.force = bool(force)
        self.is_bare = not bool(self.remote_path)
        self.repo_descriptor = "remote, bare" if self.is_bare else "local, work"

        self.exists = bp_git.repo_exists(self.path, self.is_bare)
        if self.exists:
            LOG.debug(f"Successfully found {self.repo_descriptor} repository")
        else:
            LOG.debug(f"Unable to locate {self.repo_descriptor} repository")
            if not no_create:
                self.create()
            else:
                LOG.error(f"Cannot proceed; missing {self.repo_descriptor} repository")
                sh.fail_process()

    def create(self):
        """Method that initializes a Git repository"""
        # LOG.debug("Init")
        display_path = self.path if (self.is_bare) else f"{self.path}/.git"
        if not self.force:
            response = input(f"Repository not found ({display_path}), initialize?  (y or yes): ")
            if response.lower() not in ["y", "yes"]:
                LOG.info("Exiting without creating repository")
                sh.fail_process()
        else:
            LOG.info(f"Repository not found ({display_path}), initializing...")

        # Initialize the repository
        (self.exists, changed) = bp_git.repo_create(self.path, self.is_bare)
        if self.exists:
            LOG.info("Repository successfully created!")
        else:
            LOG.error(f"Unable to create {self.repo_descriptor} repository")
            sh.fail_process()


class GitController(object):
    """Class that controls a Git repository"""

    def __init__(self):
        # LOG.debug("Init")
        LOG.debug(f"ARGS: {ARGS}")
        LOG.info(f"Git '{ARGS.action}' action detected")
        LOG.debug("--------------------------------------------------------")

        # ------------------------ Bare Repo (remote repository) ------------------------

        # Ensure bare repo exists
        if ARGS.action in ["status", "reset"]:
            LOG.debug(f"skip bare repository check for '{ARGS.action}' action")
        else:
            # fail when not 'push' action and repo is missing
            no_create = ARGS.action != "push"
            self.bare_repository = Repository(ARGS.remote_path, no_create=no_create, force=True)
            LOG.debug(f"bare_repository exists: {self.bare_repository.exists}")

        # ------------------------ Work Repo (local repository) ------------------------

        # Ensure work repo exists
        # fail when not 'push' action and repo is missing
        no_create = ARGS.action != "push"
        self.work_repository = Repository(ARGS.local_path, ARGS.remote_path, no_create=no_create, force=True)
        LOG.debug(f"work_repository exists: {self.work_repository.exists}")

        # Set work repo's remote path to bare repo
        remote_result = bp_git.work_remote(ARGS.local_path, ARGS.remote_path, ARGS.remote_alias)
        if not remote_result:
            LOG.error("Error occurred updating remote path")
            sh.fail_process()

        # Fetch the latest meta data; increases '.git' directory size
        if ARGS.action in ["push", "pull"]:
            bp_git.work_fetch(ARGS.local_path)

        # Update '.gitignore' based on hash check
        if ARGS.action in ["push", "pull"] and len(ARGS.gitignore_path) > 0:
            file_src = ARGS.gitignore_path
            file_dest = sh.join_path(ARGS.local_path, ".gitignore")
            if sh.path_exists(file_dest, "f"):
                hash_result = sh.match_file(file_src, file_dest)
                if not hash_result:
                    LOG.debug("'.gitignore' hashes don't match, updating...")
                    update_result = sh.copy_file(file_src, file_dest)
                    if update_result:
                        LOG.debug("'.gitignore' was successfully updated!")
                    else:
                        LOG.debug("'.gitignore' failed to be updated")
                        sh.fail_process()
                else:
                    LOG.debug("'.gitignore' is already up-to-date")
            else:
                LOG.debug("'.gitignore' is missing, adding...")
                add_result = sh.copy_file(file_src, file_dest)
                if add_result:
                    LOG.debug("'.gitignore' was successfully added!")
                else:
                    LOG.debug("'.gitignore' failed to be added")
                    sh.fail_process()

        # ------------------------ Validation Checks ------------------------

        LOG.debug("---------------- Validation Checks ----------------")

        # Check work-tree status
        work_tree_is_clean = bp_git.work_status(ARGS.local_path)
        LOG.debug(f"work-tree is clean: {work_tree_is_clean}")
        # Gather cache of branch names (fewer queries to refs)
        local_branches = bp_git.branch_list(ARGS.local_path)
        remote_branches = bp_git.branch_list(ARGS.local_path, ARGS.remote_alias)
        # Check for branches in 'refs/heads' and 'refs/remotes'
        master_local_branch_exists = bp_git.branch_exists(ARGS.local_path, master_branch, branches=local_branches)
        master_remote_branch_exists = bp_git.branch_exists(ARGS.local_path, master_branch, ARGS.remote_alias, branches=remote_branches)
        LOG.debug(f"master_local_branch_exists: {master_local_branch_exists}")
        LOG.debug(f"master_remote_branch_exists: {master_remote_branch_exists}")
        stash_local_branch_exists = bp_git.branch_exists(ARGS.local_path, stash_branch, branches=local_branches)
        LOG.debug(f"stash_local_branch_exists: {stash_local_branch_exists}")
        version_local_branch_exists = bp_git.branch_exists(ARGS.local_path, ARGS.branch, branches=local_branches)
        version_remote_branch_exists = bp_git.branch_exists(ARGS.local_path, ARGS.branch, ARGS.remote_alias, branches=remote_branches)
        LOG.debug(f"version_local_branch_exists: {version_local_branch_exists}")
        LOG.debug(f"version_remote_branch_exists: {version_remote_branch_exists}")

        # Fail early when attempting to pull/delete a dirty work-tree
        if ARGS.action in ["pull", "delete"] and not work_tree_is_clean:
            LOG.error(f"Unable to perform '{ARGS.action}' action with dirty work-tree")
            sh.fail_process()

        # Fail early when attempting to delete 'master' branch; assumed to always exist after initial commit
        if ARGS.action == "delete" and ARGS.branch == master_branch:
            LOG.error(f"Unable to delete the '{master_branch}' branch")
            sh.fail_process()

        # Fail early when attempting to pull 'master' or 'version' branch that's missing from bare repo
        if ARGS.action == "pull":
            if not master_remote_branch_exists:
                LOG.error(f"Unable to perform '{ARGS.action}' action; '{ARGS.remote_alias}/{master_branch}' branch not found")
                sh.fail_process()
            if not version_remote_branch_exists:
                LOG.error(f"Unable to perform '{ARGS.action}' action; '{ARGS.remote_alias}/{master_branch}' branch not found")
                sh.fail_process()

        # ------------------------ 'master' branch ------------------------

        LOG.debug("---------------- Master Branch Steps ----------------")

        # 'master' branch should always exist; regardless whether it's the focus of this run
        if ARGS.action in ["push", "pull"] and not master_local_branch_exists:
            if master_remote_branch_exists:
                # Switch to bare repo 'master' branch before any commits
                bp_git.branch_switch(ARGS.local_path, master_branch, ARGS.remote_alias)
                LOG.debug(f"checked out '{ARGS.remote_alias}/{master_branch}' branch")
                master_local_branch_exists = bp_git.branch_create(ARGS.local_path, master_branch)
                LOG.debug(f"created local '{master_branch}' branch from remote '{ARGS.remote_alias}/{master_branch}' branch")
            else:
                # Push initial 'master' branch to remote when not already there
                LOG.warning(f"'{master_branch}' branch is missing, creating initial commit...")
                (commit_succeeded, commit_changed) = bp_git.work_commit(ARGS.local_path, initial=True)
                LOG.info(f"Intial commit for '{master_branch}' branch successfully created!")
                # 'master' branch automatically active after initial commit; explicit checkout unnecessary

                (push_succeeded, push_changed) = bp_git.work_push(ARGS.local_path, master_branch, ARGS.remote_alias)
                LOG.debug(f"initial push to '{ARGS.remote_alias}/{master_branch}' has succeeded: {push_succeeded}")
                # No need to refresh metadata again; push will update references

        # ------------------------ 'my-stash' branch ------------------------

        LOG.debug("---------------- Stash Branch Steps ----------------")

        # When work-tree is dirty, commit the changes to 'my-stash' branch
        if ARGS.action == "push" and version_remote_branch_exists and not work_tree_is_clean:
            LOG.debug("preparing to stash work-tree changes...")

            # Create 'my-stash' branch from local 'master' branch
            bp_git.branch_switch(ARGS.local_path, master_branch)
            LOG.debug(f"checked out '{master_branch}' branch")

            # Check if stash branch already exists, delete if so
            if stash_local_branch_exists:
                LOG.debug(f"previous '{work_tree_is_clean}' branch was detected, removing...")
                bp_git.branch_delete(ARGS.local_path, stash_branch)
                LOG.debug(f"'{work_tree_is_clean}' branch was deleted")

            # Create and checkout 'my-stash' branch to stage and commit those dirty files
            stash_local_branch_exists = bp_git.branch_create(ARGS.local_path, stash_branch)
            bp_git.branch_switch(ARGS.local_path, stash_branch)
            LOG.debug(f"created and checked out '{stash_branch}' branch")
            (commit_succeeded, commit_changed) = bp_git.work_commit(ARGS.local_path)
            LOG.debug(f"commit for '{stash_branch}' branch succeeded: {commit_succeeded}")

            # Verify work-tree status (should always be clean after commit)
            work_tree_is_clean = bp_git.work_status(ARGS.local_path)
            LOG.debug(f"work-tree is clean: {work_tree_is_clean}")

        # ------------------------ 'version' branch ------------------------

        LOG.debug("---------------- Version Branch Steps ----------------")
        # -------- Avoid checkout of branch until work-tree is clean --------

        # Create local 'version' branch if missing
        if ARGS.action in ["push", "pull"]:
            version_branch_just_created = False
            if not version_local_branch_exists:
                if version_remote_branch_exists:
                    # Create local 'version' branch from bare repo
                    bp_git.branch_switch(ARGS.local_path, ARGS.branch, ARGS.remote_alias)
                    LOG.debug(f"checked out '{ARGS.remote_alias}/{ARGS.branch}' branch")
                    version_local_branch_exists = bp_git.branch_create(ARGS.local_path, ARGS.branch)
                    LOG.debug(f"created local '{ARGS.branch}' branch from remote '{ARGS.remote_alias}/{ARGS.branch}' branch")
                else:
                    # Create local 'version' branch from 'master' branch
                    bp_git.branch_switch(ARGS.local_path, master_branch)
                    LOG.debug(f"checked out '{master_branch}' branch")
                    version_local_branch_exists = bp_git.branch_create(ARGS.local_path, ARGS.branch)
                    LOG.debug(f"created local '{ARGS.branch}' branch from '{master_branch}' branch")
                version_branch_just_created = True

                # Verify successfully created 'version' branch
                if not version_local_branch_exists:
                    LOG.error(f"local '{ARGS.branch}' branch still appears to be missing; failed to create")
                    sh.fail_process()

                # Checkout local 'version' branch
                bp_git.branch_switch(ARGS.local_path, ARGS.branch)

            # Commit changes to local 'version' branch; not using 'my-stash' branch because remote 'version' branch is missing
            if ARGS.action == "push":
                # When work-tree is dirty, commit changes to 'version' branch
                if not work_tree_is_clean and not version_remote_branch_exists:
                    (commit_succeeded, commit_changed) = bp_git.work_commit(ARGS.local_path)
                    LOG.debug(f"commit for '{ARGS.branch}' branch succeeded: {commit_succeeded}")
                    # Verify work-tree status (should always be clean after commit)
                    work_tree_is_clean = bp_git.work_status(ARGS.local_path)
                    LOG.debug(f"work_tree_is_clean: {work_tree_is_clean}")

            # Merge remote 'version' branch into local when both exist and local wasn't just created
            if ARGS.action in ["push", "pull"]:
                if version_remote_branch_exists and not version_branch_just_created:
                    # Merge 'version' branch from bare repo into work repo
                    LOG.debug(f"merge '{ARGS.remote_alias}/{ARGS.branch}' branch into local '{ARGS.remote_alias}' branch")
                    (succeeded, changed) = bp_git.work_merge(ARGS.local_path, ARGS.branch, ARGS.remote_alias)
                    LOG.debug(f"'{ARGS.remote_alias}/{ARGS.branch}' branch merge succeeded: {succeeded}")

            # Rebase local 'my-stash' branch onto local 'version' branch
            if ARGS.action == "push" and stash_local_branch_exists:
                bp_git.branch_switch(ARGS.local_path, stash_branch)
                LOG.debug(f"checked out '{stash_branch}' branch")
                LOG.debug(f"rebasing '{stash_branch}' branch onto local '{ARGS.branch}' branch...")
                (succeeded, changed) = bp_git.work_rebase(ARGS.local_path, ARGS.branch)
                LOG.debug(f"'{stash_branch}' branch rebase succeeded: {succeeded}")
                # Checkout local 'version' branch
                bp_git.branch_switch(ARGS.local_path, ARGS.branch)
                # Delete 'my-stash' branch
                bp_git.branch_delete(ARGS.local_path, stash_branch)

        # TODO: other action steps
        if ARGS.action == "reset":
            # Hard reset will also clear any pending (unpushed) commits
            LOG.info("::mock:: reset action")
            # bp_git.work_reset(ARGS.local_path, ARGS.branch, ARGS.remote_alias)

        elif ARGS.action == "delete":
            # Deleting both local and remote branches, no pull steps needed
            LOG.debug(f"deleting '{ARGS.branch}' branch...")
            # Checkout local 'master' branch
            bp_git.branch_switch(ARGS.local_path, master_branch)
            # Delete 'version' branch
            bp_git.branch_delete(ARGS.local_path, ARGS.branch)
            bp_git.branch_delete(ARGS.remote_path, ARGS.branch)
            LOG.debug(f"'{ARGS.branch}' branch deleted")

        elif ARGS.action == "status":
            # Verify work-tree status and display status statement
            work_tree_is_clean = bp_git.work_status(ARGS.local_path)
            LOG.info(f"work_tree_is_clean: {work_tree_is_clean}")

        # Push to bare repo
        if ARGS.action == "push":
            # Push 'version' branch to bare repo
            LOG.debug(f"pushing '{ARGS.branch}' branch to {ARGS.remote_alias}")
            (push_succeeded, push_changed) = bp_git.work_push(ARGS.local_path, ARGS.branch, ARGS.remote_alias)
            LOG.debug(f"'{ARGS.remote_alias}/{ARGS.branch}' branch push has succeeded: {push_succeeded}")
            # No need to refresh metadata again; the push will update references


# ------------------------ Main program ------------------------

master_branch = "master"
stash_branch = "my-stash"

# Initialize the logger
BASENAME = "mygit"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
# log_file = f"/var/log/{BASENAME}.log"
LOG: log.Logger = log.get_logger(BASENAME)

if __name__ == "__main__":

    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("action", choices=["push", "pull", "reset", "status", "delete"])
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--force", "-f", action="store_true")
        parser.add_argument("--branch", "-b", default=master_branch)
        parser.add_argument("--remote-alias", default="origin")
        parser.add_argument("--remote-path", default="~/my_origin_repo.git")
        parser.add_argument("--local-path", default=sh.current_path())
        parser.add_argument("--gitignore-path", default="")
        return parser.parse_args()

    ARGS = parse_arguments()

    #  Configure the main logger
    LOG_HANDLERS: List[log.LogHandlerOptions] = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("------------------------------------------------")

    # Configure the logger
    log_level = 20  # logging.INFO
    if ARGS.debug:
        log_level = 10  # logging.DEBUG
    LOG.setLevel(log_level)

    # Configure the shell_boilerplate logger
    if ARGS.debug:
        sh_logger = log.get_logger("shell_boilerplate")
        sh_logger.setLevel(log_level)

    # Configure the git_boilerplate logger
    if ARGS.debug:
        git_logger = log.get_logger("git_boilerplate")
        git_logger.setLevel(log_level)

    controller = GitController()

    # If we get to this point, assume all went well
    LOG.debug("--------------------------------------------------------")
    LOG.debug("--- end point reached :3 ---")
    sh.exit_process()


# :: Usage Example ::
# mygit push --branch="Zoolander"
# mygit push --debug --force --branch="Zoolander" --gitignore-path="~/.gitignore"
