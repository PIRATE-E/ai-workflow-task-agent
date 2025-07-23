import socket
import subprocess
import time
import os
import sys
from .error_transfer import SocketCon

# Import config - handle case where it might not be available
try:
    from src.config import settings as config
except ImportError:
    # Fallback config if main config is not available
    class Config:
        ENABLE_SOCKET_LOGGING = False
        SOCKET_HOST = 'localhost'
        SOCKET_PORT = 5390
    config = Config()

class SocketManager:
    _instance = None
    _socket_con = None
    _log_server_process = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    
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
            
            # Start the subprocess - choose method based on config
            log_display_mode = getattr(config, 'LOG_DISPLAY_MODE', 'separate_window')
            
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
                # Option 3: Log to file
                log_file = os.path.join(os.path.dirname(error_transfer_path), 'socket_server.log')
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
        """Stop the log server subprocess"""
        if self._log_server_process is not None:
            try:
                print("🛑 Stopping log server...")
                self._log_server_process.terminate()
                
                # Wait for process to terminate gracefully
                try:
                    self._log_server_process.wait(timeout=5)
                    print("✅ Log server stopped gracefully")
                except subprocess.TimeoutExpired:
                    print("⚠️ Log server didn't stop gracefully, forcing termination...")
                    self._log_server_process.kill()
                    self._log_server_process.wait()
                    print("✅ Log server forcefully terminated")
                    
            except Exception as e:
                print(f"❌ Error stopping log server: {e}")
            finally:
                self._log_server_process = None
    
    def is_log_server_running(self):
        """Check if the log server subprocess is running"""
        if self._log_server_process is None:
            return False
        return self._log_server_process.poll() is None
    
    def get_socket_connection(self):
        """Get or create the socket connection (singleton pattern)"""
        if self._socket_con is None:
            try:
                if not config.ENABLE_SOCKET_LOGGING:
                    print("Socket logging is disabled in config")
                    return None
                
                # First, try to connect to existing server
                socket_req = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                socket_req.settimeout(2)  # Short timeout for initial connection attempt
                
                try:
                    socket_req.connect((config.SOCKET_HOST, config.SOCKET_PORT))
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
                        socket_req.settimeout(5)  # Longer timeout for new server
                        socket_req.connect((config.SOCKET_HOST, config.SOCKET_PORT))
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

# Global instance
socket_manager = SocketManager()