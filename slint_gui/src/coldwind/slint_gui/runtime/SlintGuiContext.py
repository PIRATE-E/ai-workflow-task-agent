"""
Slint_UI_Logger is the same as the DesktopDebugLogge used in desktop but rather to
emitted as per logs we would catch and consider events in the Slint_UI_Logger
"""

from typing import Any, Self, override

from coldwind.core.config import CoreSettinngs
from coldwind.core.interfaces import (
    CommandParserInterface,
    ExceptionHandlerInterface,
    MessageDisplayInterface,
    PlatformRuntimeContextInterface,
)
from coldwind.core.interfaces.logging_interface import DebugLoggerInterface
from coldwind.core.models import StateAccessor

# these are the default dispatcher implementation defined in core to avoid boiler plat !!
from coldwind.core.system_logging.debug_protocol import (
    debug_critical,
    debug_error,
    debug_info,
    debug_warning,
)
from coldwind.core.tools.lggraph_tools.tool_response_manager import ToolResponseManager
from coldwind.slint_gui.config.SlintGuiConfig import SlintGuiConfig
from coldwind.slint_gui.runtime.ui.exception_handler import SlintExceptionHandler
from coldwind.slint_gui.slash_commands import SlintCommandResult


# instead of logging it is used as current for event streaming of the log entries !!
class Slint_UI_Logger(DebugLoggerInterface):

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


class SlintGuiDisplay(MessageDisplayInterface):
    """
    SlintGUI implementation for displaying user-facing messages and banners.
    Wraps the print_message and print_banner UI modules.
    """

    # injected by the native rust !!

    # show per message got or send from serder(role)
    def display_message(
        self, role: str, content: str, metadata: dict[str, Any] | None = None
    ) -> None:
        # The existing print_message expects role as sender ('user', 'ai', 'tool')
        print_message(sender=role, content=content)

    def display_banner(self, title: str, subtitle: str = "") -> None:
        # this also doesnt not accept any args
        # it is welcome splash screen thing !!
        splash_screen_display()


class SlintCommandParser(CommandParserInterface):
    # TODO:
    """
        CommandParserInterface is for getting input of user but it never used in core
        except only in the classify agent where it use to determine the slash command execution
        got success or not !! it pass the command to the command parser if there is '/' in it !!
        and determine did the command parser able to execute the command or not !!

        classify agent pass the raw text to the command parser and
        expected dict["success"] also exact that data class to parse the result from the parser and then pass to llm

    --
    @dataclass
    class CommandResult:
        # this could be changed to typed dict later for more structure
        success: bool
        message: str
        data: Any | None = None # this could be changed to typed dict later for more structure
        additional_warnings: list[str] | None = None # like handled errors but not critical
        error: dict[str, str] | None = None # error message if any # this could be changed to typed dict later for more structure

    data is also access to pass the llm !!

    """

    # this doesnt got used with in the core it is just for conventional purpose it doesnt get called
    # until delibrately in the platform side !!
    @override
    def get_user_input(self, prompt_text: str = "> ") -> str:
        raise NotImplementedError(
            "Slint GUI submits prompts via TicketIn to ColdWindEngine.process_ticket(); "
            "blocking get_user_input() is not used."
        )

    # we have to specify our own slash command based on platform
    # register the command here this is not any registry but API convention to
    # readable registration orchestration here !! register all the slash command here for doc purpose !
    @override
    def register_default_commands(self) -> None:
        """
        currently because we are not sure what are the slash comand for the slint gui we are not doing any slash registration here
        """

    @override
    def parse_and_execute(self, raw_input: str) -> Any:
        """
        return this to make classify agent work

        @dataclass
        class CommandResult:
            # this could be changed to typed dict later for more structure
            success: bool
            message: str
            data: Any | None = None # this could be changed to typed dict later for more structure
            additional_warnings: list[str] | None = None # like handled errors but not critical
            error: dict[str, str] | None = None # error message if any # this could be changed to typed dict later for more structure
        """

        # TODO:
        # we are currently doing this as monkey patch but this would required to explicitly create package and rust implementation
        # for same as desktop got its own slash command parsing things
        # currently returning artificial CommandResult !!
        # this is mainly about {agent, llm routings purposes but added few others to as monkey patched}
        # but slint gui required it own rust command parsning and routing things !!
        cleaned = raw_input.strip()
        if not cleaned.startswith("/"):
            return SlintCommandResult(
                success=False,
                message="Input is not a slash command.",
                error={"error": "Missing '/' prefix"},
            )

        # monkey patch !!
        tokens = cleaned[1:].strip().split()
        if not tokens:
            return SlintCommandResult(
                success=False,
                message="Empty slash command.",
                error={"error": "Missing command name"},
            )

        cmd = tokens[0].lower()

        # 1. Workflow Routing Slash Commands (/llm, /tool, /agent)
        if cmd in ("llm", "tool", "agent"):
            return SlintCommandResult(
                success=True,
                message=f"Routed request to '{cmd}' workflow.",
                data={"message_type": cmd},
            )

        # 2. GUI-Safe /clear (No os.system("clear")!)
        if cmd == "clear":
            ToolResponseManager().clear_response()
            StateAccessor().clear_state()
            debug_info(
                heading="AGENT_WORKFLOW • CLEAR",
                body="Chat history cleared.",
                metadata={"gui_event": "clear_chat"},
            )
            return SlintCommandResult(
                success=True,
                message="Chat history cleared successfully.",
            )

        # 3. GUI-Safe /exit (Sets ContextRegistry.get().request_exit())
        if cmd == "exit":
            from coldwind.core.runtime.CoreContextRegistry import ContextRegistry

            ContextRegistry.get().request_exit()
            debug_info(
                heading="AGENT_WORKFLOW • EXIT",
                body="Application exit requested.",
                metadata={"gui_event": "exit_requested"},
            )
            return SlintCommandResult(
                success=True,
                message="Exit requested. Waiting for workflow completion...",
                data={"exit_requested": True},
            )

        # 4. GUI-Safe /help
        if cmd == "help":
            return SlintCommandResult(
                success=True,
                message=(
                    "Available Slash Commands:\n"
                    "  /llm <query>   - Route directly to conversational LLM\n"
                    "  /tool <query>  - Route directly to tool selector\n"
                    "  /agent <query> - Route to hierarchical AgentGraphCore\n"
                    "  /clear         - Clear conversation state\n"
                    "  /exit          - Request engine shutdown"
                ),
            )

        return SlintCommandResult(
            success=False,
            message=f"Unknown slash command: /{cmd}",
            error={"error": f"Unknown command '{cmd}'"},
        )


class SlintGuiExceptionHandler(ExceptionHandlerInterface):
    """
    Slint GUi implementation for exception handling.
    Wraps the existing RichTracebackManager.
    """

    def handle_exception(
        self,
        error: Exception,
        context: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        SlintExceptionHandler.handle_exception(error, context, extra_context)


# ============================================================================
# 5. MASTER RUNTIME CONTEXT (PlatformRuntimeContextInterface — 14 Methods)
# ============================================================================


# BUG:
# this is not classified as how to populate the slint runtime because there are key issues in the core
# core is still acting as mother of single desktop platform calling checks up on console.print and isinstance of console of rich !!
#
class SlintRuntimeContext(PlatformRuntimeContextInterface):
    """
    Concrete PlatformRuntimeContextInterface for the Slint + Rust GUI platform.
    Implements all 14 abstract methods of the post-Oct-25 master contract.
    """

    _instance: Self | None = None

    def __new__(cls, *args, **kwargs) -> Self:
        if cls._instance is not None:
            return cls._instance
        cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: SlintGuiConfig):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._settings: SlintGuiConfig = settings

        # Pillar 4: Console slots are born None per runtime_interface.py:111-125.
        # Until Report 04's 6 patches are applied to coldwind-core, setting
        # use_silent_console_fallback=True provides a silent Rich Console sink so
        # unpatched `console.print()` calls in router.py/chat_llm.py do not crash.
        # Once Report 04 is applied to Core, pass use_silent_console_fallback=False
        # so self._console is literally None!
        self._debug_console: Any = None

        # Pillar 3: Exit flag
        self._exit_flag: bool = False

        # Pillar 2: Dynamic service store (Core injects CoreRunTimeObjects.message_classes here)
        self._dynamic_services: dict[type, Any] = {}

        # Pillar 1: Satellite contract instances
        self._logger = Slint_UI_Logger()
        self._error_handler = SlintGuiExceptionHandler()
        self._message_display = SlintGuiDisplay()
        self._command_parser = SlintCommandParser()

    # ── Pillar 1: 5 Typed Service Accessors ──

    @override
    def get_logger(self) -> DebugLoggerInterface:
        return self._logger

    @override
    def get_error_handler(self) -> ExceptionHandlerInterface:
        return self._error_handler

    @override
    def get_message_display(self) -> MessageDisplayInterface:
        return self._message_display

    @override
    def get_command_parser(self) -> CommandParserInterface:
        return self._command_parser

    @override
    def get_settings(self) -> CoreSettinngs:
        return self._settings

    # ── Pillar 2: 2 Dynamic Service Store Methods ──

    @override
    def get_service(self, service_type: type) -> Any:
        if service_type not in self._dynamic_services:
            name = getattr(service_type, "__name__", str(service_type))
            raise RuntimeError(f"Service {name} not registered in SlintRuntimeContext.")
        return self._dynamic_services[service_type]

    @override
    def register_service(self, service_type: type, service: Any) -> None:
        self._dynamic_services[service_type] = service

    # ── Pillar 3: 3 Lifecycle State Machine Methods ──

    @override
    def is_exiting(self) -> bool:
        return self._exit_flag

    @override
    def request_exit(self) -> None:
        self._exit_flag = True

    @override
    def reset_exit_request(self) -> None:
        self._exit_flag = False

    # ── Pillar 4: 4 Mutable Console Slot Methods ──

    @override
    def get_console(self) -> Any:
        return self._console

    @override
    def set_console(self, console: Any) -> None:
        self._console = console

    @override
    def get_debug_console(self) -> Any:
        return self._debug_console

    @override
    def set_debug_console(self, console: Any) -> None:
        self._debug_console = console
