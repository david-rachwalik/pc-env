#!/usr/bin/env python
"""Test backing up a directory of files"""

#                   *** Options ***
# src:          Path to source files                    default=(current directory)
# dest:         Path to backup directory                default=(~/Backups)
# suffix:       Directory name or relative path end     default=(current direcory name)
# extension:    Extension file types to include         default="*"
# deep:         Copy/move files in subdirectories       default=False
# cut:          Move files instead of copy              default=False

import argparse
import os

from shell_boilerplate import ShellManager

# import shutil
# import sys


# ------------------------ Primary classes/functions ------------------------


class FileBackup(ShellManager):
    def __init__(self):
        self.args = self.ParseCommandLineArguments()
        logLevel = 20  # logging.INFO
        if self.args.debug:
            logLevel = 10  # logging.DEBUG
        # Initialize the inherited class constructor
        ShellManager.__init__(self, logLevel)
        self.log.debug("(FileBackup:__init__) Init")
        # Initial values
        self.args.src = self.ExpandPath(self.args.src)
        # self.args.dest = os.path.join(self.ExpandPath(self.args.dest), self.args.suffix)

        self.args.dest = self.ExpandPath(self.args.dest)
        dest_basepath = os.path.basename(self.args.dest)
        # Add suffix to path when the top directory name doesn't match
        if self.args.dest != os.path.join(dest_basepath, self.args.suffix):
            self.log.info(dest_basepath)
            self.log.info(self.args.suffix)
            self.args.dest = os.path.join(self.ExpandPath(self.args.dest), self.args.suffix)
        else:
            self.log.info(self.args.dest)

        # ---------------- Primary business logic area ----------------
        self.log.debug(f"source: {self.args.src}")
        self.log.debug(f"destination: {self.args.dest}")

        # Ensure source directory exists
        if not os.path.isdir(self.args.src):
            self.log.error("Source directory does not exist")
            self.Fail()
        # Ensure backup directory exists; will create if absent
        self.DirectoryCreate(self.args.dest)
        # Perform backup copy of directory files
        self.DirectoryCopy(
            self.args.src,
            self.args.dest,
            self.args.deep,
            self.args.cut,
            self.args.extension,
        )

    def ParseCommandLineArguments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--src", default=os.getcwd())
        parser.add_argument("--dest", default="$HOME/Backups")
        parser.add_argument("--suffix", default=os.path.basename(os.getcwd()))
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--extension", default="*")
        parser.add_argument("--deep", action="store_true")
        parser.add_argument("--cut", action="store_true")
        return parser.parse_args()


# ------------------------ Main Program ------------------------

if __name__ == "__main__":
    backup = FileBackup()
    backup.Exit()

# py $Env:AppData\Python\Python311\site-packages\boilerplates\file_backup.py --debug
