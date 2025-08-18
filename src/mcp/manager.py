import json
import subprocess
from typing import Any, Literal, Callable

from src.config import settings
from src.mcp.dynamically_tool_register import DynamicToolRegister

# 🎨 Rich Traceback Integration
from src.ui.diagnostics.rich_traceback_manager import RichTracebackManager, rich_exception_handler
# ✅ Structured Debug Helpers
from src.ui.diagnostics.debug_helpers import (
    debug_info,
    debug_warning,
    debug_error,
)


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
    def add_server(cls, name: str, runner: Literal["uvx", "npx"], package: str, args: list[str], func: Callable):
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
        debug_info(
            heading="MCP • SERVER_ADDED",
            body=f"Registered server '{name}' (runner={runner})",
            metadata={"package": package, "args": args}
        )

    @classmethod
    def tool_discovery(cls, mcp_server_name: str) -> Any:
        """
        :param mcp_server_name: Name of the MCP server to discover tools from.
        :return: Dictionary of discovered tools from the specified MCP server.
        """
        if mcp_server_name not in cls.mcp_servers:
            debug_warning(
                heading="MCP • TOOL_DISCOVERY_MISSED",
                body="Requested tool discovery on unknown server",
                metadata={"server": mcp_server_name}
            )
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

        if 'result' in response_line_json and 'tools' in response_line_json['result']:
            tools_found = response_line_json['result']['tools']
            debug_info(
                heading="MCP • TOOLS_DISCOVERED",
                body=f"Discovered {len(tools_found)} tools",
                metadata={"server": mcp_server_name, "tools": [t.get('name', 'unnamed') for t in tools_found]}
            )
            if tools_found:
                DynamicToolRegister.register_tool(response_line_json, MCP_Manager.mcp_servers[mcp_server_name]["func"])
            else:
                debug_warning(
                    heading="MCP • NO_TOOLS",
                    body="Server returned empty tool list",
                    metadata={"server": mcp_server_name}
                )
        else:
            debug_error(
                heading="MCP • INVALID_TOOL_RESPONSE",
                body="Server returned unexpected tools/list format",
                metadata={"server": mcp_server_name, "response_preview": str(response_line_json)[:200]}
            )
        return response_line_json

    @classmethod
    @rich_exception_handler("MCP Server Startup")
    def start_server(cls, name: str):
        """
        Start a server by its name.
        :param name: Name of the server to start.
        """
        try:
            if name in MCP_Manager.mcp_servers:
                server_info = MCP_Manager.mcp_servers[name]
                runner = server_info["runner"]
                package = server_info["package"]
                args = server_info.get("args", [])
                command = [runner, package] + args
                try:
                    server_process = subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        text=True,
                        bufsize=1
                    )
                    MCP_Manager.running_servers[name] = server_process
                    server_info["status"] = "running"

                    # Handshake / initialize
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
                        server_process.stdin.write(json.dumps(init_request) + "\n")
                        server_process.stdin.flush()
                        init_response = server_process.stdout.readline()
                        debug_info(
                            heading="MCP • SERVER_INITIALIZED",
                            body=f"Handshake completed for '{name}'",
                            metadata={"init_response_preview": init_response[:120]}
                        )
                        # Discover tools
                        try:
                            tools = cls.tool_discovery(name)
                            if tools and 'result' in tools:
                                debug_info(
                                    heading="MCP • DISCOVERY_COMPLETE",
                                    body=f"Tool discovery finished for '{name}'",
                                    metadata={"server": name}
                                )
                            else:
                                debug_warning(
                                    heading="MCP • DISCOVERY_EMPTY",
                                    body="No tools returned after discovery",
                                    metadata={"server": name}
                                )
                        except Exception as tool_discovery_error:
                            RichTracebackManager.handle_exception(
                                tool_discovery_error,
                                context=f"MCP Tool Discovery - {name}",
                                extra_context={"server_name": name, "init_response": str(init_response)[:100]}
                            )
                            debug_error(
                                heading="MCP • DISCOVERY_ERROR",
                                body=f"Tool discovery failed: {tool_discovery_error}",
                                metadata={"server": name}
                            )
                    except Exception as init_error:
                        RichTracebackManager.handle_exception(
                            init_error,
                            context=f"MCP Server Initialization - {name}",
                            extra_context={"server_name": name, "command": str(command), "process_id": server_process.pid}
                        )
                        debug_warning(
                            heading="MCP • INIT_FAILED",
                            body=f"Initialization failed: {init_error}",
                            metadata={"server": name}
                        )

                    debug_info(
                        heading="MCP • SERVER_STARTED",
                        body=f"Started server '{name}'",
                        metadata={"package": package, "args": args}
                    )
                    return True

                except subprocess.CalledProcessError as process_error:
                    RichTracebackManager.handle_exception(
                        process_error,
                        context=f"MCP Server Process Creation - {name}",
                        extra_context={"command": str(command), "server_name": name, "runner": runner, "package": package}
                    )
                    debug_error(
                        heading="MCP • PROCESS_ERROR",
                        body=f"Command failed: {process_error}",
                        metadata={"server": name, "command": str(command)}
                    )
                    return False
                except Exception as e:
                    RichTracebackManager.handle_exception(
                        e,
                        context=f"MCP Server Startup - {name}",
                        extra_context={"server_name": name, "command": str(command), "runner": runner, "package": package}
                    )
                    debug_error(
                        heading="MCP • STARTUP_ERROR",
                        body=f"Failed to start server: {e}",
                        metadata={"server": name}
                    )
                    return False
            else:
                debug_error(
                    heading="MCP • UNKNOWN_SERVER",
                    body="Attempted to start non-existent server",
                    metadata={"server": name}
                )
                return False
        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context=f"MCP Server Startup Wrapper - {name}",
                extra_context={"server_name": name}
            )
            debug_error(
                heading="MCP • CRITICAL_START_ERROR",
                body=f"Critical error starting server: {e}",
                metadata={"server": name}
            )
            return False

    def _initialize(self):
        """
        Initialize the MCP manager.
        This method checks the MCP_ENABLED setting and performs any necessary setup.
        :return: True if MCP is enabled, False otherwise.
        """
        # Perform any necessary initialization here
        MCP_Manager.mcp_enabled = settings.MCP_CONFIG.get("MCP_ENABLED")
        debug_info(
            heading="MCP • MANAGER_INIT",
            body="MCP Manager initialized",
            metadata={"enabled": bool(MCP_Manager.mcp_enabled)}
        )
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
            msg = f"Server '{name}' not found"
            debug_error(heading="MCP • CALL_ERROR", body=msg, metadata={"server": name})
            return {"success": False, "error": msg}
        if MCP_Manager.mcp_servers[name]["status"] != "running":
            msg = f"Server '{name}' is not running"
            debug_error(heading="MCP • CALL_ERROR", body=msg, metadata={"server": name})
            return {"success": False, "error": msg}
        debug_info(
            heading="MCP • TOOL_CALL",
            body=f"Calling tool '{tool_name}'",
            metadata={"server": name, "args": args}
        )
        proc = MCP_Manager.running_servers.get(name)
        if not proc:
            msg = f"Server '{name}' process not found"
            debug_error(heading="MCP • CALL_ERROR", body=msg, metadata={"server": name})
            return {"success": False, "error": msg}
        try:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": MCP_Manager.generate_response_id(),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": args}
            }
            proc.stdin.write(json.dumps(mcp_request) + "\n")
            proc.stdin.flush()
            response_line = proc.stdout.readline().strip()
            if not response_line:
                msg = f"No response from server '{name}'"
                debug_error(heading="MCP • CALL_ERROR", body=msg, metadata={"server": name})
                return {"success": False, "error": msg}
            try:
                json_response = json.loads(response_line)
                if "error" in json_response:
                    msg = f"MCP server error: {json_response['error']}"
                    debug_error(heading="MCP • TOOL_ERROR", body=msg, metadata={"server": name, "tool": tool_name})
                    return {"success": False, "error": msg}
                if "result" in json_response:
                    debug_info(
                        heading="MCP • TOOL_SUCCESS",
                        body="Tool executed successfully",
                        metadata={"server": name, "tool": tool_name}
                    )
                    return {"success": True, "data": json_response["result"]}
                debug_warning(
                    heading="MCP • NO_RESULT_FIELD",
                    body="Response missing 'result' field; returning raw payload",
                    metadata={"server": name, "tool": tool_name}
                )
                return {"success": True, "data": json_response}
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON response: {e}"
                debug_error(heading="MCP • PARSE_ERROR", body=msg, metadata={"server": name, "tool": tool_name})
                return {"success": False, "error": msg, "raw_response": response_line}
        except Exception as e:
            msg = f"Communication error: {e}"
            debug_error(heading="MCP • COMM_ERROR", body=msg, metadata={"server": name, "tool": tool_name})
            return {"success": False, "error": msg}

    @classmethod
    def stop_server(cls, name: str) -> bool:
        """
        Stop a specific server by its name.
        :param name: Name of the server to stop.
        :return: True if server was stopped successfully, False otherwise.
        """
        if name not in cls.running_servers:
            debug_warning(
                heading="MCP • STOP_IGNORED",
                body="Stop requested for server not running",
                metadata={"server": name}
            )
            return False
        proc = cls.running_servers[name]
        try:
            proc.terminate()
            proc.wait(timeout=5)
            del cls.running_servers[name]
            cls.mcp_servers[name]["status"] = "stopped"
            debug_info(
                heading="MCP • SERVER_STOPPED",
                body="Server stopped successfully",
                metadata={"server": name}
            )
            return True
        except Exception as e:
            debug_error(
                heading="MCP • STOP_ERROR",
                body=f"Failed to stop server: {e}",
                metadata={"server": name}
            )
            return False

    @classmethod
    def stop_all_servers(cls) -> bool:
        """
        Stop all running MCP servers. Safe for cleanup - doesn't fail on errors.
        :return: True if all servers were stopped, False if any failed.
        """
        if not cls.running_servers:
            debug_info(
                heading="MCP • STOP_ALL_SKIP",
                body="No running servers to stop",
                metadata={}
            )
            return True
        success = True
        for server_name in list(cls.running_servers.keys()):
            try:
                if not cls.stop_server(server_name):
                    success = False
            except Exception as e:
                debug_error(
                    heading="MCP • STOP_ALL_ERROR",
                    body=f"Exception stopping '{server_name}': {e}",
                    metadata={"server": server_name}
                )
                success = False
        if success:
            debug_info(heading="MCP • STOP_ALL_COMPLETE", body="All servers stopped", metadata={})
        else:
            debug_warning(heading="MCP • STOP_ALL_PARTIAL", body="Some servers failed to stop", metadata={})
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
            debug_error(
                heading="MCP • CLEANUP_ERROR",
                body=f"Cleanup failed: {e}",
                metadata={}
            )
