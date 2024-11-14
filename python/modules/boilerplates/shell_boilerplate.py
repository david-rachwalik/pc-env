#!/usr/bin/env python
"""Common logic for shell interactions"""

# --- Global Shell Commands ---
# :-Helper-:        system_platform, environment_get, environment_set, random_password
# JSON:             from_json, to_json, save_json, is_json_parse, is_json_str
# Utility:          shift_directory, change_directory, list_differences, print_command
# Process:          exit_process, fail_process, process_id, process_parent_id
# Path:             current_path, expand_path, join_path, path_exists, path_dir, path_basename, path_filename
# Directory:        list_directory, create_directory, delete_directory, copy_directory, sync_directory, remove_empty_directories
# File:             read_file, write_file, delete_file, rename_file, copy_file, hash_file, match_file, backup_file
# Signal:           max_signal, handle_signal, send_signal
# SubProcess:       run_subprocess, log_subprocess

# --- SubProcess Class Commands ---
# await_results, is_done, format_output

import argparse

# import distutils.dir_util
# import distutils.file_util
import json
import os
import shutil

# import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

import dirsync
import logging_boilerplate as log

# --- Module Key ---
# subprocess        Pipe a service command like you would ad hoc
# multiprocessing   Thread multiple processes into a Pool or Queue
# socket            Communication between server/client end points

# ------------------------ Classes ------------------------

# https://goodcode.io/articles/python-dict-object
# Access dictionary items as object attributes


class DictObj(dict):
    """Class that enables dictionary properties to be accessed as object attributes"""

    def __getattr__(self, name):
        if name not in self:
            raise AttributeError(f"No such attribute: {name}")
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError(f"No such attribute: {name}")


# ------------------------ Global Shell Commands ------------------------

# --- Helper Commands ---


def system_platform() -> str:
    """Method that fetches the system platform type"""
    # https://docs.python.org/3.11/library/sys.html#sys.platform
    if sys.platform.startswith("linux"):
        return "linux"
    elif sys.platform.startswith("win"):
        return "windows"
    return ""
    # alternatively, could use os.name (posix=linux, nt=windows)


def environment_get(key: str, default: str = "") -> str:
    """Method that fetches an environment variable"""
    #     # https://docs.python.org/3/library/os.html#os.environ
    #     return os.getenv(key, default)
    return os.environ.get(key, default) or ""


def environment_set(key: str, value: str):
    """Method that updates an environment variable"""
    os.environ[key] = value


# https://pynative.com/python-generate-random-string
def random_password(length: int = 16) -> str:
    """Method that returns a randomized password"""
    import random
    import string

    # Load all lower/upper case letters, digits, and special characters
    random_source: str = string.ascii_letters + string.digits + string.punctuation
    # Guarantee at least 1 of each
    password: str = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)
    password += random.choice(string.punctuation)
    # Fill in the remaining length
    for i in range(length - 4):
        password += random.choice(random_source)
    # Randomly shuffle all the characters
    password_list: List[str] = list(password)
    random.SystemRandom().shuffle(password_list)
    password = "".join(password_list)
    return password


# --- Utility Commands ---


# Changes directory during 'with' block and then switches back
@contextmanager
def shift_directory(path):
    """Method that changes directory prior to next step"""
    if not isinstance(path, str):
        return
    working_directory = current_path()
    change_directory(path)
    try:
        yield
    finally:
        change_directory(working_directory)


def change_directory(path):
    """Method that changes directory"""
    os.chdir(path)


def list_differences(first, second):
    """Method that return items from the first list that aren't in the second list"""
    second = set(second)
    return [item for item in first if item not in second]


# Provide beginning text of command option to 'secure' and remaining will be hidden
def print_command(command: List[str], secure: str = "") -> str:
    """Method that prints the main command text and hiding sensitive text"""
    _command: List[str] = command.copy()
    if secure:
        # Print password-safe version of command
        for i, line in enumerate(_command):
            if line.startswith(secure):
                _command[i] = f"{secure}*"
    display_command: str = " ".join(map(str, _command))  # using list comprehension
    LOG.debug(display_command)
    return display_command


# --- Process (List State) Commands ---


def exit_process():
    """Method that exits the process"""
    sys.exit(0)


def fail_process():
    """Method that fails the process"""
    sys.exit(1)


def process_id() -> int:
    """Method that returns the process ID"""
    return os.getpid()


def process_parent_id() -> int:
    """Method that returns the parent process ID"""
    return os.getppid()


# --- Path Commands ---


def current_path() -> str:
    """Method that returns the current directory path"""
    return os.getcwd()


# Expands user directory and environmental variables
def expand_path(path: str) -> str:
    """Method that returns the absolute path"""
    result: str = os.path.expanduser(path)
    result = os.path.expandvars(result)
    result = os.path.abspath(result)
    return result


def join_path(path: str, *paths) -> str:
    """Method that returns the joined paths"""
    return os.path.join(path, *paths)


# Pass either 'f' (file) or 'd' (directory) to file_type
def path_exists(path: str, file_type: str = "") -> bool:
    """Method that validates whether the path exists"""
    path = expand_path(path)
    # Use more specific type of check if provided
    if file_type == "d":
        return os.path.isdir(path)
    elif file_type == "f":
        return os.path.isfile(path)
    else:
        return os.path.exists(path)


# Returns '/foo/bar' from /foo/bar/item
def path_dir(name: str) -> str:
    """Method that returns all but the last segment of a path"""
    return os.path.dirname(name)


# Returns 'item.bat' from /foo/bar/item.bat
def path_basename(name: str) -> str:
    """Method that returns the last segment of a path"""
    return os.path.basename(name)


# Returns 'file.txt.zip' from /path/to/some/file.txt.zip.asc
# https://stackoverflow.com/questions/678236/how-to-get-the-filename-without-the-extension-from-a-path-in-python
def path_filename(name: str) -> str:
    """Method that returns the last file segment of a path"""
    extension_trimmed = os.path.splitext(name)[0]
    filename: str = path_basename(extension_trimmed)
    return filename


# --- Directory Commands ---


def list_directory(path: str) -> List[str]:
    """Method that lists a directory's contents"""
    if not path_exists(path, "d"):
        return []
    paths: List[str] = os.listdir(path)
    paths.sort()
    return paths


def create_directory(path: str, mode=0o777) -> bool:
    """Method that creates a directory"""
    if path_exists(path, "d"):
        return False
    # directories_created: List[str] = distutils.dir_util.mkpath(path, mode)
    # No longer using 'mode' here - prefer to change permissions (os.chmod) when needed
    # https://stackoverflow.com/questions/1627198/python-mkdir-giving-me-wrong-permissions
    # https://docs.python.org/3/library/os.html#os.makedirs
    os.makedirs(path, mode)
    return True


def delete_directory(path: str):
    """Method that deletes a directory"""
    if not path_exists(path, "d"):
        return False
    try:
        # distutils.dir_util.remove_tree(path)
        shutil.rmtree(path)
        return True
    except Exception as e:
        LOG.error(f"Exception: {e}")
        return False


def copy_directory(src: str, dest: str) -> bool:
    """Method that copies a directory"""
    try:
        shutil.copytree(src, dest)
        return True
    except shutil.Error as e:
        LOG.error(f"shutil.Error: {e}")
        return False


# Uses rsync, a better alternative to 'shutil.copytree' with ignore
def rsync_directory(
    src: str,
    dest: str,
    recursive: bool = True,
    purge: bool = True,
    cut: bool = False,
    include: Tuple = (),
    exclude: Tuple = (),
    debug: bool = False,
) -> Tuple[List[str], List[str]]:
    """Method that syncs a directory's contents"""
    LOG.debug("Init")
    changed_files: List[str] = []
    changes_dirs: List[str] = []
    # Create sequence of command options
    command_options = []
    # --itemize-changes returns files with any change (e.g. permission attributes)
    # --list-only returns eligible files, not what actually changed
    command_options.append("--itemize-changes")
    command_options.append("--compress")
    command_options.append("--prune-empty-dirs")
    command_options.append("--human-readable")
    command_options.append("--out-format=%i %n")  # omit %L for symlink paths
    # No operations performed, returns file paths the actions would effect
    if debug:
        command_options.append("--dry-run")
    # Copy files recursively, not only first level
    if recursive:
        command_options.append("--archive")  # rlptgoD (not -H -A -X)
    else:
        command_options.append("--links")
        command_options.append("--perms")
        command_options.append("--times")
        command_options.append("--group")
        command_options.append("--owner")
        command_options.append("--devices")
        command_options.append("--specials")
    # Purge destination files not in source
    if purge:
        command_options.append("--delete")
    # Delete source files after successful transfer
    if cut:
        command_options.append("--remove-source-files")
    # Add whitelist/blacklist filters
    for i in include:
        if i:
            command_options.append(f"--include={i}")
    for i in exclude:
        if i:
            command_options.append(f"--exclude={i}")
    # Build and run the command
    command = ["rsync"]
    command.extend(command_options)
    command.extend([src, dest])
    LOG.debug(f"command used: {command}")
    process = run_subprocess(command)
    # log_subprocess(LOG, process)

    results: List[str] = str.splitlines(str(process.stdout))
    LOG.debug(f"results: {results}")

    for r in results:
        result = r.split(" ", 1)
        itemized_output = result[0]
        file_name = result[1]
        if itemized_output[1] == "f":
            changed_files.append(join_path(dest, file_name))
        elif itemized_output[1] == "d":
            changes_dirs.append(join_path(dest, file_name))

    LOG.debug(f"changed_files: {changed_files}")
    return (changed_files, changes_dirs)


def sync_directory(
    sourcedir: str,
    targetdir: str,
    action: str = "sync",
    options: Optional[Dict[str, Any]] = None,
    ignore: Optional[List[str]] = None,
) -> bool:
    """Method that copies a directory

    Args:
        src (str): Source directory location
        dest (str): Destination directory location
        action (str): Action strategy for behavior.  Defaults to 'sync'.
        options (dict): Provide additional options, such as: only, exclude, include

    Returns:
        bool: Whether directories are in sync
    """
    action_choices: List[str] = ["diff", "sync", "update"]
    if action not in action_choices:
        return False

    if not ignore:
        ignore = []

    # https://github.com/tkhyn/dirsync/#additional-options
    # https://github.com/tkhyn/dirsync/#custom-logger
    default_options: Dict[str, Any] = {
        "logger": LOG,  # custom logger to send output somewhere other than stdout
        "verbose": True,
        "create": True,  # create target directory if it does not exist
        "ctime": True,  # takes into account the creation time or last metadata change
        "content": True,  # synchronize only different files (e.g. hash check)
        # use raw string notation for regex (https://docs.python.org/3/howto/regex.html)
        "ignore": [
            r".*\.bak$",  # ignore files with '.bak' extension
            *ignore,
        ],  # regex patterns to ignore (https://regexr.com)
    }
    if options:
        LOG.debug(f"options provided: {options}")
        full_options: Dict[str, Any] = {
            **default_options,
            **options,
        }
    else:
        full_options: Dict[str, Any] = default_options
    LOG.debug(f"options used: {full_options}")

    try:
        # https://github.com/tkhyn/dirsync
        dirsync.sync(sourcedir, targetdir, action, **full_options)
        return True
    except Exception as e:
        LOG.error(f"Exception: {e}")
        return False


# https://stackoverflow.com/questions/47093561/remove-empty-folders-python
def remove_empty_directories(root) -> List[str]:
    """Method that recursively removes empty subdirectories"""
    removed_dirs: List[str] = []

    for current_dir, subdirs, files in os.walk(root, topdown=False):
        if files:
            continue  # skip directory with files
        # LOG.debug(f'current_dir: {current_dir}')

        still_has_subdirs = False
        for subdir in subdirs:
            # LOG.debug(f'subdir: {subdir}')
            if os.path.join(current_dir, subdir) not in removed_dirs:
                still_has_subdirs = True
            # LOG.debug(f'still_has_subdirs: {still_has_subdirs}')

        if not still_has_subdirs:
            os.rmdir(current_dir)
            removed_dirs.append(current_dir)

    # LOG.debug(f'empty directories removed: {removed_dirs}')
    return removed_dirs


# --- File Commands ---


# Touch file and optionally fill with content
def write_file(path: str, content: Optional[Any] = None, append: bool = False):
    """Method that creates a file"""
    strategy = "a" if (append) else "w"  # write mode
    # open() only accepts absolute paths, not relative
    path = expand_path(path)
    # Ensure containing directory exists
    if not path_exists(path, "d"):
        create_directory(path_dir(path))
    # http://python-notes.curiousefficiency.org/en/latest/python3/text_file_processing.html
    with open(path, strategy, encoding="latin-1") as f:
        # Accept content as string or sequence of strings
        if isinstance(content, list):
            f.writelines(content)
        elif content is None:
            f.write("")
        else:
            f.write(str(content))


def read_file(path: str, oneline: bool = False) -> str:
    """Method that reads a file's content"""
    data: str = ""
    path = expand_path(path)
    if not (path or path_exists(path, "f")):
        return data
    try:
        # http://python-notes.curiousefficiency.org/en/latest/python3/text_file_processing.html
        with open(path, "r", encoding="latin-1") as f:
            data = f.readline().rstrip() if (oneline) else f.read().strip()
    except IOError as e:
        # File does not exist or some other IOError
        LOG.error(f"Exception: {e}")
    return data


def delete_file(path: str):
    """Method that deletes a file"""
    path = expand_path(path)
    if path_exists(path, "f"):
        os.unlink(path)


def rename_file(src: str, dest: str):
    """Method that renames a file"""
    src = expand_path(src)
    dest = expand_path(dest)
    if path_exists(src, "f"):
        os.rename(src, dest)


def copy_file(src: str, dest: str) -> bool:
    """Method that copies a file"""
    if not path_exists(src, "f"):
        return False
    # Ensure containing directory exists
    dest_dir = path_dir(dest)  # grab directory path from file path
    create_directory(dest_dir)
    try:
        shutil.copy2(src, dest)
        return True
    except Exception as e:
        LOG.error(f"Exception: {e}")
        return False


def hash_file(path: str) -> str:
    """Method that verifies a file hash"""
    if not path_exists(path, "f"):
        return ""
    # Using SHA-2 hash check (more secure than MD5|SHA-1)
    command: List[str] = ["sha256sum", path]
    process = run_subprocess(command)
    # log_subprocess(LOG, process, debug=ARGS.debug)
    results: List[str] = str(process.stdout).split()
    # LOG.debug(f"results: {results}")
    return results[0]


# Uses hash to validate file integrity
def match_file(path1: str, path2: str) -> bool:
    """Method that verifies whether files match based on hash"""
    # LOG.debug(f"path1: {path1}")
    hash1 = hash_file(path1)
    # LOG.debug(f"hash1: {hash1}")
    # LOG.debug(f"path2: {path2}")
    hash2 = hash_file(path2)
    # LOG.debug(f"hash2: {hash2}")
    if len(hash1) > 0 and len(hash2) > 0:
        return hash1 == hash2
    else:
        return False


def backup_file(path: str, ext="bak", time_format="%Y%m%d-%H%M%S") -> str:
    """Method that creates a file backup"""
    current_time = time.strftime(time_format)
    backup_path = f"{path}.{current_time}.{ext}"
    rename_file(path, backup_path)
    return backup_path


# --- JSON Commands ---


# https://realpython.com/python-json
def _decode_dict(dct) -> DictObj:
    """Method that casts dictionary items to be accessed as object attributes"""
    return DictObj(dct)


# Deserialize JSON string to Python dictionary: https://docs.python.org/3/library/json.html
def from_json(jsonstr: str, object_hook: Optional[Callable] = None) -> Dict[str, Any] | None:
    """Method that deserializes JSON string to Python dictionary"""
    results = None
    if not (jsonstr and isinstance(jsonstr, str)):
        return results
    try:
        # Decode/parse the json string
        # https://stackoverflow.com/questions/43286178/object-hook-in-json-module-doesnt-seem-to-work-as-id-expect
        # results = json.loads(json_str, object_hook=_decode_dict)
        results = json.loads(jsonstr, object_hook=object_hook)
    except ValueError as e:
        LOG.error(f"ValueError: {e}")
    # LOG.debug(f"results: {results}")
    return results


# Serialize Python dictionary into JSON string
def to_json(data: Any, indent: Optional[int] = None) -> str:
    """Method that serializes Python dictionary into JSON string"""
    results = ""
    try:
        results = json.dumps(data, indent=indent)  # convert to json
        # https://www.bruceeckel.com/2018/09/16/json-encoding-python-dataclasses
        # can pass a json.JSONEncoder to json.dumps 'cls' param for custom objects
    except ValueError as e:
        LOG.error(f"ValueError: {e}")
    # LOG.debug(f'results: {results}')
    return results


# TODO: only backup if content has changed
def save_json(path: str, data: Any, indent: Optional[int] = 2) -> bool:
    """Method that saves JSON to a file"""
    # Handle previous service principal if found
    if path_exists(path, "f"):
        backup_path = backup_file(path)
    # https://stackoverflow.com/questions/39491420/python-jsonexpecting-property-name-enclosed-in-double-quotes
    # Valid JSON syntax uses quotation marks; single quotes are only valid in string
    # https://stackoverflow.com/questions/43509448/building-json-file-out-of-python-objects
    # LOG.debug(f'data: {data}')
    file_ready = to_json(data, indent)
    # LOG.debug(f'file_ready: {file_ready}')
    write_file(path, file_ready)
    return path_exists(path, "f")


def is_json_parse(obj) -> bool:
    """Method that validates whether object is a JSON parse"""
    return isinstance(obj, DictObj)


def is_json_str(json_str: str) -> bool:
    """Method that validates whether string is JSON"""
    if not (json_str and isinstance(json_str, str)):
        return False
    results = from_json(json_str)
    return bool(results)


# --- Process Commands ---


# Creates asyncronous process and immediately awaits the tuple results
# NOTE: Only accepting 'command' as list; argument options can have spaces
def run_subprocess(
    command: List[str],
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    # ) -> Tuple[str, str, int]:
) -> subprocess.CompletedProcess:
    """Method that runs a command in a subprocess"""
    run_command: List[str] = []

    # process: SubProcess = SubProcess(command, cwd, env)
    # (stdout, stderr, rc) = process.await_results()

    # Detect shell to run command in based on system platform
    platform = system_platform()
    if platform == "windows":
        # run_command = ['powershell', '-Command'] + command  # legacy Windows PowerShell, built on Windows-only .NET
        run_command = [
            "pwsh",
            "-Command",
        ] + command  # PowerShell [Core], built on cross-platform .NET Core
    elif platform == "linux":
        run_command = ["bash", "-c"] + command  # use Bash for *nix
    # LOG.debug(f'run_command: {run_command}')

    # Execute the command in a subprocess
    result: subprocess.CompletedProcess = subprocess.run(
        run_command,
        capture_output=True,
        cwd=cwd,
        check=False,  # False avoids need to try/except (only CompletedProcess, no CalledProcessError)
        env=env,
        universal_newlines=True,
    )
    # LOG.debug(f'subprocess result: {result}')

    # stdout: str = result.stdout
    # stderr: str = result.stderr
    # rc: int = result.returncode

    # return (stdout, stderr, rc)
    return result


# Log the subprocess output provided
def log_subprocess(logger: log.Logger, process: subprocess.CompletedProcess, debug: bool = False):
    """Method that logs a command in a subprocess"""
    if isinstance(process.stdout, str) and len(process.stdout) > 0:
        log_stdout = f"stdout: {process.stdout}" if debug else process.stdout
        logger.info(log_stdout)
    if isinstance(process.stderr, str) and len(process.stderr) > 0:
        log_stderr = f"stderr: {process.stderr}" if debug else process.stderr
        # Level at least INFO (above DEBUG) so exceptions are shown
        # https://docs.python.org/3/library/logging.html#levels
        logger.error(log_stderr)
    if isinstance(process.returncode, int) and debug:
        log_rc = f"rc: {process.returncode}" if debug else process.returncode
        logger.debug(log_rc)

    # debug=False           debug=True
    # [Info]  "{0}"         "stdout: {0}"
    # [Info]  "{0}"         "stderr: {0}"
    # [Debug]               "rc: {0}"


# --- Signal Commands ---

# def max_signal() -> int:
#     return int(signal.NSIG) - 1


# # Accepts 'task' of <function>, 0 (signal.SIG_DFL), or 1 (signal.SIG_IGN)
# def handle_signal(signal_num: int, task: Callable | int):
#     task_whitelist = [signal.SIG_DFL, signal.SIG_IGN]
#     valid_task = callable(task) or task in task_whitelist
#     if not valid_task:
#         raise ValueError(
#             "handle_signal() expects 'task' parameter as callable <function> or an integer of 0 or 1 (signal.SIG_DFL or signal.SIG_IGN)")
#     # Update the signal handler (callback method)
#     signal.signal(signal_num, task)


# def send_signal(pid: int, signal_num: int = signal.SIGTERM):
#     if not pid:
#         raise ValueError("send_signal() expects 'pid' parameter as a positive integer")
#     os.kill(pid, signal_num)


# ------------------------ SubProcess Class ------------------------


# Only accepts 'command' parameter as a list/sequence of strings
# - Cannot string split because any argument options with values use spaces
class SubProcess(object):
    """Class of subprocess methods"""

    def __init__(
        self,
        command: List[str],
        chdir: str = "",
        env: Optional[Dict[str, str]] = None,
        shell: bool = False,
    ):
        # Initial values
        self.command: List[str] = command
        self.cwd: str = current_path()
        self.chdir: str = str(chdir)
        self.env = env
        self.pid: int = int()
        self.rc: int = int()
        self.stdout: str = str()
        self.stderr: str = str()

        # Build arguments and environment variables to support command
        command_args = {
            "close_fds": True,
            "universal_newlines": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }

        if env or shell:
            # LOG.debug('evaluating subprocess as shell')
            command_args["shell"] = True

        if env:
            # LOG.debug('implementing environment variables')
            # https://stackoverflow.com/questions/2231227/python-subprocess-popen-with-a-modified-environment
            # Combine current environment variables with those provided
            current_env = os.environ.copy()
            # LOG.debug(f'current_env: {current_env}')
            current_env.update(env)  # update for dict, extend for list
            # LOG.debug(f'current_env: {current_env}')
            # command_args['shell'] = True
            command_args["env"] = current_env
            self.env = current_env

        # if not hasattr(command_args, "shell") or command_args["shell"] is False:
        #     # Get the windows system directory
        #     win_dir_path = os.path.join(os.environ['WINDIR'], 'System32')
        #     # Get the windows executable file ( notepad.exe ) path.
        #     cmd_executeable_file_path = os.path.join(win_dir_path, 'notepad.exe')
        #     self.command.insert(0, cmd_executeable_file_path)

        # Create an async process to await
        # https://docs.python.org/3.9/library/subprocess.html#subprocess.Popen
        process_dir: str = self.chdir if bool(self.chdir) else self.cwd
        with shift_directory(process_dir):
            self.process = subprocess.Popen(self.command, **command_args)

    # def __repr__(self):
    #     return self.process

    def __str__(self):
        return str(self.process)

    def await_results(self) -> Tuple[str, str, int]:
        """Method that waits for the process to finish and return its output (stdout, stderr, rc)"""
        try:
            (stdout, stderr) = self.process.communicate()
            self.pid = self.process.pid
            self.rc = self.process.returncode
            self.stdout = self.format_output(stdout)
            self.stderr = self.format_output(stderr)
            return (self.stdout, self.stderr, self.rc)
        except Exception as e:
            LOG.error(f"Exception: {e}")
            return ("", "", -1)

    def format_output(self, text: str) -> str:
        """Method that formats process output"""
        # Split newlines and strip/trim whitespace
        whitespace_trimmed = str(text).strip()
        if not whitespace_trimmed:
            return ""
        if whitespace_trimmed.endswith("\n"):
            return whitespace_trimmed[-2]
        else:
            return whitespace_trimmed


# ------------------------ Main program ------------------------

# Initialize the logger
BASENAME = "shell_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: log.Logger = log.get_logger(BASENAME)

if __name__ == "__main__":
    # Returns argparse.Namespace; to pass into function, use **vars(self.ARGS)
    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        parser.add_argument("--test", choices=["subprocess", "multiprocess", "xml"])
        return parser.parse_args()

    ARGS = parse_arguments()

    #  Configure the main logger
    LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("------------------------------------------------")

    # -------- XML Test --------
    if ARGS.test == "xml":
        # Build command to send
        xml_config: str = "$HOME/configuration.xml"
        xml_schema: str = "$HOME/configuration.xsd"
        validator_command: List[str] = [
            "/usr/bin/xmllint",
            "--noout",
            f"--schema {xml_schema}",
            xml_config,
        ]
        LOG.debug(f"validation command => {validator_command}")

        # Validate configuration against the schema
        PROCESS = run_subprocess(validator_command)
        if PROCESS.returncode != 0:
            LOG.error(f"XML file ({xml_config}) failed to validate against schema ({xml_schema})")
            log_subprocess(LOG, PROCESS, debug=ARGS.debug)
        else:
            LOG.debug(f"{xml_config} was successfully validated")

    # -------- SubProcess Test --------
    elif ARGS.test == "subprocess":
        test_command: List[str] = ["ls", "-la", "/var"]
        LOG.debug(f"test command => {test_command}")
        PROCESS = run_subprocess(test_command)
        log_subprocess(LOG, PROCESS, debug=ARGS.debug)

        # Test writing to files
        test_file = "/tmp/ewertz"
        test_command = ["cat", test_file]
        inputs: List[str] = ["", "123", "12345", "1"]
        for I in inputs:
            write_file(test_file, I)
            PROCESS = run_subprocess(test_command)
            log_subprocess(LOG, PROCESS, debug=ARGS.debug)
        delete_file(test_file)

    # -------- SubProcess (simple) Test --------
    else:
        # test_command = ['ls', '-la', '/tmp']
        # test_command = ['ls']
        test_command = ["pwd"]
        LOG.debug(f"test command => {test_command}")
        PROCESS = run_subprocess(test_command)
        log_subprocess(LOG, PROCESS, debug=ARGS.debug)


# :: Usage Example ::
# sudo python /root/.local/lib/python2.7/site-packages/shell_boilerplate.py
# sudo python /root/.local/lib/python2.7/site-packages/shell_boilerplate.py --debug --test=subprocess
# py $Env:AppData\Python\Python311\site-packages\boilerplates\shell_boilerplate.py --debug --test=subprocess
