from abc import ABC, abstractmethod
from typing import Any, Optional


class MessageDisplayInterface(ABC):
    """
    Contract for displaying application messages (e.g., chat messages, tool outputs) to the user.
    Replaces direct imports of `print_message` and UI banners.
    """

    @abstractmethod
    def display_message(self, role: str, content: str, metadata: Optional[dict[str, Any]] = None) -> None:
        """Display a standard message to the user."""
        pass

    @abstractmethod
    def display_banner(self, title: str, subtitle: str = "") -> None:
        """Display an application banner or section header."""
        pass


class CommandParserInterface(ABC):
    """
    Contract for handling user inputs and slash commands.
    Abstracts away prompt_toolkit or REST API request parsing.
    """

    @abstractmethod
    def get_user_input(self, prompt_text: str = "> ") -> str:
        """Request input from the user."""
        pass

    @abstractmethod
    def parse_and_execute(self, raw_input: str) -> Any:
        """Parse raw user input, execute slash commands if present, or route to agent."""
        pass
