"""
Dashboard Rich Printer.

Receives raw JSONL stream from the IPC socket connection, deserializes
into typed LogEntry objects, and renders formatted Rich panels in the
dashboard window.
"""

import json
from typing import Any, Dict, Optional, Union

from rich.box import ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from coldwind.core.system_logging.debug_protocol import LogCategory, LogEntry, LogLevel

# Shared console configured for terminal output with safe box characters
console = Console(force_terminal=True, safe_box=True)


class Printer:
    """
    Renders incoming LogEntry records as structured, color-coded Rich panels.
    """

    # =========================================================================
    # WHAT: Styling definitions mapping LogLevel to (tag, title_style, border_style).
    # WHY: Provides visual distinction between DEBUG, INFO, WARNING, ERROR, and
    #      CRITICAL messages so developers can scan logs quickly in the dashboard.
    # =========================================================================
    LEVEL_STYLES: Dict[LogLevel, tuple[str, str, str]] = {
        LogLevel.DEBUG: ("🔍 DEBUG", "dim cyan", "dim cyan"),
        LogLevel.INFO: ("ℹ️  INFO", "bold cyan", "cyan"),
        LogLevel.WARNING: ("⚠️  WARNING", "bold yellow", "yellow"),
        LogLevel.ERROR: ("🚨 ERROR", "bold red", "red"),
        LogLevel.CRITICAL: ("💥 CRITICAL", "bold bright_white on red", "bright_red"),
    }

    CATEGORY_LABELS: Dict[LogCategory, str] = {
        LogCategory.API_CALL: "🌐 API_CALL",
        LogCategory.TOOL_EXECUTION: "⚙️ TOOL_EXECUTION",
        LogCategory.AGENT_WORKFLOW: "🤖 AGENT_WORKFLOW",
        LogCategory.MCP_SERVER: "🔌 MCP_SERVER",
        LogCategory.ERROR_TRACEBACK: "💥 ERROR_TRACEBACK",
        LogCategory.OTHER: "📋 SYSTEM_LOG",
    }

    @classmethod
    def process_log(cls, raw_line: Union[str, bytes]) -> None:
        """
        Parse raw JSON line into a LogEntry and render it to the Rich console.

        WHAT: Deserializes JSON string into typed LogEntry, extracts metadata,
              constructs a styled Rich Panel, and renders it directly to the console.
        WHY: Performs pure, live terminal rendering without retaining unneeded in-memory queues.
        """
        if isinstance(raw_line, bytes):
            raw_line = raw_line.decode("utf-8", errors="replace")

        raw_line = raw_line.strip()
        if not raw_line:
            return

        try:
            log_entry = LogEntry.from_json(raw_line)
            cls._render_entry(log_entry)
        except Exception:
            # Fallback for plain-text or malformed JSON payloads
            cls._render_fallback(raw_line)

    @classmethod
    def _render_entry(cls, entry: LogEntry) -> None:
        """
        Render a structured LogEntry into a Rich Panel.
        """
        # Resolve level style safely
        level = entry.LOG_LEVEL
        if isinstance(level, str):
            try:
                level = LogLevel(level)
            except ValueError:
                level = LogLevel.INFO
        tag, title_style, border_style = cls.LEVEL_STYLES.get(
            level, ("📝 LOG", "bold white", "white")
        )

        # Resolve category label safely
        category = entry.LOG_TYPE
        if isinstance(category, str):
            try:
                category = LogCategory(category)
            except ValueError:
                category = LogCategory.OTHER
        category_label = cls.CATEGORY_LABELS.get(category, str(category))

        # Build composite title: [LEVEL] • [CATEGORY] • [TIMESTAMP]
        title = Text()
        title.append(f"{tag} ", style=title_style)
        title.append(f"• {category_label} • ", style="bold white")
        title.append(f"{entry.TIME_STAMP}", style="dim")

        # Main message body
        msg_text = Text(entry.MESSAGE, style="white")

        # If metadata is present and non-empty, render key-value grid
        if entry.METADATA and isinstance(entry.METADATA, dict):
            grid = Table.grid(padding=(0, 2))
            grid.add_column(style="dim cyan", justify="right")
            grid.add_column(style="white")
            for key, val in entry.METADATA.items():
                grid.add_row(f"{key}:", str(val))

            content = Group(msg_text, Text(""), grid)
        else:
            content = msg_text

        # WHAT: Configure Panel with expand=True and title_align="center".
        # WHY: Stretches the panel across the full width of the dashboard window
        #      and centers the title/badge symmetrically on the top border.
        panel = Panel(
            content,
            title=title,
            title_align="center",
            border_style=border_style,
            box=ROUNDED,
            expand=True,
            padding=(0, 1),
        )
        console.print(panel)

    @classmethod
    def _render_fallback(cls, raw_text: str) -> None:
        """
        Fallback renderer for raw string messages that did not adhere to JSON format.
        """
        panel = Panel(
            Text(raw_text, style="yellow"),
            title=Text("⚠️ RAW MESSAGE", style="bold yellow"),
            title_align="center",
            border_style="yellow",
            box=ROUNDED,
            expand=True,
            padding=(0, 1),
        )
        console.print(panel)
