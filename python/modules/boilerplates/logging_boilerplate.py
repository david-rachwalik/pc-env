#!/usr/bin/env python
"""Common logic for Python logging"""

# https://peps.python.org/pep-0008/#naming-conventions
# https://peps.python.org/pep-0257/#what-is-a-docstring

# --- Global Logging Commands ---
# logger:               get_logger
# handler:              get_handler, add_handler, set_handlers

# :: Usage Instructions ::
# * Call get_logger() to receive a logger by name
# * Pass handlers to logger as a list of LogHandlerOptions
# * The logger types are stream (console/terminal) and file-based
# * Providing 'path' to LogHandlerOptions toggles handler from stream to file

import argparse
import datetime
import logging
import sys
from typing import List, Optional, TypeAlias

import colorlog
import pytz

# ------------------------ Classes ------------------------

Logger: TypeAlias = logging.Logger
_timezone: str = "US/Central"
_time_format: str = "%Y-%m-%d %H:%M:%S"
_message_format: str = "%(message)s"

# Pass 'path' for file handler; must expand absolute paths ('~' treated relatively)


class LogHandlerOptions(object):
    """Options object for log handling"""

    def __init__(
        self,
        level=logging.WARNING,
        path="",
        message_format=_message_format,
        time_format=_time_format,
        timezone=_timezone,
    ):
        # levels: 10-DEBUG, 20-INFO, 30-WARNING, 40-ERROR, 50-CRITICAL
        level_choices = [10, 20, 30, 40, 50]
        if isinstance(level, int) and level in level_choices:
            self.level = level
        else:
            self.level = logging.WARNING
        self.path = str(path)
        self.message_format = str(message_format)
        self.time_format = str(time_format)
        self.timezone = str(timezone)


# ------------------------ Global Functions ------------------------

# --- Logger Commands ---

_stream_handler: LogHandlerOptions = LogHandlerOptions()


def get_logger(log_name: str = "root", handlers: Optional[List[LogHandlerOptions]] = None) -> logging.Logger:
    """Method to fetch the logging Logger"""
    # Automatically attach default handlers (stream handler)
    if handlers is None:
        handlers = [_stream_handler]
    # Obtain instance of logging.Logger based on name (idempotent)
    # logger: logging.Logger = logging.getLogger(log_name)
    logger: logging.Logger = colorlog.getLogger(log_name)
    # Set logger to lowest level because handlers will control the true level
    logger.setLevel(logging.DEBUG)
    set_handlers(logger, handlers)
    return logger


def get_handler(options: LogHandlerOptions):
    """Method to fetch the logging Handler"""
    if options.path:
        # Setup a file handler for writing to log file
        handler = logging.FileHandler(filename=options.path)
    else:
        # Setup a stream handler for live console output (stdout/stderr); stderr is default
        # handler = logging.StreamHandler()
        # handler = logging.StreamHandler(sys.stdout)
        handler = colorlog.StreamHandler(sys.stdout)
    # Create formatter to attach to handler
    # log_formatter = logging.Formatter(fmt=options.message_format, datefmt=options.time_format)
    log_formatter = colorlog.ColoredFormatter(options.message_format, datefmt=options.time_format)
    log_formatter.converter = _get_timezone_converter(options.timezone)
    # Configure handler with log format and level
    handler.setFormatter(log_formatter)
    handler.setLevel(options.level)
    return handler


# Generate handler from LogHandlerOptions and attach to logger
def add_handler(logger: logging.Logger, options: LogHandlerOptions):
    """Method to add a logging Handler"""
    handler = get_handler(options)
    logger.addHandler(handler)


# Apply batch of handlers to logger based on list of LogHandlerOptions
def set_handlers(logger: logging.Logger, handlers: Optional[List[LogHandlerOptions]] = None):
    """Method to apply one or more logging Handler"""
    if handlers is None:
        handlers = []
    # Clear all pre-existing handlers attached to logger
    for handler in logger.handlers:
        logger.removeHandler(handler)
    # Generate batch of handlers and attach each to logger
    for options in handlers:
        add_handler(logger, options)


# Generate handlers with a standard configuration
def default_handlers(debug: bool = False, log_path: str = "") -> List[LogHandlerOptions]:
    """Method to generate default logging Handlers"""
    # https://docs.python.org/3/library/logging.html#logrecord-attributes
    # _message_format = "%(asctime)s %(name)s\t[%(levelname)s]\t%(message)s"
    # _message_format = "%(asctime)s %(levelname)-7s %(message)s"
    # _message_format = "%(asctime)s [%(levelname)s] %(message)s"
    if debug:
        log_level = 10  # logging.DEBUG
        # log_format = '%(asctime)s [%(levelname).1s] (%(module)s:%(funcName)s): %(message)s'
        log_format = "%(log_color)s%(asctime)s [%(levelname).1s] (%(module)s:%(funcName)s): %(message)s"
    else:
        log_level = 20  # logging.INFO
        # log_format = '%(message)s'
        log_format = "%(log_color)s%(asctime)s: %(message)s"
    # Create stream handler (console/terminal)
    log_stream_options = LogHandlerOptions(log_level, "", log_format)
    log_handlers = [log_stream_options]
    # Create file handler when path is provided
    if log_path:
        log_file_options = LogHandlerOptions(log_level, log_path, log_format)
        log_handlers.append(log_file_options)
    return log_handlers


# --- Private Commands ---


# Convert to timezone for log output
def _get_timezone_converter(timezone="UTC"):
    def format_timezone(*args):
        utc_date = pytz.utc.localize(datetime.datetime.utcnow())
        tz = pytz.timezone(timezone)
        converted = utc_date.astimezone(tz)
        return converted.timetuple()

    return format_timezone


# ------------------------ Main Program ------------------------

# # Replace built-in level names
# logging.addLevelName(logging.WARNING, "WARN")
# logging.addLevelName(logging.CRITICAL, "FATAL")

# Initialize the logger
BASENAME = "logging_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: Logger = get_logger(BASENAME)

if __name__ == "__main__":

    def parse_arguments():
        """Method that parses arguments provided"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--log-path", default="")
        return parser.parse_args()

    ARGS = parse_arguments()

    # # Configure the logger
    # log_level: int = 10 # logging.DEBUG
    # # Pass 'path' for file handler; must expand absolute paths ('~' treated relatively)
    # # log_file: str = f"/home/david/logs/{basename}.log" # wsl
    # home_dir = os.path.expanduser("~")
    # log_file: str = os.path.join(home_dir, "logs", f"{BASENAME}.log")
    # # Set the log handler options
    # log_stream_options: LogHandlerOptions = LogHandlerOptions(log_level)
    # log_file_options: LogHandlerOptions = LogHandlerOptions(log_level, log_file)
    # # Refresh logger with the new handlers
    # LOG_HANDLERS: List[LogHandlerOptions] = [log_stream_options, log_file_options]

    # Configure the logger
    LOG_HANDLERS: List[LogHandlerOptions] = default_handlers(ARGS.debug, ARGS.log_path)
    set_handlers(LOG, LOG_HANDLERS)

    LOG.debug("--- Log test successful! ---")
    LOG.info("--- Log test successful! ---")
    LOG.warning("--- Log test successful! ---")
    LOG.error("--- Log test successful! ---")
    LOG.critical("--- Log test successful! ---")

    HANDLER_LENGTH = len(LOG.handlers)
    LOG.warning(f"log handler count: {HANDLER_LENGTH}")
    LOG.warning(f"log handlers: {LOG.handlers}")


# :: Usage Example ::
# python $HOME/.local/lib/python3.6/site-packages/logging_boilerplate.py
# py $Env:AppData\Python\Python311\site-packages\boilerplates\logging_boilerplate.py
