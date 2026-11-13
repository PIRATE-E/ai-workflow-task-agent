"""
Core interfaces for Application Context Registry Architecture.

This module defines the `RuntimeContextInterface`, which is the master contract
dictating what services are available to the Core system at runtime.
Core modules must use `ContextRegistry.get()` to obtain this interface,
rather than importing platform-specific implementations directly.
"""

from abc import ABC, abstractmethod
from typing import Any

from coldwind.core.config.coreSettings import CoreSettinngs
from coldwind.core.interfaces.exception_interface import ExceptionHandlerInterface
from coldwind.core.interfaces.logging_interface import DebugLoggerInterface
from coldwind.core.interfaces.ui_interface import (
    CommandParserInterface,
    MessageDisplayInterface,
)


class PlatformRuntimeContextInterface(ABC):
    """
    The master interface defining the contract for all runtime dependencies.

    This interface provides typed accessors for core services (logging, error handling, UI),
    as well as dynamic service registration for extensible components.
    It guarantees that Core has access to everything it needs without knowing HOW
    those things are implemented (e.g., Desktop vs. Server).
    """

    @abstractmethod
    def get_logger(self) -> DebugLoggerInterface:
        """Get the application-wide diagnostic logger."""

    @abstractmethod
    def get_error_handler(self) -> ExceptionHandlerInterface:
        """Get the platform-specific exception handler (e.g., RichTracebackManager equivalent)."""

    @abstractmethod
    def get_message_display(self) -> MessageDisplayInterface:
        """Get the service responsible for presenting chat messages and outputs."""

    @abstractmethod
    def get_command_parser(self) -> CommandParserInterface:
        """Get the service responsible for parsing inputs and slash commands."""

    @abstractmethod
    def get_settings(self) -> CoreSettinngs:
        """Get the read-only core configuration settings."""

    @abstractmethod
    def get_service(self, service_type: type) -> Any:
        """
        Get an dynamically registered service by its interface type.
    Examples:
        >>> ctx.get_service(CoreRunTimeObjects.neo4j_driver)

    Failure contract:
        Raises ``RuntimeError`` if ``service_type`` is not registered.
        Callers must handle the ``RuntimeError`` for optional services (e.g. Neo4j
        being unavailable at boot) rather than relying on a silent ``None``.
    """

    @abstractmethod
    def register_service(self, service_type: type, service: Any) -> None:
        """
        Register a dynamic service implementation against an interface type.
        This is typically called by the platform initialization code.
        """

    @abstractmethod
    def is_exiting(self) -> bool:
        """
        Query if the application has been requested to shut down.
        Replaces the direct read of `settings.exit_flag`.
        """

    @abstractmethod
    def request_exit(self) -> None:
        """
        Command the application to shut down safely.
        Replaces direct assignment to `ContextRegistry.get().request_exit()`.
        """

    @abstractmethod
    def reset_exit_request(self) -> None:
        """
        Clear the exit flag (set it back to False). Used when a non-exit message
        arrives after an exit was previously requested, so the app keeps running.
        Replaces direct assignment `settings.exit_flag = False`.
        """

    # ── Platform-optional mutable slots (abstractmethods — implemented per platform) ──
    # These wrap *platform-optional* MUTABLE runtime slots (rich Console, raw
    # socket, listener dict). Each platform implements them its own way.
    #
    # MUTABILITY CONTRACT (read carefully before implementing):
    #   • Slots are MUTABLE — born None and filled
    #     POST-construction via the set_* method at orchestrator boot rather
    #     than eagerly built in __init__. Building-then-overwriting in __init__
    #     is wasted work. See DesktopRunTimeContext.__init__ for the canonical
    #     pattern (slots declared None at construction, filled by setters).
    #   • **get_console / get_debug_console return None
    #     when the slot is still unset.** Callers reading these before boot
    #     MUST handle None explicitly. A headless server implementation that
    #     needs no Console MAY return None literally and skip the slot
    #     entirely — the contract is satisfied either way.
    #   • These differ from get_service (which raises RuntimeError when a
    #     registered service is missing) — these are value slots, not
    #     registry-mandatory services.
    #
    # =========================================================================
    # WHAT CHANGED & WHY:
    # Purged `get_listeners()`, `register_listener()`, `get_socket_connection()`,
    # and `set_socket_connection()` from the interface.
    # WHY: The legacy listeners subsystem was deleted, and raw socket streaming
    # was superseded by Core's `Dispatcher` and dashboard transport. Runtime
    # slots now strictly encompass platform UI consoles.
    # =========================================================================
    #
    # NOTE: the interface deliberately declares ONLY the method shape, never the
    # backing attribute (`self._console` etc.). The platform implementation owns
    # the storage. This keeps the interface free of implementation-state leaks.
    @abstractmethod
    def get_console(self) -> Any:
        """Return the primary rich Console (or None if unset / no terminal)."""

    @abstractmethod
    def set_console(self, console: Any) -> None:
        """Fill the primary Console slot post-construction (boot)."""

    @abstractmethod
    def get_debug_console(self) -> Any:
        """Return the debug rich Console (or None if unset / no terminal)."""

    @abstractmethod
    def set_debug_console(self, console: Any) -> None:
        """Fill the debug Console slot post-construction."""
