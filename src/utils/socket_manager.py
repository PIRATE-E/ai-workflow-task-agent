import os
import socket
import subprocess
import sys
import time
import pathlib

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
        sys.path.append(pathlib.Path(__file__).resolve().parent)
        from error_transfer import SocketCon

# Import settings - handle case where it might not be available
from src.config import settings

# Structured debug protocol imports (lazy fallback if unavailable)
try:
    from src.ui.diagnostics.debug_message_protocol import DebugMessageSender, LogLevel
except ImportError:  # Minimal fallbacks so legacy still works

    class DebugMessageSender:  # type: ignore
        def __init__(self, socket_connection=None):
            self.socket_connection = socket_connection

        def send_plain_text(self, text: str):
            if self.socket_connection and hasattr(self.socket_connection, "send_error"):
                self.socket_connection.send_error(text)
            else:
                print(text)

        # Unified interface expected below
        def send_debug_message(self, heading, body, level, metadata=None):
            self.send_plain_text(f"[{level}] {heading} - {body} :: {metadata or {}}")

    class LogLevel:  # type: ignore
        INFO = "INFO"
        WARNING = "WARNING"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"


class SocketManager:
    def __init__(self):
        self._socket_connection = None
        self._debug_sender = DebugMessageSender()  # Initialized without connection initially
        self._log_server_process = None
        self._terminal_process = None

    @staticmethod
    def get_socket_con():
        """Get socket connection only when needed"""
        return (
            SocketManager().get_socket_connection()
            if settings.ENABLE_SOCKET_LOGGING
            else None
        )

    def get_socket_connection(self):
        if self._socket_connection is None or not self._socket_connection.is_connected():
            print("📡 No log server found, starting new one...")
            if self.start_log_server():
                # Wait for server to start
                time.sleep(1)
                
                # Create client socket and connect
                try:
                    from src.config import settings
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(2)
                    client_socket.connect((settings.SOCKET_HOST, settings.SOCKET_PORT))
                    
                    self._socket_connection = SocketCon(client_socket)  # Pass client socket to SocketCon
                    
                    # Update debug sender with the new connection
                    self._debug_sender = DebugMessageSender(self._socket_connection)
                    return self._socket_connection
                except Exception as e:
                    print(f"❌ Error establishing socket connection: {e}")
                    self._socket_connection = None
                    return None
            else:
                return None
        return self._socket_connection

    def start_log_server(self):
        # Check if we already have a running process
        if self._log_server_process is not None:
            if self._log_server_process.poll() is None:
                print("Log server is already running")
                return True
            else:
                print("Previous log server process has ended")
                self._log_server_process = None

        try:
            # Get the path to error_transfer.py and project root
            current_dir = pathlib.Path(__file__).resolve().parent
            error_transfer_path = current_dir / "error_transfer.py"
            project_root = current_dir.parent.parent  # Navigate to project root

            if not pathlib.Path(error_transfer_path).exists():
                print(f"❌ Error: error_transfer.py not found at {error_transfer_path}")
                return False

            print(f"🚀 Starting log server subprocess: {error_transfer_path}")

            if os.name == 'nt':  # Windows
                # Windows implementation
                self._log_server_process = subprocess.Popen(
                    [sys.executable, str(error_transfer_path)],
                    cwd=str(project_root),
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:  # Linux/Mac  
                # Enhanced terminal commands with proper working directory and UV
                terminals = [
                    # qterminal with bash wrapper for persistence
                    ["qterminal", "-e", "bash", "-c", f"cd '{project_root}' && uv run python '{error_transfer_path}'; echo 'Log server ended. Press Enter to close...'; read"],
                    # gnome-terminal with bash wrapper for persistence
                    ["gnome-terminal", "--", "bash", "-c", f"cd '{project_root}' && uv run python '{error_transfer_path}'; echo 'Log server ended. Press Enter to close...'; read"],
                    # xterm with hold flag
                    ["xterm", "-hold", "-e", "bash", "-c", f"cd '{project_root}' && uv run python '{error_transfer_path}'"],
                    # konsole with hold flag
                    ["konsole", "--hold", "-e", "bash", "-c", f"cd '{project_root}' && uv run python '{error_transfer_path}'"],
                    # tmux as persistent fallback
                    ["tmux", "new-session", "-d", "-s", "ai_logs", f"cd '{project_root}' && uv run python '{error_transfer_path}'"]
                ]
                
                started = False
                terminal_type = None
                
                for terminal_cmd in terminals:
                    try:
                        # Check if terminal exists
                        if subprocess.run(["which", terminal_cmd[0]], capture_output=True).returncode == 0:
                            self._terminal_process = subprocess.Popen(terminal_cmd, cwd=str(project_root))
                            self._log_server_process = self._terminal_process
                            terminal_type = terminal_cmd[0]
                            started = True
                            print(f"🔍 Started terminal monitor for {terminal_type}")
                            break
                    except (subprocess.CalledProcessError, FileNotFoundError) as e:
                        print(f"⚠️ Failed to start {terminal_cmd[0]}: {e}")
                        continue

                if not started:
                    print("❌ No compatible terminal found for log server")
                    return False

            # Give the process time to start
            time.sleep(2)

            if self._log_server_process and self._log_server_process.poll() is None:
                print(f"✅ Log server started with {terminal_type if os.name != 'nt' else 'new console'}")
                print(f"✅ Log server started with PID: {self._log_server_process.pid}")
                
                # Validate server is running after brief startup delay
                time.sleep(1)
                if self.is_server_running():
                    print("✅ Log server is running successfully")
                    return True
                else:
                    print("⚠️ Log server started but may not be responsive")
                    return False
            else:
                print("❌ Failed to start log server process")
                return False

        except Exception as e:
            print(f"❌ Error starting log server: {e}")
            return False

    def is_server_running(self):
        """Check if the log server is running by testing socket connection"""
        try:
            # Test socket connection without creating persistent connection
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(1)
            result = test_socket.connect_ex(('localhost', 5390))
            test_socket.close()
            return result == 0
        except Exception:
            return False

    def restart_log_server(self):
        """Restart the log server if it has stopped"""
        print("⚠️ Log terminal closed, attempting restart...")
        
        # Clean up existing connections
        if self._socket_connection:
            try:
                self._socket_connection.disconnect()
            except Exception:
                pass
            self._socket_connection = None
        
        # Start new server
        if self.start_log_server():
            # Re-establish connection
            return self.get_socket_connection() is not None
        return False

    def monitor_terminal_process(self):
        """Monitor terminal process and restart if needed (Linux only)"""
        if os.name != 'nt' and self._terminal_process:
            if self._terminal_process.poll() is not None:
                # Terminal has closed, attempt restart
                self.restart_log_server()

    def cleanup(self):
        """Clean up processes and connections"""
        if self._socket_connection:
            try:
                self._socket_connection.disconnect()
            except Exception:
                pass
            self._socket_connection = None
            
        if self._log_server_process:
            try:
                self._log_server_process.terminate()
                self._log_server_process.wait(timeout=5)
            except Exception:
                try:
                    self._log_server_process.kill()
                except Exception:
                    pass
            self._log_server_process = None
            self._terminal_process = None

    @classmethod
    def cleanup(cls):
        """Legacy class method for cleanup"""
        pass  # No global state to clean up in new implementation