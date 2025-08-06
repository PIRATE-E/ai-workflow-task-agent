import atexit
import os
import signal
import socket
import sys
from pathlib import Path

import winsound

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings


class SocketCon:
    got_killed: bool = None  # Flag to indicate if the server was killed

    def __init__(self, _client_socket: socket.socket):
        self.client_socket = _client_socket

    def send_error(self, error_message: str, close_socket: bool = False):
        try:
            #     check whether the socket is connected
            if not self._is_connected():
                print(error_message, flush=True, file=sys.stderr)
                raise socket.error("Socket is not connected.")
            # Send the error message
            else:
                # print("Sending error message: ", error_message, flush=True, file=sys.stderr)
                winsound.Beep(7933, 500)  # Beep sound for error notification
                self.client_socket.sendall(error_message.encode('utf-8'))
            # self.client_socket.sendall(error_message.encode('utf-8'))
        except socket.error as e:
            if str(e) == "Socket is not connected.":
                pass
            else:
                print(f"Error sending message: {e}")
        finally:
            if close_socket:
                self.client_socket.close()

    def receive_error(self) -> str:
        try:
            data = self.client_socket.recv(1024)
            return data.decode('utf-8')
        except socket.error as e:
            print(f"Error receiving message: {e}")
            return ""

    def _is_connected(self):
        try:
            # Use getsockopt to check socket state without sending data
            # This works for both unidirectional and bidirectional connections
            error = self.client_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if error:
                return False

            # Additional check: see if socket is still connected
            # This uses a more reliable method that doesn't send data
            try:
                # Check if socket is readable (has data or is closed)
                import select
                ready, _, _ = select.select([self.client_socket], [], [], 0)
                if ready:
                    # Socket is readable - peek at data without consuming it
                    data = self.client_socket.recv(1, socket.MSG_PEEK)
                    return len(data) > 0  # If no data, connection is closed
                return True  # Socket exists and no error
            except socket.error:
                return False
        except socket.error:
            return False
        except Exception as e:
            print(f"Unexpected error in connection check: {e}")
            return False


def signal_handler(signum, frame):
    """Handle termination signals gracefully"""
    print(f"Received signal {signum}, shutting down server...")
    SocketCon.got_killed = True


def cleanup_lock_file():
    """Remove lock file on exit"""
    lock_file = settings.BASE_DIR / 'basic_logs' / 'server.lock'
    try:
        if os.path.exists(lock_file):
            os.remove(lock_file)
            print("Lock file removed")
    except Exception as e:
        print(f"Error removing lock file: {e}")


def create_lock_file():
    """Create lock file to prevent multiple instances"""
    lock_file = settings.BASE_DIR / 'basic_logs' / 'server.lock'
    # Check if another instance is already running
    if os.path.exists(lock_file):
        try:
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())

            # Check if the process is still running
            try:
                os.kill(pid, 0)  # This doesn't kill, just checks if process exists
                print(f"Another server instance is already running (PID: {pid})")
                return False
            except OSError:
                # Process doesn't exist, remove stale lock file
                os.remove(lock_file)
                print("Removed stale lock file")
        except (ValueError, FileNotFoundError):
            # Invalid or missing lock file, remove it
            try:
                os.remove(lock_file)
            except Exception as e:
                print(f"Error removing stale lock file: {e}")
                pass

    # Create new lock file
    try:
        os.makedirs(os.path.dirname(lock_file), exist_ok=True)
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))
        print(f"Created lock file with PID: {os.getpid()}")
        return True
    except Exception as e:
        print(f"Error creating lock file: {e}")
        return False


if __name__ == '__main__':
    # Check for existing instance and create lock file
    if not create_lock_file():
        print("Exiting: Another server instance is already running")
        sys.exit(1)

    # Register cleanup function
    atexit.register(cleanup_lock_file)

    # Set up signal handlers for graceful shutdown
    try:
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        # On Windows, also handle SIGBREAK
        if hasattr(signal, 'SIGBREAK'):
            signal.signal(signal.SIGBREAK, signal_handler)
    except Exception as e:
        print(f"Warning: Could not set up signal handlers: {e}")

    # Initialize server
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow socket reuse
        server_socket.bind(('localhost', 5390))
        server_socket.listen(1)
        server_socket.settimeout(1)  # Shorter timeout to check got_killed flag more frequently
        listening = True
        SocketCon.got_killed = False  # Flag to indicate if the server was killed

        print("Server is listening...")

        while listening and not SocketCon.got_killed:
            try:
                client_socket, addr = server_socket.accept()
                print(f"Connection from {addr}")
                try:
                    socket_con = SocketCon(client_socket)
                    while not SocketCon.got_killed and client_socket:
                        received_error = socket_con.receive_error()
                        if not received_error:
                            print("No data received, closing connection.", flush=True, file=sys.stderr)
                            break  # Client disconnected or error occurred
                        print(f"{received_error}", flush=True, file=sys.stderr)
                    listening = False  # Exit the loop after handling the connection
                finally:
                    client_socket.close()
            except socket.timeout:
                # Check got_killed flag on timeout and continue if not killed
                if SocketCon.got_killed:
                    print("Server shutdown requested, exiting...")
                    break
                continue  # Continue listening if not killed
            except Exception as e:
                if not SocketCon.got_killed:
                    print(f"Error accepting connection: {e}")
                break

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        if server_socket:
            print("Closing server socket...")
            server_socket.close()
        cleanup_lock_file()
        print("Server shutdown complete.")
