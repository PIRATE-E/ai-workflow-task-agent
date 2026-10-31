from typing import override

from coldwind.core.system_logging.debug_protocol import LogEntry
from coldwind.core.system_logging.handlers.handler_base import Handler

"""
this is core details

current platform would be handle the events or logs using the rust 
this is handle implmentation and contract it would handle all the events and logs 

but those would be piped to the rust object !! the rest of the handling is designed in the rust 

"""


class RustGuiEventHandler(Handler):
    """
    handle method would be replaced at run time from the rust
    injected rust internal private method
    on the running instance of RustGuiEventHandler's slots as descriptor
    using FFI Cpython's PyCfunction closure
    """

    name: str = "RustGuiEventHandler"

    @override
    def should_handle(self, log_entry: LogEntry, *args):
        return True

    @override
    def handle(self, log_entry: LogEntry, *args):
        raise NotImplementedError
