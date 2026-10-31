"""
Exit Slash Command

Handles the /exit slash command by requesting application exit
through the active runtime context (ContextRegistry.get().request_exit()).
"""

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.system_logging.debug_protocol import debug_error
from coldwind.desktop.slash_commands.protocol import (
    CommandOption,
    CommandResult,
    SlashCommand,
)


def register_exit_command() -> None:
    """Function to register the /exit command."""
    from ..on_run_time_register import OnRunTimeRegistry

    exit_command = SlashCommand(
        command="exit",
        options=None,
        requirements=None,
        description="Exit the application.",
        handler=exit_handler,
    )
    registry = OnRunTimeRegistry()
    try:
        registry.register(exit_command)
    except registry.CommandAlreadyRegisteredError:
        pass


def exit_handler(
    command: SlashCommand, options: CommandOption | None
) -> CommandResult:
    """
    Handler function to exit the application.

    ---------------------------------------------------------------------------
    WHAT CHANGED & WHY:
    Retired legacy ExitListener / event_manager from exit command handling.
    WHY: Exit signaling is now standardized via ContextRegistry.get().request_exit().
    The host platform's turn loop checks context.is_exiting() to break cleanly,
    eliminating monolithic in-memory event bus dependencies.
    ---------------------------------------------------------------------------
    """
    try:
        ContextRegistry.get().request_exit()
        return CommandResult(
            success=True,
            message="🎫 Exit requested. Waiting for workflow completion...",
            data={"exit_requested": True},
        )
    except Exception as e:
        debug_error(
            f"Error in exit_handler: {e}",
            body="An error occurred while trying to request exit.",
            metadata={"exception": str(e)},
        )
        return CommandResult(
            success=False,
            message=f"Failed to exit cleanly: {e}",
            error={"error": str(e)},
        )
