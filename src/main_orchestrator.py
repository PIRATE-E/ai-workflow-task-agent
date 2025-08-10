import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 🎨 Initialize Rich Traceback FIRST for comprehensive error handling
from src.utils.rich_traceback_manager import RichTracebackManager, rich_exception_handler
RichTracebackManager.initialize(
    show_locals=True,
    max_frames=15,
    theme="monokai",
    extra_lines=2,
    suppress_modules=["click", "rich", "__main__", "runpy", "threading"]
)

from src.core.chat_destructor import ChatDestructor
from src.utils.socket_manager import SocketManager

import gc
from rich.align import Align

from src.core.chat_initializer import ChatInitializer
from src.config import settings
from src.core.graphs.node_assign import GraphBuilder
from src.models.state import State
from src.ui.print_banner import print_banner
from src.utils.model_manager import ModelManager
from src.mcp.manager import MCP_Manager
from src.utils.argument_schema_util import get_tool_argument_schema


@rich_exception_handler("Main Chat Application")
def run_chat(destructor: ChatDestructor):
    """
    Run the chat application.
    This function initializes the chat and compile the graph and starts the conversation loop.
    """
    try:
        chat = ChatInitializer()
        graph = GraphBuilder(State).compile_graph()
        chat.set_graph(graph).tools_register().set_exit(destructor.call_all_cleanup_functions)

        os.system('cls' if os.name == 'nt' else 'clear')  # Clear console for better UX
        print_banner()
        console = settings.console
        console.print(Align.center("[bold blue]Welcome to the LangGraph Chatbot![/bold blue]"))
        console.print(Align.center("Type '[bold red]exit[/bold red]' to end the conversation.\n"))

        # Display tools in a table
        from rich.table import Table

        table = Table(title="Registered Tools", border_style="blue", show_lines=True)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="magenta")
        table.add_column("Arguments", style="green")

        for tool in chat.tools:
            try:
                name = getattr(tool, "name", "N/A")
                desc = getattr(tool, "description", "N/A")
                args = get_tool_argument_schema(tool)
                table.add_row(str(name), str(desc), str(args))
            except Exception as tool_error:
                RichTracebackManager.handle_exception(
                    tool_error, 
                    context=f"Tool Registration Display - {getattr(tool, 'name', 'Unknown Tool')}"
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
                        extra_context={"break_loop": chat.break_loop}
                    )
                    # Continue the loop unless it's a critical error
                    if isinstance(chat_error, (KeyboardInterrupt, SystemExit)):
                        raise
        except (KeyboardInterrupt, SystemExit):
            console.print("[bold red]Chat ended. Goodbye![/bold red]")
        finally:
            # Let ChatDestructor handle all cleanup
            console.print("[dim]Exiting chat application...[/dim]")
            
    except Exception as init_error:
        RichTracebackManager.handle_exception(
            init_error, 
            context="Chat Application Initialization",
            extra_context={"phase": "startup"}
        )
        raise


if __name__ == '__main__':
    try:
        # Start the chat application
        destructor = ChatDestructor()
        # Add cleanup functions in reverse dependency order
        # (SocketManager last because it handles logging for other cleanups)
        destructor.add_destroyer_function(SocketManager.cleanup)
        destructor.add_destroyer_function(ModelManager.cleanup_all_models)
        destructor.add_destroyer_function(MCP_Manager.cleanup)
        destructor.register_cleanup_handlers()  # Register cleanup handlers

        # Pass destructor to run_chat function
        run_chat(destructor)
    except Exception as e:
        console = settings.console
        console.print(f"[bold red]Unexpected error: {e}[/bold red]")
    finally:
        # Let ChatDestructor handle all cleanup via atexit/signal handlers
        gc.collect()  # Clean up resources after the chat ends
