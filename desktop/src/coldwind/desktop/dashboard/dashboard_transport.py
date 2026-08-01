import json
import os
import select
import socket
import subprocess
import sys
from abc import abstractmethod
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, override

from coldwind.core.mcp.mcp_register_structure import ServerConfig
from coldwind.core.system_logging.debug_protocol import LogEntry
from coldwind.core.system_logging.debug_protocol.dashboard_transport import (
    DashboardManager,
)
from coldwind.desktop.runtime.DesktopContext import DesktopRunTimeContext


class SocketManager:
    """
    Manages socket connections for the dashboard debug server.

    This class is responsible for launching and managing the debug server
    as a subprocess on either the local system or a remote machine.

    The server binds to port 59700 and its main entry point is the
    :meth:`start_server` method, which is invoked when the server is
    launched as a subprocess. The socket connection between the
    subprocess and this manager is maintained here.

    All server-related constants are defined at the class level to keep
    the subprocess orchestration logic cleanly separated from the server
    process itself.

    Attributes:
        SERVER_PORT (int): The port the debug server binds to (59700).
    """

    _instance: "SocketManager | None" = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    # TODO: sever related code dynamically inserting here if todo remains that means the server related code is incomplete

    @dataclass(frozen=True)
    class ServerConfig:
        SERVER_PORT: int = 59700
        SERVER_HOST: str = "127.0.0.1"
        LISTNERS: int = 1
        BAND_WIDTH: int = 1024 * 1024

        _instance: "ServerConfig | None" = None

        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    # NOTE:_ after receiving any message through the socket SocketMnaager.process_message
    # where we would validate the message and print to the rich CREATE_NEW_CONSOLE
    #

    class ServerSocketManager:
        _instance: "SocketManager.ServerSocketManager | None" = None

        server_socket: socket.socket | None = None
        client_socket: socket.socket | None = None
        connection_alive: bool = False

        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super().__new__(cls, *args, **kwargs)
            return cls._instance

        def start_server(self):
            # NOTE:- this runs in a different process, listens on defined constants
            config = SocketManager.ServerConfig()

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            # configuring up socket and tcp options
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

            # connection
            self.server_socket.bind((config.SERVER_HOST, config.SERVER_PORT))
            self.server_socket.listen(config.LISTNERS)

            self.server_socket.settimeout(5)

            try:
                self.client_socket, client_address = self.server_socket.accept()
                self.connection_alive = True
            except OSError:
                self.connection_alive = False
                raise
            except KeyboardInterrupt:
                self.connection_alive = False
                sys.exit(1)

        def recieve_raw_log(self, queue_ptr):
            """
            *** LIFO queue ptr required to insert the message we got from the client ~!!
            """
            ##NOTE: only raw message would be taken from here, no debugging printing here
            config = SocketManager.ServerConfig()
            while self.client_socket and self.connection_alive:
                data = self.client_socket.recv(config.BAND_WIDTH)
                try:
                    if not data:
                        # graceful disconnect
                        self.connection_alive = False
                        break
                    queue_ptr.append(data.decode())
                except socket.timeout:
                    raise
                except ConnectionRefusedError:
                    raise
                finally:
                    self.client_socket.close()
                    if self.server_socket:
                        self.server_socket.close()

    #
    # TODO:- Dashboard related code like ensure socket connection is open. Reopen after accidental closing
    # TODO:- sending logs related code below would be orchestrated into the dashboard using just one method api
    #

    class ClientSocketManager:
        _instance: "SocketManager.ClientSocketManager | None" = None

        connection_alive: bool = False
        client_socket: socket.socket | None = None

        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super().__new__(cls, *args, **kwargs)
            return cls._instance

        def connect_to_server(self):
            config = SocketManager.ServerConfig()

            self.client_socket = socket.socket(
                socket.AddressFamily.AF_INET, socket.SocketKind.SOCK_STREAM
            )

            try:
                self.client_socket.connect((config.SERVER_HOST, config.SERVER_PORT))
                self.connection_alive = True
            except (
                ConnectionRefusedError,
                TimeoutError,
                OSError,
                PermissionError,
            ):
                ###NOTE: could not make connection to server
                self.connection_alive = False
                raise

        def send_message(self, data: bytes):
            if not self.connection_alive or not self.client_socket:
                return
            try:
                self.client_socket.sendall(data)
            except (ConnectionResetError, BrokenPipeError):
                ####NOTE: server got disconnected mid session
                self.connection_alive = False
                raise

        def is_connected_status(self) -> bool:  ## False for closed
            ##NOTE: client side is_connected_status method optimized for client_socket and sending
            ##TODO: currently basic optimization only

            if self.connection_alive:
                # first check the ERROR flag, then look up the FIN byte in the kernel's socket buffer
                ## checking for RST flag (reset flag) of a gracefully closed server
                error_socket = self.client_socket.getsockopt(
                    socket.SOL_SOCKET, socket.SO_ERROR
                )
                if error_socket:
                    return False

                # no error but socket hasn't got any FIN flag in the client's mailbox
                # NOTE: RST flag usually stored in the error stack, but the FIN flag is
                # delivered to the socket expecting we would read it !!
                fin_read, _, _ = select.select(
                    [self.client_socket], [], [], 0
                )  ### NOTE: returns whether we got something in the mailbox or not !!
                if fin_read:
                    ## we got any data back that is not expected because the server is
                    ## not programmed to do so — server should only receive, not send
                    fin_data = self.client_socket.recv(1, socket.MSG_PEEK)
                    return len(fin_data) > 0  ## FIN flag is typically b'' (len is 0)
                return True
            return False  ## connection already lost


class DesktopDashboardManager(DashboardManager):
    """Desktop implementation of :class:`DashboardManager`.

    Provides the desktop-specific logic for starting and managing the
    debug dashboard, including launching the server subprocess via
    :class:`SocketManager`.
    """

    _instance: "DesktopDashboardManager | None" = None

    server_process: subprocess.Popen | None = None
    data_queue: deque | None = None  # for maintaining messages to send to the dashboard

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    @classmethod
    @override
    def start_dashboard(cls) -> None:
        """Start the desktop dashboard.

        Delegates to the parent :meth:`DashboardManager.start_dashboard`
        implementation.
        """
        # client_manager = SocketManager.ClientSocketManager()

        if os.name == "nt":
            cmd: list[Any] = [sys.executable, Path.cwd() / "runner_server.py"]
            cls.server_process = subprocess.Popen(
                cmd, cwd=Path.cwd(), creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:

            # Enhanced terminal commands with proper working directory and UV
            cwder = Path.cwd()
            runner_server_path = Path(__file__).absolute().parent / "runner_server.py"
            terminals = [
                # qterminal with bash wrapper for persistence
                [
                    "qterminal",
                    "-e",
                    "bash",
                    "-c",
                    f"cd '{cwder}' && uv run python '{runner_server_path}'; echo 'Log server ended. Press Enter to close...'; read",
                ],
                # gnome-terminal with bash wrapper for persistence
                [
                    "gnome-terminal",
                    "--",
                    "bash",
                    "-c",
                    f"cd '{cwder}' && uv run python '{runner_server_path}'; echo 'Log server ended. Press Enter to close...'; read",
                ],
                # xterm with hold flag
                [
                    "xterm",
                    "-hold",
                    "-e",
                    "bash",
                    "-c",
                    f"cd '{cwder}' && uv run python '{runner_server_path}'",
                ],
                # konsole with hold flag
                [
                    "konsole",
                    "--hold",
                    "-e",
                    "bash",
                    "-c",
                    f"cd '{cwder}' && uv run python '{runner_server_path}'",
                ],
                # tmux as persistent fallback
                [
                    "tmux",
                    "new-session",
                    "-d",
                    "-s",
                    "ai_logs",
                    f"cd '{cwder}' && uv run python '{runner_server_path}'",
                ],
            ]

            for active_terminal in terminals:
                if (
                    subprocess.run(
                        ["which", active_terminal[0]], capture_output=True
                    ).returncode
                    == 0
                ):
                    cmd = active_terminal
                    break

            cls.server_process = subprocess.Popen(cmd)

        # TODO: this is causing issue because the server got spawned but the actual runner script didnt make to actually ran up to listen and accept
        # so if we call this immediately that connect to the port but the issue is server is not listening to port for now (1-2 seconds cold start up cost)
        # we are currently making it comment out and calling some where after delay !! (into handler file)
        # client_manager.connect_to_server()

    @classmethod
    @abstractmethod
    @override
    def send_to_dashboard(cls, log_entry: LogEntry, **kwargs):
        if cls.server_process and cls.server_process.poll() is None:
            # server process is alive
            client_manager = SocketManager.ClientSocketManager()
            if client_manager.is_connected_status():
                # connection is alive
                # converting the log_entry to the payload (by Defualt enums are not serialise-able for the json )
                payload_log_entry = asdict(log_entry)
                print(payload_log_entry)
                data = json.dumps(asdict(log_entry), indent=2).encode()
                client_manager.send_message(data)
                return

            # @ connection is dead
            # NOTE: connection is dead, the data also did not reach dashboard server
            print("server process is alive but connection is dead")
            return
        ##TODO: this is causing race condition becasue the server is gettings started but not started fully to match above if statement and relaunching it is causing spawning many mpore windows that are crashing application

        """
        OPTION 1:- we can create lock file which would gonna tell us that does the server is in the mid way !! and at axit of the server application we would 
        manage to actually delete that lock file !! and in the lock file we would print the pipd of the server for which we can eval !! the current server is 
        Computational expensive 
        """
        # print("server is dead, relaunching it")
        # cls.start_dashboard()
