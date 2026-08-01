"""
Desktop Runtime Context Implementation

this class inherites the core PlatformRuntimeContextInterface
by which we can able to implement its methods but using the
getter on our private attr of the class
the implementation and services defined into different modules
we are orchestrating them here ...
"""

from typing import Any, Optional, Self, override

from coldwind.core.config.coreSettings import CoreSettinngs
from coldwind.core.interfaces.exception_interface import ExceptionHandlerInterface
from coldwind.core.interfaces.logging_interface import DebugLoggerInterface
from coldwind.core.interfaces.runtime_interface import PlatformRuntimeContextInterface
from coldwind.core.interfaces.ui_interface import (
    CommandParserInterface,
    MessageDisplayInterface,
)
from coldwind.desktop.config.DesktopConfig import DesktopConfig
from coldwind.desktop.slash_commands.executionar import ExecutionAr
from coldwind.desktop.slash_commands.parser import ParseCommand
from coldwind.desktop.ui.chatInputHandler import InputHandler
from coldwind.core.system_logging.debug_protocol import (
    debug_critical,
    debug_error,
    debug_info,
    debug_warning,
)
from coldwind.desktop.ui.diagnostics.rich_traceback_manager import RichTracebackManager
from coldwind.desktop.ui.print_banner import print_banner
from coldwind.desktop.ui.print_message_style import print_message


class DesktopDebugLogger(DebugLoggerInterface):
    """
    Desktop implementation of the DebugLoggerInterface.
    Routes core logs to the existing desktop debug_helpers which use rich console output.
    """

    @override
    def log_debug(
        self, heading: str, body: str, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        debug_info(heading, body, metadata)

    @override
    def log_info(
        self, heading: str, body: str, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        debug_info(heading, body, metadata)

    @override
    def log_warning(
        self, heading: str, body: str, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        debug_warning(heading, body, metadata)

    @override
    def log_error(
        self, heading: str, body: str, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        debug_error(heading, body, metadata)

    @override
    def log_critical(
        self, heading: str, body: str, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        debug_critical(heading, body, metadata)


class DesktopExceptionHandler(ExceptionHandlerInterface):
    """
    Desktop implementation for exception handling.
    Wraps the existing RichTracebackManager.
    """

    def handle_exception(
        self,
        error: Exception,
        context: str = "",
        extra_context: Optional[dict[str, Any]] = None,
    ) -> None:
        RichTracebackManager.handle_exception(error, context, extra_context)


class DesktopMessageDisplay(MessageDisplayInterface):
    """
    Desktop implementation for displaying user-facing messages and banners.
    Wraps the print_message and print_banner UI modules.
    """

    def display_message(
        self, role: str, content: str, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        # The existing print_message expects role as sender ('user', 'ai', 'tool')
        print_message(content, sender=role)

    def display_banner(self, title: str, subtitle: str = "") -> None:
        print_banner(title, subtitle)


class DesktopCommandParser(CommandParserInterface):
    """
    Desktop implementation for handling interactive user input and slash commands.
    Orchestrates the prompt_toolkit InputHandler, ParseCommand, and ExecutionAr.
    """

    def __init__(self):
        self._input_handler = InputHandler()
        self._executionar = ExecutionAr()

    def get_user_input(self, prompt_text: str = "> ") -> str:
        return self._input_handler.get_user_input(prompt_text=prompt_text)

    def parse_and_execute(self, raw_input: str) -> Any:
        # Convert the raw text into a parsed slash command, then execute it
        slash_cmd = ParseCommand.get_command(raw_input)
        return self._executionar.execute(slash_cmd)


#### NOTE:-this is the main runtine context that we would be gonna access using the get method on the context registry !!
class DesktopRunTimeContext(PlatformRuntimeContextInterface):
    """
    that class used in many ways first when we use the get method on the
    run time registry to get the context which is this
    after which when we try to access the attr
    which really is the getters of the implementation of the run time interface
    contract, but also it owns the intialized global required runtimes like console, and others ...
    """

    _instace = None

    def __new__(cls, *args, **kwargs) -> Self:
        if cls._instace:
            return cls._instace
        return super().__new__(cls)

    # it is master implementation that means we collect all the implementation of the services and the attr of the services and we are providing them to the core by implementing the interface methods.
    def __init__(self, settings: DesktopConfig):
        """
        Initialize the Desktop Runtime Context with the provided settings.
        This context owns the global runtime objects and provides access to them via the getters defined in the PlatformRuntimeContextInterface.
        ### NOTE:- this is mother of interfaces because it returns the other contracts
        returns :- getters defined in the RuntimeCotextInterface of other interfaces like logging, exception etc
        """
        self._settings = settings

        # ── Global Runtime Objects (Previously in settings.py) ──
        # In the old architecture, these were public mutable globals in settings.py.
        # Now, they are strictly private state owned by the Desktop Context, preventing
        # Core modules from accidentally depending on Desktop-specific objects.

        # 1. Console instances (Previously: settings.console, settings.debug_console).
        # These are MUTABLE slots — born None, filled post-construction by the
        # orchestrator via set_console() / set_debug_console() (mirrors the old
        # `settings.console = console` post-boot write pattern). We deliberately
        # do NOT construct them here: building them in __init__ would be wasted
        # work since the orchestrator overwrites them anyway before first use.
        # get_console() / get_debug_console() return None when unset, so callers
        # reading the slot before boot must handle the None case explicitly.
        self._console = None
        self._debug_console = None

        # 2. Socket Connection (Previously: settings.socket_con)
        # Born None — filled later by the orchestrator via set_socket_connection().
        self._socket_con = None

        # 3. Listeners & Flags (Previously: settings.listeners, settings.exit_flag)
        self._listeners = {"eval": None, "exit": None}
        self._exit_flag = False

        # ── Interface Implementations ──
        # Instantiate the desktop-specific adapter classes.
        # (In the future, we will pass self._console into these constructors instead of
        # having them import from settings.py).
        self._logger = DesktopDebugLogger()
        self._error_handler = DesktopExceptionHandler()
        self._message_display = DesktopMessageDisplay()
        self._command_parser = DesktopCommandParser()

        # Dictionary for dynamic services (e.g., Neo4j driver)
        self._dynamic_services: dict[type, Any] = {}

    def get_logger(self) -> DebugLoggerInterface:
        return self._logger

    def get_error_handler(self) -> ExceptionHandlerInterface:
        return self._error_handler

    def get_message_display(self) -> MessageDisplayInterface:
        return self._message_display

    def get_command_parser(self) -> CommandParserInterface:
        return self._command_parser

    def get_settings(self) -> CoreSettinngs:
        return self._settings

    def get_service(self, service_type: type) -> Any:
        if service_type not in self._dynamic_services:
            raise RuntimeError(
                f"Service {service_type.__name__} not registered in Desktop context."
            )
        return self._dynamic_services[service_type]

    def register_service(self, service_type: type, service: Any) -> None:
        self._dynamic_services[service_type] = service

    def is_exiting(self) -> bool:
        """Returns True if a shutdown has been requested (replaces reading settings.exit_flag)."""
        return self._exit_flag

    def request_exit(self) -> None:
        """
        Sets the exit flag to True.
        In the future, this can immediately emit an 'exit_requested' event.
        (replaces setting settings.exit_flag = True).
        """
        self._exit_flag = True

    def reset_exit_request(self) -> None:
        """Clear the exit flag (replaces `settings.exit_flag = False`)."""
        self._exit_flag = False

    # ── Platform-optional mutable slots (concrete implementations) ──
    # These satisfy the abstractmethods declared in PlatformRuntimeContextInterface.
    # Slots themselves are declared in __init__ (born None / empty dict); these
    # methods just read/write them. A headless server subclass would implement
    # these its own way (server may skip _console entirely and return None).

    def get_console(self) -> Any:
        """Return the primary rich Console, or None if boot has not filled it yet."""
        return self._console

    def set_console(self, console: Any) -> None:
        """Fill the primary Console slot post-construction (orchestrator boot)."""
        self._console = console

    def get_debug_console(self) -> Any:
        """Return the debug rich Console, or None if unset."""
        return self._debug_console

    def set_debug_console(self, console: Any) -> None:
        """Fill the debug Console slot post-construction (e.g. subprocess bootstrap)."""
        self._debug_console = console

    def get_socket_connection(self) -> Any:
        """Return the raw socket connection, or None if not yet connected."""
        return self._socket_con

    def set_socket_connection(self, conn: Any) -> None:
        """Fill the socket slot post-construction (e.g. SocketManager.get_socket_con())."""
        self._socket_con = conn

    def get_listeners(self) -> Any:
        """Return the listener dict (born empty)."""
        return self._listeners

    def register_listener(self, key: str, listener: Any) -> None:
        """Add ``listener`` to the listener dict under ``key`` (overwrites on clash)."""
        self._listeners[key] = listener
