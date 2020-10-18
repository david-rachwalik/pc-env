#!/usr/bin/env python

# Basename: shell_boilerplate
# Description: Common business logic for *nix shell interactions
# Version: 1.6.1
# VersionDate: 21 Sep 2020

# --- Global Shell Commands ---
# Utility:          directory_shift, directory_change, is_list_of_strings, list_differences
# Process:          process_exit, process_fail, process_id, process_parent_id
# Path:             path_current, path_expand, path_join, path_exists, path_dir, path_basename, path_filename
# Directory:        directory_list, directory_create, directory_delete, directory_copy, directory_sync
# File:             file_read, file_write, file_delete, file_rename, file_copy, file_hash, file_match, file_backup
# Signal:           signal_max, signal_handler, signal_send
# SubProcess:       subprocess_run, subprocess_log

# --- SubProcess Class Commands ---
# await_results, is_done, format_output

from logging_boilerplate import *
import sys, os, subprocess, signal, time
from contextlib import contextmanager
import distutils.dir_util
# import distutils.file_util

# --- Module Key ---
# subprocess        Pipe a service command like you would ad hoc
# multiprocessing   Thread multiple processes into a Pool or Queue
# socket            Communication between server/client end points

try:
    # Python 2 has both 'str' (bytes) and 'unicode' text
    basestring = basestring
    unicode = unicode
except NameError:
    # Python 3 names the unicode data type 'str'
    basestring = str
    unicode = str

# ------------------------ Global Shell Commands ------------------------

# --- Utility Commands ---

# Changes directory during 'with' block and then switches back
@contextmanager
def directory_shift(path):
    if not isinstance(path, str): return
    working_directory = path_current()
    directory_change(path)
    try:
        yield
    finally:
        directory_change(working_directory)


def directory_change(path):
    os.chdir(path)


def is_list_of_strings(obj):
    if not isinstance(obj, list): return False
    return bool(obj) and all(isinstance(elem, str) for elem in obj)


# Return items from first list that aren't in second
def list_differences(first, second):
    second = set(second)
    return [item for item in first if item not in second]


# --- Process (List State) Commands ---

def process_exit():
    sys.exit(0)


def process_fail():
    sys.exit(1)


def process_id():
    return os.getpid()


def process_parent_id():
    return os.getppid()


# --- Path Commands ---

def path_current():
    return os.getcwd()


# Expands user directory and environmental variables
def path_expand(path):
    result = os.path.expanduser(path)
    result = os.path.expandvars(result)
    result = os.path.abspath(result)
    return result


def path_join(path, *paths):
    return os.path.join(path, *paths)


# Pass either "f" (file) or 'd' (directory) to file_type
def path_exists(path, file_type=""):
    path = path_expand(path)
    if not (path and isinstance(path, str)): raise TypeError("path_exists() expects 'path' parameter as string")
    if file_type == "d":
        return os.path.isdir(path)
    elif file_type == "f":
        return os.path.isfile(path)
    else:
        return os.path.exists(path)


# Returns '/foo/bar' from /foo/bar/item
def path_dir(name):
    return os.path.dirname(name)


# Returns 'item' from /foo/bar/item
def path_basename(name):
    return os.path.basename(name)


# Returns 'file.txt.zip' from /path/to/some/file.txt.zip.asc
# https://stackoverflow.com/questions/678236/how-to-get-the-filename-without-the-extension-from-a-path-in-python
def path_filename(name):
    extension_trimmed = os.path.splitext(name)[0]
    filename = path_basename(extension_trimmed)
    return filename


# --- Directory Commands ---

def directory_create(path, mode=0o775):
    directories_created = distutils.dir_util.mkpath(path, mode)
    return directories_created


# Use directory_sync() for similar functionality with file filters
def directory_copy(src, dest):
    prefix = path_basename(src)
    full_dest = path_join(dest, prefix) if path_basename(dest) != prefix else dest
    destination_paths = distutils.dir_util.copy_tree(src, full_dest, update=True)
    return destination_paths


def directory_delete(path):
    result = None
    if path_exists(path, "d"):
        # Better alternative to shutil.rmtree(path)
        result = distutils.dir_util.remove_tree(path)
    return result


def directory_list(path):
    if not path_exists(path, "d"): return []
    paths = os.listdir(path)
    paths.sort()
    return paths


# Uses rsync, a better alternative to 'shutil.copytree' with ignore
def directory_sync(src, dest, recursive=True, purge=True, cut=False, include=(), exclude=(), debug=False):
    if not isinstance(include, tuple): raise TypeError("directory_sync() expects 'include' parameter as tuple")
    if not isinstance(exclude, tuple): raise TypeError("directory_sync() expects 'exclude' parameter as tuple")
    _log.debug("Init")
    changed_files = []
    changes_dirs = []
    # Create sequence of command options
    command_options = []
    # --itemize-changes returns files with any change (e.g. permission attributes)
    # --list-only returns eligible files, not what actually changed
    command_options.append("--itemize-changes")
    command_options.append("--compress")
    command_options.append("--prune-empty-dirs")
    command_options.append("--human-readable")
    command_options.append("--out-format=%i %n") # omit %L for symlink paths
    # No operations performed, returns file paths the actions would effect
    if debug: command_options.append("--dry-run")
    # Copy files recursively, not only first level
    if recursive:
        command_options.append("--archive") # rlptgoD (not -H -A -X)
    else:
        command_options.append("--links")
        command_options.append("--perms")
        command_options.append("--times")
        command_options.append("--group")
        command_options.append("--owner")
        command_options.append("--devices")
        command_options.append("--specials")
    # Purge destination files not in source
    if purge: command_options.append("--delete")
    # Delete source files after successful transfer
    if cut: command_options.append("--remove-source-files")
    # Add whitelist/blacklist filters
    for i in include:
        if i: command_options.append("--include={0}".format(i))
    for i in exclude:
        if i: command_options.append("--exclude={0}".format(i))
    # Build and run the command
    command = ["rsync"]
    command.extend(command_options)
    command.extend([src, dest])
    _log.debug("command used: {0}".format(command))
    (stdout, stderr, rc) = subprocess_run(command)
    # subprocess_log(_log, stdout, stderr, rc)

    results = str.splitlines(stdout)
    _log.debug("results: {0}".format(results))

    for r in results:
        result = r.split(" ", 1)
        itemized_output = result[0]
        file_name = result[1]
        if itemized_output[1] == "f":
            changed_files.append(path_join(dest, file_name))
        elif itemized_output[1] == "d":
            changes_dirs.append(path_join(dest, file_name))

    _log.debug("changed_files: {0}".format(changed_files))
    return (changed_files, changes_dirs)


# --- File Commands ---

# Touch file and optionally fill with content
def file_write(path, content=None, append=False):
    # Ensure path is specified
    if not isinstance(path, str): raise TypeError("file_write() expects 'path' parameter as string")
    strategy = "a" if (append) else "w"
    # open() only accepts absolute paths, not relative
    path = path_expand(path)
    # Ensure containing directory exists
    if not path_exists(path, "d"): directory_create(path_dir(path))
    f = open(path, strategy)
    # Accept content as string or sequence of strings
    if content:
        if content is None:
            f.write("")
        elif is_list_of_strings(content):
            f.writelines(content)
        else:
            f.write(str(content))
    f.close()


def file_read(path, oneline=False):
    data = ""
    if not (path or path_exists(path, "f")): return data
    try:
        path = path_expand(path)
        # Open with file(); file() is deprecated
        f = open(path, "r")
        data = f.readline().rstrip() if (oneline) else f.read().strip()
        f.close()
    except:
        data = ""
    return data


def file_delete(path):
    path = path_expand(path)
    if path_exists(path, "f"): os.unlink(path)


def file_rename(src, dest):
    src = path_expand(src)
    dest = path_expand(dest)
    if path_exists(src, "f"): os.rename(src, dest)


def file_copy(src, dest):
    if not path_exists(src, "f"): return False
    command = ["cp", "--force", src, dest]
    (stdout, stderr, rc) = subprocess_run(command)
    subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return (rc == 0)


def file_hash(path):
    if not path_exists(path, "f"): return ""
    # Using SHA-2 hash check (more secure than MD5|SHA-1)
    command = ["sha256sum", path]
    (stdout, stderr, rc) = subprocess_run(command)
    subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    results = stdout.split()
    # _log.debug("results: {0}".format(results))
    return results[0]


# Uses hash to validate file integrity
def file_match(path1, path2):
    _log.debug("path1: {0}".format(path1))
    hash1 = file_hash(path1)
    _log.debug("hash1: {0}".format(hash1))
    _log.debug("path2: {0}".format(path2))
    hash2 = file_hash(path2)
    _log.debug("hash2: {0}".format(hash2))
    if len(hash1) > 0 and len(hash2) > 0:
        return (hash1 == hash2)
    else:
        return False


def file_backup(path, ext="bak", time_format="%Y%m%d-%H%M%S"):
    current_time = time.strftime(time_format)
    backup_path = "{0}.{1}.{2}".format(path, current_time, ext)
    file_rename(path, backup_path)
    return backup_path



# --- Process Commands ---

# Creates asyncronous process and immediately awaits the tuple results
# NOTE: Only accepting 'command' as list; argument options can have spaces
def subprocess_run(command, path="", env=""):
    if not isinstance(command, list): raise TypeError("subprocess_run() expects 'command' parameter as list")
    process = SubProcess(command, path, env)
    (stdout, stderr, rc) = process.await_results()
    return (stdout, stderr, rc)


# Log the subprocess output provided
def subprocess_log(_log, stdout=None, stderr=None, rc=None, debug=False):
    if not is_logger(_log): raise TypeError("subprocess_log() expects '_log' parameter as logging.Logger instance")
    if isinstance(stdout, str) and len(stdout) > 0:
        log_stdout = "stdout: {0}".format(stdout) if debug else stdout
        _log.info(log_stdout)
    if isinstance(stderr, str) and len(stdout) > 0:
        log_stderr = "stderr: {0}".format(stderr) if debug else stderr
        # _log.error(log_stderr)
        _log.info(log_stderr) # INFO so message is below WARN level (default on import)
    if isinstance(rc, int) and debug:
        log_rc = "rc: {0}".format(rc) if debug else rc
        _log.debug(log_rc)

    # debug=False           debug=True
    # [Info]  "{0}"         "stdout: {0}"
    # [Info]  "{0}"         "stderr: {0}"
    # [Debug]               "rc: {0}"


# --- Signal Commands ---

def signal_max():
    return int(signal.NSIG) - 1


# Accepts 'task' of <function>, 0 (signal.SIG_DFL), or 1 (signal.SIG_IGN)
def signal_handler(signal_num, int):
    # Validate parameter input
    if not isinstance(signal_num, int):
        raise TypeError("signal_handler() expects 'signal_num' parameter as integer")
    task_whitelist = [signal.SIG_DFL, signal.SIG_IGN]
    valid_task = callable(task) or task in task_whitelist
    if not valid_task:
        raise TypeError("signal_handler() expects 'task' parameter as callable <function> or an integer of 0 or 1 (signal.SIG_DFL or signal.SIG_IGN)")
    # Update the signal handler (callback method)
    signal.signal(signal_num, task)


def signal_send(pid, signal_num=signal.SIGTERM):
    if not (pid and isinstance(pid, int)): raise TypeError("signal_send() expects 'pid' parameter as positive integer")
    if not isinstance(signal_num, int): raise TypeError("signal_send() expects 'signal_num' parameter as integer")
    os.kill(pid, signal_num)


# ------------------------ SubProcess Class ------------------------

# Only accepts 'command' parameter as a list/sequence of strings
# - Cannot string split because any argument options with values use spaces
class SubProcess(object):
    def __init__(self, command, path="", env=None):
        # Initial values
        self.rc = int()
        self.stdout = str()
        self.stderr = str()
        self.command = []
        self.path = str(path)
        self.env = env

        # Ensure command was provided as text or a sequence/list
        if is_list_of_strings(command):
            self.command = command
        else:
            raise TypeError("SubProcess 'command' property expects a list/sequence of strings")

        # Build arguments and environment variables to support command
        command_args = {
            "close_fds": True,
            "universal_newlines": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE
        }
        if self.env: command_args["env"] = self.env

        # Create an async process to await
        self.process = None
        if self.path:
            with directory_shift(self.path):
                self.process = subprocess.Popen(self.command, **command_args)
        else:
            self.process = subprocess.Popen(self.command, **command_args)


    # def __repr__(self):
    #     return self.process


    def __str__(self):
        return str(self.process)


    # Waits for process to finish and returns output tuple (stdout, stderr, rc)
    def await_results(self):
        try:
            (stdout, stderr) = self.process.communicate()
            self.rc = self.process.returncode
            self.pid = self.process.pid
            self.stdout = self.format_output(stdout)
            self.stderr = self.format_output(stderr)
            return (self.stdout, self.stderr, self.rc)
        except:
            return (None, None, -1)


    # ProcessOutputFormat
    def format_output(self, text):
        # Split newlines and strip/trim whitespace
        whitespace_trimmed = str(text).strip()
        if not whitespace_trimmed: return ""
        if whitespace_trimmed.endswith("\n"):
            return whitespace_trimmed[-2]
        else:
            return whitespace_trimmed


# ------------------------ Main program ------------------------

# Initialize the logger
basename = "shell_boilerplate"
args = LogArgs() # for external modules
log_options = LogOptions(basename)
_log = get_logger(log_options)

if __name__ == "__main__":
    # Returns argparse.Namespace; to pass into function, use **vars(self.args)
    def parse_arguments():
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        parser.add_argument("--test", choices=["subprocess", "multiprocess", "xml"])
        return parser.parse_args()
    args = parse_arguments()

    #  Configure the main logger
    log_handlers = gen_basic_handlers(args.debug, args.log_path)
    set_handlers(_log, log_handlers)

    _log.debug("args: {0}".format(args))
    _log.debug("------------------------------------------------")


    # -------- XML Test --------
    if args.test == "xml":
        # Build command to send
        xml_path = "$HOME/configuration.xml"
        schema_path = "$HOME/configuration.xsd"
        validator_command = ["/usr/bin/xmllint", "--noout", "--schema {0}".format(schema_path), xml_path]
        _log.debug("validation command => {0}".format(validator_command))

        # Validate configuration against the schema
        (stdout, stderr, rc) = subprocess_run(validator_command)
        if rc != 0:
            _log.error("XML file ({0}) failed to validate against schema ({1})".format(config_xml, config_xsd))
            subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
        else:
            _log.debug("{0} was successfully validated".format(xml_path))

    # -------- SubProcess Test --------
    elif args.test == "subprocess":
        test_command = ["ls", "-la", "/var"]
        _log.debug("test command => {0}".format(test_command))
        (stdout, stderr, rc) = subprocess_run(test_command)
        subprocess_log(_log, stdout, stderr, rc, debug=args.debug)

        # Test writing to files
        test_file = "/tmp/ewertz"
        test_command = ["cat", test_file]
        inputs = ["", "123", "12345", "1"]
        for i in inputs:
            file_write(test_file, i)
            (stdout, stderr, rc) = subprocess_run(test_command)
            subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
        file_delete(test_file)

    # -------- SubProcess (simple) Test --------
    else:
        test_command = ["ls", "-la", "/tmp"]
        _log.debug("test command => {0}".format(test_command))
        (stdout, stderr, rc) = subprocess_run(test_command)
        subprocess_log(_log, stdout, stderr, rc, debug=args.debug)


    # --- Usage Example ---
    # sudo python /root/.local/lib/python2.7/site-packages/shell_boilerplate.py
    # sudo python /root/.local/lib/python2.7/site-packages/shell_boilerplate.py --debug --test=subprocess
