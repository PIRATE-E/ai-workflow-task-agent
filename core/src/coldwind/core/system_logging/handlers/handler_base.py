"""
this is base class for system_logging handlers
===========================================================
handlers are responsible for processing log entries and directing them to appropriate destinations (e.g., console, file, external services).
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, TextIO
from datetime import datetime
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.system_logging.debug_protocol import LogEntry


class Handler(ABC):

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "name"):
            raise KeyError(
                f"expected attribute *name* not in the the class {cls.__name__}"
            )
        return super().__init_subclass__()

    name: str

    @abstractmethod
    def should_handle(self, log_entry: LogEntry, *args) -> bool:
        """
        Determine if this handler should process the given log entry.

        Args:
            log_entry : The log entry to evaluate.
        Returns:
            bool: True if the handler should process the log entry, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def handle(self, log_entry: LogEntry, *args) -> None:
        """
        Process a log entry and direct it to the appropriate destination.

        Args:
            log_entry : The log entry to process.

        Returns:
            None
        """
        raise NotImplementedError


# ====================================================================
# TextBased Handler implementation
# ====================================================================


class TextHandler(Handler):
    name = "TextHandler"
    writers: Dict[str, TextIO] = {}

    # file rotation settings - fetched from active runtime context at access time
    _accessed_rotation_size_limit = False
    _accessed_time_rotation_limit = False

    @property
    def rotation_size_limit(self):
        return (
            ContextRegistry.get().get_settings().log_text_handler_rotation_size_limit_mb
        )

    @property
    def time_rotation_limit(self):
        return (
            ContextRegistry.get()
            .get_settings()
            .log_text_handler_rotation_time_limit_hours
        )

    def should_handle(self, log_entry: LogEntry, *args) -> bool:
        """
        Determine if this handler should process the given log entry.

        Args:
            log_entry : The log entry to evaluate.
            args : Additional arguments. force_stop (bool):- if True, the handler should not process the log entry.
        Returns:
            bool: True if the handler should process the log entry, False otherwise.
        """
        # For TextHandler, we assume it handles all log entries
        return not args or not args[0].get("force_stop", False)

    def handle(self, log_entry: LogEntry, *args) -> None:
        """
        Process a log entry and direct it to the appropriate destination.

        Args:
            log_entry : The log entry to process.

        Returns:
            None
        """

        ##### Logs are directed on based on LogCategory/LogType defined into the protocol

        file_name = log_entry.LOG_TYPE
        if file_name.value not in TextHandler.writers.keys():  # value because Enum type
            # Create log files in basic_logs/ directory — resolved from ContextRegistry project root
            from coldwind.core.runtime.CoreContextRegistry import ContextRegistry

            log_dir = (
                ContextRegistry.get().get_settings().project_root / "basic_logs"
            )  ### NOTE: TODO This is the default directory for log files; it can be customized in the future if needed.
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = log_dir / f"log_{file_name.value}.txt"

            # apply the log file for rotation check
            rotation_checks = self._text_file_rotation(log_file_path)

            file_mode = "a" if not rotation_checks.get("rotate", False) else "w"

            # Open with UTF-8 encoding to support emojis and international characters
            TextHandler.writers[file_name.value] = open(
                log_file_path, file_mode, 1, encoding="utf-8"
            )
            TextHandler.writers[file_name.value].write(
                ""
                if file_mode == "w"
                else f"\n\n{'='*20} New Logging Session Started at {datetime.now().isoformat()} {'='*20}\n\n"
            )
            TextHandler.writers[file_name.value].flush()

        from ..formatter import TextFormater

        formater = TextFormater.format(log_entry)
        TextHandler.writers[file_name.value].write(f"{formater} \n")

    @classmethod
    def clean_up(cls):
        # we have to close all opened file handlers
        for writer in TextHandler.writers.values():
            writer.flush()
            os.fsync(writer.fileno())
            writer.close()
        TextHandler.writers.clear()
        pass

    def _text_file_rotation(self, file_path: Path):
        """
        Rotate log files if they exceed a certain size (e.g., 5MB or TIME).
        check for defined time or size limit and rotate accordingly.
        :return:
        """

        if not file_path.exists():
            return {"rotate": True}

        if ContextRegistry.get().get_settings().log_rotation_always_on:
            return {"rotate": True}

        # check for file size
        file_size = file_path.stat().st_size

        if file_size > self.rotation_size_limit:  # 5 MB size limit
            return {"rotate": True}

        if (
            datetime.fromtimestamp(file_path.stat().st_mtime).timestamp()
            + self.time_rotation_limit
            < datetime.now().timestamp()
        ):  # 24 hours time limit
            return {"rotate": True}
        return {"rotate": False}
