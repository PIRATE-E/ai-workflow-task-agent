from abc import ABC, abstractmethod
from typing import Any


class DebugLoggerInterface(ABC):
    """
    Contract for application-wide logging and diagnostic output.
    
    This interface abstracts away the underlying logging implementation
    (e.g., Rich console panels for Desktop, standard logging for Server).
    Core modules must use this interface instead of importing desktop debug helpers.
    """

    @abstractmethod
    def log_debug(self, heading: str, body: str, metadata: dict[str, Any] | None = None) -> None:
        """Log low-level debugging information."""

    @abstractmethod
    def log_info(self, heading: str, body: str, metadata: dict[str, Any] | None = None) -> None:
        """Log general informational messages."""

    @abstractmethod
    def log_warning(self, heading: str, body: str, metadata: dict[str, Any] | None = None) -> None:
        """Log warnings that don't stop execution but require attention."""

    @abstractmethod
    def log_error(self, heading: str, body: str, metadata: dict[str, Any] | None = None) -> None:
        """Log recoverable errors."""

    @abstractmethod
    def log_critical(self, heading: str, body: str, metadata: dict[str, Any] | None = None) -> None:
        """Log severe, potentially unrecoverable errors."""
