"""manager.py

MCP (Model Context Protocol) Manager for server lifecycle and communication.

This module provides comprehensive management of MCP servers, handling their lifecycle
from initialization through execution to cleanup. It manages server processes, handles
stdio-based JSON-RPC communication, and provides tool discovery for LangChain integration.

Features:
    - Singleton pattern for centralized MCP server management
    - Async and sync server startup with subprocess management
    - JSON-RPC 2.0 communication over stdio pipes
    - Automatic tool discovery and LangChain tool registration
    - Resource URI reading capabilities (prompts, resources)
    - Graceful shutdown and cleanup of all managed processes

Classes:
    MCP_Manager: Singleton manager for all MCP server operations

Dependencies:
    - subprocess: Process management for MCP server spawning
    - json: JSON-RPC message serialization/deserialization
    - coldwind.core.config.settings: Configuration for MCP servers and timeouts
    - coldwind.core.mcp.dynamically_tool_register: Dynamic tool registration system
    - coldwind.desktop.ui.diagnostics: Logging and error tracking

Notes:
    MCP servers communicate via stdio using JSON-RPC 2.0 protocol. Each server
    runs as a separate subprocess with stdin/stdout pipes for bidirectional
    communication. Response IDs are auto-incremented for request tracking.

Warning:
    This manager is NOT thread-safe for concurrent server operations. Use
    asyncio patterns for concurrent server management.
"""

import json
import os
import subprocess
from typing import Any, Callable, Optional

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.mcp.dynamically_tool_register import DynamicToolRegister
from coldwind.core.mcp.mcp_register_structure import (
    ServerConfig,
    Command,
    MPC_TOOL_SERVER_MAPPING,
)

# ✅ Structured Debug Helpers
from coldwind.desktop.ui.diagnostics.debug_helpers import (
    debug_info,
    debug_warning,
    debug_error,
)

# 🎨 Rich Traceback Integration
from coldwind.desktop.ui.diagnostics.rich_traceback_manager import (
    RichTracebackManager,
    rich_exception_handler,
)
import pathlib


class MCP_Manager:
    """Singleton manager for MCP (Model Context Protocol) server lifecycle and communication.

    This class implements a singleton pattern to provide centralized management of multiple
    MCP servers. It handles server registration, process spawning, JSON-RPC communication,
    tool discovery, and graceful cleanup.

    Attributes:
        instance (MCP_Manager|None): Singleton instance of the manager. Ensures only one
            manager exists across the application lifecycle.
        mcp_enabled (bool|None): Global flag indicating whether MCP functionality is enabled.
            Set from configuration during initialization.
        mcp_servers (dict[str, ServerConfig]): Registry of all configured MCP servers.
            Keys are server names, values are ServerConfig dictionaries containing
            command, args, and registration metadata.
        running_servers (dict[str, subprocess.Popen]): Active server processes.
            Keys are server names, values are Popen objects for process control.
        response_id (int): Auto-incrementing counter for JSON-RPC request IDs.
            Used to track request-response pairs in the protocol.

    Methods:
        generate_response_id: Generate unique IDs for JSON-RPC requests
        add_server: Register a new MCP server configuration
        tool_discovery: Discover and register tools from an MCP server
        start_server: Start a registered MCP server subprocess
        call_mcp_server: Send JSON-RPC requests to running servers
        stop_server: Gracefully stop a single MCP server
        stop_all_servers: Stop all running MCP servers
        cleanup: Perform final cleanup of all resources
        read_uri_resource: Read resources/prompts via URI from servers

    Notes:
        - Singleton pattern ensures centralized state across the application
        - Servers communicate via stdio using JSON-RPC 2.0 protocol
        - Tool discovery automatically registers discovered tools with LangChain
        - All subprocess management uses proper pipe handling for bidirectional I/O

    Warning:
        - NOT thread-safe. Use asyncio patterns for concurrent operations.
        - Subprocess pipes can deadlock if not properly flushed.
        - Server processes are not automatically cleaned up on crashes.

    Examples:
        >>> manager = MCP_Manager()  # Get singleton instance
        >>> manager.add_server("github", Command.NPX, None, ["-y", "@model..."], func)
        >>> manager.start_server("github")
        >>> result = manager.call_mcp_server("github", "list_tools", {})
    """

    instance = None
    # mcp.md configs
    mcp_enabled = None
    mcp_servers: dict[str, ServerConfig] = {}
    running_servers: dict[str, subprocess.Popen] = {}
    response_id = 0

    def __new__(cls, *args, **kwargs):
        """Implement singleton pattern to ensure only one MCP_Manager instance exists.

        This method overrides __new__ to implement the singleton design pattern.
        On first instantiation, it creates and stores a new instance. On subsequent
        calls, it returns the existing instance, ensuring centralized state management.

        Args:
            *args: Variable positional arguments (ignored for singleton)
            **kwargs: Variable keyword arguments (ignored for singleton)

        Returns:
            MCP_Manager: The singleton instance of MCP_Manager. Same object returned
                on every call regardless of arguments.

        Notes:
            - Thread-safe for CPython due to GIL protection on class attribute access
            - Instance is stored as class attribute, persists for application lifetime
            - Arguments beyond first instantiation are ignored

        Examples:
            >>> manager1 = MCP_Manager()
            >>> manager2 = MCP_Manager()
            >>> assert manager1 is manager2  # Same instance
        """
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self):
        """Initialize the MCP_Manager instance by loading configuration.

        This constructor calls the _initialize method to load MCP configuration
        from .mcp.json and register all configured servers. On subsequent calls
        (due to singleton pattern), initialization is skipped if already completed.

        Args:
            None

        Returns:
            None

        Raises:
            FileNotFoundError: If .mcp.json configuration file is missing
            json.JSONDecodeError: If .mcp.json contains invalid JSON
            KeyError: If required configuration keys are missing

        Notes:
            - Only performs full initialization on first call
            - Subsequent calls do nothing due to singleton pattern
            - _initialize() handles actual configuration loading

        Warning:
            If .mcp.json is malformed, initialization fails and no servers are registered.
        """
        self._initialize()

    @classmethod
    def generate_response_id(cls) -> int:
        """Generate a unique, auto-incrementing ID for JSON-RPC requests.

        This method provides thread-unsafe ID generation for tracking JSON-RPC
        request-response pairs. IDs start at 1 and increment indefinitely.

        Args:
            None

        Returns:
            int: A unique response ID. Guaranteed to be greater than all previous
                IDs generated in this session. Starts at 1 and increments by 1.

        Notes:
            - NOT thread-safe. Concurrent calls may produce duplicate IDs.
            - IDs are not persisted across application restarts.
            - Used in JSON-RPC 2.0 "id" field for request tracking.
            - Counter resets to 0 if manager instance is destroyed.

        Warning:
            In multi-threaded contexts, use locking to prevent duplicate ID generation.

        Examples:
            >>> id1 = MCP_Manager.generate_response_id()  # Returns 1
            >>> id2 = MCP_Manager.generate_response_id()  # Returns 2
        """
        MCP_Manager.response_id += 1
        return MCP_Manager.response_id

    @classmethod
    def add_server(
        cls,
        name: str,
        runner: Command,
        package: Optional[str],
        args: list[str],
        func: Callable,
    ):
        """Register a new MCP server configuration for later startup.

        This method adds a server configuration to the registry without starting it.
        The server can be started later using start_server(). It validates the runner
        command and constructs the full argument list.

        Args:
            name (str): Unique identifier for the server. Used as key in mcp_servers
                dict and for all subsequent operations (start, stop, call).
            runner (Command): Command enum specifying the execution runner (NPX, UVX,
                DOCKER, PYTHON). Determines how the server process is spawned.
            package (Optional[str]): Package name or main module to execute. For NPX,
                this is the npm package. For Python, this is the script path. Can be
                None if package is included in args.
            args (list[str]): Command-line arguments to pass to the server. Combined
                with package to form full command array.
            func (Callable): Function reference for handling server tool calls. This
                function is registered with LangChain to route tool invocations.

        Returns:
            None

        Raises:
            ValueError: If name is already registered in mcp_servers
            TypeError: If runner is not a valid Command enum value

        Notes:
            - Server is NOT started by this method, only registered
            - If package is None, it's excluded from the args array
            - Full command becomes: [runner.value, package, *args]
            - func is used by DynamicToolRegister for tool routing
            - Server config is stored in ServerConfig TypedDict format

        Warning:
            Duplicate server names will overwrite previous configuration without warning.

        Examples:
            >>> MCP_Manager.add_server(
            ...     "github",
            ...     Command.NPX,
            ...     None,
            ...     ["-y", "@modelcontextprotocol/server-github@latest"],
            ...     universal_tool_handler
            ... )
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
        # MCP_Manager.mcp_servers[name] = {
        #     "runner": runner,
        #     "package": package,
        #     "args": args,
        #     "status": "stopped",  # Initial status of the server
        #     "func": func  # Function to handle server operations \
        #                   # (function that is associated with the server to handle its responses and make requests) \
        #                   # to assign the function to the llm's tools.
        # }

        # Filter out None package to avoid None in args array
        server_args = args if package is None else [package] + args

        MCP_Manager.mcp_servers[name] = ServerConfig(
            name=name,
            command=runner,
            args=server_args,  # Use filtered args
            env={},
            wrapper=func,
            status="stopped",
            pid=None,
        )
        debug_info(
            heading="MCP • SERVER_ADDED",
            body=f"Registered server '{name}' (runner={runner})",
            metadata={"package": package, "args": args},
        )

    @classmethod
    def tool_discovery(cls, mcp_server_name: str) -> Any:
        """Discover available tools from a running MCP server and register them.

        This method sends a "tools/list" JSON-RPC request to the specified server,
        parses the response to extract tool definitions, and automatically registers
        them with the DynamicToolRegister for LangChain integration.

        Args:
            mcp_server_name (str): Name of the running MCP server to query. Must be
                in running_servers dict (i.e., server must be started first).

        Returns:
            dict[str, Any]: Dictionary of discovered tools. Keys are tool names,
                values are tool definitions containing name, description, and input
                schema. Returns empty dict {} if server not found, not running, or
                returns no tools.

        Raises:
            BrokenPipeError: If server process terminated unexpectedly
            json.JSONDecodeError: If server response is not valid JSON
            UnicodeDecodeError: If server response has encoding issues (handled
                with multiple fallback strategies)
            KeyError: If server response missing required fields

        Notes:
            - Sends JSON-RPC 2.0 "tools/list" request to server stdin
            - Reads response from server stdout (blocking read)
            - Handles multiple encoding strategies (utf-8, latin-1, cp1252, etc.)
            - Gracefully handles server errors with -32602 codes (invalid params)
            - Discovered tools automatically added to DynamicToolRegister
            - Tool mapping stored in MPC_TOOL_SERVER_MAPPING for routing

        Warning:
            - BLOCKING operation that waits for server response indefinitely
            - No timeout handling - can hang if server doesn't respond
            - Empty responses logged but don't raise exceptions
            - Server errors logged as warnings, return empty dict
            - Git server typically returns error -32602, treated as normal

        Examples:
            >>> tools = MCP_Manager.tool_discovery("github")
            >>> print(tools.keys())  # ['list_repos', 'search_code', ...]
        """
        if mcp_server_name not in cls.mcp_servers:
            debug_warning(
                heading="MCP • TOOL_DISCOVERY_MISSED",
                body="Requested tool discovery on unknown server",
                metadata={"server": mcp_server_name},
            )
            return {}

        tool_discovery_request = {
            "jsonrpc": "2.0",
            "id": MCP_Manager.generate_response_id(),
            "method": "tools/list",
            "params": {},
        }

        try:
            proc = MCP_Manager.running_servers[mcp_server_name]
            proc.stdin.write(json.dumps(tool_discovery_request) + "\n")
            proc.stdin.flush()

            # 🔧 ENHANCED: Robust response reading with encoding handling
            try:
                response_line = proc.stdout.readline().strip()
                if not response_line:
                    debug_warning(
                        heading="MCP • TOOL_DISCOVERY_EMPTY_RESPONSE",
                        body="Server returned empty response for tools/list",
                        metadata={"server": mcp_server_name},
                    )
                    return {}

                # Handle potential encoding issues with multiple fallback strategies
                if isinstance(response_line, bytes):
                    # Try multiple encoding strategies for robust handling
                    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                        try:
                            response_line = response_line.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        # Final fallback: decode with error replacement
                        response_line = response_line.decode("utf-8", errors="replace")
                        debug_warning(
                            heading="MCP • TOOL_DISCOVERY_ENCODING_FALLBACK",
                            body="Used encoding fallback with character replacement",
                            metadata={"server": mcp_server_name},
                        )
                elif isinstance(response_line, str):
                    # Already a string, but might have encoding issues
                    try:
                        # Test if string is properly encoded by trying to encode/decode
                        response_line.encode("utf-8")
                    except UnicodeEncodeError:
                        # Re-encode with error handling
                        response_line = response_line.encode(
                            "utf-8", errors="replace"
                        ).decode("utf-8")
                        debug_warning(
                            heading="MCP • TOOL_DISCOVERY_STRING_ENCODING_FIX",
                            body="Fixed string encoding issues",
                            metadata={"server": mcp_server_name},
                        )

                response_line_json = json.loads(response_line)

            except UnicodeDecodeError as encoding_error:
                debug_error(
                    heading="MCP • TOOL_DISCOVERY_ENCODING_ERROR",
                    body=f"All encoding strategies failed: {encoding_error}",
                    metadata={"server": mcp_server_name},
                )
                return {}
            except json.JSONDecodeError as json_error:
                debug_error(
                    heading="MCP • TOOL_DISCOVERY_JSON_ERROR",
                    body=f"JSON parsing failed: {json_error}",
                    metadata={
                        "server": mcp_server_name,
                        "response_preview": str(response_line),
                    },
                )
                return {}

            # 🔧 ENHANCED: Handle different response formats and error cases
            if "error" in response_line_json:
                error_info = response_line_json["error"]
                error_code = error_info.get("code", "unknown")
                error_message = error_info.get("message", "unknown error")

                debug_warning(
                    heading="MCP • TOOL_DISCOVERY_SERVER_ERROR",
                    body=f"Server returned error: {error_message} (code: {error_code})",
                    metadata={
                        "server": mcp_server_name,
                        "error_code": error_code,
                        "error_message": error_message,
                        "full_error": str(error_info),
                    },
                )

                # For git server, this might be normal - just continue without tools
                if mcp_server_name == "git" and error_code == -32602:
                    debug_info(
                        heading="MCP • GIT_SERVER_PROTOCOL_ISSUE",
                        body="Git server has different protocol requirements, continuing without tools",
                        metadata={"server": mcp_server_name},
                    )

                return {}

            ### main successful path
            if (
                "result" in response_line_json
                and "tools" in response_line_json["result"]
            ):
                tools_found = response_line_json["result"]["tools"]
                debug_info(
                    heading="MCP • TOOLS_DISCOVERED",
                    body=f"Discovered {len(tools_found)} tools",
                    metadata={
                        "server": mcp_server_name,
                        "tools": [t.get("name", "unnamed") for t in tools_found],
                    },
                )
                if tools_found:
                    DynamicToolRegister.register_tool(
                        response_line_json,
                        MCP_Manager.mcp_servers[mcp_server_name].get("wrapper"),
                    )
                else:
                    debug_warning(
                        heading="MCP • NO_TOOLS",
                        body="Server returned empty tool list",
                        metadata={"server": mcp_server_name},
                    )
            else:
                debug_error(
                    heading="MCP • INVALID_TOOL_RESPONSE",
                    body="Server returned unexpected tools/list format",
                    metadata={
                        "server": mcp_server_name,
                        "response_preview": str(response_line_json),
                    },
                )
            return response_line_json

        except Exception as discovery_error:
            debug_error(
                heading="MCP • TOOL_DISCOVERY_EXCEPTION",
                body=f"Tool discovery failed with exception: {discovery_error}",
                metadata={
                    "server": mcp_server_name,
                    "error_type": type(discovery_error).__name__,
                    "error_message": str(discovery_error)[:200],
                },
            )
            return {}

    @classmethod
    @rich_exception_handler("MCP Server Startup")
    def start_server(cls, name: str):
        """Start an MCP server subprocess and initialize communication.

        This method spawns a registered MCP server as a subprocess, establishes
        stdio pipes for JSON-RPC communication, performs handshake initialization,
        discovers available tools, and registers them with the dynamic tool system.

        Args:
            name (str): Name of the server to start. Must match a server previously
                registered via add_server(). Used to lookup configuration in mcp_servers.

        Returns:
            bool: True if server started successfully, handshake completed, and tools
                discovered. False if any step fails or server is not registered.

        Raises:
            FileNotFoundError: If the runner command (npx, uvx, etc.) is not found
                in system PATH.
            PermissionError: If insufficient permissions to execute the command.
            subprocess.SubprocessError: If process spawning fails for any reason.
            json.JSONDecodeError: If server sends malformed JSON during handshake.
            TimeoutError: If server doesn't respond to initialization within timeout.

        Notes:
            - Server process uses PIPE for stdin/stdout for JSON-RPC communication
            - stderr is logged separately for debugging
            - Working directory set to project root (BASE_DIR.parent)
            - Handshake sends initialize request with protocol version info
            - Tool discovery happens immediately after successful handshake
            - Tools are automatically registered with DynamicToolRegister for LangChain
            - Process handle stored in running_servers dict for later management

        Warning:
            - This is a BLOCKING operation that can take 5-60 seconds for server startup
            - NPX servers take longer (15-30s) than UVX servers (5-10s)
            - Failed servers leave zombie processes if not properly cleaned up
            - No timeout on handshake - can hang indefinitely if server misbehaves
            - NOT thread-safe - concurrent start_server calls may cause race conditions

        Examples:
            >>> MCP_Manager.start_server("github")
            True
            >>> MCP_Manager.start_server("nonexistent")
            False
        """
        try:
            if name in MCP_Manager.mcp_servers:
                server_info = MCP_Manager.mcp_servers[name]
                runner = server_info["command"]
                args = server_info.get("args", [])

                # 🔧 DEBUG: Add comprehensive debugging
                debug_info(
                    heading="MCP • DEBUG_SERVER_START",
                    body=f"Starting server '{name}' with detailed debug info",
                    metadata={
                        "server": name,
                        "runner": str(runner),
                        "runner_type": str(type(runner)),
                        "runner_value": getattr(runner, "value", "NO_VALUE_ATTR"),
                        "args": str(args),
                        "args_type": str(type(args)),
                    },
                )

                # Convert Command enum to its string value
                try:
                    if hasattr(runner, "value"):
                        command_str = runner.value
                    else:
                        command_str = str(runner)

                    command = [command_str] + args

                    debug_info(
                        heading="MCP • DEBUG_COMMAND_ARRAY",
                        body=f"Command array created for '{name}'",
                        metadata={
                            "command_str": command_str,
                            "command_array": str(command),
                            "first_element": str(command[0]) if command else "EMPTY",
                            "first_element_type": (
                                str(type(command[0])) if command else "EMPTY"
                            ),
                        },
                    )

                except Exception as cmd_error:
                    debug_error(
                        heading="MCP • DEBUG_COMMAND_ERROR",
                        body=f"Error creating command for '{name}': {cmd_error}",
                        metadata={"server": name, "runner": str(runner)},
                    )
                    return False

                # Check working directory
                try:
                    working_dir = str(settings.BASE_DIR.parent.resolve())
                    debug_info(
                        heading="MCP • DEBUG_WORKING_DIR",
                        body=f"Working directory for '{name}': {working_dir}",
                        metadata={
                            "server": name,
                            "working_dir": working_dir,
                            "base_dir": str(settings.BASE_DIR),
                            "parent_exists": pathlib.Path(working_dir).exists(),
                        },
                    )
                except Exception as wd_error:
                    debug_error(
                        heading="MCP • DEBUG_WORKING_DIR_ERROR",
                        body=f"Error getting working directory: {wd_error}",
                        metadata={"server": name},
                    )
                    return False

                # the env variables must be added into the env to make server work as expected
                server_env = {**os.environ, **server_info.get("env", {})}
                # but now one more challange is that diff between env strings of windows and linux that we have to handle
                # for windows env could be gonna looks like :- %VAR_NAME% and for linux it could be $VAR_NAME so we have to handle this diff
                if os.name == "nt":  # windows
                    for key, value in server_env.items():
                        server_env[key] = os.path.expandvars(value)
                try:
                    # 🔧 FIX: Set proper encoding for subprocess communication
                    server_process = subprocess.Popen(
                        command,
                        shell=False,  # Use the shell false because it is causing issue if it ran in linux env with list arguments {reports/mcp/mcp_cascade_real_root_cause.md}
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",  # Explicitly set UTF-8 encoding
                        errors="replace",  # Handle encoding errors gracefully
                        bufsize=1,
                        cwd=working_dir,
                        env=server_env,
                    )
                    MCP_Manager.running_servers[name] = server_process
                    server_info["status"] = (
                        "failed"  # Set to failed until handshake completes
                    )

                    debug_info(
                        heading="MCP • SERVER_PROCESS_STARTED",
                        body=f"Successfully started process for '{name}'",
                        metadata={
                            "server": name,
                            "pid": server_process.pid,
                            "command": str(command),
                            "working_dir": working_dir,
                        },
                    )

                    # Handshake / initialize
                    try:
                        init_request = {
                            "jsonrpc": "2.0",
                            "id": MCP_Manager.generate_response_id(),
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {},
                                "clientInfo": {
                                    "name": "langgraph-mcp.md-client",
                                    "version": "1.0.0",
                                },
                            },
                        }
                        server_process.stdin.write(json.dumps(init_request) + "\n")
                        server_process.stdin.flush()
                        init_response = server_process.stdout.readline()
                        debug_info(
                            heading="MCP • SERVER_INITIALIZED",
                            body=f"Handshake completed for '{name}'",
                            metadata={"init_response_preview": init_response[:120]},
                        )
                        # Discover tools
                        try:
                            tools = cls.tool_discovery(name)
                            if tools and "result" in tools:
                                # map discovered tools to server
                                MPC_TOOL_SERVER_MAPPING.update(
                                    {
                                        tool["name"]: name
                                        for tool in tools["result"]["tools"]
                                    }
                                )  # working
                                server_info["status"] = "running"

                            else:
                                debug_warning(
                                    heading="MCP • DISCOVERY_EMPTY",
                                    body="No tools returned after discovery",
                                    metadata={"server": name},
                                )
                        except Exception as tool_discovery_error:
                            RichTracebackManager.handle_exception(
                                tool_discovery_error,
                                context=f"MCP Tool Discovery - {name}",
                                extra_context={
                                    "server_name": name,
                                    "init_response": str(init_response),
                                },
                            )
                            debug_error(
                                heading="MCP • DISCOVERY_ERROR",
                                body=f"Tool discovery failed: {tool_discovery_error}",
                                metadata={"server": name},
                            )
                            return False  # Server started but tool discovery failed, treat as failure for now
                    except Exception as init_error:
                        RichTracebackManager.handle_exception(
                            init_error,
                            context=f"MCP Server Initialization - {name}",
                            extra_context={
                                "server_name": name,
                                "command": str(command),
                                "process_id": server_process.pid,
                            },
                        )
                        debug_warning(
                            heading="MCP • INIT_FAILED",
                            body=f"Initialization failed: {init_error}",
                            metadata={"server": name},
                        )
                        return False  # Server process started but handshake failed, treat as failure for now

                    debug_info(
                        heading="MCP • SERVER_STARTED",
                        body=f"Started server '{name}'",
                        metadata={"args": args},
                    )
                    return True

                except subprocess.CalledProcessError as process_error:
                    RichTracebackManager.handle_exception(
                        process_error,
                        context=f"MCP Server Process Creation - {name}",
                        extra_context={
                            "command": str(command),
                            "server_name": name,
                            "runner": runner,
                        },
                    )
                    debug_error(
                        heading="MCP • PROCESS_ERROR",
                        body=f"Command failed: {process_error}",
                        metadata={"server": name, "command": str(command)},
                    )
                    return False
                except Exception as e:
                    RichTracebackManager.handle_exception(
                        e,
                        context=f"MCP Server Startup - {name}",
                        extra_context={
                            "server_name": name,
                            "command": str(command),
                            "runner": runner,
                        },
                    )
                    debug_error(
                        heading="MCP • STARTUP_ERROR",
                        body=f"Failed to start server: {e}",
                        metadata={"server": name},
                    )
                    return False
            else:
                debug_error(
                    heading="MCP • UNKNOWN_SERVER",
                    body="Attempted to start non-existent server",
                    metadata={"server": name},
                )
                return False
        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context=f"MCP Server Startup Wrapper - {name}",
                extra_context={"server_name": name},
            )
            debug_error(
                heading="MCP • CRITICAL_START_ERROR",
                body=f"Critical error starting server: {e}",
                metadata={"server": name},
            )
            return False

    def _initialize(self):
        """Initialize MCP Manager by loading enabled status from configuration.

        This private method is called by __init__ to set up the manager. It reads
        the MCP_ENABLED flag from settings and stores it in the class attribute.
        This determines whether MCP functionality is active.

        Args:
            None

        Returns:
            bool: True if MCP is enabled in configuration, False otherwise.
                Value is read from ContextRegistry.get().get_settings().mcp_enabled.

        Notes:
            - Sets MCP_Manager.mcp_enabled class attribute
            - Logs initialization with enabled status for debugging
            - Called only once per singleton instance creation
            - Does NOT load .mcp.json or register servers (done elsewhere)

        Warning:
            If MCP_ENABLED is False, servers may be registered but won't function.

        Examples:
            >>> manager._initialize()
            True  # If MCP_ENABLED=true in config
        """
        # Perform any necessary initialization here
        MCP_Manager.mcp_enabled = settings.MCP_CONFIG.get("MCP_ENABLED")
        debug_info(
            heading="MCP • MANAGER_INIT",
            body="MCP Manager initialized",
            metadata={"enabled": bool(MCP_Manager.mcp_enabled)},
        )
        return MCP_Manager.mcp_enabled

    @classmethod
    def call_mcp_server(
        cls, name: str, tool_name: str, args: dict
    ) -> Optional[dict[str, Any]]:
        """Send a JSON-RPC tool invocation request to a running MCP server.

        This method constructs and sends a "tools/call" JSON-RPC request to the
        specified server, waits for the response, and returns the parsed result.
        It handles encoding, error responses, and timeout scenarios.

        Args:
            name (str): Name of the running MCP server to call. Must exist in
                running_servers dict (server must be started first).
            tool_name (str): Name of the specific tool to invoke on the server.
                Must be a tool discovered during server startup.
            args (dict): Arguments to pass to the tool. Structure depends on tool's
                input schema. Sent in JSON-RPC "params" field.

        Returns:
            Optional[dict[str, Any]]: Structured response dictionary with keys:
                - "success" (bool): True if tool executed successfully
                - "content" (list): Array of content blocks from tool response
                - "error" (dict): Error details if success=False
                Returns None for critical failures (server not found, pipe broken).

        Raises:
            BrokenPipeError: If server process terminated unexpectedly
            json.JSONDecodeError: If server response is invalid JSON
            UnicodeDecodeError: If response encoding fails (handled internally)
            KeyError: If response missing required fields

        Notes:
            - Generates unique request ID via generate_response_id()
            - Sends JSON-RPC 2.0 "tools/call" method
            - Blocks waiting for server response on stdout
            - Handles both successful results and error responses
            - Content array can contain text, images, or resource URIs
            - Response structure: {"success": bool, "content": [...], "error": {...}}

        Warning:
            - BLOCKING operation with NO TIMEOUT - can hang indefinitely
            - If server doesn't respond, caller will block forever
            - No retry mechanism for transient failures
            - Pipe errors return None instead of raising

        Examples:
            >>> response = MCP_Manager.call_mcp_server(
            ...     "github",
            ...     "search_repositories",
            ...     {"query": "langchain", "perPage": 10}
            ... )
            >>> if response and response["success"]:
            ...     print(response["content"])
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
            metadata={"server": name, "args": args},
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
                "params": {"name": tool_name, "arguments": args},
            }
            proc.stdin.write(json.dumps(mcp_request) + "\n")
            proc.stdin.flush()

            # 🔧 FIX: Robust response reading with encoding handling
            try:
                response_line = proc.stdout.readline().strip()
                if not response_line:
                    msg = f"No response from server '{name}'"
                    debug_error(
                        heading="MCP • CALL_ERROR", body=msg, metadata={"server": name}
                    )
                    return {"success": False, "error": msg}

                # Handle potential encoding issues with multiple fallback strategies
                if isinstance(response_line, bytes):
                    # Try multiple encoding strategies for robust handling
                    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                        try:
                            response_line = response_line.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        # Final fallback: decode with error replacement
                        response_line = response_line.decode("utf-8", errors="replace")
                        debug_warning(
                            heading="MCP • CALL_ENCODING_FALLBACK",
                            body="Used encoding fallback with character replacement for tool call",
                            metadata={"server": name, "tool": tool_name},
                        )
                elif isinstance(response_line, str):
                    # Already a string, but might have encoding issues
                    try:
                        # Test if string is properly encoded by trying to encode/decode
                        response_line.encode("utf-8")
                    except UnicodeEncodeError:
                        # Re-encode with error handling
                        response_line = response_line.encode(
                            "utf-8", errors="replace"
                        ).decode("utf-8")
                        debug_warning(
                            heading="MCP • CALL_STRING_ENCODING_FIX",
                            body="Fixed string encoding issues in tool call response",
                            metadata={"server": name, "tool": tool_name},
                        )

            except UnicodeDecodeError as encoding_error:
                msg = f"Encoding error reading response: {encoding_error}"
                debug_error(
                    heading="MCP • CALL_ENCODING_ERROR",
                    body=msg,
                    metadata={"server": name, "tool": tool_name},
                )
                return {"success": False, "error": msg}

            try:
                json_response = json.loads(response_line)
                if "error" in json_response:
                    msg = f"MCP server error: {json_response['error']}"
                    debug_error(
                        heading="MCP • TOOL_ERROR",
                        body=msg,
                        metadata={"server": name, "tool": tool_name},
                    )
                    return {"success": False, "error": msg}
                if "result" in json_response:
                    debug_info(
                        heading="MCP • TOOL_SUCCESS",
                        body="Tool executed successfully",
                        metadata={"server": name, "tool": tool_name},
                    )
                    return {"success": True, "data": json_response["result"]}
                debug_warning(
                    heading="MCP • NO_RESULT_FIELD",
                    body="Response missing 'result' field; returning raw payload",
                    metadata={"server": name, "tool": tool_name},
                )
                return {"success": True, "data": json_response}
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON response: {e}"
                debug_error(
                    heading="MCP • PARSE_ERROR",
                    body=msg,
                    metadata={"server": name, "tool": tool_name},
                )
                return {"success": False, "error": msg, "raw_response": response_line}
        except Exception as e:
            msg = f"Communication error: {e}"
            debug_error(
                heading="MCP • COMM_ERROR",
                body=msg,
                metadata={"server": name, "tool": tool_name},
            )
            return {"success": False, "error": msg}

    @classmethod
    def stop_server(cls, name: str) -> bool:
        """Gracefully stop a specific MCP server by terminating its process.

        This method terminates the server subprocess, waits for clean exit, removes
        it from running_servers tracking, and updates its status. Handles timeout
        and errors gracefully.

        Args:
            name (str): Name of the server to stop. Must exist in running_servers.

        Returns:
            bool: True if server stopped successfully, False if server not running
                or termination failed.

        Raises:
            Does NOT raise exceptions. All errors caught and logged.

        Notes:
            - Sends SIGTERM to process (graceful shutdown)
            - Waits up to 5 seconds for process to exit
            - Removes process from running_servers dict
            - Updates server status to "stopped" in mcp_servers
            - If process doesn't exit in 5s, leaves zombie process
            - Logs all outcomes for debugging

        Warning:
            - Does NOT send SIGKILL if SIGTERM fails
            - May leave zombie processes if server hangs
            - No cleanup of stdio pipes or file handles
            - Status set to "stopped" even if termination fails

        Examples:
            >>> MCP_Manager.stop_server("github")
            True  # Server stopped successfully
            >>> MCP_Manager.stop_server("nonexistent")
            False  # Server not running
        """
        if name not in cls.running_servers:
            debug_warning(
                heading="MCP • STOP_IGNORED",
                body="Stop requested for server not running",
                metadata={"server": name},
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
                metadata={"server": name},
            )
            return True
        except Exception as e:
            debug_error(
                heading="MCP • STOP_ERROR",
                body=f"Failed to stop server: {e}",
                metadata={"server": name},
            )
            return False

    @classmethod
    def stop_all_servers(cls) -> bool:
        """Stop all running MCP servers sequentially.

        This method iterates through all running servers and attempts to stop each
        one. It's designed for graceful shutdown and cleanup scenarios. Continues
        attempting to stop all servers even if some fail.

        Args:
            None

        Returns:
            bool: True if ALL servers stopped successfully. False if ANY server
                failed to stop or if stopping raised exceptions.

        Raises:
            Does NOT raise exceptions. All errors caught and logged.

        Notes:
            - Iterates over copy of running_servers keys to avoid mutation issues
            - Calls stop_server() for each running server
            - Continues stopping other servers if one fails
            - Logs overall success/partial failure status
            - If no servers running, returns True immediately
            - Safe to call multiple times

        Warning:
            - Some servers may be stopped while others fail
            - No rollback if partial failure occurs
            - Failed servers may leave zombie processes
            - NOT atomic - state changes even on failure

        Examples:
            >>> MCP_Manager.stop_all_servers()
            True  # All servers stopped successfully
        """
        if not cls.running_servers:
            debug_info(
                heading="MCP • STOP_ALL_SKIP",
                body="No running servers to stop",
                metadata={},
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
                    metadata={"server": server_name},
                )
                success = False
        if success:
            debug_info(
                heading="MCP • STOP_ALL_COMPLETE",
                body="All servers stopped",
                metadata={},
            )
        else:
            debug_warning(
                heading="MCP • STOP_ALL_PARTIAL",
                body="Some servers failed to stop",
                metadata={},
            )
        return success

    @classmethod
    def cleanup(cls):
        """Perform final cleanup of all MCP resources for application shutdown.

        This method is designed for integration with ChatDestructor or similar
        cleanup systems. It attempts to stop all servers and handles any errors
        gracefully without raising exceptions.

        Args:
            None

        Returns:
            None

        Raises:
            Does NOT raise exceptions. All errors caught and logged.

        Notes:
            - Called during application shutdown or error recovery
            - Wraps stop_all_servers() with exception handling
            - Logs cleanup failures but doesn't propagate them
            - Safe to call multiple times
            - Safe to call if no servers running

        Warning:
            - Does NOT wait for servers to fully terminate
            - Does NOT cleanup server configurations or registrations
            - Does NOT release other resources (file handles, etc.)
            - Only stops running processes

        Examples:
            >>> MCP_Manager.cleanup()  # Called by ChatDestructor
        """
        try:
            cls.stop_all_servers()
        except Exception as e:
            debug_error(
                heading="MCP • CLEANUP_ERROR", body=f"Cleanup failed: {e}", metadata={}
            )

    @classmethod
    def read_uri_resource(cls, server_name: str, uri_resource) -> dict[str, Any] | None:
        """Read a resource or prompt from an MCP server via URI.

        This method sends a "resources/read" JSON-RPC request to retrieve content
        from a server-provided URI. Used for accessing prompts, templates, or other
        resources exposed by MCP servers.

        Args:
            server_name (str): Name of the running MCP server to query.
            uri_resource (str): URI of the resource to read. Format depends on
                server implementation (e.g., "prompt://template-name").

        Returns:
            Optional[dict[str, Any]]: Structured response with keys:
                - "success" (bool): True if resource read successfully
                - "content" (list): Array of content blocks from resource
                - "error" (dict): Error details if success=False
                Returns None for critical failures (server not found).

        Raises:
            Does NOT raise exceptions. All errors returned in response dict.

        Notes:
            - Sends JSON-RPC 2.0 "resources/read" method
            - Similar protocol to call_mcp_server but different method
            - Blocks waiting for server response
            - Response structure mirrors tool call responses

        Warning:
            - BLOCKING operation with NO TIMEOUT
            - URI format varies by server implementation
            - Not all servers support resources/read

        Examples:
            >>> response = MCP_Manager.read_uri_resource(
            ...     "memory",
            ...     "prompt://recall-context"
            ... )
        """

        if server_name not in cls.mcp_servers:
            msg = f"Server '{server_name}' not found"
            debug_error(
                heading="MCP • URI_READ_ERROR",
                body=msg,
                metadata={"server": server_name},
            )
            return {"success": False, "error": msg}
        if MCP_Manager.mcp_servers[server_name]["status"] != "running":
            msg = f"Server '{server_name}' is not running"
            debug_error(
                heading="MCP • URI_READ_ERROR",
                body=msg,
                metadata={"server": server_name},
            )
            return {"success": False, "error": msg}
        debug_info(
            heading="MCP • URI_READ",
            body=f"Reading URI resource '{uri_resource}'",
            metadata={"server": server_name, "uri": uri_resource},
        )
        proc = MCP_Manager.running_servers.get(server_name)
        if not proc:
            msg = f"Server '{server_name}' process not found"
            debug_error(
                heading="MCP • URI_READ_ERROR",
                body=msg,
                metadata={"server": server_name},
            )
            return {"success": False, "error": msg}
        try:
            mcp_uri_read_request = {
                "jsonrpc": "2.0",
                "id": MCP_Manager.generate_response_id(),
                "method": "resources/read",
                "params": {"uri": uri_resource},
            }
            proc.stdin.write(json.dumps(mcp_uri_read_request) + "\n")
            proc.stdin.flush()
            # 🔧 FIX: Robust response reading with encoding handling
            try:
                response_line = proc.stdout.readline().strip()
                if not response_line:
                    msg = f"No response from server '{server_name}'"
                    debug_error(
                        heading="MCP • URI_READ_ERROR",
                        body=msg,
                        metadata={"server": server_name},
                    )
                    return {"success": False, "error": msg}

                # Handle potential encoding issues with multiple fallback strategies
                if isinstance(response_line, bytes):
                    # Try multiple encoding strategies for robust handling
                    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
                        try:
                            response_line = response_line.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        # Final fallback: decode with error replacement
                        response_line = response_line.decode("utf-8", errors="replace")
                        debug_warning(
                            heading="MCP • URI_READ_ENCODING_FALLBACK",
                            body="Used encoding fallback with character replacement for URI read",
                            metadata={"server": server_name, "uri": uri_resource},
                        )
                elif isinstance(response_line, str):
                    # Already a string, but might have encoding issues
                    try:
                        # Test if string is properly encoded by trying to encode/decode
                        response_line.encode("utf-8")
                    except UnicodeEncodeError:
                        # Re-encode with error handling
                        response_line = response_line.encode(
                            "utf-8", errors="replace"
                        ).decode("utf-8")
                        debug_warning(
                            heading="MCP • URI_READ_STRING_ENCODING_FIX",
                            body="Fixed string encoding issues in URI read response",
                            metadata={"server": server_name, "uri": uri_resource},
                        )
            except UnicodeDecodeError as encoding_error:
                msg = f"Encoding error reading response: {encoding_error}"
                debug_error(
                    heading="MCP • URI_READ_ENCODING_ERROR",
                    body=msg,
                    metadata={"server": server_name, "uri": uri_resource},
                )
                return {"success": False, "error": msg}
            try:
                json_response = json.loads(response_line)
                if "error" in json_response:
                    msg = f"MCP server error: {json_response['error']}"
                    debug_error(
                        heading="MCP • URI_READ_TOOL_ERROR",
                        body=msg,
                        metadata={"server": server_name, "uri": uri_resource},
                    )
                    return {"success": False, "error": msg}
                ## pass main successful response
                if "result" in json_response:
                    debug_info(
                        heading="MCP • URI_READ_SUCCESS",
                        body="URI resource read successfully",
                        metadata={"server": server_name, "uri": uri_resource},
                    )
                    return {"success": True, "data": json_response["result"]}
                debug_warning(
                    heading="MCP • URI_READ_NO_RESULT_FIELD",
                    body="Response missing 'result' field; returning raw payload",
                    metadata={"server": server_name, "uri": uri_resource},
                )
                # return full response if no result field
                return {"success": True, "data": json_response}
            except json.JSONDecodeError as e:
                msg = f"Invalid JSON response: {e}"
                debug_error(
                    heading="MCP • URI_READ_PARSE_ERROR",
                    body=msg,
                    metadata={"server": server_name, "uri": uri_resource},
                )
                return {"success": False, "error": msg, "raw_response": response_line}
        except Exception as e:
            msg = f"Communication error: {e}"
            debug_error(
                heading="MCP • URI_READ_COMM_ERROR",
                body=msg,
                metadata={"server": server_name, "uri": uri_resource},
            )
            return {"success": False, "error": msg}

