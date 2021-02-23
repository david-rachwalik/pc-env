#!/usr/bin/env python

# Basename: shell_boilerplate
# Description: Common business logic for *nix shell interactions
# Version: 1.7.0
# VersionDate: 5 Feb 2021

# --- Global Shell Commands ---
# :-Helper-:        format_resource, valid_resource, get_random_password
# JSON:             is_json_parse, is_json, json_parse, json_convert, json_save
# Utility:          directory_shift, directory_change, is_list_of_strings, list_differences, print_command
# Process:          process_exit, process_fail, process_id, process_parent_id
# Path:             path_current, path_expand, path_join, path_exists, path_dir, path_basename, path_filename
# Directory:        directory_list, directory_create, directory_delete, directory_copy, directory_sync
# File:             file_read, file_write, file_delete, file_rename, file_copy, file_hash, file_match, file_backup
# Signal:           signal_max, signal_handler, signal_send
# SubProcess:       subprocess_run, subprocess_log

# --- SubProcess Class Commands ---
# await_results, is_done, format_output

from logging_boilerplate import *
import sys, os, subprocess, signal
from contextlib import contextmanager
import distutils.dir_util
# import distutils.file_util
import json, time, re

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

# ------------------------ Classes ------------------------

# https://goodcode.io/articles/python-dict-object
# Access dictionary items as object attributes
class _dict2obj(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)



# ------------------------ Global Shell Commands ------------------------

# --- JSON Commands ---

# https://realpython.com/python-json
def _decode_dict(dct):
    return _dict2obj(dct)


def is_json_parse(obj):
    return isinstance(obj, _dict2obj)


def is_json(myjson):
    # _log.debug("myjson: {0}".format(myjson))
    if isinstance(myjson, _dict2obj): return True
    try:
        # _log.debug("attempting json load")
        json_object = json.loads(myjson)
        # _log.debug("json_object: {0}".format(json_object))
    except ValueError as e:
        return False
    return True


# Deserialize JSON data: https://docs.python.org/2/library/json.html
def json_parse(json_str):
    # _log.debug("json_str: {0}".format(json_str))
    # _log.debug("json_str type: {0}".format(type(json_str)))
    if not (json_str and is_json(json_str)): return ""
    results = json.loads(json_str, object_hook=_decode_dict)
    return results


# Serialize Python string into JSON
def json_convert(raw_str, indent=4):
    # _log.debug("raw_str: {0}".format(raw_str))
    if not (raw_str and is_json(raw_str)): return ""
    results = json.dumps(raw_str, indent=indent)
    # _log.debug("results: {0}".format(results))
    return results


def json_save(path, json_str, indent=4):
    if not (path and isinstance(path, str)): TypeError("'path' parameter expected as string")
    if not (json_str and isinstance(json_str, str)): TypeError("'json_str' parameter expected as string")
    if not (indent and isinstance(indent, int)): TypeError("'indent' parameter expected as integer")
    # Handle previous service principal if found
    if path_exists(path, "f"): backup_path = file_backup(path)
    # https://stackoverflow.com/questions/39491420/python-jsonexpecting-property-name-enclosed-in-double-quotes
    # Valid JSON syntax uses quotation marks; single quotes are only valid in string
    # https://stackoverflow.com/questions/43509448/building-json-file-out-of-python-objects
    # file_ready = json.dumps(json_str, indent=indent)
    file_ready = json_convert(json_str, indent)
    file_write(path, file_ready)



# --- Helper Commands ---

# Must conform to the following pattern: '^[0-9a-zA-Z-]+$'
def format_resource(raw_name, lowercase=True):
    if not (raw_name and isinstance(raw_name, str)): TypeError("'raw_name' parameter expected as string")
    name = raw_name.lower() if lowercase else raw_name # lowercase
    # name = re.sub('[^a-zA-Z0-9 \n\.]', '-', raw_name) # old, ignores '.'
    name = re.sub("[^a-zA-Z0-9-]", "-", name) # replace
    return name


# Must conform to the following pattern: '^[0-9a-zA-Z-]+$'
def valid_resource(raw_name, lowercase=True):
    og_name = str(raw_name)
    formatted_name = format_resource(raw_name, lowercase)
    return bool(og_name == formatted_name)


# https://pynative.com/python-generate-random-string
def get_random_password(length=16):
    import random, string
    # Load all lower/upper case letters, digits, and special characters
    random_source = string.ascii_letters + string.digits + string.punctuation
    # Guarantee at least 1 of each
    password = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)
    password += random.choice(string.punctuation)
    # Fill in the remaining length
    for i in range(length - 4):
        password += random.choice(random_source)
    # Randomly shuffle all the characters
    password_list = list(password)
    random.SystemRandom().shuffle(password_list)
    password = "".join(password_list)
    return password



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
    # return bool(obj) and all(isinstance(elem, str) for elem in obj)
    if not obj: return True # empty list
    return all(isinstance(elem, str) for elem in obj)


# Return items from first list that aren't in second
def list_differences(first, second):
    second = set(second)
    return [item for item in first if item not in second]


# Provide beginning text of command option to 'secure' and remaining will be hidden
# TODO: consider moving into shell_boilerplate if need for this logging arises
def print_command(command, secure=""):
    if not (command and is_list_of_strings(command)): TypeError("'command' parameter expected as list of strings")
    _command = command.copy()
    if secure:
        # Print password-safe version of command
        for (i, line) in enumerate(_command):
            if line.startswith(secure):
                _command[i] = "{0}*".format(secure)
    # display_command = "command => {0}".format(str.join(" ", _command))
    display_command = " ".join(map(str, _command)) # using list comprehension
    _log.debug(display_command)
    return display_command



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
    # subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    return (rc == 0)


def file_hash(path):
    if not path_exists(path, "f"): return ""
    # Using SHA-2 hash check (more secure than MD5|SHA-1)
    command = ["sha256sum", path]
    (stdout, stderr, rc) = subprocess_run(command)
    # subprocess_log(_log, stdout, stderr, rc, debug=args.debug)
    results = stdout.split()
    # _log.debug("results: {0}".format(results))
    return results[0]


# Uses hash to validate file integrity
def file_match(path1, path2):
    # _log.debug("path1: {0}".format(path1))
    hash1 = file_hash(path1)
    # _log.debug("hash1: {0}".format(hash1))
    # _log.debug("path2: {0}".format(path2))
    hash2 = file_hash(path2)
    # _log.debug("hash2: {0}".format(hash2))
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
def subprocess_run(command, path="", env=None, shell=False):
    if not is_list_of_strings(command): raise TypeError("'command' parameter expected as list/sequence of strings")
    if not isinstance(path, str): raise TypeError("'path' parameter expected as string")
    if not (env is None or isinstance(env, dict)): raise TypeError("'env' parameter expected as dictionary")
    if not isinstance(shell, bool): raise TypeError("'shell' parameter expected as boolean")
    process = SubProcess(command, path, env, shell)
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
    def __init__(self, command, chdir="", env=None, shell=False):
        if not is_list_of_strings(command): raise TypeError("'command' property expected as list/sequence of strings")
        if not isinstance(chdir, str): raise TypeError("'chdir' property expected as string")
        if not (env is None or isinstance(env, dict)): raise TypeError("'env' property expected as dictionary")
        if not isinstance(shell, bool): raise TypeError("'shell' property expected as boolean")
        # Initial values
        self.command = command
        self.chdir = str(chdir)
        self.env = env
        self.rc = int()
        self.stdout = str()
        self.stderr = str()

        # Build arguments and environment variables to support command
        command_args = {
            "close_fds": True,
            "universal_newlines": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE
        }

        if env or shell:
            # _log.debug("evaluating subprocess as shell")
            command_args["shell"] = True

        if env:
            # _log.debug("implementing environment variables")
            # https://stackoverflow.com/questions/2231227/python-subprocess-popen-with-a-modified-environment
            # Combine current environment variables with those provided
            current_env = os.environ.copy()
            # _log.debug("current_env: {0}".format(current_env))
            current_env.update(env) # update for dict, extend for list
            # _log.debug("current_env: {0}".format(current_env))
            # command_args["shell"] = True
            command_args["env"] = current_env
            self.env = current_env

        # Create an async process to await
        # https://docs.python.org/3.9/library/subprocess.html#subprocess.Popen
        self.process = None
        if self.chdir:
            with directory_shift(self.chdir):
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
