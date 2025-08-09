import json
import subprocess
from typing import Any, Literal, Callable

from src.config import settings
from src.mcp.dynamically_tool_register import DynamicToolRegister


class MCP_Manager:
    instance = None
    # mcp configs
    mcp_enabled = None
    mcp_servers: dict[str, dict[str, Any]] = {}
    running_servers: dict[str, subprocess.Popen] = {}
    response_id = 0

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        self._initialize()

    @classmethod
    def generate_response_id(cls) -> int:
        """
        Generate a unique response ID for each request.
        :return: Unique response ID.
        """
        MCP_Manager.response_id += 1
        return MCP_Manager.response_id

    @classmethod
    def add_server(cls, name: str, runner: Literal["uvx", "npx"], package: str, args: list[str], func : Callable):
        """
        Add a server to the MCP manager.
        :param name: Name of the server.
        :param runner: Reference to the runner (e.g., uvx, npx).
        :param package: Command to run the server.
        :param args: List of arguments for the command.
        :param func: To assign the function to the llm's tools
        """

        """
        Example of mcp_servers dict with current structure:
        mcp_servers = {
            "name_of_server1": {
                "runner": "uvx",
                "package": "python server1.py",
                "args": ["--port", "8080"],
                "status": "stopped"
            },
            "name_of_server2": {
                "runner": "npx",
                "package": "python server2.py",
                "args": ["--host", "localhost", "--port", "9090"],
                "status": "stopped"
            }
        }
        """
        MCP_Manager.mcp_servers[name] = {
            "runner": runner,
            "package": package,
            "args": args,
            "status": "stopped",  # Initial status of the server
            "func": func  # Function to handle server operations \
                          # (function that is associated with the server to handle its responses and make requests) \
                          # to assign the function to the llm's tools.
        }
        # Here you would implement the logic to add the server
        settings.socket_con.send_error(
            f"[LOG] Server '{name}' 'runner' {runner} added with package '{package}' and args {args}.")

    @classmethod
    def tool_discovery(cls, mcp_server_name: str) -> Any:
        """
        :param mcp_server_name: Name of the MCP server to discover tools from.
        :return: Dictionary of discovered tools from the specified MCP server.
        """
        if mcp_server_name not in cls.mcp_servers:
            settings.socket_con.send_error("[LOG] No MCP servers found.")
            return {}

        tool_discovery_request = {
            "jsonrpc": "2.0",
            "id": MCP_Manager.generate_response_id(),
            "method": "tools/list",
            "params": {}
        }

        MCP_Manager.running_servers[mcp_server_name].stdin.write(json.dumps(tool_discovery_request) + "\n")
        MCP_Manager.running_servers[mcp_server_name].stdin.flush()

        response_line_json = json.loads(MCP_Manager.running_servers[mcp_server_name].stdout.readline().strip())
        
        # DEBUG: Log the actual tools/list response
        # settings.socket_con.send_error(f"[DEBUG] Tools/list response from {mcp_server_name}: {response_line_json}")
        
        # Check if tools exist in response
        if 'result' in response_line_json and 'tools' in response_line_json['result']:
            tools_found = response_line_json['result']['tools']
            settings.socket_con.send_error(f"[DEBUG] Found {len(tools_found)} tools: {[tool.get('name', 'unnamed') for tool in tools_found]}")
            
            if tools_found:
                # experimental
                DynamicToolRegister.register_tool(response_line_json, MCP_Manager.mcp_servers[mcp_server_name]["func"])
            else:
                settings.socket_con.send_error(f"[WARNING] No tools found in MCP server '{mcp_server_name}' response")
        else:
            settings.socket_con.send_error(f"[ERROR] Invalid tools/list response format from '{mcp_server_name}': {response_line_json}")
        
        # set the tool into tool assignment
        return response_line_json

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
                server_process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE, stdin=subprocess.PIPE, text=True, bufsize=1)
                MCP_Manager.running_servers[name] = server_process
                server_info["status"] = "running"
                # ######## Initialize MCP server with handshake ########
                try:
                    init_request = {
                        "jsonrpc": "2.0",
                        "id": MCP_Manager.generate_response_id(),
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "langgraph-mcp-client", "version": "1.0.0"}
                        }
                    }
                    init_json = json.dumps(init_request) + "\n"
                    server_process.stdin.write(init_json)
                    server_process.stdin.flush()

                    # Read initialization response (but don't process it for now)
                    init_response = server_process.stdout.readline()
                    settings.socket_con.send_error(
                        f"[LOG] MCP server '{name}' initialized the response is :- {init_response}")

                    ######## now get the tools from the server ############
                    tools = cls.tool_discovery(name)
                    if tools:
                        settings.socket_con.send_error(
                            f"[LOG] Discovered tools from server {name} ")
                    else:
                        settings.socket_con.send_error(
                            f"[WARNING] No tools discovered from server '{name}'. This might be expected if the server has no tools registered.")
                except Exception as e:
                    settings.socket_con.send_error(f"[WARNING] MCP initialization failed for '{name}': {e} server err: {server_process.stderr}")
                settings.socket_con.send_error(
                    f"[LOG] started server '{name}' with package '{package}' and args {args}.")
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
    def call_mcp_server(cls, name: str, tool_name: str, args: dict) -> dict | None:
        """
        Call a specific MCP server by its name with additional arguments.
        :param name: Name of the server to call.
        :param tool_name: Name of the tool to call on the server.
        :param args: Additional arguments to pass to the server.
        :return: Structured response dict with success/error status, or None for critical failures.
        """
        # Check if server exists and is running
        if name not in MCP_Manager.mcp_servers:
            error_msg = f"Server '{name}' not found"
            settings.socket_con.send_error(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg}

        if MCP_Manager.mcp_servers[name]["status"] != "running":
            error_msg = f"Server '{name}' is not running"
            settings.socket_con.send_error(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg}

        settings.socket_con.send_error(f"[LOG] Calling server '{name}' with tool '{tool_name}' and args {args}.")

        get_mcp_server_process = MCP_Manager.running_servers.get(name)
        if not get_mcp_server_process:
            error_msg = f"Server '{name}' process not found"
            settings.socket_con.send_error(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg}

        try:
            # Create MCP JSON-RPC request
            mcp_request = {
                "jsonrpc": "2.0",
                "id": MCP_Manager.generate_response_id(),
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": args
                }
            }

            # Send request to MCP server
            request_json = json.dumps(mcp_request) + "\n"
            get_mcp_server_process.stdin.write(request_json)
            get_mcp_server_process.stdin.flush()

            # Read response from MCP server
            response_line = get_mcp_server_process.stdout.readline().strip()
            if not response_line:
                error_msg = f"No response from server '{name}'"
                settings.socket_con.send_error(f"[ERROR] {error_msg}")
                return {"success": False, "error": error_msg}

            # Parse JSON-RPC response
            try:
                json_response = json.loads(response_line)

                # Check for JSON-RPC error
                if "error" in json_response:
                    error_msg = f"MCP server error: {json_response['error']}"
                    settings.socket_con.send_error(f"[ERROR] {error_msg}")
                    return {"success": False, "error": error_msg}

                # Extract result from JSON-RPC response
                if "result" in json_response:
                    result_data = json_response["result"]
                    settings.socket_con.send_error(f"[LOG] Server '{name}' tool '{tool_name}' executed successfully")
                    return {"success": True, "data": result_data}
                else:
                    # Fallback: return entire response if no result field
                    settings.socket_con.send_error(f"[LOG] Server '{name}' returned response without result field")
                    return {"success": True, "data": json_response}

            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON response from server '{name}': {e}"
                settings.socket_con.send_error(f"[ERROR] {error_msg}")
                # Return raw response as data for debugging
                return {"success": False, "error": error_msg, "raw_response": response_line}

        except Exception as e:
            error_msg = f"Communication error with server '{name}': {str(e)}"
            settings.socket_con.send_error(f"[ERROR] {error_msg}")
            return {"success": False, "error": error_msg}

    @classmethod
    def stop_server(cls, name: str) -> bool:
        """
        Stop a specific server by its name.
        :param name: Name of the server to stop.
        :return: True if server was stopped successfully, False otherwise.
        """
        if name not in cls.running_servers:
            settings.socket_con.send_error(f"[ERROR] Server '{name}' not found or not running.")
            return False

        server_process = cls.running_servers[name]
        try:
            server_process.terminate()
            server_process.wait(timeout=5)  # Wait up to 5 seconds
            del cls.running_servers[name]
            cls.mcp_servers[name]["status"] = "stopped"
            settings.socket_con.send_error(f"[LOG] Server '{name}' stopped successfully.")
            return True
        except Exception as e:
            settings.socket_con.send_error(f"[ERROR] Failed to stop server '{name}': {e}")
            return False

    @classmethod
    def stop_all_servers(cls) -> bool:
        """
        Stop all running MCP servers. Safe for cleanup - doesn't fail on errors.
        :return: True if all servers were stopped, False if any failed.
        """
        if not cls.running_servers:
            settings.socket_con.send_error("[LOG] No MCP servers running to stop.")
            return True

        success = True
        server_names = list(cls.running_servers.keys())  # Copy to avoid modification during iteration

        for server_name in server_names:
            try:
                if not cls.stop_server(server_name):
                    success = False
            except Exception as e:
                settings.socket_con.send_error(f"[ERROR] Exception stopping server '{server_name}': {e}")
                success = False

        if success:
            settings.socket_con.send_error("[LOG] All MCP servers stopped successfully.")
        else:
            settings.socket_con.send_error("[WARNING] Some MCP servers failed to stop cleanly.")

        return success

    @classmethod
    def cleanup(cls):
        """
        Cleanup method for ChatDestructor integration.
        Stops all servers and handles any cleanup errors gracefully.
        """
        try:
            cls.stop_all_servers()
        except Exception as e:
            # Don't let cleanup errors crash the application
            if hasattr(settings, 'socket_con') and settings.socket_con:
                settings.socket_con.send_error(f"[ERROR] MCP cleanup failed: {e}")
            else:
                print(f"[ERROR] MCP cleanup failed: {e}")
