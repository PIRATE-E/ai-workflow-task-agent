import atexit
import signal
from typing import Callable, List

# Socket connection lives on the active RuntimeContextInterface — accessed via
# ContextRegistry.get().get_socket_connection() (returns None until the
# orchestrator wires it, so the existing truthy-guard pattern still works).
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry


# this is cleanup code for the chat system
class ChatDestructor:
    """
    Handles the cleanup of chat resources, ensuring that all models are stopped and resources are released.
    also clean other resources that might be used during the chat session. like socket connections, files, etc.
    This is typically called when the chat session ends or when the application is exiting.
    """

    is_cleaned_registered = False
    _cleanup_executed = False  # Flag to prevent double cleanup execution
    _all_functions: List[Callable] = []  # Function to be called for cleanup, if any
    _original_sigint_handler = None  # Original SIGINT handler
    _original_sigterm_handler = None  # Original SIGTERM handler

    @classmethod
    def add_destroyer_function(cls, function: Callable):
        """
        Add a cleanup function to be called during the cleanup process.
        :param function: A callable function that performs cleanup.
        """
        if (
            function
            and callable(function)
            and function not in ChatDestructor._all_functions
        ):
            ChatDestructor._all_functions.append(function)
        else:
            raise ValueError("Provided function is not callable")

    @classmethod
    def register_cleanup_handlers(cls):
        """
        Register cleanup handlers for graceful shutdown.
        This ensures models are stopped even during abrupt termination.
        """
        if cls.is_cleaned_registered:
            socket = ContextRegistry.get().get_socket_connection()
            if socket:
                socket.send_error(
                    "[LOG]Cleanup handlers already registered."
                )
            return

        # Register atexit handler (called during normal Python exit)
        atexit.register(cls.call_all_cleanup_functions)

        # Register signal handlers for termination signals
        try:
            # Store original handlers before overwriting
            cls._original_sigint_handler = signal.signal(
                signal.SIGINT, cls._signal_handler
            )  # Ctrl+C
            cls._original_sigterm_handler = signal.signal(
                signal.SIGTERM, cls._signal_handler
            )  # Termination signal

            if hasattr(signal, "SIGBREAK"):  # Windows specific
                signal.signal(signal.SIGBREAK, cls._signal_handler)
        except (OSError, ValueError) as e:
            print(f"Could not register signal handler: {e}")

        cls.is_cleaned_registered = True
        socket = ContextRegistry.get().get_socket_connection()
        if socket:
            socket.send_error(
                "[LOG]✅ Chat cleanup handlers registered successfully"
            )

    @classmethod
    def _signal_handler(cls, signum, frame):
        """
        Handle termination signals and ensure proper cleanup.
        """
        socket = ContextRegistry.get().get_socket_connection()
        if socket:
            socket.send_error(
                f"🛑 Signal {signum} received, cleaning up models..."
            )
        cls.call_all_cleanup_functions()

        # Call original handler if it existed
        if signum == signal.SIGINT and cls._original_sigint_handler:
            cls._original_sigint_handler(signum, frame)
        elif signum == signal.SIGTERM and cls._original_sigterm_handler:
            cls._original_sigterm_handler(signum, frame)
        else:
            # Default termination
            signal.default_int_handler(signum, frame)

    @classmethod
    def call_all_cleanup_functions(cls):
        # Grab the socket once for the duration of cleanup — repeated reads would
        # thrash the registry and the value is stable inside a single teardown.
        socket = ContextRegistry.get().get_socket_connection()
        # Prevent double cleanup execution
        if cls._cleanup_executed:
            if socket:
                socket.send_error(
                    "[LOG]Cleanup already executed, skipping."
                )
            return

        cls._cleanup_executed = True  # Set flag to prevent re-execution

        if len(cls._all_functions) == 0:
            if socket:
                socket.send_error("[LOG]No cleanup functions registered.")
            return

        if socket:
            socket.send_error("[LOG]🧹 Starting cleanup process...")

        terminated_count = 0
        for func in cls._all_functions:
            try:
                if callable(func):
                    if socket:
                        socket.send_error(
                            f"[LOG]Executing cleanup: {func.__name__}"
                        )
                    func()  # Call the cleanup function
                    terminated_count += 1
                else:
                    print(f"[LOG]Function {func} is not callable, skipping.")
            except Exception as e:
                error_msg = f"[LOG]Error during cleanup function {func.__name__ if hasattr(func, '__name__') else func}: {e}"
                if socket:
                    socket.send_error(error_msg)
                else:
                    print(error_msg)

        if socket:
            socket.send_error(
                f"[LOG]✅ Cleanup completed. {terminated_count} functions executed."
            )
        else:
            print(f"[LOG]✅ Cleanup completed. {terminated_count} functions executed.")
