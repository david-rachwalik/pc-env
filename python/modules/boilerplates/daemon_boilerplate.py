#!/usr/bin/env python
"""Common business logic for daemons"""

import argparse
import atexit
import errno
import os
import resource
import signal
import sys
import time
from typing import List, Set

import logging_boilerplate as log
import shell_boilerplate as sh

# ------------------------ Classes ------------------------

# Context for turning a program into daemon process instance
# Usage: subclass DaemonContext() and override the run() method


class DaemonContext(object):
    def __init__(self, basename: str, log_file: str = ""):
        LOG.debug("Init")
        # Initial values
        self.basename = basename
        self.log_file = log_file
        self.pidfile = f"/var/run/{self.basename}.pid"
        self.lockfile = f"/var/lock/subsys/{self.basename}"
        self._is_open = bool()

    # Entry point for 'with' context

    def __enter__(self):
        self.open()
        return self

    # Exit point for 'with' context

    def __exit__(self):
        self.close()

    @property
    def is_locked(self):
        result = sh.path_exists(self.lockfile, "f")
        return result

    @property
    def is_open(self):
        return self._is_open

    def open(self):
        LOG.debug("Init")
        if self.is_locked:
            LOG.warning(f"Cannot open DaemonContext instance '{self.basename}', lockfile already exists")
            return
        if self.is_open:
            LOG.warning(f"DaemonContext instance '{self.basename}' is open already")
            return

        # ------------------------ Initial Values ------------------------
        self.working_directory = "/"
        self.umask = 0o000
        self.gid = os.getgid()
        self.uid = os.getuid()
        # Initial file descriptor values
        self.open_fds = self.list_open_file_descriptors()
        self.standard_streams = [sys.stdin, sys.stdout, sys.stderr]
        self.standard_fds = list(int(stream.fileno()) for stream in self.standard_streams)
        LOG.debug(f"standard file descriptors: {self.standard_fds}")
        self.log_fds = self.find_log_file_descriptors()
        LOG.debug(f"logging file descriptors: {self.log_fds}")
        # Check if log_fd is borrowing a standard index (possible error no longer occurs)
        for fd in self.log_fds:
            if fd in self.standard_fds:
                log_index = self.standard_fds.index(fd)
                self.standard_streams.pop(log_index)
                self.standard_fds.pop(log_index)
                LOG.debug(f"log using standard file descriptor; adjusted standard_fds: {self.standard_fds}")
        # -------------------------------------------------------------

        # Prevent this process from generating a core dump
        self.prevent_core_dump()
        # Change file creation mask for this process
        os.umask(self.umask)
        # Change working directory of this process
        os.chdir(self.working_directory)
        # Change process owner GID and UID (in that order to avoid permission errors)
        os.setgid(self.gid)
        os.setuid(self.uid)
        # Fork the program to daemonize its context
        self.detach_process_context()
        # Reset signal behavior for daemon context; use run() for further signal updates
        self.reset_signal_handlers()
        # Reset file descriptors; automatically exclude standard I/O and log
        fd_exclusions = self.list_default_file_descriptors()
        self.close_all_open_files(exclude=fd_exclusions)
        # Redirect standard file decsriptors from /dev/pts/* to /dev/null
        for stream in self.standard_streams:
            self.redirect_stream(stream)
        LOG.debug(f"standard file descriptors redirected to null: {self.standard_fds}")
        # Attach exit event
        atexit.register(self.exit_handler)
        LOG.debug("exit handler registered")
        # Enforce unique daemon instance and store PID for stop method
        self.create_pidfile()
        self.create_lock()
        self._is_open = True
        LOG.debug("daemon has been started")
        # Run tasks within the daemon context
        self.run()

    def close(self):
        LOG.debug("Init")
        pid = self.read_pidfile()
        if not pid:
            LOG.debug(f"pidfile '{self.pidfile}' does not exist. Daemon not running?")
            return  # Not an error in a restart
        LOG.debug(f"found '{self.pidfile}' in pidfile")
        # Try killing the daemon process
        try:
            while True:
                # Send terminate signal to the process
                sh.send_signal(pid)
                time.sleep(0.1)
        except OSError as exc:
            if exc.errno == errno.ESRCH:
                # Expected to land here for graceful exit when SIGTERM takes effect
                LOG.debug("daemon has stopped")
                pass  # [Errno 3] no such process
            else:
                LOG.warning(f"error occurred attempting to terminate process ({pid}): {exc}")
                raise

    # Write the latest PID to file

    def create_pidfile(self):
        LOG.debug("Init")
        sh.write_file(self.pidfile, str(sh.process_id()))
        LOG.debug("pid file created successfully")

    # Obtain an exclusive lock before running actions

    def create_lock(self):
        LOG.debug("Init")
        sh.write_file(self.lockfile)
        LOG.debug("lockfile created successfully")

    def read_pidfile(self):
        LOG.debug("Init")
        pid = sh.read_file(self.pidfile, True)
        return int(pid) if (pid) else pid

    def prevent_core_dump(self):
        LOG.debug("Init")
        core_resource = resource.RLIMIT_CORE
        # Ensure the resource limit exists on this platform, by requesting its current value
        try:
            resource.getrlimit(core_resource)
        except Exception as exc:
            LOG.error(f"System does not support RLIMIT_CORE resource limit ({exc})")
            raise
        # Set hard and soft limits to zero, i.e. no core dump at all
        core_limit = (0, 0)
        resource.setrlimit(core_resource, core_limit)

    def detach_process_context(self):
        LOG.debug("Init")
        self.become_child_process(error_message="Failed first fork")
        # LOG.debug(f"fork 1 pid: {sh.process_id()}")
        os.setsid()  # decouple from parent
        # Do the UNIX double-fork to prevent daemon from acquiring TTY
        self.become_child_process(error_message="Failed second fork")
        # LOG.debug(f"fork 2 pid: {sh.process_id()}")
        self.pid = sh.process_id()
        LOG.debug(f"Daemon PID: {self.pid}")

    # Attempt to spawn a child process

    def become_child_process(self, error_message=""):
        LOG.debug("Init")
        try:
            child_pid = os.fork()
        except OSError as e:
            LOG.debug(f"ERRNO {e.errno}: {e.strerror}")
            LOG.debug(f"{error_message}: [{e.errno:d}] {e.strerror}")
            raise
        # Positive PID is parent process needing to exit; child process waits for parent to complete
        if child_pid > 0:
            LOG.debug(f"child spawned ({child_pid}), performing exit")
            os._exit(0)
        elif child_pid == 0:
            # Wait until parent exits and child is inherited by init (PID=1) for ownership of files
            while sh.process_parent_id() != 1:
                LOG.debug(f"waiting until parent ({sh.process_parent_id()}) exits")
                time.sleep(0.1)

    def reset_signal_handlers(self):
        LOG.debug("Init")
        # Create signal handler map of default actions
        # NOTE: Setting signal.SIG_DFL on signal.SIGTERM is immediate exit; won't call atexit
        signal_handler_map = {
            signal.SIGUP: signal.SIG_IGN,
            signal.SIGTERM: self.terminate,
            signal.SIGTSTP: signal.SIG_IGN,
            signal.SIGTTIN: signal.SIG_IGN,
            signal.SIGTTOU: signal.SIG_IGN,
        }
        LOG.debug(f"signal_handler_map: {signal_handler_map}")
        # Update each signal handler (callback method)
        for signal_number, handler in signal_handler_map.items():
            signal.signal(signal_number, handler)
        LOG.debug("all signal handlers are updated")

    # Gather open file descriptors from system directory

    def list_open_file_descriptors(self):
        LOG.debug("Init")
        # NOTE: Always reflects file descriptors when process was started (even with /proc/{pid}/fd)
        open_fd_strings = os.listdir("/proc/self/fd")
        open_fds = list(int(result) for result in open_fd_strings)
        LOG.debug(f"file descriptors open: {open_fds}")
        return open_fds

    def redirect_stream(self, system_stream, target_stream=None):
        # LOG.debug("Init")
        if target_stream is None:
            target_fd = os.open(os.devnull, os.O_RDWR)
        else:
            target_fd = target_stream.fileno()
        system_fd = system_stream.fileno()
        # Redirect a system stream to specified file
        if target_stream:
            LOG.debug(f"redirecting file descriptor {target_fd} to {system_fd}")
        try:
            os.dup2(target_fd, system_fd)
        except Exception as exc:
            LOG.error(f"Unable to redirect file descriptor ({exc})")
            raise
        # Cleanup '/dev/null' file when opened
        if target_stream is None:
            self.close_file_descriptor(target_fd)

    def get_file_descriptor_path(self, fd):
        # LOG.debug("Init")
        try:
            fd_path = os.readlink(f"/proc/self/fd/{fd}")
        except OSError as exc:
            if exc.errno == errno.ENOENT:
                # [Errno 2] No such file or directory
                fd_path = ""
            else:
                LOG.debug(f"Failed to get file descriptor ({fd}) path: {exc}")
                raise
        return fd_path

    def find_log_file_descriptors(self):
        LOG.debug("Init")
        log_fds = []
        for fd in self.open_fds:
            fd_path = self.get_file_descriptor_path(fd)
            if fd_path == self.log_file:
                log_fds.append(fd)
        return log_fds

    def list_default_file_descriptors(self):
        LOG.debug("Init")
        default_fds: List[int] = []
        # Add all standard file descriptors
        for fd in self.standard_fds:
            default_fds.append(fd)
        # Add logging file descriptor
        for fd in self.log_fds:
            default_fds.append(fd)
        LOG.debug(f"default_fds: {default_fds}")
        return default_fds

    def close_file_descriptor(self, fd: int):
        LOG.debug("Init")
        if not fd:
            raise ValueError("expects 'fd' parameter as positive integer.")
        try:
            os.close(fd)
        except OSError as exc:
            if exc.errno == errno.EBADF:
                pass  # [Errno 9] Bad file descriptor
            else:
                LOG.debug(f"error closing file descriptor ({fd}): {exc}")
                raise

    # Close all open file streams; primarily needs to close /dev/tty

    def close_all_open_files(self, exclude: List | Set = set()):
        LOG.debug("Init")
        LOG.debug(f"excluded file descriptors: {exclude}")
        # Determine candidate file descriptors to close
        fds_to_close = sh.list_differences(self.open_fds, exclude)
        # Close each file descriptor
        for fd in reversed(fds_to_close):
            fd_path = self.get_file_descriptor_path(fd)
            LOG.debug(f"closing file descriptor ({fd}) for path '{fd_path}'")
            self.close_file_descriptor(fd)
        LOG.debug("all file descriptors are closed")

    # Cleanup lockfile and PID file

    def exit_handler(self):
        LOG.debug("Init")
        if sh.path_exists(self.lockfile, "f"):
            LOG.debug(f"removed lockfile: {self.lockfile}")
            sh.file_delete(self.lockfile)
        if sh.path_exists(self.pidfile, "f"):
            LOG.debug(f"removed PID file: {self.pidfile}")
            sh.file_delete(self.pidfile)

    def run(self):
        LOG.warning("Override this method when you subclass DaemonContext.  It will be called after the process has been daemonized.")

    def terminate(self):
        LOG.warning("Signal handler for end-process")
        sh.exit_process()


# ------------------------ Main Program ------------------------

# Initialize the logger
BASENAME = "daemon_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
# log_file = f"/var/log/{basename}.log"
LOG: log.Logger = log.get_logger(BASENAME)

if __name__ == "__main__":
    # Returns argparse.Namespace; to pass into function, use **vars(self.ARGS)
    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("action", choices=["restart", "stop", "start"])
        parser.add_argument("--debug", action="store_true")
        return parser.parse_args()

    ARGS = parse_arguments()

    #  Configure the main logger
    # LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    # log.set_handlers(LOG, LOG_HANDLERS)

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("------------------------------------------------")

    # Initialize the daemon
    class TestDaemon(DaemonContext):
        # DaemonContext remains alive so long as 'while' loop continues
        def run(self):
            LOG.debug("(TestDaemon:run): Init")
            # Main heartbeat for business logic
            self.counter = 0
            while True:
                self.test_tasks()
                time.sleep(3)

        # Test writing to files
        def test_tasks(self):
            # LOG.debug("(TestDaemon:test_tasks): Init")
            testFile = "/tmp/ewertz"
            self.counter += 1
            message = f"Daemon counter: {self.counter}"
            sh.write_file(testFile, message, True)
            return

    daemon = TestDaemon(BASENAME, log_file)

    # --- Business Logic ---
    if ARGS.action in ["stop", "restart"]:
        daemon.close()
    if ARGS.action in ["start", "restart"]:
        daemon.open()
    # Assume all is well if here
    sh.exit_process()


# :: Usage Example ::
# sudo python /root/.local/lib/python2.7/site-packages/daemon_boilerplate.py
# sudo python /root/.local/lib/python2.7/site-packages/daemon_boilerplate.py --debug && sudo less +F /var/log/daemon_boilerplate.log
# ps -eaf | grep -i python

# sudo ls -la /var/run/daemon_boilerplate.pid
# sudo ls -la /var/lock/daemon_boilerplate
# sudo ls -la /var/log/daemon_boilerplate.log
# sudo ls -la /tmp/ewertz
