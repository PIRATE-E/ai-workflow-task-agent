"""
this is base class for system_logging handlers
===========================================================
handlers are responsible for processing log entries and directing them to appropriate destinations (e.g., console, file, external services).
"""
import os
from abc import ABC, abstractmethod
from typing import Dict, TextIO

from ..protocol import LogEntry


class Handler(ABC):
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
        return not args or not args[0].get('force_stop', False)

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
            # Create log files in src/basic_logs/ directory with absolute path
            from src.config import settings

            log_dir = settings.BASE_DIR / "basic_logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = log_dir / f"log_{file_name.value}.txt"

            # Open with UTF-8 encoding to support emojis and international characters
            TextHandler.writers[file_name.value] = open(log_file_path, 'w', 1, encoding='utf-8')
            TextHandler.writers[file_name.value].flush()

        from ..formater import TextFormater
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
