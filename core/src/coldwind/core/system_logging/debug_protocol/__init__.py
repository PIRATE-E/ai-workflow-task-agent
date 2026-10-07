"""
system logging protocols definitions and defined 'api' routes for  expected implementation of debug logging based on core or desktop

Whether these are the protocols so we made into the module itself ...

Defined :-
    LogLevel -> for definining the log level in the LogEntry data class example (error, critical, warning, info)
    LogCategory -> for defining the log category in the LogEntry data class example (api call, tool executions, agent workflow, mcp server, error traceback)
"""

import json
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

    # =========================================================================
    # SERIALIZATION & DESERIALIZATION METHODS
    # WHAT: Added to_dict, to_json, from_dict, and from_json helper methods.
    # WHY: Python's standard json.dumps() cannot serialize Enum members (LogCategory, LogLevel)
    #      directly when using asdict(log_entry). These methods explicitly convert enums to their
    #      string values during encoding, and restore string values back to enum instances during
    #      decoding, preventing JSON serialization crashes across the IPC socket boundary.
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the LogEntry dataclass instance into a JSON-serializable dictionary.
        Enums (LOG_TYPE and LOG_LEVEL) are converted to their underlying string values.
        """
        return {
            "LOG_TYPE": self.LOG_TYPE.value if isinstance(self.LOG_TYPE, Enum) else str(self.LOG_TYPE),
            "LOG_LEVEL": self.LOG_LEVEL.value if isinstance(self.LOG_LEVEL, Enum) else str(self.LOG_LEVEL),
            "TIME_STAMP": self.TIME_STAMP,
            "MESSAGE": self.MESSAGE,
            "METADATA": self.METADATA,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Serialize the LogEntry instance into a JSON formatted string.
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LogEntry":
        """
        Construct a LogEntry instance from a dictionary, safely restoring
        string representations of LOG_TYPE and LOG_LEVEL back to their respective Enums.
        """
        raw_type = data.get("LOG_TYPE", "OTHER")
        raw_level = data.get("LOG_LEVEL", "INFO")

        # Map strings back to enum members safely, falling back to defaults if unknown
        log_type = LogCategory(raw_type) if raw_type in LogCategory._value2member_map_ else LogCategory.OTHER
        log_level = LogLevel(raw_level) if raw_level in LogLevel._value2member_map_ else LogLevel.INFO

        return cls(
            LOG_TYPE=log_type,
            LOG_LEVEL=log_level,
            TIME_STAMP=data.get("TIME_STAMP", ""),
            MESSAGE=data.get("MESSAGE", ""),
            METADATA=data.get("METADATA"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "LogEntry":
        """
        Deserialize a JSON formatted string back into a typed LogEntry instance.
        """
        data = json.loads(json_str)
        return cls.from_dict(data)


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
