#!/usr/bin/env python
"""Common business logic for socket interactions"""

# --- Global Socket Commands ---
# socket_hostname       Returns hostname string

# --- SocketContext Class Commands ---
# socket_open           Connect to hostname/port as server or client
# socket_close          Close future requests and shutdown connection
# socket_send_data      Send data to socket
# socket_receive_data   Retrieve data from socket
# socket_next_client    Returns the next client's socket connection and address

import argparse
import socket

import logging_boilerplate as log

# ------------------------ Methods ------------------------


def socket_hostname():
    """Method that fetches the hostname of a socket"""
    return socket.gethostname()


def socket_hostport(sock):
    """Method that fetches the hostport of a socket"""
    try:
        address = sock.getsockname()  # returns tuple(IP, port) for server
        # address = sock.getpeername() # returns tuple(IP, port) for client connection
        return address[1]
    except Exception:
        return 0


# ------------------------ Class Converted Methods ------------------------


def socket_open(hostname: str, hostport: int, connect_as="client", timeout=30):
    """Method that opens a socket"""
    connection_whitelist = ["server", "client"]
    if connect_as not in connection_whitelist:
        raise ValueError(
            f"socket_open() expects 'connect_as' parameter to use approved values: {connection_whitelist}"
        )
    # Generate socket
    sock_family = socket.AF_INET
    sock_type = socket.SOCK_STREAM
    sock = socket.socket(sock_family, sock_type)
    sock.settimeout(timeout)

    if connect_as == "client":
        # Open socket client to communicate with a server
        try:
            # LOG.debug(f"Connecting to host: {hostname}:{hostport}")
            # Always provide socket.connect() with a tuple
            sock.connect((hostname, hostport))
            # LOG.debug(f"Successfully connected to host: {hostname}:{hostport}")
        except Exception as e:
            LOG.error(f"An error occurred while connecting socket: {e}")
            return

    elif connect_as == "server":
        # Open socket server as listener for client requests
        try:
            # LOG.debug(f"Connecting to host: {hostname}:{hostport}")
            # Always provide socket.bind() with a tuple
            sock.bind((hostname, hostport))
            sock.listen(5)
            # LOG.debug(f"Successfully connected to host: {hostname}:{hostport}")
        except Exception as e:
            LOG.error(f"An error occurred while connecting socket: {e}")
            return

    return sock


def socket_close(sock: socket.socket):
    """Method that closes a socket"""
    # LOG.debug("(SocketContext:socket_close): Init")
    # LOG.debug("(SocketContext:socket_close): Closing connection to host.")

    # Halt all future operations (sending/receiving) on the socket connection
    try:
        sock.shutdown(socket.SHUT_RDWR)
        # LOG.debug(f"(SocketContext:socket_close): Shutdown {self.hostname}:{self.hostport} socket traffic")
    except Exception as exc:
        if exc.errno == 107:
            pass  # [Errno 107] Transport endpoint is not connected
        else:
            # LOG.error(f"(SocketContext:socket_close): An error occurred while attempting to close the connection: {e}")
            return
    # Close the socket connection
    try:
        sock.close()
    except Exception as e:
        # LOG.error(f"(SocketContext:socket_close): An error occurred while attempting to close the connection: {e}")
        return

    # LOG.error("(SocketContext:socket_close): Socket connection closed")
    return True


def socket_send_data(sock: socket.socket, message):
    """Method that sends socket data"""
    # LOG.debug("(SocketContext:socket_send_data): Init")
    # LOG.debug(f"(SocketContext:socket_send_data): Sending message: {message}")
    # Returns None on success; raises Exception on error
    result = sock.sendall(message)
    return result


def socket_receive_data(sock: socket.socket, byteLimit=4096):
    """Method that receives socket data"""
    # LOG.debug("(SocketContext:socket_receive_data): Init")
    status = ""

    try:
        data = sock.recv(byteLimit)
        # LOG.debug(f"(SocketContext:socket_receive_data): Data received: {data}")
        if data:
            return (data, None)
        else:
            # A zero length receive indicates socket is closed
            status = "SOCKET_CLOSED"
            # LOG.warning("Empty data response indicates socket was closed.")
    except socket.timeout:
        status = "TIMED_OUT"
        # LOG.warning("Timed out waiting for data from socket.")
    except socket.error as e:
        status = "SOCKET_ERROR"
        # LOG.error(f"Socket error: {e}")

    return (None, status)


def socket_next_client(sock):
    """Method that advances to next socket"""
    # LOG.debug("(SocketContext:socket_next_client): Init")
    try:
        (conn, addr) = sock.accept()
        return (conn, addr)
    except socket.timeout:
        # LOG.debug("Socket timed out waiting for a client.")
        return (None, None)


# ------------------------ Classes ------------------------


# 'conn' accepts a socket instance, 'server', or 'client'
class SocketContext(object):
    """Class to track socket context"""

    def __init__(
        self, conn=None, hostname: str = "", hostport: int = 0, timeout: int = 30
    ):
        # Initial values
        self.family = socket.AF_INET
        self.type = socket.SOCK_STREAM
        # Generate new socket
        if isinstance(conn, socket.socket):
            self.sock = conn
            # TODO: verify connection
        else:
            # Verify values when creating socket connection
            connection_whitelist = ["server", "client"]
            if not conn in connection_whitelist:
                raise ValueError(
                    f"SocketContext() expects 'conn' parameter as choices: {connection_whitelist}"
                )

            self.sock = socket.socket(self.family, self.type)
            self.sock.settimeout(timeout)

            if conn == "client":
                # Open socket client to communicate with a server
                try:
                    # LOG.debug(f"(SocketContext:connect): Connecting to host: {hostname}:{hostport}")
                    # Always provide socket.connect() with a tuple
                    self.sock.connect((hostname, hostport))
                    # LOG.debug(f"(SocketContext:connect): Successfully connected to host: {hostname}:{hostport}")
                except Exception as e:
                    # LOG.error(f"An error occurred while connecting socket: {e}")
                    self.sock = None

            elif conn == "server":
                # Open socket server as listener for client requests
                try:
                    # LOG.debug(f"(SocketContext:ConnectAsServer): Connecting to host: {hostname}:{hostport}")
                    # Always provide socket.bind() with a tuple
                    self.sock.bind((hostname, hostport))
                    self.sock.listen(5)
                    # LOG.debug(f"(SocketContext:ConnectAsServer): Successfully connected to host: {hostname}:{hostport}")
                except Exception as e:
                    # LOG.error(f"An error occurred while connecting socket: {e}")
                    self.sock = None

    def __repr__(self):
        return self.sock

    def __str__(self):
        return str(self.sock)

    def close(self):
        """Method that closes SocketContext"""
        # LOG.debug("(SocketContext:close): Init")
        LOG.debug("(SocketContext:close): Closing connection to host.")
        try:
            # Halt send and receive of connection
            self.sock.shutdown(socket.SHUT_RDWR)
            LOG.debug(
                f"(SocketContext:close): Shutdown {self.hostname}:{self.hostport} socket traffic."
            )
            # Close all future operations on the socket
            self.sock.close()
            LOG.debug("(SocketContext:close): Socket connection closed.")
        except Exception as e:
            LOG.debug(
                f"(SocketContext:close): An error occurred while attempting to close the connection: {e}"
            )

    def send_data(self, message):
        """Method that sends data from SocketContext"""
        # LOG.debug("(SocketContext:send_data): Init")
        LOG.debug(f"(SocketContext:send_data): Sending message: {message}")
        # Returns None on success; raises Exception on error
        result = self.sock.sendall(message)
        return result

    def receive_data(self, byteLimit=4096):
        """Method that receives data from SocketContext"""
        # LOG.debug("(SocketContext:receive_data): Init")
        status = ""
        try:
            data = self.sock.recv(byteLimit)
            LOG.debug(f"(SocketContext:receive_data): Data received: {data}")
            if data:
                return (data, None)
            else:
                # A zero length receive indicates socket is closed
                status = "SOCKET_CLOSED"
                LOG.warning(
                    "(SocketContext:receive_data): empty data response indicates socket was closed"
                )
        except socket.timeout:
            status = "TIMED_OUT"
            LOG.warning(
                "(SocketContext:receive_data): timed out waiting for data from socket"
            )
        except socket.error as e:
            status = "SOCKET_ERROR"
            LOG.error(f"(SocketContext:receive_data): socket error: {e}")
        return (None, status)

    def ConnectAsClient(self, hostname, hostport):
        """Method that communicates to the server socket as client from SocketContext"""
        LOG.debug("(SocketContext:ConnectAsClient): Init")
        if self.connected:
            return True
        self.hostname = str(hostname)
        self.hostport = int(hostport)
        try:
            LOG.debug(
                f"(SocketContext:ConnectAsClient): Connecting to host: {self.hostname}:{self.hostport}"
            )
            # Always provide socket.connect() with a tuple
            self.sock.connect((self.hostname, self.hostport))
            self.connected = True
            LOG.debug(
                f"(SocketContext:ConnectAsClient): Successfully connected to host: {self.hostname}:{self.hostport}"
            )
        except Exception as e:
            LOG.error(
                f"(SocketContext:ConnectAsClient): An error occurred while connecting socket: {e}"
            )
        return self.connected

    def ConnectAsServer(self, hostname, hostport):
        """Method that communicates to client sockets as the server from SocketContext"""
        LOG.debug("(SocketContext:ConnectAsServer): Init")
        if self.connected:
            return True
        self.hostname = str(hostname)
        self.hostport = int(hostport)
        try:
            LOG.debug(
                f"(SocketContext:ConnectAsServer): Connecting to host: {self.hostname}:{self.hostport}"
            )
            # Always provide socket.bind() with a tuple
            self.sock.bind((self.hostname, self.hostport))
            self.sock.listen(5)
            self.connected = True
            LOG.debug(
                f"(SocketContext:ConnectAsServer): Successfully connected to host: {self.hostname}:{self.hostport}"
            )
        except Exception as e:
            LOG.error(
                f"(SocketContext:ConnectAsServer): An error occurred while connecting socket: {e}"
            )
        return self.connected

    def NextClient(self):
        """Method that communicates to next client socket from SocketContext"""
        LOG.debug("(SocketContext:NextClient): Init")
        try:
            (conn, addr) = self.sock.accept()
        except socket.timeout:
            LOG.debug("(SocketContext:NextClient): socket timed out waiting for client")
            return (None, None)
        conn = SocketContext(conn)
        return (conn, addr)


# ------------------------ Main program ------------------------

# Initialize the logger
BASENAME = "socket_boilerplate"
ARGS: argparse.Namespace = argparse.Namespace()  # for external modules
LOG: log.Logger = log.get_logger(BASENAME)

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
    LOG_HANDLERS = log.default_handlers(ARGS.debug, ARGS.log_path)
    log.set_handlers(LOG, LOG_HANDLERS)

    LOG.debug(f"ARGS: {ARGS}")
    LOG.debug("------------------------------------------------")

    # Initialize the socket
    HOSTNAME = socket_hostname()
    HOSTPORT = 5665
    SOCK = SocketContext("server", HOSTNAME, HOSTPORT)
    SOCK.close()


# :: Usage Example ::
# sudo python /root/.local/lib/python2.7/site-packages/socket_boilerplate.py
