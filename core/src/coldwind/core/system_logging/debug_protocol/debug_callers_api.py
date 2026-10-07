"""
public api for the desktop and core to populate there logs
using them !!

TODO:- would be Expendable through the desktop and platforms definitions too !!

"""

from typing import Dict, Optional, Any

from . import LogCategory, LogEntry, LogLevel
from coldwind.core.utils.timestamp_util import get_formatted_timestamp


def debug_info(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    from ..dispatcher import Dispatcher
    log_dispatcher = Dispatcher()
    log_dispatcher.dispatch_v2(
        LogEntry(
            LogCategory.OTHER,
            LogLevel.INFO,
            get_formatted_timestamp(),
            f"{heading} | {body}",
            metadata,
        )
    )


def debug_warning(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    from ..dispatcher import Dispatcher
    log_dispatcher = Dispatcher()
    log_dispatcher.dispatch_v2(
        LogEntry(
            LogCategory.OTHER,
            LogLevel.WARNING,
            get_formatted_timestamp(),
            f"{heading} | {body}",
            metadata,
        )
    )


def debug_error(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    from ..dispatcher import Dispatcher
    log_dispatcher = Dispatcher()
    log_dispatcher.dispatch_v2(
        LogEntry(
            LogCategory.OTHER,
            LogLevel.ERROR,
            get_formatted_timestamp(),
            f"{heading} | {body}",
            metadata,
        )
    )


def debug_critical(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None) -> None:
    from ..dispatcher import Dispatcher
    log_dispatcher = Dispatcher()
    log_dispatcher.dispatch_v2(
        LogEntry(
            LogCategory.OTHER,
            LogLevel.CRITICAL,
            get_formatted_timestamp(),
            f"{heading} | {body}",
            metadata,
        )
    )

