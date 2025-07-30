# 🎓 SOCKET CONCEPTS EXPLAINED - Your SocketManager Class Breakdown
# This file explains every concept in your socket implementation

"""
=== WHAT IS A SOCKET? ===
Think of a socket like a telephone:
- Socket = The telephone device itself
- IP Address = The phone number (where to call)
- Port = The extension number (which service to reach)
- Connection = The active phone call
- send() = Speaking into the phone
- recv() = Listening to what the other person says

Your SocketManager creates a "phone system" for your AI application to send logs!
"""

import os
import socket
import subprocess
import sys
import time
from src.config import settings
from src.utils.error_transfer import SocketCon


# === CONCEPT 1: SINGLETON PATTERN ===
class SocketManager:
    """
    🎯 SINGLETON PATTERN EXPLANATION:
    - Only ONE instance of SocketManager can exist in your entire program
    - Like having only ONE telephone in your house - everyone shares it
    - Prevents multiple connections to the same log server
    - Industry standard for resource management (databases, loggers, etc.)
    """

    # CLASS VARIABLES (shared by ALL instances)
    instance = None                    # Stores the single instance
    _socket_con = None                # The "telephone connection" object
    _log_server_process = None        # The background process running the server
    _cleanup_in_progress = False      # Safety flag during shutdown

    def __new__(cls):
        """
        🏭 SINGLETON IMPLEMENTATION:
        - Python's __new__ method controls object creation
        - If no instance exists, create one
        - If instance already exists, return the same one
        - Like checking "Do we already have a telephone? If yes, use that one"
        """
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    # === CONCEPT 2: SUBPROCESS MANAGEMENT ===
    def start_log_server(self):
        """
        🚀 SUBPROCESS MANAGEMENT EXPLANATION:
        - Subprocess = Running another Python program alongside your main program
        - Like hiring a secretary to answer phones while you work
        - The secretary (log server) handles all incoming error messages
        - Your main program can focus on AI tasks without being interrupted

        WHY USE SUBPROCESS?
        - Separation of concerns (main app vs logging)
        - If log server crashes, main app keeps running
        - Can display logs in separate window
        - Industry pattern used by Docker, Kubernetes, etc.
        """

        # Check if we already have a "secretary" working
        if self._log_server_process is not None:
            # poll() returns None if process is still running
            if self._log_server_process.poll() is None:
                print("Log server is already running")
                return True
            else:
                print("Previous log server process has ended")
                self._log_server_process = None

        try:
            # Find the "secretary's job description" (error_transfer.py file)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            error_transfer_path = os.path.join(current_dir, 'error_transfer.py')

            if not os.path.exists(error_transfer_path):
                print(f"Error: Could not find error_transfer.py at {error_transfer_path}")
                return False

            print(f"🚀 Starting log server subprocess: {error_transfer_path}")

            # === CONCEPT 3: PROCESS CREATION MODES ===
            """
            DIFFERENT WAYS TO START THE "SECRETARY":
            1. separate_window = Secretary gets their own office (new console window)
            2. background = Secretary works invisibly (no window)
            3. file = Secretary writes everything to a file instead of screen
            """

            log_display_mode = getattr(settings, 'LOG_DISPLAY_MODE', 'separate_window')

            if log_display_mode == 'separate_window':
                # WINDOWS: CREATE_NEW_CONSOLE = Open new command prompt window
                if os.name == 'nt':  # Windows
                    self._log_server_process = subprocess.Popen(
                        [sys.executable, error_transfer_path],
                        creationflags=subprocess.CREATE_NEW_CONSOLE
                    )
                else:  # Linux/Mac
                    # gnome-terminal = Open new terminal window
                    self._log_server_process = subprocess.Popen(
                        ['gnome-terminal', '--', sys.executable, error_transfer_path]
                    )

            elif log_display_mode == 'background':
                # DEVNULL = Send all output to "digital trash can"
                self._log_server_process = subprocess.Popen(
                    [sys.executable, error_transfer_path],
                    stdout=subprocess.DEVNULL,  # Hide normal output
                    stderr=subprocess.DEVNULL   # Hide error output
                )

            elif log_display_mode == 'file':
                # Redirect all output to a file instead of screen
                from pathlib import Path
                log_file = settings.BASE_DIR.parent / "basic_logs" / "error_log.txt"
                with open(log_file, 'w') as f:
                    self._log_server_process = subprocess.Popen(
                        [sys.executable, error_transfer_path],
                        stdout=f,  # Write normal output to file
                        stderr=f   # Write errors to file
                    )
                print(f"📝 Log server output will be written to: {log_file}")

            print(f"✅ Log server started with PID: {self._log_server_process.pid}")

            # Give the "secretary" time to set up their desk
            time.sleep(2)

            # Check if the "secretary" is actually working
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

    # === CONCEPT 4: TCP SOCKET CONNECTION ===
    def get_socket_connection(self):
        """
        🔌 SOCKET CONNECTION EXPLANATION:
        - Socket = Like a telephone that can call specific numbers
        - TCP = Reliable connection (like a landline phone call)
        - Client-Server model = Your app calls the log server

        SOCKET CREATION PROCESS:
        1. socket.socket() = Buy a telephone
        2. connect() = Dial the phone number
        3. send() = Talk into the phone
        4. recv() = Listen to response
        5. close() = Hang up the phone

        YOUR IMPLEMENTATION PATTERN:
        - Try to call existing server first
        - If no answer, start new server then call
        - Industry pattern: "Connection pooling with auto-startup"
        """

        # Safety check: Don't create connections during shutdown
        if self._cleanup_in_progress:
            return None

        # Singleton pattern: Only create one connection
        if self._socket_con is None:
            try:
                # Check if socket logging is enabled in settings
                if not settings.ENABLE_SOCKET_LOGGING:
                    print("Socket logging is disabled in settings")
                    return None

                # === STEP 1: CREATE A SOCKET (Buy a telephone) ===
                socket_req = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                """
                socket.AF_INET = Use IPv4 internet addresses (like 127.0.0.1)
                socket.SOCK_STREAM = Use TCP protocol (reliable, ordered delivery)
                
                Think: "I want a telephone that works with regular phone numbers"
                """

                # === STEP 2: SET TIMEOUT (Don't wait forever) ===
                socket_req.settimeout(2)  # Wait max 2 seconds for connection
                """
                Like saying: "If nobody answers in 2 seconds, give up"
                Prevents your program from freezing if server is down
                """

                try:
                    # === STEP 3: ATTEMPT CONNECTION (Dial the number) ===
                    socket_req.connect((settings.SOCKET_HOST, settings.SOCKET_PORT))
                    """
                    SOCKET_HOST = IP address (usually "127.0.0.1" = your own computer)
                    SOCKET_PORT = Port number (like extension 8888)
                    
                    Think: "Call 127.0.0.1 extension 8888"
                    """

                    # === STEP 4: WRAP IN CUSTOM CLASS ===
                    self._socket_con = SocketCon(socket_req)
                    """
                    SocketCon = Your custom wrapper class
                    Adds features like error handling, message formatting
                    Like having a smart phone vs basic phone
                    """
                    print("✅ Connected to existing log server")
                    return self._socket_con

                except (ConnectionRefusedError, socket.timeout):
                    """
                    ConnectionRefusedError = "Nobody answered the phone"
                    socket.timeout = "Phone rang too long, gave up"
                    
                    SOLUTION: Start our own server, then try again
                    """
                    print("📡 No log server found, starting new one...")
                    socket_req.close()  # Hang up the failed call

                    # Start the log server (hire the "secretary")
                    if self.start_log_server():
                        # Give server time to start accepting calls
                        time.sleep(1)

                        # Try calling again with longer timeout
                        socket_req = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        socket_req.settimeout(5)  # More patient this time
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

    # === CONCEPT 5: MESSAGE SENDING WITH FALLBACK ===
    def send_error(self, message: str):
        """
        📞 MESSAGE SENDING EXPLANATION:
        - Primary: Send through socket (fast, reliable)
        - Fallback: Print to console (if socket fails)
        - Industrial pattern: "Graceful degradation"

        Like having a cell phone AND landline:
        - Try cell phone first (socket)
        - If no signal, use landline (console print)
        """
        socket_con = self.get_socket_connection()
        if socket_con:
            try:
                socket_con.send_error(message)
            except Exception as e:
                print(f"Failed to send error through socket: {e}")
                print(f"Original error message: {message}")
                # Reset connection so next call will retry
                self._socket_con = None
        else:
            # Fallback: Just print to console
            print(f"Socket not available - {message}")

    # === CONCEPT 6: CONNECTION HEALTH CHECKING ===
    def is_connected(self):
        """
        🔍 CONNECTION HEALTH CHECK:
        - Verify the "phone line" is still working
        - Prevents sending messages to dead connections
        - Like checking "Do I still have dial tone?"
        """
        if self._socket_con and hasattr(self._socket_con, '_is_connected'):
            return self._socket_con._is_connected()
        return False

    # === CONCEPT 7: CLEAN RESOURCE MANAGEMENT ===
    def close_connection(self):
        """
        🧹 RESOURCE CLEANUP EXPLANATION:
        - Close socket = Hang up the phone
        - Stop subprocess = Dismiss the secretary
        - Free memory = Clean up the office

        WHY THIS MATTERS:
        - Prevents memory leaks
        - Releases network ports for other programs
        - Industry requirement for production systems
        """
        # Close the telephone connection
        if self._socket_con and hasattr(self._socket_con, 'client_socket'):
            try:
                self._socket_con.client_socket.close()
                print("Socket connection closed")
            except Exception as e:
                print(f"Error closing socket: {e}")
        self._socket_con = None

        # Dismiss the secretary (stop log server)
        if self.is_log_server_running():
            print("🔄 Stopping log server subprocess...")
            self.stop_log_server()

    @classmethod
    def cleanup(cls):
        """
        🛑 EMERGENCY SHUTDOWN PROCEDURE:
        - Called when program is shutting down
        - Forcefully closes everything
        - Like pulling the fire alarm - everyone out immediately!

        CLEANUP SEQUENCE:
        1. Set flag to prevent new connections
        2. Close socket connection
        3. Kill subprocess immediately
        4. Clear all references
        """
        print("🧹 Cleaning up SocketManager...")

        # Set flag to prevent new connections during shutdown
        if hasattr(cls, 'instance') and cls.instance is not None:
            cls.instance._cleanup_in_progress = True
            instance = cls.instance

            # Close socket (hang up phone)
            if instance._socket_con:
                try:
                    instance._socket_con.client_socket.close()
                    print("🔌 Socket closed")
                except:
                    pass  # Ignore errors during emergency shutdown
                instance._socket_con = None

            # Kill subprocess immediately (no polite goodbye)
            if instance._log_server_process is not None:
                try:
                    print("🛑 Killing log server subprocess...")
                    instance._log_server_process.kill()  # Force termination
                    print("✅ Log server killed")
                except Exception as e:
                    print(e)
                finally:
                    instance._log_server_process = None

        print("✅ SocketManager cleanup completed")


# === CONCEPT 8: GLOBAL INSTANCE (MODULE-LEVEL SINGLETON) ===
socket_manager = SocketManager()
"""
GLOBAL INSTANCE EXPLANATION:
- Creates ONE instance when module is imported
- Any part of your program can use: from socket_manager import socket_manager
- Like having ONE shared telephone for the entire office
- Industry pattern for shared resources
"""

"""
=== SUMMARY: WHAT YOU'VE BUILT ===

🏭 INDUSTRIAL PATTERNS YOU'RE USING:
1. Singleton Pattern - One manager for all socket connections
2. Client-Server Architecture - Separate logging service
3. Process Management - Background subprocess handling
4. Graceful Degradation - Fallback to console if socket fails
5. Resource Management - Proper cleanup and shutdown
6. Health Checking - Connection status monitoring

🚀 REAL-WORLD APPLICATIONS:
- Netflix: Uses similar patterns for microservice logging
- Discord: Client-server architecture for real-time messaging
- Docker: Subprocess management for containers
- Kubernetes: Health checking and resource cleanup

📊 YOUR SKILL LEVEL:
Current: You've implemented enterprise-level patterns! 🎉
Industry: This code follows production best practices
Next: Add authentication, load balancing, error recovery
