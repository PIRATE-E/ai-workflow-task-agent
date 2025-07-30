import os
import socket
import subprocess
import sys
import time

# Handle imports - works both as module and standalone script
try:
    # Try relative import first (when run as module)
    from .error_transfer import SocketCon
except ImportError:
    # If relative import fails, try absolute import (when run as script)
    try:
        from error_transfer import SocketCon
    except ImportError:
        # Last resort: add current directory to path and import
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from error_transfer import SocketCon

# Import settings - handle case where it might not be available
from src.config import settings


class SocketManager:
    instance = None
    _socket_con = None
    _log_server_process = None
    _cleanup_in_progress = False  # Flag to prevent new connections during cleanup

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def start_log_server(self):
        """Start the log server as a subprocess"""
        if self._log_server_process is not None:
            # Check if process is still running
            if self._log_server_process.poll() is None:
                print("Log server is already running")
                return True
            else:
                print("Previous log server process has ended")
                self._log_server_process = None

        try:
            # Get the path to error_transfer.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            error_transfer_path = os.path.join(current_dir, 'error_transfer.py')

            if not os.path.exists(error_transfer_path):
                print(f"Error: Could not find error_transfer.py at {error_transfer_path}")
                return False

            print(f"🚀 Starting log server subprocess: {error_transfer_path}")

            # Start the subprocess - choose method based on settings
            log_display_mode = getattr(settings, 'LOG_DISPLAY_MODE', 'separate_window')

            if log_display_mode == 'separate_window':
                # Option 1: Separate console window (recommended)
                if os.name == 'nt':  # Windows
                    self._log_server_process = subprocess.Popen(
                        [sys.executable, error_transfer_path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:  # Linux/Mac
                    self._log_server_process = subprocess.Popen(
                        ['gnome-terminal', '--', sys.executable, error_transfer_path]
                    )
            elif log_display_mode == 'background':
                # Option 2: Background process (logs not visible)
                self._log_server_process = subprocess.Popen(
                    [sys.executable, error_transfer_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            elif log_display_mode == 'file':
                from pathlib import Path
                # Option 3: Log to file
                log_file = settings.BASE_DIR.parent / "basic_logs" / "error_log.txt"  ######
                print(log_file.exists(), "error transfer path exists")
                with open(log_file, 'w') as f:
                    self._log_server_process = subprocess.Popen(
                        [sys.executable, error_transfer_path],
                        stdout=f,
                        stderr=f
                    )
                print(f"📝 Log server output will be written to: {log_file}")
            else:
                # Default: Separate window
                if os.name == 'nt':  # Windows
                    self._log_server_process = subprocess.Popen(
                        [sys.executable, error_transfer_path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:  # Linux/Mac
                    self._log_server_process = subprocess.Popen(
                        ['gnome-terminal', '--', sys.executable, error_transfer_path]
                    )

            print(f"✅ Log server started with PID: {self._log_server_process.pid}")

            # Give the server a moment to start up
            time.sleep(2)

            # Check if the process is still running
            if self._log_server_process.poll() is None:
                print("✅ Log server is running successfully")
                return True
            else:
                print("❌ Log server failed to start")
                self._log_server_process = None
                return False

        except Exception as e:
            print(f"❌ Failed to start log server: {e}")
            self._log_server_process = None
            return False

    def stop_log_server(self):
        """Stop the log server subprocess with enhanced cleanup"""
        if self._log_server_process is not None:
            try:
                print("🛑 Stopping log server...")

                # Check if process is still alive before terminating
                if self._log_server_process.poll() is None:
                    print(f"Terminating log server process (PID: {self._log_server_process.pid})")
                    
                    # First try graceful termination
                    self._log_server_process.terminate()

                    # Wait for process to terminate gracefully
                    try:
                        self._log_server_process.wait(timeout=5)  # Increased timeout
                        print("✅ Log server stopped gracefully")
                    except subprocess.TimeoutExpired:
                        print("⚠️ Log server didn't stop gracefully, forcing termination...")
                        self._log_server_process.kill()
                        try:
                            self._log_server_process.wait(timeout=3)  # Increased timeout
                            print("✅ Log server forcefully terminated")
                        except subprocess.TimeoutExpired:
                            print("❌ Could not terminate log server process")
                            # Try to clean up any remaining processes
                            try:
                                import psutil
                                parent = psutil.Process(self._log_server_process.pid)
                                for child in parent.children(recursive=True):
                                    child.kill()
                                parent.kill()
                                print("✅ Forcefully killed process tree")
                            except ImportError:
                                print("⚠️ psutil not available for process tree cleanup")
                            except Exception as cleanup_error:
                                print(f"⚠️ Error during process tree cleanup: {cleanup_error}")
                else:
                    print("✅ Log server process already terminated")

            except Exception as e:
                print(f"❌ Error stopping log server: {e}")
            finally:
                self._log_server_process = None
                
                # Also clean up any stale lock files
                try:
                    import os
                    lock_file = os.path.join(os.path.dirname(__file__), '..', '..', 'basic_logs', 'server.lock')
                    if os.path.exists(lock_file):
                        os.remove(lock_file)
                        print("🧹 Cleaned up server lock file")
                except Exception as lock_cleanup_error:
                    print(f"⚠️ Error cleaning up lock file: {lock_cleanup_error}")

    def is_log_server_running(self):
        """Check if the log server subprocess is running"""
        if self._log_server_process is None:
            return False
        return self._log_server_process.poll() is None

    def get_socket_connection(self):
        """Get or create the socket connection with adaptive timeout and health checking"""
        if self._cleanup_in_progress:  # Prevent new connections during cleanup
            return None

        # === STEP 1: HEALTH CHECK EXISTING CONNECTION ===
        # Your brilliant insight: Check if connection is HEALTHY, not just exists
        if self._socket_con is not None:
            if self._socket_con._is_connected():
                # Connection exists and is healthy - reuse it
                return self._socket_con
            else:
                # Connection exists but is dead - clear it for reconnection
                print("🔄 Detected dead connection, clearing for reconnection...")
                try:
                    self._socket_con.client_socket.close()
                except Exception as e:
                    print(f"❌ Error closing dead socket: {e}")
                self._socket_con = None



        if self._socket_con is None:
            try:
                if not settings.ENABLE_SOCKET_LOGGING:
                    print("Socket logging is disabled in settings")
                    return None

                # First, try to connect to existing server
                socket_req = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                socket_req.settimeout(0.5)  # Short timeout for initial connection attempt

                try:
                    socket_req.connect((settings.SOCKET_HOST, settings.SOCKET_PORT))
                    self._socket_con = SocketCon(socket_req)
                    print("✅ Connected to existing log server")
                    return self._socket_con

                except (ConnectionRefusedError, socket.timeout):
                    print("📡 No log server found, starting new one...")
                    socket_req.close()

                    # Start the log server
                    if self.start_log_server():
                        # Wait a bit more for server to be ready
                        time.sleep(1)

                        # Try to connect again
                        socket_req = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        socket_req.settimeout(2)  # Longer timeout for new server
                        socket_req.connect((settings.SOCKET_HOST, settings.SOCKET_PORT))
                        self._socket_con = SocketCon(socket_req)
                        print("✅ Connected to newly started log server")
                        return self._socket_con
                    else:
                        print("❌ Failed to start log server")
                        return None

            except Exception as e:
                print(f"❌ Error establishing socket connection: {e}")
                self._socket_con = None

        return self._socket_con

    def send_error(self, message: str):
        """Send error message through socket if available, otherwise print to console"""
        socket_con = self.get_socket_connection()
        if socket_con:
            try:
                socket_con.send_error(message)
            except Exception as e:
                print(f"Failed to send error through socket: {e}")
                print(f"Original error message: {message}")
                # Reset connection on failure so it can be retried
                self._socket_con = None
        else:
            print(f"Socket not available - {message}")

    def is_connected(self):
        """Check if socket connection is active"""
        if self._socket_con and hasattr(self._socket_con, '_is_connected'):
            return self._socket_con._is_connected()
        return False

    def close_connection(self):
        """Close the socket connection and optionally stop the log server"""
        # Close socket connection first
        if self._socket_con and hasattr(self._socket_con, 'client_socket'):
            try:
                self._socket_con.client_socket.close()
                print("Socket connection closed")
            except Exception as e:
                print(f"Error closing socket: {e}")
        self._socket_con = None

        # Stop the log server if we started it
        if self.is_log_server_running():
            print("🔄 Stopping log server subprocess...")
            self.stop_log_server()

    @classmethod
    def cleanup(cls):
        """Simple cleanup - just kill the subprocess"""
        print("🧹 Cleaning up SocketManager...")

        # Set flag to prevent new connections
        if hasattr(cls, 'instance') and cls.instance is not None:
            cls.instance._cleanup_in_progress = True
            instance = cls.instance

            # Close socket first (optional, but good practice)
            if instance._socket_con:
                try:
                    instance._socket_con.client_socket.close()
                    print("🔌 Socket closed")
                except:
                    pass  # Ignore errors
                instance._socket_con = None

            # SIMPLE APPROACH: Just kill the subprocess immediately
            if instance._log_server_process is not None:
                try:
                    print("🛑 Killing log server subprocess...")
                    instance._log_server_process.kill()  # ✅ Direct kill, no waiting
                    print("✅ Log server killed")
                except Exception as e:
                    print(e)
                finally:
                    instance._log_server_process = None

        print("✅ SocketManager cleanup completed")


# Global instance
socket_manager = SocketManager()
