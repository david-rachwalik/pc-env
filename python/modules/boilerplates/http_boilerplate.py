#!/usr/bin/env python
"""Common logic for Python HTTP request interactions"""

import argparse
from typing import Any, List, Optional, TypeAlias

import logging_boilerplate as log
import requests as req
import shell_boilerplate as sh
from requests.auth import HTTPBasicAuth

# ------------------------ Global Methods ------------------------
# https://requests.readthedocs.io
# https://realpython.com/python-requests


# --- Authentication ---
# https://requests.readthedocs.io/en/latest/user/authentication

AUTH_TYPE: TypeAlias = HTTPBasicAuth


def authentication_web(user: str, password: str) -> HTTPBasicAuth:
    """Method that creates HTTP 'Basic Auth' for web services that require authentication"""
    basic = HTTPBasicAuth(user, password)
    # LOG.debug(f'basic auth: {basic}')
    return basic


# https://requests-oauthlib.readthedocs.io/en/latest/oauth2_workflow.html
# def authentication_oauth2():


# --- CRUD Operations ---

DEFAULT_TIMEOUT = 100  # seconds before exception is raised if server has not responded
Response = req.Response


def create(
    url: str, data: Any = None, auth: Optional[AUTH_TYPE] = None
) -> req.Response:
    """Method that creates - performs an HTTP 'POST' request"""
    response = req.post(url, data=data, timeout=DEFAULT_TIMEOUT, auth=auth)
    # LOG.debug(f'response: {response}')
    return response


def get(url: str, auth: Optional[AUTH_TYPE] = None) -> req.Response:
    """Method that reads/fetches - performs an HTTP 'GET' request"""
    response = req.get(url, timeout=DEFAULT_TIMEOUT, auth=auth)
    # LOG.debug(f'response: {response}')
    return response


def update(
    url: str, data: Any = None, auth: Optional[AUTH_TYPE] = None
) -> req.Response:
    """Method that updates - performs an HTTP 'PUT' request"""
    response = req.put(url, data=data, timeout=DEFAULT_TIMEOUT, auth=auth)
    # LOG.debug(f'response: {response}')
    return response


def delete(url: str, auth: Optional[AUTH_TYPE] = None) -> req.Response:
    """Method that deletes - performs an HTTP 'DELETE' request"""
    response = req.delete(url, timeout=DEFAULT_TIMEOUT, auth=auth)
    # LOG.debug(f'response: {response}')
    return response


# ------------------------ Main Program ------------------------

ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
BASENAME = "http_boilerplate"
LOG: log.Logger = log.get_logger(BASENAME)  # Initialize the logger

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

    RES = get("https://api.github.com/events")
    LOG.debug(f"RESPONSE: {RES}")
    LOG.debug(f"RESPONSE elapsed: {RES.elapsed}")
    # LOG.debug(f'RESPONSE encoding: {RES.encoding}')
    # LOG.debug(f'RESPONSE cookies: {RES.cookies}')
    # LOG.debug(f'RESPONSE history: {RES.history}')
    # LOG.debug(f'RESPONSE headers: {RES.headers}')
    # LOG.debug(f'RESPONSE content: {RES.content}')

    LOG.debug(f"RESPONSE status code: {RES.status_code}")
    RESPONSE_SUCCEEDED = bool(RES.status_code == req.codes.ok)
    LOG.debug(f"RESPONSE status code OK: {RESPONSE_SUCCEEDED}")

    # If we get to this point, assume all went well
    LOG.debug("--------------------------------------------------------")
    LOG.debug("--- end point reached :3 ---")
    sh.exit_process()
