"""
Desktop Status Handler (Rich Status & Spinner Telemetry Integration).

=============================================================================
WHAT CHANGED & WHY:
- Created stateful telemetry aggregator inside DesktopStatusHandler.
- Combines all critical runtime metrics into ONE unified status display line:
  [Task X/Y: Activity] | API: N/40 RPM | Failed: F
- Aggregates Core LogEntry milestones without wiping out concurrent counters:
  1. Current task activity & progress (e.g. [Task 2/5: GoogleSearch])
  2. Cumulative API request velocity out of 40 RPM limit
  3. Recorded failed API requests count
  4. Real-time rate-limit countdown when waiting for window reset
- Drops internal retry noise (API_ATTEMPT, API_CALL).
=============================================================================
"""

import re
import threading
from typing import final, override

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.system_logging.debug_protocol import LogCategory, LogEntry
from coldwind.core.system_logging.handlers.handler_base import Handler
from rich.console import Console
from rich.status import Status


@final
class DesktopStatusHandler(Handler):
    """
    Desktop Status Handler.
    Aggregates Core telemetry and renders a live, unified Rich spinner status.
    """

    name: str = "DesktopStatusHandler"

    STATUS_CATEGORIES: set[LogCategory] = {
        LogCategory.AGENT_WORKFLOW,
        LogCategory.TOOL_EXECUTION,
    }

    def __init__(self, console: Console | None = None) -> None:
        """
        Initialize the Desktop status handler.

        Args:
            console: Optional Rich Console. Defaults to the active runtime context console.
        """
        self._console: Console | None = console
        self._lock: threading.Lock = threading.Lock()
        self._status_context: Status | None = None
        self._current_status: Status | None = None
        self._is_active: bool = False

        # --- Aggregated Telemetry State ---
        self.current_task: str = "Thinking..."
        self.task_index: int = 1
        self.total_tasks: int = 1
        self.requests_count: int = 0
        self.max_rpm: int = 40
        self.failed_count: int = 0
        self.rate_limit_wait: float = 0.0

    def _get_console(self) -> Console:
        """Resolve active Rich console from context if not explicitly provided."""
        if self._console is not None:
            return self._console
        try:
            resolved = ContextRegistry.get().get_console()
            if isinstance(resolved, Console):
                return resolved
        except Exception:
            pass
        return Console()

    def _format_aggregated_status(self) -> str:
        """
        Aggregate all tracked metrics into one concise status line:
        [Task X/Y: Activity] | API: N/40 RPM | Failed: F
        """
        # 1. Task progress & description
        if self.total_tasks > 1:
            task_tag = f"[Task {self.task_index}/{self.total_tasks}: {self.current_task}]"
        else:
            task_tag = f"[{self.current_task}]"

        # 2. Rate limit / RPM status
        if self.rate_limit_wait > 0:
            api_tag = f"[bold yellow]Rate Limit: wait {self.rate_limit_wait:.1f}s ({self.requests_count}/{self.max_rpm} RPM)[/bold yellow]"
        else:
            style = "bold green" if self.requests_count < 30 else "bold yellow"
            api_tag = f"[{style}]API: {self.requests_count}/{self.max_rpm} RPM[/{style}]"

        # 3. Failed requests counter
        fail_style = "dim red" if self.failed_count == 0 else "bold red"
        fail_tag = f"[{fail_style}]Failed: {self.failed_count}[/{fail_style}]"

        return f"[bold cyan]{task_tag}[/bold cyan] │ {api_tag} │ {fail_tag}"

    def start(self, initial_message: str = "Thinking...", spinner: str = "dots") -> None:
        """
        Start the Rich animated spinner display with initial aggregated state.
        """
        with self._lock:
            if not self._is_active:
                self.current_task = initial_message
                self.rate_limit_wait = 0.0
                console = self._get_console()
                initial_display = self._format_aggregated_status()
                self._status_context = console.status(
                    initial_display, spinner=spinner
                )
                self._current_status = self._status_context.__enter__()
                self._is_active = True

    def update(self, message: str) -> None:
        """Update the Rich spinner text."""
        with self._lock:
            if self._is_active and self._current_status is not None:
                self._current_status.update(message)

    def stop(self) -> None:
        """Stop and tear down the Rich spinner display cleanly."""
        with self._lock:
            if self._is_active and self._current_status is not None:
                try:
                    self._current_status.__exit__(None, None, None)
                except Exception:
                    pass
                finally:
                    self._current_status = None
                    self._status_context = None
                    self._is_active = False

    @final
    class _TurnStatusContext:
        """Internal context manager for wrapping a single turn execution."""

        def __init__(
            self,
            handler: "DesktopStatusHandler",
            initial_message: str,
            spinner: str,
        ) -> None:
            self._handler: DesktopStatusHandler = handler
            self._initial_message: str = initial_message
            self._spinner: str = spinner

        def __enter__(self) -> "DesktopStatusHandler":
            self._handler.start(self._initial_message, self._spinner)
            return self._handler

        def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
            self._handler.stop()

    def turn_status(
        self, initial_message: str = "Thinking...", spinner: str = "dots"
    ) -> _TurnStatusContext:
        """
        Context manager to scope the spinner lifecycle to a single ticket turn.
        """
        return self._TurnStatusContext(self, initial_message, spinner)

    @override
    def should_handle(self, log_entry: LogEntry, *args: object) -> bool:
        """
        Filter log entries to only update status when the spinner is actively running.
        Ignores internal API network traces (API_CALL, API_ATTEMPT).
        """
        if not self._is_active:
            return False

        msg_upper = log_entry.MESSAGE.upper()

        # Drop internal API network call traces and retry attempt logs
        if "API_CALL" in msg_upper or "API_ATTEMPT" in msg_upper:
            return False

        # Explicit STATUS events from Core nodes, agent_status, or rate-limiting
        if "STATUS" in msg_upper:
            return True

        if log_entry.LOG_TYPE in self.STATUS_CATEGORIES:
            return True

        return any(
            kw in msg_upper
            for kw in ("RATE_LIMIT", "ROUTER", "CLASSIFIER", "AGENT_MODE", "FAILURE")
        )

    @override
    def handle(self, log_entry: LogEntry, *args: object) -> None:
        """
        Aggregate telemetry from Core LogEntry into unified single-string status display.
        """
        with self._lock:
            if not self._is_active or self._current_status is None:
                return

            metadata = log_entry.METADATA if isinstance(log_entry.METADATA, dict) else {}

            # Update request & failure counters from metadata if present
            if "requests_count" in metadata:
                try:
                    self.requests_count = int(metadata["requests_count"])
                except Exception:
                    pass
            if "api_calls" in metadata:
                try:
                    self.requests_count = int(metadata["api_calls"])
                except Exception:
                    pass
            if "failure_count" in metadata or "failed_count" in metadata:
                try:
                    self.failed_count = int(
                        metadata.get("failure_count") or metadata.get("failed_count") or 0
                    )
                except Exception:
                    pass
            if "task_id" in metadata or "task_index" in metadata:
                try:
                    self.task_index = int(
                        metadata.get("task_id") or metadata.get("task_index") or 1
                    )
                except Exception:
                    pass
            if "total_tasks" in metadata:
                try:
                    self.total_tasks = int(metadata["total_tasks"])
                except Exception:
                    pass
            if "wait_time" in metadata:
                try:
                    self.rate_limit_wait = float(metadata["wait_time"])
                except Exception:
                    self.rate_limit_wait = 0.0
            else:
                self.rate_limit_wait = 0.0

            # Parse message content
            parts = log_entry.MESSAGE.split(" | ", 1)
            heading = parts[0].strip().upper()
            body = parts[1].strip() if len(parts) > 1 else parts[0].strip()

            # If message is API request progress counter, update requests_count without wiping current task
            if "API REQUEST" in body.upper() and "IN PROGRESS" in body.upper():
                match = re.search(r"API request (\d+)", body)
                if match:
                    self.requests_count = int(match.group(1))
            elif "RATE LIMIT HIT" in body.upper():
                pass
            elif (
                heading == "STATUS"
                or "AGENT" in heading
                or "ROUTER" in heading
                or "TOOL" in heading
                or "CLASSIFIER" in heading
            ):
                # Clean up any trailing funny quote '@ API calls: X' so task label stays clean
                cleaned_task = body.split(" @ API calls:")[0].strip()
                if cleaned_task:
                    self.current_task = cleaned_task

            # Push aggregated single-line update to Rich spinner
            self._current_status.update(self._format_aggregated_status())
