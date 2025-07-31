import os
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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


def run_chat(destructor: ChatDestructor):
    """
    Run the chat application.
    This function initializes the chat and compile the graph and starts the conversation loop.
    """
    chat = ChatInitializer()
    graph = GraphBuilder(State).compile_graph()
    chat.set_graph(graph).tools_register().set_exit(destructor.call_all_cleanup_functions)

    os.system('cls' if os.name == 'nt' else 'clear')  # Clear console for better UX
    print_banner()
    console = settings.console
    console.print(Align.center("[bold blue]Welcome to the LangGraph Chatbot![/bold blue]"))
    console.print(Align.center("Type '[bold red]exit[/bold red]' to end the conversation.\n"))

    try:
        while not chat.break_loop:
            chat.run_chat()
            gc.collect()
    except (KeyboardInterrupt, SystemExit):
        console.print("[bold red]Chat ended. Goodbye![/bold red]")
    finally:
        # Let ChatDestructor handle all cleanup
        console.print("[dim]Exiting chat application...[/dim]")


if __name__ == '__main__':
    try:
        # Start the chat application
        destructor = ChatDestructor()
        # Add cleanup functions in reverse dependency order
        # (SocketManager last because it handles logging for other cleanups)
        destructor.add_destroyer_function(SocketManager.cleanup)
        destructor.add_destroyer_function(ModelManager.cleanup_all_models)
        destructor.register_cleanup_handlers()  # Register cleanup handlers

        # Pass destructor to run_chat function
        run_chat(destructor)
    except Exception as e:
        console = settings.console
        console.print(f"[bold red]Unexpected error: {e}[/bold red]")
    finally:
        # Let ChatDestructor handle all cleanup via atexit/signal handlers
        gc.collect()  # Clean up resources after the chat ends
