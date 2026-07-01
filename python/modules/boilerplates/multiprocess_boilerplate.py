#!/usr/bin/env python
"""Common business logic for multiple processes"""

# --- ProcessEvent Commands ---
# .Run, .IsRunning

# --- ProcessPool Commands ---
# .Close, .RunAsync, .await_results

import argparse
import multiprocessing
import random
import socket
import sys
import threading
import time
from collections.abc import Callable

import logging_boilerplate as log
from socket_boilerplate import SocketContext

# ------------------------ Classes ------------------------


class ProcessEvent(object):
    def __init__(self):
        LOG.debug("(ProcessEvent:__init__): Init")
        # Initial values
        self.running: bool = False
        self.event = multiprocessing.Event()

    def Run(self) -> bool:
        try:
            self.event.set()
        except Exception:
            return False
        return True

    def IsRunning(self) -> bool:
        return self.event.is_set()


class ProcessPool(object):
    def __init__(self):
        LOG.debug("(ProcessPool:__init__): Init")
        # Initial values
        self.running: bool = False
        self.pool = multiprocessing.Pool()
        self.processes = None

    def Close(self):
        self.pool.close()
        self.pool.join()

    def RunAsync(self, func: Callable, args_list: list) -> bool:
        if not callable(func):
            self.running = False
            return False
        try:
            # map_async recommended over apply_async (not used in Python 3)
            self.processes = self.pool.map_async(func, args_list)
            self.running = True
        except Exception:
            self.running = False
        return self.running

    def await_results(self):
        self.Close()
        if self.running and self.processes:
            results = self.processes.get()
            return results
        else:
            return None


# Supports either a single function with list of args
# OR takes a list of functions with a list of list of args (lengths must match)
def ProcessPoolAwait(func: Callable, args_list: list):
    if not (callable(func) and isinstance(args_list, list)):
        return None
    pool = ProcessPool()
    pool.RunAsync(func, args_list)
    results = pool.await_results()
    return results


# Supports either a single function with list of args
# OR takes a list of functions with a list of list of args (lengths must match)
def ProcessPoolAsync(func: Callable, args_list: list):
    if not callable(func):
        return None
    # Create pool and args enumerable
    pool = multiprocessing.Pool()
    # Run async processes, close pool, await (join), gather results
    processes = pool.map_async(func, args_list)
    pool.close()
    pool.join()
    results = processes.get()
    return results


def rando(args: tuple):
    (in_num, tester) = args
    num = random.random()
    print(f"{in_num} '{tester}' in with rando: {num}")

    try:
        data[in_num] = num
    except Exception:
        print("rando nope!")

    result = dict()
    result[in_num] = num
    return result


def rng_generate(in_num, tester):
    num = random.random()
    print(f"{in_num} '{tester}' in with rng_generate: {num}")
    try:
        data[in_num] = num
    except Exception:
        print("rng_generate): Nope!")

    result = dict()
    result[in_num] = num
    return result


data = {}


def end_print(start_time):
    end_time = time.time() - start_time
    print(f"time taken: {end_time}")
    print("")


def data_callback(pack: dict):
    for key, val in pack.items():
        data[key] = val


def timer(args: tuple[Callable, object]):
    (func, val) = args

    start_time = time.time()
    func(val)
    end_time = time.time() - start_time

    print(f"val: {val}")
    print(f"end time: {end_time}")
    print("")


def random_num():
    num = random.random()
    print(num)


def worker():
    name = multiprocessing.current_process().name
    print(f"{name}, starting...")
    time.sleep(2)
    print(f"{name}, exiting...")


def my_service():
    name = multiprocessing.current_process().name
    print(f"{name}, starting...")
    time.sleep(3)
    print(f"{name}, exiting...")


# ------------------------ Test Program ------------------------


class MultiprocessSocketTester:
    def __init__(
        self, host_name: str, host_port: int, logger: log.Logger | None = None
    ):
        self.host_name = host_name
        self.host_port = host_port
        self.logger = logger or LOG
        self.kill_socket_event = threading.Event()

    def fail(self):
        self.logger.error("MultiprocessSocketTester failed to initialize properly.")
        sys.exit(1)

    def socket_client(self, args: tuple):
        # Stub for processing client connections socket testing
        (conn, addr) = args
        self.logger.info(f"Socket client started for: {addr}")

    def run(self):
        self.logger.debug("(MultiprocessSocketTester): Init")

        # Create server socket to communicate with clients
        server_socket = SocketContext()
        connected = server_socket.ConnectAsServer(self.host_name, self.host_port)
        if not connected:
            self.logger.debug("(MultiprocessSocketTester): not connected")
            self.fail()

        # Signal the main thread that we are up and listening
        bind_string = f"{self.host_name}:{self.host_port}"
        self.logger.info(f"Socket listener started and listening on {bind_string}")

        # Create a holder for our client threads
        clients = {}
        # Accept connections until told to stop
        new_conn = False

        while True:
            # Wrap the blocking accept in a try because it will raise an error
            # when the timeout is reached. This allows us to break out and periodically check.
            try:
                (conn, addr) = server_socket.accept()
                new_conn = True
            except socket.timeout:
                self.logger.debug("Socket timed out waiting for a client.")

            if new_conn:
                # Create args enumerable and run against process pool
                args_list = [(conn, addr)]
                results = ProcessPoolAsync(self.socket_client, args_list)
                print(f"results: {results}")

                # Launch a new thread to service the client
                cl_thread = threading.Thread(
                    target=self.socket_client, args=((conn, addr),)
                )
                cl_thread.start()
                addr_string = ":".join([str(x) for x in addr])
                clients[cl_thread] = addr_string
                new_conn = False

            # If we are requested to die, break out of the while loop
            if self.kill_socket_event.is_set():
                self.logger.warning(
                    f'Socket listener ("{bind_string}") detected exit request, exiting.'
                )
                break

        # After the socket server/listener exits wait for clients to finish
        # list() wrapper avoids 'dictionary changed size during iteration' exception
        while len(clients) > 0:
            for thrd in list(clients.keys()):
                if thrd.is_alive():
                    self.logger.debug(
                        "Waiting for client to disconnect: " + clients[thrd]
                    )
                else:
                    clients.pop(thrd)
            time.sleep(1)

        # When finished accepting connections clean up the socket
        server_socket.Close()
        self.logger.info(f"Socket listener shutdown ({bind_string})")


# ------------------------ Main Program ------------------------

# Initialize the logger
BASENAME = "multiprocess_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: log.Logger = log.get_logger(BASENAME)

if __name__ == "__main__":
    iterations = range(10)

    # --- MAP ASYNC ---

    start_time = time.time()
    # Create args enumerable and run against process pool
    test_args_list = []
    for i in iterations:
        test_args_list.append((i, "test"))
    results_async = ProcessPoolAsync(rando, test_args_list)
    # Print results
    print(f"results: {results_async}")
    end_print(start_time)

    # --- MAP ASYNC (class) ---

    start_time = time.time()
    # Create args enumerable and run against process pool
    test_args_list = []
    for i in iterations:
        test_args_list.append((i, "test"))
    results_await = ProcessPoolAwait(rando, test_args_list)
    # Print results
    print(f"results: {results_await}")
    end_print(start_time)


# :: Usage Example ::
# sudo python /root/.local/lib/python2.7/site-packages/multiprocess_boilerplate.py
# ps -eaf | grep -i python
