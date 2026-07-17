"""chat_initializer.py

Chat session initialization and lifecycle management for AI Agent Workflow.

This module provides the ChatInitializer class which orchestrates the complete
setup of the chat application, including LangGraph compilation, tool registration,
MCP server management, socket initialization, and Neo4j database connections.

Features:
    - Complete chat session bootstrap and initialization
    - LangGraph graph compilation with State schema
    - Tool registration (18 core tools + MCP dynamic tools)
    - MCP server management with async startup
    - Socket server for external integrations
    - Neo4j database connection management
    - Exit listener for graceful shutdown
    - Rich CLI presentation with modern input handling

Classes:
    ChatInitializer: Main orchestrator for chat session initialization

Dependencies:
    - langgraph: Graph-based agent orchestration
    - rich: Terminal UI and error formatting
    - asyncio: Async MCP server management
    - src.mcp.manager: MCP server lifecycle
    - src.tools: Core tool implementations
    - src.models.state: State management
    - src.ui.chatInputHandler: Modern CLI input

Notes:
    This class handles the complete initialization sequence:
    1. Core class setup
    2. Tool registration (LangChain tools)
    3. LangGraph compilation
    4. MCP server startup (async)
    5. Neo4j connection
    6. Socket server (if enabled)
    7. Exit listener registration

Warning:
    - Initialization can take 30-60 seconds due to MCP server startup
    - Network-dependent operations may fail silently
    - Some initialization errors are non-fatal (logged but don't stop startup)
"""
import asyncio
import gc
import json
import platform
import threading
from pathlib import Path
from threading import Thread
from typing import Awaitable

from langgraph.graph.state import CompiledStateGraph
from rich import console, inspect
from rich import prompt as rich_prompt  # Renamed to avoid conflict

from src.config import settings
from src.config.settings import PNG_FILE_PATH
from src.mcp.load_config import McpConfigFile
from src.mcp.manager import MCP_Manager
from src.models.state import StateAccessor, State
from src.ui.diagnostics.debug_helpers import debug_warning, debug_info

# 🎨 Rich Traceback Integration
from src.ui.diagnostics.rich_traceback_manager import (
    RichTracebackManager,
    rich_exception_handler,
)
from src.ui.print_message_style import print_message
from src.utils.socket_manager import SocketManager

from src.utils.listeners.exit_listener import ExitListener

# mcp.md servers integration

# Modern CLI input handler
from src.ui.chatInputHandler import InputHandler


class ChatInitializer:
    """Orchestrate complete initialization of the AI chat application.

    This class manages the full lifecycle setup of the chat session, including
    tool registration, graph compilation, MCP server startup, database connections,
    and UI initialization. It ensures all components are properly initialized before
    the chat loop begins.

    Attributes:
        break_loop (bool|None): Flag to signal chat loop termination. Set by
            exit commands or listeners.
        _exit_function (Callable|None): Callback function for graceful shutdown.
            Registered with ExitListener.
        os (str): Operating system name (Linux, Windows, Darwin). Used for
            platform-specific behavior.
        console (rich.console.Console): Rich console for formatted terminal output.
        _state (State): TypedDict containing messages list and message_type.
            Initial state with empty messages.
        state_accessor (StateAccessor): Singleton accessor for state management.
            Provides thread-safe state access.
        graph (CompiledStateGraph|None): Compiled LangGraph graph. None until
            compiled via node_assign.
        tools (list|None): List of registered LangChain tools. Includes core
            tools and dynamically discovered MCP tools.

    Methods:
        tools_register: Register all LangChain tools (core + MCP)
        initialize_mcp: Start and configure all MCP servers
        initialize_neo4j: Connect to Neo4j vector database
        initialize_socket: Start socket server for external communication

    Notes:
        - Initialization order matters - tools before graph, MCP after tools
        - MCP server startup is async and can take 30-60 seconds
        - Non-fatal errors are logged but don't prevent startup
        - Rich traceback handler wraps initialization for beautiful error reporting
        - State is initialized empty and populated during first user interaction

    Warning:
        - Initialization failures in non-critical components don't stop startup
        - MCP server failures are logged but application continues
        - Socket and Neo4j failures are non-blocking
        - Graph must be compiled before chat loop starts

    Examples:
        >>> initializer = ChatInitializer()
        >>> await initializer.initialize_mcp()
        >>> initializer.tools_register()
        >>> # Graph compilation happens in main_orchestrator
    """

    @rich_exception_handler("ChatInitializer Initialization")
    def __init__(self):
        self.break_loop = None  # This will be used to break the chat loop
        self._exit_function = None
        self.os = platform.system()
        self.console = console.Console()
        # Rich traceback is already initialized in main_orchestrator.py
        self._set_core_classes()  # set core classes for messages
        # Initialize state with empty messages and no message type
        self._state: State = {"messages": [], "message_type": None}
        self.state_accessor = StateAccessor()
        self.graph = None  # graph.compile() will be called later
        self.tools = None

        # mcp.md servers integration - only if enabled
        if settings.MCP_CONFIG.get("MCP_ENABLED", False):
            self._initialize_mcp_servers_sync()
        else:
            debug_info(
                heading="MCP • SKIPPED",
                body="MCP server initialization skipped (MCP_ENABLED=false)",
                metadata={"enabled": False},
            )
        self.initialize_neo4j()
        self._register_slash_commands()

        # Register logging handlers
        self._register_logging_handlers()

        self.ToolResponseManager = None  # Initialize ToolResponseManager later

    @rich_exception_handler("Core Classes Setup")
    def _set_core_classes(self):
        try:
            # Import here to avoid circular imports
            from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

            try:
                import sentry_sdk  # Optional; ignore if missing

                sentry_sdk.init(send_default_pii=True)
            except Exception:
                pass

            # we must set the console for rich console to use it in different classes to the settings
            settings.console = self.console

            # Set message classes for centralized access
            settings.HumanMessage = HumanMessage
            settings.AIMessage = AIMessage
            settings.BaseMessage = BaseMessage

            # now import the ToolResponseManager to set the response
            from src.tools.lggraph_tools.tool_response_manager import (
                ToolResponseManager,
            )

            self.ToolResponseManager = ToolResponseManager()

            # Set the socket connection for system_logging
            settings.socket_con = SocketManager.get_socket_con()

            # register the exit listener
            settings.listeners["exit"] = ExitListener()
            settings.listeners["exit"].register()

        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="Core Classes Setup",
                extra_context={"phase": "message_classes_initialization"},
            )
            raise

    def set_graph(self, graph):
        if not isinstance(graph, CompiledStateGraph):
            raise ValueError(
                "Provided graph is not a valid CompiledStateGraph instance"
            )
        self.graph = graph
        return self

    def set_exit(self, func):
        if hasattr(func, "__call__"):
            self._exit_function = func
            return self
        else:
            raise ValueError("Provided exit function is not callable")

    def on_exit(self):
        """
        Handles cleanup and saving of conversation history when the chatbot session ends.
        """
        self.console.print("\t\t----[bold][red]Node is onExit[/bold][red]")
        # 🔄 Sync StateAccessor with final LangGraph state
        self.state_accessor.sync_with_langgraph(self._state)
        history = []
        messages = self.state_accessor.get_messages()
        for msg in messages:
            history.append({"type": msg.type, "content": msg.content})
        json.dump(history, Path("conversation_history.json").open("w"), indent=2)
        # Let ChatDestructor handle socket cleanup - don't close prematurely
        # run the exit function if it is set in the another thread
        if self._exit_function:
            # run the exit function in another thread
            t = Thread(target=self._exit_function)
            t.start()
        else:
            self.console.print(
                "[bold red]No exit function set. Exiting without cleanup.[/bold red]"
            )
        # print the final state for debugging
        inspect(self._state)
        return {
            "messages": [
                settings.AIMessage(content="Thank you for using the LangGraph Chatbot!")
            ]
        }

    def save_graph_png(self):
        import os

        if self.graph is None:
            raise ValueError(
                "Graph is not initialized. Please compile the graph first."
            )
        path = PNG_FILE_PATH
        with Path(path).open("wb") as f:
            f.write(self.graph.get_graph().draw_mermaid_png())
        if self.os == "Linux":
            os.system(f"xdg-open {path}")
        elif self.os == "Darwin":
            os.system(f"open {path}")
        elif self.os == "Windows":
            os.startfile(path)
        return self

    @rich_exception_handler("MCP Server Initialization")
    async def initialize_mcp_servers(self):
        """Initialize and start all configured MCP servers asynchronously with timeout.

        This method loads MCP server configurations from .mcp.json, registers each
        server with MCP_Manager, and starts them concurrently using asyncio.gather.
        Each server startup is wrapped with timeout protection to prevent indefinite
        hangs.

        Args:
            None

        Returns:
            None

        Raises:
            Exception: Non-fatal exceptions are caught and logged via RichTracebackManager.
                Server startup failures don't prevent application from continuing.

        Notes:
            - Loads server configs from McpConfigFile.retrieve_config()
            - Each server config contains: name, command, args, wrapper function
            - Servers are added to MCP_Manager registry before starting
            - All servers start concurrently via asyncio.create_task
            - Individual server timeouts configurable via MCP_SERVER_START_TIMEOUT
            - Default timeout is 30 seconds per server
            - Uses Utils.start_server_async_with_timeout for timeout enforcement
            - Failed servers are logged but don't block other servers

        Warning:
            - Uses asyncio.gather() which FAILS FAST by default
            - If any server times out, ALL pending servers may be cancelled
            - Should use asyncio.gather(*tasks, return_exceptions=True) for fault tolerance
            - NPX servers take 15-30s to start (may timeout)
            - UVX servers take 5-10s to start
            - Git server often returns errors but this is expected

        Examples:
            >>> await initializer.initialize_mcp_servers()
            # All servers start concurrently with 30s timeout each
        """
        try:
            from src.mcp.manager import MCP_Manager

            # Add and start MCP servers if needed with allowed path of AI_llm folder
            # to add server we required [server_name, runner, package, server_args, server_wrapper]
            # list form of that is: (that's working)
            # add_servers_config: List[ServerConfig] = [
            #     {
            #         "name": 'filesystem',
            #         "command": Command.NPX,
            #         "package": "@modelcontextprotocol/server-filesystem",
            #         "args": [f"{settings.BASE_DIR.parent}"],
            #         "wrapper": FileSystemWrapper
            #     },
            #     # Add more servers here as needed
            # ]

            add_servers_config = McpConfigFile.retrieve_config()

            # add servers for list (that's working)
            for server_config in add_servers_config:
                server_name = server_config["name"]
                runner = server_config[
                    "command"
                ]  # this has been changed to command from runner (uvx, npx, pipx, pip, python)
                # package = server_config["package"]
                args = server_config["args"]
                wrapper = server_config["wrapper"]

                MCP_Manager.add_server(
                    server_name, package=None, runner=runner, args=args, func=wrapper
                )

            # LEGACY: Uncomment if you want to use the legacy filesystem server
            # MCP_Manager.add_server("filesystem", "npx", "@modelcontextprotocol/server-filesystem", [f"{settings.BASE_DIR.parent}"], FileSystemWrapper)
            # start the MCP servers in asynchronously (that's working)
            # todo tesinng for applying time out for starintg up the servers
            # async def start_mcp_server(server_name: str):
            #     loop = asyncio.get_running_loop()
            #     got_start = await loop.run_in_executor(
            #         None, MCP_Manager.start_server, server_name
            #     )
            #     if not got_start:
            #         debug_warning(
            #             heading="MCP Server Startup Failed",
            #             body=f"Failed to start MCP server: {server_name}",
            #             metadata={"server_name": server_name},
            #         )
            #     else:
            #         debug_info(
            #             heading="MCP Server Started",
            #             body=f"MCP server '{server_name}' started successfully.",
            #             metadata={"server_name": server_name},
            #         )
            #
            from ..mcp.mcp_manager_util import Utils

            utils = Utils()  # Create an instance of the utility class

            start_mcp_server = (
                utils.start_server_async_with_timeout
            )  # Use the utility function with timeout (monkey patch for better recovery to the legacy code if any issues or change of mind)
            task: list[Awaitable] = [
                asyncio.create_task(
                    start_mcp_server(
                        server, settings.MCP_CONFIG.get("MCP_SERVER_START_TIMEOUT", 30)
                    )
                )
                for server in MCP_Manager.mcp_servers
            ]
            await asyncio.gather(*task)

        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="MCP Server Initialization",
                extra_context={"phase": "mcp_manager_import_and_setup"},
            )
            # Non-fatal

    @rich_exception_handler("Neo4j Database Initialization")
    def initialize_neo4j(self):
        from src.ui.diagnostics.debug_helpers import debug_warning, debug_info

        """Attempt to initialize Neo4j connection; skip silently if unavailable."""
        try:
            try:
                from neo4j import GraphDatabase  # type: ignore
            except Exception:
                # Neo4j not installed; log and return
                debug_warning(
                    heading="Neo4j Driver Not Found",
                    body="Neo4j driver is not installed. Skipping Neo4j initialization.",
                    metadata={
                        "neo4j_uri": settings.NEO4J_URI,
                        "neo4j_user": settings.NEO4J_USER,
                    },
                )
                return
            # if neo4j driver is installed, try to create the driver
            settings.neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
            if settings.neo4j_driver is None:
                raise RuntimeError("Failed to create Neo4j driver.")
            debug_info(
                heading="Neo4j Driver Initialized",
                body="Neo4j driver created successfully.",
                metadata={
                    "neo4j_uri": settings.NEO4J_URI,
                    "neo4j_user": settings.NEO4J_USER,
                    "driver_status": "created_successfully",
                },
            )
        except Exception as e:
            # Log but DO NOT raise (make optional)
            RichTracebackManager.handle_exception(
                e,
                context="Neo4j Database Connection (optional)",
                extra_context={
                    "neo4j_uri": settings.NEO4J_URI,
                    "neo4j_user": settings.NEO4J_USER,
                    "driver_status": "failed_to_create_optional",
                },
            )
            if settings.socket_con:
                debug_warning(
                    heading="Neo4j Driver Initialization Failed",
                    body="Neo4j driver initialization failed. Continuing without Neo4j support.",
                    metadata={
                        "neo4j_uri": settings.NEO4J_URI,
                        "neo4j_user": settings.NEO4J_USER,
                        "error_message": str(e),
                    },
                )
            settings.neo4j_driver = None

    @rich_exception_handler("Tool Registration")
    def tools_register(self):
        """
        Register tools for the chat application.
        This method can be extended to register any tools needed for the chat.
        """
        try:
            from src.tools.lggraph_tools.tool_assign import ToolAssign
            from src.tools.lggraph_tools.wrappers.google_wrapper import (
                GoogleSearchToolWrapper,
            )
            from src.tools.lggraph_tools.wrappers.translate_wrapper import (
                TranslateToolWrapper,
            )
            from src.tools.lggraph_tools.wrappers.rag_search_classifier_wrapper import (
                RagSearchClassifierWrapper,
            )
            from src.tools.lggraph_tools.wrappers.run_shell_comand_wrapper import (
                ShellCommandWrapper,
            )
            from src.tools.lggraph_tools.wrappers.browser_use_wrapper import (
                BrowserUseWrapper,
            )

            # schema
            from src.tools.lggraph_tools.tool_schemas.tools_structured_classes import (
                google_search,
                rag_search_message,
                TranslationMessage,
                run_shell_command_message,
                browser_agent,
            )

            # dynamically register tools
            from src.mcp.dynamically_tool_register import DynamicToolRegister

            tools = []

            # Register each tool with individual error handling
            tool_configs = [
                (
                    "google_search",
                    GoogleSearchToolWrapper,
                    "For general web searches (recent info, facts, news).",
                    google_search,
                ),
                (
                    "rag_search",
                    RagSearchClassifierWrapper,
                    "For searching the knowledge base (RAG search).",
                    rag_search_message,
                ),
                (
                    "translate",
                    TranslateToolWrapper,
                    "For translating messages into different languages.",
                    TranslationMessage,
                ),
                (
                    "run_shell_command",
                    ShellCommandWrapper,
                    "For executing shell commands.",
                    run_shell_command_message,
                ),
                (
                    "browser_agent",
                    BrowserUseWrapper,
                    "An autonomous AI agent that can control a web browser to perform complex tasks. Provide a high-level objective (e.g., 'Open Spotify and play a sad song') and the agent will handle the step-by-step execution. This is a powerful, autonomous tool; do not decompose its tasks.",
                    browser_agent,
                ),
            ]

            for name, func, description, schema in tool_configs:
                try:
                    tool = ToolAssign(
                        func=func,
                        name=name,
                        description=description,
                        args_schema=schema,
                    )
                    tools.append(tool)
                except Exception as tool_error:
                    RichTracebackManager.handle_exception(
                        tool_error,
                        context=f"Tool Registration - {name}",
                        extra_context={"tool_name": name, "tool_function": str(func)},
                    )
                    # Continue with other tools even if one fails
                    continue

            # Add dynamically registered tools with error handling
            try:
                dynamic_tools = DynamicToolRegister.tool_list
                tools.extend(dynamic_tools)
            except Exception as dynamic_error:
                RichTracebackManager.handle_exception(
                    dynamic_error,
                    context="Dynamic Tool Registration",
                    extra_context={
                        "dynamic_tools_count": len(
                            getattr(DynamicToolRegister, "tool_list", [])
                        )
                    },
                )

            # Set tools list
            ToolAssign.set_tools_list(tools)
            self.tools = ToolAssign.get_tools_list()

            debug_info(
                heading="Tools Registered",
                body=f"Registered {len(self.tools)} tools successfully.",
                metadata={
                    "tools_count": len(self.tools),
                },
            )

            return self

        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="Tool Registration System",
                extra_context={"phase": "tool_registration_setup"},
            )
            raise

    @rich_exception_handler("Chat Execution Loop")
    def run_chat(self):
        try:
            # make sure all the fields are initialized
            if not self._state or not self.graph or not self.tools:
                raise ValueError(
                    "Chat is not properly initialized. Please ensure all components are set up."
                )
            # testing new chat input
            # user_input = prompt.Prompt.ask(
            #     "[bold cyan]You[/bold cyan]", default="", show_default=False
            # )

            user_input = InputHandler().get_user_input()

            if user_input.lower() == "exit" or settings.exit_flag:
                self.console.print("[bold red]Exiting the chat...[/bold red]")
                try:
                    self.on_exit()
                except Exception as exit_error:
                    RichTracebackManager.handle_exception(
                        exit_error,
                        context="Chat Exit Process",
                        extra_context={"user_input": user_input},
                    )
                self.break_loop = True
            else:
                try:
                    self._state["messages"].append(
                        settings.HumanMessage(content=user_input)
                    )
                    print_message(user_input, sender="user")
                    self._state = self.graph.invoke(self._state)

                    # ✅ FIXED: Only set exit_flag when user actually wants to exit
                    # Check if this was an exit-related workflow
                    if (
                        user_input.lower() == "exit"
                        or user_input.startswith("/exit")
                        or any(
                            msg.content.lower() == "exit"
                            or msg.content.startswith("/exit")
                            for msg in self._state.get("messages", [])[-2:]
                        )
                    ):  # Check last 2 messages

                        # Only NOW set the flag to True (first time)
                        settings.exit_flag = True

                        settings.listeners["exit"].emit_exit_ticket(
                            source_class=ChatInitializer,
                            source_name="workflow_completion",
                        )
                    else:
                        # ✅ CRITICAL FIX: Reset flag to False for non-exit messages
                        settings.exit_flag = False

                    try:
                        self.state_accessor.sync_with_langgraph(self._state)
                    except Exception as sync_error:
                        RichTracebackManager.handle_exception(
                            sync_error,
                            context="State Accessor Sync",
                            extra_context={"state_keys": list(self._state.keys())},
                        )
                except Exception as chat_processing_error:
                    RichTracebackManager.handle_exception(
                        chat_processing_error,
                        context="Chat Message Processing",
                        extra_context={
                            "user_input": user_input[:100],
                            "processing_phase": "message_handling",
                        },
                    )
                    self.console.print(
                        "[bold red]Error processing message. Please try again.[/bold red]"
                    )
            try:
                gc.collect()
            except Exception as gc_error:
                RichTracebackManager.handle_exception(
                    gc_error,
                    context="Garbage Collection",
                    extra_context={"phase": "post_chat_cleanup"},
                )
        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="Chat Execution Loop",
                extra_context={"phase": "main_chat_loop"},
            )
            raise

    def _initialize_mcp_servers_sync(self):
        """Synchronous wrapper for MCP server initialization"""

        def run_async_init():
            # Create new event loop for this thread if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async initialization
            loop.run_until_complete(self.initialize_mcp_servers())

        # Run in separate thread to avoid event loop conflicts
        init_thread = threading.Thread(target=run_async_init)
        init_thread.start()
        init_thread.join()  # Wait for completion

        debug_info(
            heading="MCP • SYNC_INIT_COMPLETE",
            body="All MCP servers initialized synchronously",
            metadata={"servers_count": len(MCP_Manager.mcp_servers)},
        )

    def _register_slash_commands(self):
        """Register core slash commands like /help, /clear, /agent"""
        from src.slash_commands.commands.clear import register_clear_command
        from src.slash_commands.commands.help import register_help_command
        from src.slash_commands.commands.exit import register_exit_command

        # core/routing slash commands
        from src.slash_commands.commands.core_slashs.agent import register_agent_command
        from src.slash_commands.commands.core_slashs.chat_llm import (
            register_chat_llm_command,
        )
        from src.slash_commands.commands.core_slashs.use_tool import (
            register_slash_command_use_tool,
        )

        async def register_commands():
            ##### this is the place which register the all slash commands #####
            tasks = [
                asyncio.to_thread(register_clear_command),
                asyncio.to_thread(register_help_command),
                asyncio.to_thread(register_agent_command),
                asyncio.to_thread(register_exit_command),
                asyncio.to_thread(register_chat_llm_command),
                asyncio.to_thread(register_slash_command_use_tool),
            ]
            await asyncio.gather(*tasks)

        def run_async_init():
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(register_commands())

        init_thread = threading.Thread(target=run_async_init)
        init_thread.start()
        init_thread.join()  # Wait for completion

        debug_info(
            heading="Slash Commands Registered",
            body="Core slash commands registered successfully.",
            metadata={},
        )

    def _register_logging_handlers(self):
        """Register logging handlers for the chat application."""
        pass  # Implement logging handler registration as needed

        from ..system_logging.on_time_registry import OnTimeRegistry
        from ..system_logging.handlers.handler_base import TextHandler

        async def register_handlers():
            ##### this is the place which register the all logging handlers #####
            tasks = [
                asyncio.to_thread(OnTimeRegistry().register, TextHandler()),
            ]
            await asyncio.gather(*tasks)

        def run_async_init():
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(register_handlers())

        init_thread = threading.Thread(target=run_async_init)
        init_thread.start()
        init_thread.join()  # Wait for completion
        debug_info(
            heading="Logging Handlers Registered",
            body="Core logging handlers registered successfully.",
            metadata={},
        )
