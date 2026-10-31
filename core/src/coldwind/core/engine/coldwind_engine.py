"""
ColdWindEngine :- Headless core agent engine facade !!
Core is headless brain that executes tickets statelessly without interactive terminal CLI loop.
All platform specific things (UI, event loop, stdin, OS signals, disk persistence) belong to the platform !!

LIFECYCLE & HANDSHAKE TIMELINE:
1. Platform boots first (DesktopConfig / ContextRegistry.activate_context(platform_context))
2. Platform calls ColdWindEngine().boot() -> Core grabs ContextRegistry.get(), registers dynamic message_classes,
   discovers tools (MCP + native), and compiles LangGraph StateGraph !!
3. Platform drives turns: passes TicketIn to process_ticket(ticket) -> Core runs graph for single turn statelessly,
   streams events to platform sinks, and returns TicketOut !!
4. Platform saves new_working_state to its own DB/session storage (Core forgets state between turns) !!
5. Platform calls shutdown() on application exit to clean up models and MCP resources !!
"""

import asyncio
import threading
import time
import traceback
from collections.abc import Awaitable
from typing import Any, cast

from coldwind.core.engine.chat_destructor import ChatDestructor
from coldwind.core.engine.graphs.node_assign import GraphBuilder

# -------------------------------------------------------------------------
# WHAT CHANGED & WHY:
# 1. Imported HumanMessage, AIMessage, BaseMessage from langchain_core.messages.
#    WHY: Required for runtime message class registration in boot() and
#    deserialization in process_ticket().
# 2. Changed import from `coldwind.desktop.ui.diagnostics.rich_traceback_manager`
#    to `coldwind.core.interfaces.exception_interface`.
#    WHY: Invariant: Desktop imports Core; Core NEVER imports Desktop.
#    exception_interface provides the canonical Core exception handling decorator.
# -------------------------------------------------------------------------
from coldwind.core.interfaces.exception_interface import (
    rich_exception_handler,
)
from coldwind.core.mcp.load_config import McpConfigFile
from coldwind.core.mcp.manager import MCP_Manager
from coldwind.core.mcp.mcp_manager_util import Utils
from coldwind.core.models import StateAccessor
from coldwind.core.models.state import State
from coldwind.core.models.ticket_in import TicketIn
from coldwind.core.models.ticket_out import TicketOut
from coldwind.core.runtime import ContextRegistry, CoreRunTimeObjects
from coldwind.core.tools.lggraph_tools.tools.browser_tool import BrowserHandler
from coldwind.core.utils.model_manager import ModelManager
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph


class OnBootError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class RuntimeTicketError(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ColdWindEngine:
    """
    ColdWindEngine :- Main turnkey engine facade replacing legacy ChatInitializer internals !!

    RESPONSIBILITIES:
    - Bootstraps Core infrastructure on boot() using ContextRegistry.get()
    - Injects message_classes into platform context dynamic store
    - Discovers MCP servers and native tools via ToolAssigner
    - Compiles LangGraph StateGraph (GraphBuilder)
    - Executes single-turn tickets statelessly (process_ticket)
    - Coordinates clean resource teardown on shutdown()

    STATE / CLASS FIELDS:
    - _is_booted: bool -> flag to guard against processing tickets before boot()
    - _graph: Any -> compiled LangGraph instance holding agent nodes and router
    - _destructor: Any -> ChatDestructor reference for explicit teardown

    NOTE: Zero conversation history or messages stored here !! Core receives working_state
    in TicketIn, executes turn, returns it in TicketOut, and forgets it !!
    """

    def __init__(self):
        """
        Initialize the engine facade instance.
        Class fields keep minimal setup state, zero conversation state !!
        """
        self._is_booted: bool = False
        self._graph: CompiledStateGraph[Any, Any, Any, Any] | None = None
        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # Instantiated ChatDestructor directly and declared self.tools.
        # WHY: ChatDestructor coordinates teardown callbacks (ModelManager,
        # MCP_Manager, BrowserHandler). If initialized as None, callbacks were
        # never registered and shutdown() was a dead-code no-op.
        # ---------------------------------------------------------------------
        self._destructor: ChatDestructor = ChatDestructor()
        self.tools: list[Any] = []

    async def _init_mcp(self):
        async def initialize_mcp_servers():
            try:
                server_config_list = McpConfigFile().retrieve_config()
            except FileNotFoundError:
                ContextRegistry.get().get_logger().log_info(
                    heading="MCP • CONFIG_NOT_FOUND",
                    body=".mcp.json not found. Continuing without MCP servers.",
                )
                return

            if not server_config_list:
                return
            for server_config in server_config_list:
                server_name = server_config["name"]
                runner = server_config["command"]
                # this has been changed to command from runner (uvx, npx, pipx, pip, python)
                # currently for DOC purposes how it was got started !!
                # package = server_config["package"]
                args = server_config["args"]
                wrapper = server_config["wrapper"]

                MCP_Manager.add_server(
                    server_name, package=None, runner=runner, args=args, func=wrapper
                )

            start_mcp_server = Utils.start_server_async_with_timeout

            context = ContextRegistry.get()
            time_out = context.get_settings().mcp_start_timeout
            server_names = list(MCP_Manager.mcp_servers.keys())
            server_start_tasks: list[Awaitable[Any]] = [
                asyncio.create_task(start_mcp_server(server_name, time_out))
                for server_name in server_names
            ]

            # -----------------------------------------------------------------
            # WHAT CHANGED & WHY:
            # Fault-tolerant gather with return_exceptions=True.
            # WHY: Previously, if any single MCP server failed to boot, gather()
            # raised an exception that abruptly aborted all other server boots and
            # left background tasks unmonitored. Now, exceptions are caught per server
            # and routed to the platform error handler while healthy servers connect.
            # -----------------------------------------------------------------
            results = await asyncio.gather(*server_start_tasks, return_exceptions=True)
            for server_name, result in zip(server_names, results):
                if isinstance(result, Exception):
                    try:
                        context.get_error_handler().handle_exception(
                            result,
                            context=f"MCP Server Boot - {server_name}",
                            extra_context={"server_name": server_name},
                        )
                    except Exception:
                        pass

        # -- thread runner entry ---
        def run_async_init():
            # -----------------------------------------------------------------
            # WHAT CHANGED & WHY:
            # Isolated thread exception boundary.
            # WHY: If loop.run_until_complete() raised an exception in this thread,
            # it was dropped without notifying the main process or platform error
            # handler. Now caught and dispatched to get_error_handler().
            # -----------------------------------------------------------------
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(initialize_mcp_servers())
            except Exception as thread_exc:
                try:
                    ContextRegistry.get().get_error_handler().handle_exception(
                        thread_exc,
                        context="MCP Async Thread Runner",
                        extra_context={"phase": "mcp_thread_init"},
                    )
                except Exception:
                    pass
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        # Run in separate thread to avoid event loop conflicts
        init_thread = threading.Thread(target=run_async_init)
        init_thread.start()
        init_thread.join()  # Wait for completion

        ContextRegistry.get().get_logger().log_info(
            heading="MCP • SYNC_INIT_COMPLETE",
            body="All MCP servers initialized synchronously",
            metadata={"servers_count": len(MCP_Manager.mcp_servers)},
        )

    def _parse_handler_manage_tools_discovery_and_registry(self):
        # static and dynamic tool discovery, parsing and register
        # dynamically register tools
        from coldwind.core.mcp.dynamically_tool_register import DynamicToolRegister
        from coldwind.core.tools.lggraph_tools.tool_assign import ToolAssign

        # schema
        from coldwind.core.tools.lggraph_tools.tool_schemas.tools_structured_classes import (
            TranslationMessage,
            browser_agent,
            google_search,
            rag_search_message,
            run_shell_command_message,
        )
        from coldwind.core.tools.lggraph_tools.wrappers.browser_use_wrapper import (
            BrowserUseWrapper,
        )
        from coldwind.core.tools.lggraph_tools.wrappers.google_wrapper import (
            GoogleSearchToolWrapper,
        )
        from coldwind.core.tools.lggraph_tools.wrappers.rag_search_classifier_wrapper import (
            RagSearchClassifierWrapper,
        )
        from coldwind.core.tools.lggraph_tools.wrappers.run_shell_comand_wrapper import (
            ShellCommandWrapper,
        )
        from coldwind.core.tools.lggraph_tools.wrappers.translate_wrapper import (
            TranslateToolWrapper,
        )

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
                # -------------------------------------------------------------
                # WHAT CHANGED & WHY:
                # Routed error to ContextRegistry.get().get_error_handler().
                # WHY: Replaced legacy RichTracebackManager import from manager.py
                # with canonical core contract call, preserving the Layering Invariant.
                # -------------------------------------------------------------
                try:
                    ContextRegistry.get().get_error_handler().handle_exception(
                        tool_error,
                        context=f"Tool Registration - {name}",
                        extra_context={"tool_name": name, "tool_function": str(func)},
                    )
                except Exception:
                    pass
                # Continue with other tools even if one fails
                continue

        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # Dedented dynamic tool registration and tool logging out of the static loop.
        # WHY: Previously nested inside `for name, func, ... in tool_configs:`, causing
        # DynamicToolRegister.tool_list to be appended 5 times and logging 5 times.
        # ---------------------------------------------------------------------
        # Add dynamically registered tools with error handling
        try:
            dynamic_tools = DynamicToolRegister.tool_list
            tools.extend(dynamic_tools)
        except Exception as dynamic_error:
            # -----------------------------------------------------------------
            # WHAT CHANGED & WHY:
            # Routed dynamic tool registration error to get_error_handler().
            # WHY: Eliminated legacy RichTracebackManager adapter dependency in core.
            # -----------------------------------------------------------------
            try:
                ContextRegistry.get().get_error_handler().handle_exception(
                    dynamic_error,
                    context="Dynamic Tool Registration",
                    extra_context={
                        "dynamic_tools_count": len(
                            getattr(DynamicToolRegister, "tool_list", [])
                        )
                    },
                )
            except Exception:
                pass

        # Set tools list
        ToolAssign.set_tools_list(tools)
        self.tools = ToolAssign.get_tools_list()

        ContextRegistry.get().get_logger().log_info(
            heading="Tools Registered",
            body=f"Registered {len(self.tools)} tools successfully.",
            metadata={
                "tools_count": len(self.tools),
            },
        )

    def _register_logging_handlers(self):
        """Register logging handlers for the chat application."""
        from ..system_logging.handlers.handler_base import TextHandler
        from ..system_logging.on_time_registry import OnTimeRegistry

        async def register_handlers():
            ##### this is the place which register the all logging handlers #####
            tasks = [
                asyncio.to_thread(OnTimeRegistry().register, TextHandler()),
            ]
            await asyncio.gather(*tasks)

        def run_async_init():
            # -----------------------------------------------------------------
            # WHAT CHANGED & WHY:
            # Isolated thread exception boundary.
            # WHY: Prevents uncaught exceptions in thread from vanishing silently.
            # Routes any handler registration failure to platform error handler.
            # -----------------------------------------------------------------
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(register_handlers())
            except Exception as handler_exc:
                try:
                    ContextRegistry.get().get_error_handler().handle_exception(
                        handler_exc,
                        context="Logging Handlers Thread Runner",
                        extra_context={"phase": "logging_handler_init"},
                    )
                except Exception:
                    pass
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        init_thread = threading.Thread(target=run_async_init)
        init_thread.start()
        init_thread.join()  # Wait for completion
        ContextRegistry.get().get_logger().log_info(
            heading="Logging Handlers Registered",
            body="Core logging handlers registered successfully.",
            metadata={},
        )

    @rich_exception_handler("Boot Core")
    def boot(self) -> None:
        """
        Boot Phase (runs once at app startup triggered by platform) !!

        TIMELINE:
        - Grab active runtime context via ContextRegistry.get() (fails fast if platform didn't activate context)
        - Log startup through platform logger (context.get_logger())
        - Register CoreRunTimeObjects.message_classes into context._services
        - Discover and boot MCP tools + native tools via ToolAssigner
        - Compile LangGraph StateGraph via GraphBuilder and save to self._graph
        - Set self._is_booted = True
        """
        try:
            context = ContextRegistry.get()
        except Exception as e:
            raise OnBootError from e

        # inject core run times of
        context.register_service(
            cast(type, cast(object, CoreRunTimeObjects.message_classes)),
            (HumanMessage, AIMessage, BaseMessage),
        )

        self._register_logging_handlers()

        # build graph !!
        self._graph = GraphBuilder(State).compile_graph()

        # destructor registration for resource clean up !
        self._destructor = ChatDestructor()
        if self._destructor:
            self._destructor.add_destroyer_function(ModelManager.cleanup_all_models)
            self._destructor.add_destroyer_function(MCP_Manager.cleanup)
            self._destructor.add_destroyer_function(BrowserHandler.clear_all_processes)

        #  mcp discovery
        if context.get_settings().mcp_enabled:
            asyncio.Runner().run(self._init_mcp())

        self._parse_handler_manage_tools_discovery_and_registry()

        self._is_booted = True

    def process_ticket(self, ticket: TicketIn) -> TicketOut:
        """
        Turn Phase (runs whenever platform sends user input) !!

        TIMELINE:
        - Verify engine is booted (raise RuntimeTicketError if not booted)
        - Fail-fast validation of ticket.user_message and working_state messages
        - Unpack ticket.working_state and append HumanMessage(content=ticket.user_message)
        - Invoke self._graph.invoke(state) statelessly for that single turn
        - Progress events stream in real-time to platform display and logger sinks
        - Package updated state, final response transcript, and usage metrics into TicketOut
        - Return TicketOut to platform (Core forgets turn state immediately) !!
        """
        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # 1. Fail-fast validation: If ticket.user_message is empty or working_state
        #    has malformed messages/unrecognized roles, raises RuntimeTicketError
        #    immediately with zero silent fallbacks.
        # 2. Fixed typo `HumaneMessage` -> `HumanMessage` from context dynamic store.
        # 3. Contract keys: checked `role = raw_message.get("role") or raw_message.get("type")`
        #    to support standard Pydantic/LangChain serialized message dicts.
        # 4. Zero memory-leak / O(1) transcript access: reads `messages[-1]` directly
        #    instead of allocating reversed list copies.
        # 5. Fixed logger level: log_info instead of log_critical, with lightweight
        #    primitive metadata (avoiding live message object leaks into JSON loggers).
        # 6. Error boundary: Wrapped invocation in try-except returning TicketOut(status="FAILED")
        #    so host platform can release its session lock gracefully on graph failure.
        # ---------------------------------------------------------------------
        if not self._is_booted or not self._graph:
            raise RuntimeTicketError("Environment not satisfied !! Call boot() first.")

        if not ticket.user_message:
            raise RuntimeTicketError("TicketIn user_message cannot be empty !!")

        start_time = time.perf_counter()
        context = ContextRegistry.get()
        logger = context.get_logger()

        HumanMessage, AIMessage, BaseMessage = context.get_service(
            cast(type, cast(object, CoreRunTimeObjects.message_classes))
        )

        fetched_state = ticket.working_state if ticket.working_state else {}
        raw_messages = fetched_state.get("messages", [])

        if not isinstance(raw_messages, list):
            raise RuntimeTicketError("Malformed ticket working_state: 'messages' must be a list !!")

        serialized_messages: list[HumanMessage | AIMessage] = []

        for raw_message in raw_messages:
            if isinstance(raw_message, (HumanMessage, AIMessage)):
                serialized_messages.append(raw_message)
            elif isinstance(raw_message, BaseMessage):
                if getattr(raw_message, "type", "") == "human":
                    serialized_messages.append(HumanMessage(content=raw_message.content))
                else:
                    serialized_messages.append(AIMessage(content=raw_message.content))

            elif isinstance(raw_message, dict):
                role = raw_message.get("role") or raw_message.get("type")
                content = raw_message.get("content")

                if role is None or content is None:
                    raise RuntimeTicketError(f"Malformed ticket message: role={role}, content={content}")

                role_normalized = str(role).lower()
                if role_normalized in ("user", "human"):
                    serialized_messages.append(HumanMessage(content=content))
                elif role_normalized in ("ai", "assistant"):
                    serialized_messages.append(AIMessage(content=content))
                else:
                    raise RuntimeTicketError(f"Unsupported message role in ticket: '{role}'")
            else:
                raise RuntimeTicketError(f"Unsupported message format in working_state: {type(raw_message).__name__}")

        # O(1) append human turn - zero redundant casting
        serialized_messages.append(HumanMessage(content=ticket.user_message))

        state: State = {
            "messages": serialized_messages,
            "message_type": fetched_state.get("message_type"),
        }
        StateAccessor().sync_with_langgraph(state)

        # --- single execution begins
        logger.log_info(
            "TICKET • START",
            body=f"Processing ticket {ticket.ticket_id} for user {ticket.user_id}",
            metadata={
                "ticket_id": str(ticket.ticket_id),
                "session_id": str(ticket.session_id),
                "messages_count": len(serialized_messages),
            },
        )

        try:
            updated_state: dict[str, Any] = self._graph.invoke(state)
            StateAccessor().sync_with_langgraph(cast(State, cast(object, updated_state)))

            logger.log_info(
                "TICKET • DONE",
                body=f"Processed ticket {ticket.ticket_id} for user {ticket.user_id}",
                metadata={
                    "ticket_id": str(ticket.ticket_id),
                    "session_id": str(ticket.session_id),
                    "messages_count": len(updated_state.get("messages", [])),
                },
            )

            usage = {
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "message_count": len(updated_state.get("messages", [])),
            }

            # O(1) last message extraction - no extra lists, no memory leak
            messages = updated_state.get("messages", [])
            if not messages:
                raise RuntimeTicketError("Graph execution completed with empty messages state !!")

            last_msg = messages[-1]
            if isinstance(last_msg, AIMessage):
                transcript = last_msg.content
            elif isinstance(last_msg, BaseMessage):
                transcript = last_msg.content
                logger.log_warning(
                    "TICKET • DETAILS",
                    body=f"Last message is {type(last_msg).__name__} instead of AIMessage",
                )
            else:
                transcript = str(last_msg)

            return TicketOut(
                ticket_id=ticket.ticket_id,
                status="COMPLETED",
                new_working_state=updated_state,
                transcript=transcript if isinstance(transcript, str) else str(transcript),
                usage=usage,
                error_info=None,
            )

        except Exception as exc:
            try:
                context.get_error_handler().handle_exception(
                    exc,
                    context="ColdWindEngine.process_ticket",
                    extra_context={"ticket_id": str(ticket.ticket_id)},
                )
            except Exception:
                pass
            usage = {
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "message_count": len(serialized_messages),
            }
            return TicketOut(
                ticket_id=ticket.ticket_id,
                status="FAILED",
                new_working_state=dict(state),
                transcript="",
                usage=usage,
                error_info={
                    "error": str(exc),
                    "type": type(exc).__name__,
                    "traceback": traceback.format_exc(),
                },
            )

    def shutdown(self) -> None:
        """
        Shutdown Phase (triggered explicitly by platform exit handler) !!

        TIMELINE:
        - Calls ChatDestructor.call_all_cleanup_functions()
        - Releases all models, MCP client subprocesses, and background connections cleanly !!
        - Resets self._is_booted = False
        """
        if self._destructor:
            self._destructor.call_all_cleanup_functions()
        self._is_booted = False
