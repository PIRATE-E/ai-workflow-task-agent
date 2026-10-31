"""
Desktop Runtime Context Implementation

this class inherites the core PlatformRuntimeContextInterface
by which we can able to implement its methods but using the
getter on our private attr of the class
the implementation and services defined into different modules
we are orchestrating them here ...
"""

from typing import Any, Self, override

from coldwind.core.config.coreSettings import CoreSettinngs
from coldwind.core.interfaces.exception_interface import ExceptionHandlerInterface
from coldwind.core.interfaces.logging_interface import DebugLoggerInterface
from coldwind.core.interfaces.runtime_interface import PlatformRuntimeContextInterface
from coldwind.core.interfaces.ui_interface import (
    CommandParserInterface,
    MessageDisplayInterface,
)
from coldwind.core.system_logging.debug_protocol import (
    debug_critical,
    debug_error,
    debug_info,
    debug_warning,
)
from coldwind.desktop.config.DesktopConfig import DesktopConfig
from coldwind.desktop.slash_commands.executionar import ExecutionAr
from coldwind.desktop.slash_commands.parser import ParseCommand
from coldwind.desktop.ui.chatInputHandler import InputHandler
from coldwind.desktop.ui.diagnostics.rich_traceback_manager import RichTracebackManager
from coldwind.desktop.ui.print_banner import print_banner
from coldwind.desktop.ui.print_message_style import print_message


class DesktopDebugLogger(DebugLoggerInterface):
    """
    Desktop implementation of the DebugLoggerInterface.
    Routes core logs to the core system_logging debug protocol
    (debug_info / debug_warning / debug_error / debug_critical).
    """

    @override
    def log_debug(
        self, heading: str, body: str, metadata: dict[str, Any] | None = None
    ) -> None:
        debug_info(heading, body, metadata)

    @override
    def log_info(
        self, heading: str, body: str, metadata: dict[str, Any] | None = None
    ) -> None:
        debug_info(heading, body, metadata)

    @override
    def log_warning(
        self, heading: str, body: str, metadata: dict[str, Any] | None = None
    ) -> None:
        debug_warning(heading, body, metadata)

    @override
    def log_error(
        self, heading: str, body: str, metadata: dict[str, Any] | None = None
    ) -> None:
        debug_error(heading, body, metadata)

    @override
    def log_critical(
        self, heading: str, body: str, metadata: dict[str, Any] | None = None
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
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        # ---------------------------------------------------------------------
        # WHAT CHANGED & WHY:
        # Explicitly pass context and extra_context as keyword arguments.
        # WHY: Previously passed positionally as the 3rd argument, which landed in
        # `exc_type` in RichTracebackManager.handle_exception(exception, context, exc_type, ...),
        # causing an AttributeError ('dict' object has no attribute '__name__').
        # ---------------------------------------------------------------------
        RichTracebackManager.handle_exception(
            error, context=context, extra_context=extra_context
        )


class DesktopMessageDisplay(MessageDisplayInterface):
    """
    Desktop implementation for displaying user-facing messages and banners.
    Wraps the print_message and print_banner UI modules.
    """

    def display_message(
        self, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        # The existing print_message expects role as sender ('user', 'ai', 'tool')
        print_message(content, sender=role)

    def display_banner(self, title: str, subtitle: str = "") -> None:
        # NOTE: print banner doesnt accept any argument for desktop !!
        print_banner()


class DesktopCommandParser(CommandParserInterface):
    """
    Desktop implementation for handling interactive user input and slash commands.
    Orchestrates the prompt_toolkit InputHandler, ParseCommand, and ExecutionAr.
    """

    def __init__(self):
        self._input_handler = InputHandler()
        self._executionar = ExecutionAr()
        self.register_default_commands()

    def get_user_input(self, prompt_text: str = "> ") -> str:
        return self._input_handler.get_user_input(prompt_text=prompt_text)

    def parse_and_execute(self, raw_input: str) -> Any:
        # Convert the raw text into a parsed slash command, then execute it
        slash_cmd = ParseCommand.get_command(raw_input)
        return self._executionar.execute(slash_cmd)

    def register_default_commands(self) -> None:
        """
        WHAT: Register default desktop slash commands into OnRunTimeRegistry.
        WHY: Moves desktop slash command registration out of core ColdWindEngine,
        preserving the Layering Invariant ('Desktop imports Core; Core NEVER imports Desktop').
        """
        from coldwind.desktop.slash_commands.commands.clear import (
            register_clear_command,
        )
        from coldwind.desktop.slash_commands.commands.core_slashs.agent import (
            register_agent_command,
        )
        from coldwind.desktop.slash_commands.commands.core_slashs.chat_llm import (
            register_chat_llm_command,
        )
        from coldwind.desktop.slash_commands.commands.core_slashs.use_tool import (
            register_slash_command_use_tool,
        )
        from coldwind.desktop.slash_commands.commands.exit import register_exit_command
        from coldwind.desktop.slash_commands.commands.help import register_help_command

        for reg_fn in (
            register_clear_command,
            register_help_command,
            register_agent_command,
            register_exit_command,
            register_chat_llm_command,
            register_slash_command_use_tool,
        ):
            try:
                reg_fn()
            except Exception:
                pass


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

        # 2. Exit Flag (Previously: settings.exit_flag)
        # WHAT: Purged legacy `self._listeners` container and `self._socket_con` slot.
        # WHY: Legacy ExitListener, RichStatusListener, and raw SocketManager were deleted.
        # Exit signaling is unified via `is_exiting()` / `request_exit()`.
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
