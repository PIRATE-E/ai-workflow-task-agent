"""
works for command parser
TODO: NOT IMPLEMENTED--

currently monkey patched for the classify agent !!

"""

from dataclasses import dataclass
from typing import Any


@dataclass
class SlintCommandResult:
    """Matches the CommandResult shape expected by classify_agent.py (lines 35–58)."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: dict[str, str] | None = None
