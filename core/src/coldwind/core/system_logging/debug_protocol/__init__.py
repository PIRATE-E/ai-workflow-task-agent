"""
system logging protocols definitions and defined 'api' routes for  expected implementation of debug logging based on core or desktop

Whether these are the protocols so we made into the module itself ...

Defined :-
    LogLevel -> for definining the log level in the LogEntry data class example (error, critical, warning, info)
    LogCategory -> for defining the log category in the LogEntry data class example (api call, tool executions, agent workflow, mcp server, error traceback)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    API_CALL = "API_CALL"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    AGENT_WORKFLOW = "AGENT_WORKFLOW"
    MCP_SERVER = "MCP_SERVER"
    ERROR_TRACEBACK = "ERROR_TRACEBACK"
    OTHER = "OTHER"


@dataclass
class LogEntry:
    LOG_TYPE: LogCategory
    LOG_LEVEL: LogLevel
    TIME_STAMP: str
    MESSAGE: str  # main message body
    METADATA: Optional[Dict[str, Any]] = None

    """
    LogLevel - DEBUG, INFO, WARNING, ERROR, CRITICAL
    LogType - API_CALL, TOOL_EXECUTION, AGENT_WORKFLOW, MCP_SERVER, ERROR_TRACEBACK
    """


from .debug_callers_api import debug_info, debug_critical, debug_error, debug_warning


__all__ = [
    "LogEntry",
    "LogCategory",
    "LogLevel",
    "debug_error",
    "debug_warning",
    "debug_critical",
    "debug_info",
]
