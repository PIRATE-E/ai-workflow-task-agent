import gc
import os
from pathlib import Path
import sys

from rich.align import Align

from coldwind.core.engine.chat_destructor import ChatDestructor
from coldwind.core.engine.chat_initializer import ChatInitializer
from coldwind.core.engine.graphs.node_assign import GraphBuilder
from coldwind.core.mcp.manager import MCP_Manager
from coldwind.core.models.state import State
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.system_logging import OnTimeRegistry
from coldwind.core.tools.lggraph_tools.tools.browser_tool import BrowserHandler
from coldwind.core.utils.argument_schema_util import get_tool_argument_schema
from coldwind.core.utils.model_manager import ModelManager
# from coldwind.core.utils.socket_manager import SocketManager
from coldwind.desktop.config.DesktopConfig import DesktopConfig
from coldwind.desktop.dashboard.dashboard_handler import DashBoardHandler
from coldwind.desktop.runtime.DesktopContext import DesktopRunTimeContext
from coldwind.desktop.ui.diagnostics.rich_traceback_manager import (
    RichTracebackManager,
    rich_exception_handler,
)
from coldwind.desktop.ui.print_banner import print_banner

# Add project root to Python path
project_root = Path.cwd()  ### NOTE:- AI_LLM directory
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 🎨 Initialize Rich Traceback for MAIN PROCESS (display happens in debug console)


RichTracebackManager.initialize(
    show_locals=False,  # Disabled for main process - display in debug console
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
def run_chat(destructor: ChatDestructor):
    """Run the chat application."""
    try:
        chat = ChatInitializer()
        graph = GraphBuilder(State).compile_graph()
        chat.set_graph(graph).tools_register().set_exit(
            destructor.call_all_cleanup_functions
        )
        # NOTE: the former `settings.chat = chat` global write was removed — it was
        # write-only (no reads anywhere in core/ or desktop/ production code), so it
        # was dead state. If a future platform needs to expose the ChatInitializer
        # handle globally it should register it via the dynamic service store
        # (`context.register_service(CoreRunTimeObjects.<name>, chat)`), never via a
        # settings-globals write.

        os.system("cls" if os.name == "nt" else "clear")  # Clear console
        print_banner()
        # Resolve the primary rich Console via the runtime context slot, falling
        # back to a fresh Console() if the platform did not pre-assign one. Persist
        # the resolved console back onto the context slot (was settings.console
        # read/write) so the rest of the app reads it via ContextRegistry.get().get_console().
        context = ContextRegistry.get()
        console = context.get_console() or __import__("rich").console.Console()
        context.set_console(console)

        console.print(
            Align.center("[bold blue]Welcome to the LangGraph Chatbot![/bold blue]")
        )
        console.print(
            Align.center("Type '[bold red]exit[/bold red]' to end the conversation.\n")
        )

        from rich.table import Table

        table = Table(title="Registered Tools", border_style="blue", show_lines=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")
        table.add_column("Arguments", style="green")

        for tool in chat.tools or []:
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

        try:
            while not chat.break_loop:
                try:
                    chat.run_chat()
                    gc.collect()
                except Exception as chat_error:
                    RichTracebackManager.handle_exception(
                        chat_error,
                        context="Chat Loop Execution",
                        extra_context={"break_loop": chat.break_loop},
                    )
                    if isinstance(chat_error, (KeyboardInterrupt, SystemExit)):
                        raise
        except (KeyboardInterrupt, SystemExit):
            console.print("[bold red]Chat ended. Goodbye![/bold red]")
        finally:
            console.print("[dim]Exiting chat application...[/dim]")
    except Exception as init_error:
        RichTracebackManager.handle_exception(
            init_error,
            context="Chat Application Initialization",
            extra_context={"phase": "startup"},
        )
        raise


def boot():
    """Boot the chat application."""
    print(Path.cwd())
    ContextRegistry()  # Ensure the singleton is initialized
    console = None
    try:
        # setting up the desktop settings and runtime context and adapters for core to access them on demand ...
        desktop_settings = DesktopConfig(project_root=project_root)
        runtime_context = DesktopRunTimeContext(desktop_settings)
        ContextRegistry.activate_context(
            runtime_context
        )  # registry of the desktop runtimes and contexts for core to access them on demand ...
        console = ContextRegistry.get().set_console(
            __import__("rich").console.Console()
        )
        # add the handlers into the core
        handler_registry = OnTimeRegistry()
        handler_registry.register(DashBoardHandler())
        # load the settins using the run time context
        destructor = ChatDestructor()
        # destructor.add_destroyer_function(SocketManager.cleanup)
        destructor.add_destroyer_function(ModelManager.cleanup_all_models)
        destructor.add_destroyer_function(MCP_Manager.cleanup)
        destructor.add_destroyer_function(BrowserHandler.clear_all_processes)

        destructor.register_cleanup_handlers()
        run_chat(destructor)
    except Exception as e:  # pragma: no cover
        # Ultimate fallback in the __main__ boot path. The prior code assigned the
        # settings MODULE to `console` (a latent bug — `settings` has no `.print`,
        # so it would itself raise inside this handler). Resolve the console via
        # the runtime context slot, guarding for the possibility that the context
        # was never activated or the console slot is still unset.
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
