"""
Desktop Platform Event Handler (PROTOTYPE & DEMONSTRATOR ONLY).

=============================================================================
ARCHITECTURAL STATUS: PROTOTYPE / DEMONSTRATOR ONLY — NOT USED AT RUNTIME
- Desktop does NOT use this handler at runtime because Desktop already has
  `DashBoardHandler` for streaming logs and diagnostics to its debug terminal.
- This file is preserved strictly as an architectural demonstrator for how
  external platforms (such as Slint+Rust native GUI `ai-workflow-gui` or
  headless FastAPI server workers) can bridge Core's `LogEntry` pipeline
  into a thread-safe consumer queue or callback subscriber if needed.
=============================================================================
"""

import threading
from collections import deque
from collections.abc import Callable
from typing import Any, override

from coldwind.core.system_logging.debug_protocol import LogEntry
from coldwind.core.system_logging.handlers.handler_base import Handler


class DesktopPlatformEventHandler(Handler):
    """
    PROTOTYPE DEMONSTRATOR: Platform Event Handler.
    (Desktop does NOT need this at runtime; Desktop uses DashBoardHandler).
    
    Demonstrates how a platform ambassador can receive LogEntry objects
    from Core's OnTimeRegistry and funnel them to platform consumer callbacks.
    """

    name: str = "DesktopPlatformEventHandler"

    def __init__(
        self,
        consumer: Callable[[dict[str, Any]], None] | None = None,
        max_buffered_events: int = 1000,
    ) -> None:
        """
        Initialize the platform event handler.

        Args:
            consumer: Optional callable invoked whenever a LogEntry arrives.
                      Receives the serialized event dictionary.
            max_buffered_events: Max capacity of the thread-safe circular event buffer.
        """
        self._lock = threading.Lock()
        self._consumers: list[Callable[[dict[str, Any]], None]] = []
        if consumer:
            self._consumers.append(consumer)
        self._event_buffer: deque[dict[str, Any]] = deque(maxlen=max_buffered_events)

    def subscribe(self, consumer: Callable[[dict[str, Any]], None]) -> None:
        """Add a platform event listener/consumer callback."""
        with self._lock:
            if consumer not in self._consumers:
                self._consumers.append(consumer)

    def unsubscribe(self, consumer: Callable[[dict[str, Any]], None]) -> None:
        """Remove a platform event listener/consumer callback."""
        with self._lock:
            if consumer in self._consumers:
                self._consumers.remove(consumer)

    def get_buffered_events(self) -> list[dict[str, Any]]:
        """Return a snapshot of recently buffered events."""
        with self._lock:
            return list(self._event_buffer)

    def clear_buffer(self) -> None:
        """Clear all buffered events."""
        with self._lock:
            self._event_buffer.clear()

    @override
    def should_handle(self, log_entry: LogEntry, *args) -> bool:
        """Accept all log entries as platform execution events."""
        return True

    @override
    def handle(self, log_entry: LogEntry, *args) -> None:
        """
        Convert LogEntry to a serializable event dict and dispatch to all registered consumers.
        Guarantees that individual consumer exceptions do not interrupt Core execution.
        """
        event_payload = log_entry.to_dict()

        with self._lock:
            self._event_buffer.append(event_payload)
            active_consumers = list(self._consumers)

        for consumer in active_consumers:
            try:
                consumer(event_payload)
            except Exception:
                # Defensive error boundary: platform consumer errors must never crash Core
                pass
