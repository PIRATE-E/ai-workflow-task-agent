"""
Cold Wind AI - Desktop Orchestrator

Main entry point for the desktop CLI application.
Initializes DesktopConfig, activates DesktopRunTimeContext, registers
presentation handlers (DashBoardHandler, DesktopStatusHandler),
and drives conversational turns via the headless ColdWindEngine facade.
"""

import gc
import os
from pathlib import Path
import sys
from typing import Any
import uuid

from rich.align import Align
from rich.table import Table

# -----------------------------------------------------------------------------
# WHAT CHANGED & WHY:
# 1. Cleaned up legacy monolithic imports (ChatInitializer, GraphBuilder, State,
#    ChatDestructor, MCP_Manager, ModelManager, BrowserHandler).
#    WHY: ColdWindEngine handles internal graph compilation, tool discovery,
#    and resource teardown (destructor). Desktop only interacts with the headless
#    engine facade and its input/output ticket contracts.
# 2. Added DesktopStatusHandler and TicketIn.
#    WHY: Connects Desktop terminal spinner display to Core logging without
#    in-memory pub-sub queues or monkey-patched event registers.
# -----------------------------------------------------------------------------
from coldwind.core.engine.coldwind_engine import ColdWindEngine
from coldwind.core.models.ticket_in import TicketIn
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.system_logging import OnTimeRegistry
from coldwind.core.utils.argument_schema_util import get_tool_argument_schema
from coldwind.desktop.config.DesktopConfig import DesktopConfig
from coldwind.desktop.dashboard.dashboard_handler import DashBoardHandler
from coldwind.desktop.runtime.DesktopContext import DesktopRunTimeContext
from coldwind.desktop.ui.desktop_status_handler import DesktopStatusHandler
from coldwind.desktop.ui.diagnostics.rich_traceback_manager import (
    RichTracebackManager,
    rich_exception_handler,
)

# Add project root to Python path
# NOTE: The app must be launched from the repo root (cwd = project root)
project_root = Path.cwd()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Initialize Rich Traceback for MAIN PROCESS (display happens in debug console)
RichTracebackManager.initialize(
    show_locals=False,
    max_frames=10,
    suppress_modules=[
        "click",
        "rich",
        "__main__",
        "runpy",
        "threading",
        "socket",
        "pickle",
    ],
)


@rich_exception_handler("Main Chat Application")
def run_chat(status_handler: DesktopStatusHandler) -> None:
    """
    Run the interactive desktop chat application.

    Drives interactive user input, dispatches slash commands, and submits
    conversational turns to ColdWindEngine.process_ticket() while DesktopStatusHandler
    presents live execution milestones.
    """
    engine = ColdWindEngine()
    try:
        # Boot the headless engine facade (LangGraph, MCP tools, dynamic services)
        engine.boot()

        os.system("cls" if os.name == "nt" else "clear")
        context = ContextRegistry.get()
        context.get_message_display().display_banner("null", "null")
        console = context.get_console() or __import__("rich").console.Console()
        context.set_console(console)

        console.print(Align.center("[bold blue]Welcome to Cold Wind AI![/bold blue]"))
        console.print(
            Align.center("Type '[bold red]exit[/bold red]' to end the conversation.\n")
        )

        table = Table(title="Registered Tools", border_style="blue", show_lines=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")
        table.add_column("Arguments", style="green")

        for tool in engine.tools or []:
            try:
                name = getattr(tool, "name", "N/A")
                desc = getattr(tool, "description", "N/A")
                args = get_tool_argument_schema(tool)
                table.add_row(str(name), str(desc), str(args))
            except Exception as tool_error:
                RichTracebackManager.handle_exception(
                    tool_error,
                    context=f"Tool Registration Display - {getattr(tool, 'name', 'Unknown Tool')}",
                )
                table.add_row("ERROR", "Failed to load tool", "N/A")

        console.print(table)

        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # Replaced legacy chat.run_chat() while-loop with headless ticket loop.
        # WHY: Desktop maintains local conversation state across turns and
        # delegates turn processing to engine.process_ticket() wrapped in
        # status_handler.turn_status().
        # ---------------------------------------------------------------------
        session_state: dict[str, Any] = {"messages": [], "message_type": None}
        allowed_tools = [
            getattr(tool, "name", "")
            for tool in (engine.tools or [])
            if getattr(tool, "name", None)
        ]

        while not context.is_exiting():
            try:
                user_input = context.get_command_parser().get_user_input()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[bold red]Interrupted. Exiting chat...[/bold red]")
                break

            if not user_input or not user_input.strip():
                continue

            cleaned_input = user_input.strip()

            # Exit command handling
            if cleaned_input.lower() in ("exit", "quit", "/exit"):
                context.request_exit()
                console.print("[bold red]Exiting Cold Wind AI. Goodbye![/bold red]")
                break

            # Local screen and history clear
            if cleaned_input.lower() == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                session_state = {"messages": [], "message_type": None}
                console.print("[dim]Chat history cleared.[/dim]")
                continue

            # Render outbound user message
            context.get_message_display().display_message("user", cleaned_input)

            # Single-turn ticket construction
            ticket = TicketIn(
                ticket_id=f"desktop-{uuid.uuid4().hex[:8]}",
                session_id="desktop-main",
                user_id="desktop-user",
                user_message=cleaned_input,
                working_state=session_state,
                allowed_tools=allowed_tools,
                limits={"timeout_seconds": 120},
            )

            # Turn execution scoped within DesktopStatusHandler spinner
            try:
                with status_handler.turn_status("Cold Wind AI is thinking..."):
                    ticket_out = engine.process_ticket(ticket)

                if ticket_out.status == "FAILED":
                    error_msg = "Unknown error"
                    if isinstance(ticket_out.error_info, dict):
                        error_msg = ticket_out.error_info.get("error", str(ticket_out.error_info))
                    elif ticket_out.error_info:
                        error_msg = str(ticket_out.error_info)
                    console.print(f"[bold red]Turn failed: {error_msg}[/bold red]")
                else:
                    session_state = ticket_out.new_working_state
                    # Note: Graph nodes (chat_llm, agent_mode_node) render via print_message
                    # directly during execution. If a turn completes without node-level output,
                    # render the final transcript here as a fallback.
            except KeyboardInterrupt:
                # -------------------------------------------------------------
                # WHAT CHANGED & WHY:
                # Catch KeyboardInterrupt explicitly during turn execution.
                # WHY: When the user hits Ctrl+C while the model/graph is executing,
                # this cleanly cancels the active turn and returns to prompt instead
                # of escaping the chat loop and crashing the entire application.
                # -------------------------------------------------------------
                console.print("\n[bold yellow]Turn cancelled by user (Ctrl+C).[/bold yellow]")
                continue
            except Exception as turn_error:
                RichTracebackManager.handle_exception(
                    turn_error,
                    context="Turn Execution",
                    extra_context={"ticket_id": ticket.ticket_id},
                )
                console.print(f"[bold red]Execution error: {turn_error}[/bold red]")

    except Exception as init_error:
        RichTracebackManager.handle_exception(
            init_error,
            context="Chat Application Initialization",
            extra_context={"phase": "startup"},
        )
        raise
    finally:
        # Gracefully release models, MCP client subprocesses, and background connections
        engine.shutdown()
        try:
            ContextRegistry.get().get_console().print("[dim]Exiting chat application...[/dim]")
        except Exception:
            pass


def boot() -> None:
    """Boot the desktop chat application."""
    ContextRegistry()  # Ensure the singleton is initialized
    console = None
    try:
        # Initialize desktop settings and platform runtime context
        desktop_settings = DesktopConfig(project_root=project_root)
        runtime_context = DesktopRunTimeContext(desktop_settings)
        ContextRegistry.activate_context(runtime_context)

        console = __import__("rich").console.Console()
        ContextRegistry.get().set_console(console)

        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # Single, clean registration of presentation handlers into Core's OnTimeRegistry.
        # WHY: Purged the over-engineered dual-registration pattern (registering in
        # OnTimeRegistry AND storing in runtime_context._listeners["platform_events"]).
        # Core emits LogEntry via Dispatcher; handlers receive it directly.
        # ---------------------------------------------------------------------
        status_handler = DesktopStatusHandler(console)
        handler_registry = OnTimeRegistry()
        handler_registry.register(DashBoardHandler())
        handler_registry.register(status_handler)

        run_chat(status_handler)
    except KeyboardInterrupt:
        if console:
            console.print("\n[dim]Process interrupted. Goodbye![/dim]")
        else:
            print("\nProcess interrupted. Goodbye!")
    except Exception as e:  # pragma: no cover
        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # Route startup crashes to RichTracebackManager for structured diagnostic display.
        # WHY: Previously dropped raw unformatted string `print(f"Unexpected error: {e}")`.
        # RichTracebackManager captures frame locals, stack traces, and debug socket telemetry.
        # ---------------------------------------------------------------------
        try:
            RichTracebackManager.handle_exception(
                e,
                context="Desktop Boot Sequence",
                extra_context={"phase": "boot_entrypoint"},
            )
        except Exception:
            pass

        try:
            console = ContextRegistry.get().get_console()
        except Exception:
            console = None
        if console:
            console.print(f"[bold red]Unexpected error: {e}[/bold red]")
        else:
            print(f"Unexpected error: {e}")
    finally:
        gc.collect()


if __name__ == "__main__":
    boot()
