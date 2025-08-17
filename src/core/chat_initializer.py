import gc
import json
import platform
from threading import Thread

from src.config import settings
from langgraph.graph.state import CompiledStateGraph
from rich import console, prompt, inspect

from src.config.settings import PNG_FILE_PATH
from src.models.state import StateAccessor, State
from src.ui.print_message_style import print_message
from src.utils.socket_manager import SocketManager

# 🎨 Rich Traceback Integration
from src.ui.diagnostics.rich_traceback_manager import RichTracebackManager, rich_exception_handler
from src.ui.diagnostics.debug_helpers import debug_warning, debug_info

# mcp servers integration
from src.tools.lggraph_tools.wrappers.mcp_wrapper.filesystem_wrapper import FileSystemWrapper

class ChatInitializer:
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

        # mcp servers integration
        self.initialize_mcp_servers()
        self.initialize_neo4j()

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
            from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
            self.ToolResponseManager = ToolResponseManager()
            
            # Set the socket connection for logging
            settings.socket_con = SocketManager.get_socket_con()
            
        except Exception as e:
            RichTracebackManager.handle_exception(
                e, 
                context="Core Classes Setup",
                extra_context={"phase": "message_classes_initialization"}
            )
            raise

    def set_graph(self, graph):
        if not isinstance(graph, CompiledStateGraph):
            raise ValueError("Provided graph is not a valid CompiledStateGraph instance")
        self.graph = graph
        return self

    def set_exit(self, func):
        if hasattr(func, '__call__'):
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
            history.append(
                {
                    "type": msg.type,
                    "content": msg.content
                }
            )
        json.dump(history, open("conversation_history.json", "w"), indent=2)
        # Let ChatDestructor handle socket cleanup - don't close prematurely
        # run the exit function if it is set in the another thread
        if self._exit_function:
            # run the exit function in another thread
            t = Thread(target=self._exit_function)
            t.start()
        else:
            self.console.print("[bold red]No exit function set. Exiting without cleanup.[/bold red]")
        # print the final state for debugging
        inspect(self._state)
        return {"messages": [settings.AIMessage(content="Thank you for using the LangGraph Chatbot!")]}

    def save_graph_png(self):
        import os
        if self.graph is None:
            raise ValueError("Graph is not initialized. Please compile the graph first.")
        path = PNG_FILE_PATH
        with open(path, "wb") as f:
            f.write(self.graph.get_graph().draw_mermaid_png())
        if self.os == 'Linux':

            os.system(f'xdg-open {path}')
        elif self.os == 'Darwin':

            os.system(f'open {path}')
        elif self.os == 'Windows':
            os.startfile(path)
        return self

    @rich_exception_handler("MCP Server Initialization")
    def initialize_mcp_servers(self):
        """
        Initialize MCP servers if they are not already running.
        This method can be extended to initialize any required MCP servers.
        """
        try:
            from src.mcp.manager import MCP_Manager
            # Add and start MCP servers if needed with allowed path of AI_llm folder
            MCP_Manager.add_server("filesystem", "npx", "@modelcontextprotocol/server-filesystem", [f"{settings.BASE_DIR.parent}"], FileSystemWrapper)

            # Start all servers
            for server in MCP_Manager.mcp_servers:
                try:
                    if not MCP_Manager.start_server(server):
                        self.console.print(f"[bold red]Failed to start MCP server: {server}[/bold red]")
                    else:
                        self.console.print(f"[bold green]MCP server '{server}' started successfully.[/bold green]")
                except Exception as server_error:
                    RichTracebackManager.handle_exception(
                        server_error,
                        context=f"MCP Server Startup - {server}",
                        extra_context={"server_name": server}
                    )
                    self.console.print(f"[bold red]Error starting MCP server {server}: {server_error}[/bold red]")
        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="MCP Server Initialization",
                extra_context={"phase": "mcp_manager_import_and_setup"}
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
                debug_warning(heading="Neo4j Driver Not Found",
                              body="Neo4j driver is not installed. Skipping Neo4j initialization.",
                                metadata={
                                    "neo4j_uri": settings.NEO4J_URI,
                                    "neo4j_user": settings.NEO4J_USER,}
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
                    "driver_status": "created_successfully"
                }
            )
        except Exception as e:
            # Log but DO NOT raise (make optional)
            RichTracebackManager.handle_exception(
                e,
                context="Neo4j Database Connection (optional)",
                extra_context={
                    "neo4j_uri": settings.NEO4J_URI,
                    "neo4j_user": settings.NEO4J_USER,
                    "driver_status": "failed_to_create_optional"
                }
            )
            if settings.socket_con:
                debug_warning(
                    heading="Neo4j Driver Initialization Failed",
                    body="Neo4j driver initialization failed. Continuing without Neo4j support.",
                    metadata={
                        "neo4j_uri": settings.NEO4J_URI,
                        "neo4j_user": settings.NEO4J_USER,
                        "error_message": str(e)
                    }
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
            from src.tools.lggraph_tools.wrappers.google_wrapper import GoogleSearchToolWrapper
            from src.tools.lggraph_tools.wrappers.translate_wrapper import TranslateToolWrapper
            from src.tools.lggraph_tools.wrappers.rag_search_classifier_wrapper import RagSearchClassifierWrapper
            from src.tools.lggraph_tools.wrappers.run_shell_comand_wrapper import ShellCommandWrapper
            # schema
            from src.tools.lggraph_tools.tool_schemas.tools_structured_classes import google_search, rag_search_message, \
                TranslationMessage, run_shell_command_message

            # dynamically register tools
            from src.mcp.dynamically_tool_register import DynamicToolRegister
            
            tools = []
            
            # Register each tool with individual error handling
            tool_configs = [
                ("GoogleSearch", GoogleSearchToolWrapper, "For general web searches (recent info, facts, news).", google_search),
                ("RAGSearch", RagSearchClassifierWrapper, "For searching the knowledge base (RAG search).", rag_search_message),
                ("Translatetool", TranslateToolWrapper, "For translating messages into different languages.", TranslationMessage),
                ("RunShellCommand", ShellCommandWrapper, "For executing shell commands.", run_shell_command_message),
            ]
            
            for name, func, description, schema in tool_configs:
                try:
                    tool = ToolAssign(func=func, name=name, description=description, args_schema=schema)
                    tools.append(tool)
                except Exception as tool_error:
                    RichTracebackManager.handle_exception(
                        tool_error,
                        context=f"Tool Registration - {name}",
                        extra_context={"tool_name": name, "tool_function": str(func)}
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
                    extra_context={"dynamic_tools_count": len(getattr(DynamicToolRegister, 'tool_list', []))}
                )
            
            # Set tools list
            ToolAssign.set_tools_list(tools)
            self.tools = ToolAssign.get_tools_list()
            
            debug_info(
                heading="Tools Registered",
                body=f"Registered {len(self.tools)} tools successfully.",
                metadata={
                    "tools_count": len(self.tools),
                }
            )
            
            return self
            
        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="Tool Registration System",
                extra_context={"phase": "tool_registration_setup"}
            )
            raise

    @rich_exception_handler("Chat Execution Loop")
    def run_chat(self):
        try:
            # make sure all the fields are initialized
            if not self._state or not self.graph or not self.tools:
                raise ValueError("Chat is not properly initialized. Please ensure all components are set up.")

            user_input = prompt.Prompt.ask("[bold cyan]You[/bold cyan]", default="", show_default=False)
            if user_input.lower() == "exit":
                self.console.print("[bold red]Exiting the chat...[/bold red]")
                try:
                    self.on_exit()
                except Exception as exit_error:
                    RichTracebackManager.handle_exception(
                        exit_error,
                        context="Chat Exit Process",
                        extra_context={"user_input": user_input}
                    )
                self.break_loop = True
            else:
                try:
                    self._state["messages"].append(settings.HumanMessage(content=user_input))
                    print_message(user_input, sender="user")
                    try:
                        self._state = self.graph.invoke(self._state)
                    except Exception as graph_error:
                        RichTracebackManager.handle_exception(
                            graph_error,
                            context="LangGraph Invocation",
                            extra_context={
                                "user_input": user_input[:100],
                                "state_messages_count": len(self._state.get("messages", [])),
                                "message_type": self._state.get("message_type")
                            }
                        )
                        raise
                    try:
                        self.state_accessor.sync_with_langgraph(self._state)
                    except Exception as sync_error:
                        RichTracebackManager.handle_exception(
                            sync_error,
                            context="State Accessor Sync",
                            extra_context={"state_keys": list(self._state.keys())}
                        )
                except Exception as chat_processing_error:
                    RichTracebackManager.handle_exception(
                        chat_processing_error,
                        context="Chat Message Processing",
                        extra_context={
                            "user_input": user_input[:100],
                            "processing_phase": "message_handling"
                        }
                    )
                    self.console.print("[bold red]Error processing message. Please try again.[/bold red]")
            try:
                gc.collect()
            except Exception as gc_error:
                RichTracebackManager.handle_exception(
                    gc_error,
                    context="Garbage Collection",
                    extra_context={"phase": "post_chat_cleanup"}
                )
        except Exception as e:
            RichTracebackManager.handle_exception(
                e,
                context="Chat Execution Loop",
                extra_context={"phase": "main_chat_loop"
            })
            raise
