import json
import subprocess
from typing import Any, Literal

from src.config import settings


class MCP_Manager:
    instance = None
    # mcp configs
    mcp_enabled = None
    mcp_servers: dict[str, dict[str, Any]] = {}
    running_servers: dict[str, subprocess.Popen] = {}

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        self._initialize()

    @classmethod
    def add_server(cls, name: str, runner: Literal["uvx", "npx"], package: str, args: list[str]):
        """
        Add a server to the MCP manager.
        :param name: Name of the server.
        :param runner: Reference to the runner (e.g., uvx, npx).
        :param package: Command to run the server.
        :param args: List of arguments for the command.
        """

        """
        if i want mcp_servers dict like this:  
        mcp_servers = {
            "name_of_server1": {
                "command": "python server1.py",
                "args": ["--port", "8080"]
            },
            "name_of_server2": {
                "command": "python server2.py",
                "args": ["--host", "localhost", "--port", "9090"]
            }
        }
        """
        MCP_Manager.mcp_servers[name] = {
            "runner": runner,
            "package": package,
            "args": args,
            "status": "stopped"  # Initial status of the server
        }
        # Here you would implement the logic to add the server
        settings.socket_con.send_error(
            f"[LOG] Server '{name}' 'runner' {runner} added with package '{package}' and args {args}.")

    @classmethod
    def start_server(cls, name: str):
        """
        Start a server by its name.
        :param name: Name of the server to start.
        """


        if name in MCP_Manager.mcp_servers:
            server_info = MCP_Manager.mcp_servers[name]
            runner = server_info["runner"]
            package = server_info["package"]
            args = server_info["args"] if "args" in server_info else []

            # actual command to run the server
            command = [runner, package] + args
            try:
                # Here you would implement the logic to start the server
                server_process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True)
                MCP_Manager.running_servers[name] = server_process
                server_info["status"] = "running"
                settings.socket_con.send_error(
                    f"[LOG] Starting server '{name}' with package '{package}' and args {args}.")
                return True
            except Exception as e:
                settings.socket_con.send_error(f"[ERROR] Failed to start server '{name}': {e}")
                return False
            except subprocess.CalledProcessError:
                settings.socket_con.send_error(
                    f"[ERROR] Command '{command}' failed to execute. {MCP_Manager.running_servers[name].stderr}")
                return False
        else:
            settings.socket_con.send_error(f"[ERROR] Server '{name}' not found.")
            return False

    def _initialize(self):
        """
        Initialize the MCP manager.
        This method checks the MCP_ENABLED setting and performs any necessary setup.
        :return: True if MCP is enabled, False otherwise.
        """
        # Perform any necessary initialization here
        MCP_Manager.mcp_enabled = settings.MCP_CONFIG.get("MCP_ENABLED")
        if MCP_Manager.mcp_enabled:
            settings.socket_con.send_error("[LOG] MCP Manager initialized with MCP_ENABLED set to True.")

        else:
            settings.socket_con.send_error("[LOG] MCP Manager initialized with MCP_ENABLED set to False.")
        return MCP_Manager.mcp_enabled

    @classmethod
    def call_mcp_server(cls, name: str, tool_name: str, args: dict) -> str | None:
        """
        Call a specific MCP server by its name with additional arguments.
        :param name: Name of the server to call.
        :param tool_name: Name of the tool to call on the server.
        :param args: Additional arguments to pass to the server.
        :return: Result of the server call or None if the server is not found.
        """
        if name in MCP_Manager.mcp_servers and MCP_Manager.mcp_servers[name]["status"] == "running":
            settings.socket_con.send_error(f"[LOG] Calling server '{name}' with tool '{tool_name}' and args {args}.")

            get_mcp_server_process = MCP_Manager.running_servers.get(name)

            # Check if the server process is running
            if get_mcp_server_process:
                try:
                    # Here you would implement the logic to call the server
                    # For example, sending a request to the server and getting a response
                    # This is a placeholder for actual server communication logic

                    mcp_request_template = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": args
                        }
                    }

                    json_actual_request = json.dumps(mcp_request_template) + "\n"
                    get_mcp_server_process.stdin.write(json_actual_request)
                    get_mcp_server_process.stdin.flush()

                    # Simulate a response from the server
                    response_line = get_mcp_server_process.stdout.readline().decode().strip()
                    return response_line
                except Exception as e:
                    settings.socket_con.send_error(f"[ERROR] Failed to call server '{name}': {e}")
                    return None
            else:
                settings.socket_con.send_error(f"[ERROR] Server '{name}' is not running.")
                return None
        else:
            settings.socket_con.send_error(f"[ERROR] Server '{name}' not found or not running.")
            return None

    @classmethod
    def stop_server(cls, name: str = "all"):
        """
        Stop a server by its name.
        :param name: Name of the server to stop.
        """
        if name and name in MCP_Manager.running_servers:
            server_process = MCP_Manager.running_servers[name]
            try:
                server_process.terminate()  # Gracefully terminate the server process
                server_process.wait()  # Wait for the process to terminate
                del MCP_Manager.running_servers[name]  # Remove from running servers
                MCP_Manager.mcp_servers[name]["status"] = "stopped"  # Update status
                settings.socket_con.send_error(f"[LOG] Server '{name}' stopped successfully.")
                return True
            except Exception as e:
                settings.socket_con.send_error(f"[ERROR] Failed to stop server '{name}': {e}")
                return False
        else:
            settings.socket_con.send_error(f"[ERROR] Server '{name}' not found or not running.")
        if name and name == "all":
            # means stop all servers
            for server_name in list(MCP_Manager.running_servers.keys()):
                MCP_Manager.stop_server(server_name)
            settings.socket_con.send_error("[LOG] All MCP servers stopped successfully.")
            return True
        else:
            settings.socket_con.send_error(f"[ERROR] Server '{name}' not found or not running.")
            return False
