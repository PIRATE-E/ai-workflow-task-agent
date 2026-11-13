from abc import ABC, abstractmethod
from typing import Any


class MessageDisplayInterface(ABC):
    """
    Contract for displaying application messages (e.g., chat messages, tool outputs) to the user.
    Replaces direct imports of `print_message` and UI banners.
    """

    @abstractmethod
    def display_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """Display a standard message to the user."""

    @abstractmethod
    def display_banner(self, title: str, subtitle: str = "") -> None:
        """Display an application banner or section header."""


class CommandParserInterface(ABC):
    """
    Contract for handling user inputs and slash commands.
    Abstracts away prompt_toolkit or REST API request parsing.
    """

    @abstractmethod
    def get_user_input(self, prompt_text: str = "> ") -> str:
        """Request input from the user."""

    @abstractmethod
    def parse_and_execute(self, raw_input: str) -> Any:
        """Parse raw user input, execute slash commands if present, or route to agent."""

    def register_default_commands(self) -> None:
        """Register platform-specific slash commands or endpoints (optional)."""


def print_message(content: str, sender: str = "user", metadata: dict[str, Any] | None = None) -> None:
    """
    WHAT: Forward user-facing messages to the active runtime context's display service.
    WHY: Replaces illegal imports of `coldwind.desktop.ui.print_message_style.print_message`
    inside core agent and engine modules, preserving the Layering Invariant.
    """
    from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
    try:
        ContextRegistry.get().get_message_display().display_message(sender, content, metadata)
    except Exception:
        # Fallback to standard print if context or display is not yet initialized
        print(f"[{sender.upper()}] {content}")

