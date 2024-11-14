#!/usr/bin/env python
"""Common business logic for multiple processes"""

# --- ProcessEvent Commands ---
# .Run, .IsRunning

# --- ProcessPool Commands ---
# .Close, .RunAsync, .await_results

import argparse
import multiprocessing
import random
import time
from typing import Any, Callable, Optional, Tuple

import logging_boilerplate as log

# ------------------------ Classes ------------------------


class ProcessEvent(object):
    def __init__(self):
        LOG.debug("(ProcessEvent:__init__): Init")
        # Initial values
        self.running = bool()
        self.event = multiprocessing.Event()

    def Run(self):
        try:
            self.event.set()
        except Exception:
            return False
        return True

    def IsRunning(self):
        return self.event.is_set()


class ProcessPool(object):
    def __init__(self):
        LOG.debug("(ProcessPool:__init__): Init")
        # Initial values
        self.running = bool()
        self.pool = multiprocessing.Pool()

    def Close(self):
        self.pool.close()
        self.pool.join()

    def RunAsync(self, func, args_list):
        if not callable(func):
            self.running = False
            return
        try:
            # map_async recommended over apply_async (not used in Python3)
            self.processes = pool.map_async(func, args_list)
            self.running = True
        except Exception:
            self.running = False
        return self.running

    def await_results(self):
        self.Close()
        if running:
            # results = [p.get() for p in self.processes]
            results = self.processes.get()
            return results
        else:
            return None


# Supports either a single function with list of args
# OR takes a list of functions with a list of list of args (lengths must match)
def ProcessPoolAwait(func, args_list, callback=None, log=None):
    if not (callable(func) and isinstance(args_list, list)):
        return
    pool = ProcessPool(log=log)
    pool.RunAsync(func, args_list)
    results = pool.await_results()
    return results


# Supports either a single function with list of args
# OR takes a list of functions with a list of list of args (lengths must match)
def ProcessPoolAsync(func, args_list, callback=None):
    if not callable(func):
        return
    # Create pool and args enumerable
    pool = multiprocessing.Pool()
    # Run async processes, close pool, await (join), gather results
    # recommended over apply_async, which isn't used anymore in Python3
    processes = pool.map_async(func, args_list)
    pool.close()
    pool.join()
    # results = [p.get() for p in processes]
    results = processes.get()
    return results


def rando(args: Tuple):
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
    # print("rng_generate): Init")
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


def data_callback(pack):
    # print("data_callback): Init")
    for (key, val) in pack.items():
        # print(f"key: {key}")
        # print(f"val: {val}")
        data[key] = val


# def timer((func, *args, **kwargs)):
def timer(args: Tuple[Callable, Any]):
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
    # """worker function"""
    # pid = os.getpid()
    # print("Worker pid: {pid}")
    # process_name = multiprocessing.current_process().name
    # print("Worker process name: {process_name}")
    name = multiprocessing.current_process().name
    print(f"{name}, starting...")
    time.sleep(2)
    print(f"{name}, exiting...")


def my_service():
    name = multiprocessing.current_process().name
    print(f"{name}, starting...")
    # pid = os.getpid()
    # print("Worker pid: {pid}")
    # process_name = multiprocessing.current_process().name
    # print("Worker process name: {process_name}")
    time.sleep(3)
    print(f"{name}, exiting...")


# ------------------------ Test Program ------------------------

# socket_listener()
def MultiprocessSocketTester(hostName, hostPort, logger: Optional[log.Logger] = None):
    # Initialize the logger
    LOG = log.get_logger(logger)
    LOG.debug("(MultiprocessSocketTester): Init")

    # Create server socket to communicate with clients
    serverSocket = SocketContext(log=logger)
    connected = serverSocket.ConnectAsServer(hostName, hostPort)
    if not connected:
        LOG.debug("(MultiprocessSocketTester): not connected")
        Fail()

    # Signal the main thread that we are up and listening
    LOG.info(f"Socket listener started and listening on {hostName}:{hostPort}")

    LOG.debug("(MultiprocessSocketTester): ACTION METHOD")

    # Create server socket to communicate with clients
    serverSocket = SocketContext(log=self.loggerOptions)
    connected = serverSocket.ConnectAsServer(self.hostName, self.config.hostPort)
    if not connected:
        self.Fail()

    # Signal the main thread that we are up and listening
    bindString = f"{self.hostName}:{self.config.hostPort}"
    LOG.info(f"Socket listener started and listening on {bindString}")

    # Create a holder for our client threads
    clients = {}
    # Accept connections until told to stop
    newConn = False
    while True:
        # Wrap the blocking accept in a try because it will raise
        # an error when the timeout set by 'settimeout' is reached
        # This allows us to break out and periodically check if we
        # need to exit or not.
        try:
            (conn, addr) = serverSocket.accept()
            newConn = True
        except socket.timeout:
            LOG.debug("Socket timed out waiting for a client.")

        if newConn:
            # Create args enumerable and run against process pool
            args_list = [(conn, addr)]
            results = ProcessPoolAsync(self.socket_client, args_list)
            # Print results
            print(f"results: {results}")

            # Launch a new thread to service the client
            clThread = threading.Thread(target=self.socket_client, args=(conn, addr))
            clThread.start()
            addrString = ':'.join([str(x) for x in addr])
            clients[clThread] = addrString
            newConn = False
        # If we are requested to die, break out of the while loop
        if self.killSocketEvent.is_set():
            LOG.warning(f"Socket listener ("{bindString}") detected exit request, exiting.")
            break
        else:
            continue

    # After the socket server/listener exits wait for clients to finish
    while len(clients) > 0:
        for thrd in clients.keys():
            if thrd.is_alive():
                LOG.debug("Waiting for client to disconnect: " + clients[thrd])
            else:
                clients.pop(thrd)
        sleep(1)

    # When finished accepting connections clean up the socket
    serverSocket.Close()
    LOG.info("Socket listener shutdown (" + bindString + ")")


# ------------------------ Main Program ------------------------

# Initialize the logger
BASENAME = "shell_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: log.Logger = log.get_logger(BASENAME)

if __name__ == "__main__":
    iterations = range(10)

    # --- MAP ASYNC ---

    start_time = time.time()
    # Create args enumerable and run against process pool
    args_list = []
    for i in iterations:
        args_list.append((i, "test"))
    results = ProcessPoolAsync(rando, args_list)
    # Print results
    print(f"results: {results}")
    end_print(start_time)

    # --- MAP ASYNC (class) ---

    start_time = time.time()
    # Create args enumerable and run against process pool
    args_list = []
    for i in iterations:
        args_list.append((i, "test"))
    results = ProcessPoolAwait(rando, args_list)
    # Print results
    print(f"results: {results}")
    end_print(start_time)


# :: Usage Example ::
# sudo python /root/.local/lib/python2.7/site-packages/multiprocess_boilerplate.py
# ps -eaf | grep -i python
