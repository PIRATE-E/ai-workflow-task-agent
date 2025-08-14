"""
Debug Helper Functions for AI-Agent-Workflow Project

This module provides convenient wrapper functions to migrate from the old
socket_con.send_error() approach to the new structured JSON protocol.

Usage:
    # Instead of: settings.socket_con.send_error("[WARNING] Tool failed")
    # Use: debug_warning("AGENT_MODE • TOOL_EVALUATION", "Tool failed", {"tool_name": "GoogleSearch"})
    
    # Instead of: settings.socket_con.send_error(json_pickle_panel)
    # Use: debug_rich_panel(panel_object)
"""

from typing import Dict, Any, Optional
from rich.console import RenderableType

from src.config import settings
from src.utils.debug_message_protocol import DebugMessageSender, LogLevel


def _get_debug_sender() -> DebugMessageSender:
    """Get debug message sender - always returns a sender (with or without socket)"""
    socket_con = None
    if hasattr(settings, 'socket_con') and settings.socket_con:
        socket_con = settings.socket_con
    return DebugMessageSender(socket_con)


def debug_info(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None):
    """Send INFO level debug message"""
    sender = _get_debug_sender()
    sender.send_debug_message(heading, body, LogLevel.INFO, metadata)


def debug_warning(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None):
    """Send WARNING level debug message"""
    sender = _get_debug_sender()
    sender.send_debug_message(heading, body, LogLevel.WARNING, metadata)


def debug_error(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None):
    """Send ERROR level debug message"""
    sender = _get_debug_sender()
    sender.send_debug_message(heading, body, LogLevel.ERROR, metadata)


def debug_critical(heading: str, body: str, metadata: Optional[Dict[str, Any]] = None):
    """Send CRITICAL level debug message"""
    sender = _get_debug_sender()
    sender.send_debug_message(heading, body, LogLevel.CRITICAL, metadata)


def debug_tool_response(tool_name: str, status: str, response_summary: str, 
                       execution_time: float = 0.0, metadata: Optional[Dict[str, Any]] = None):
    """Send tool response information"""
    sender = _get_debug_sender()
    sender.send_tool_response(tool_name, status, response_summary, execution_time, metadata)


def debug_api_call(api_name: str, operation: str, status: str, 
                  duration: float = 0.0, metadata: Optional[Dict[str, Any]] = None):
    """Send API call information"""
    sender = _get_debug_sender()
    sender.send_api_call(api_name, operation, status, duration, metadata)


def debug_performance_warning(operation: str, duration: float, threshold: float, 
                             context: str, metadata: Optional[Dict[str, Any]] = None):
    """Send performance warning"""
    sender = _get_debug_sender()
    sender.send_performance_warning(operation, duration, threshold, context, metadata)


def debug_error_log(error_type: str, error_message: str, context: str,
                   traceback_summary: str = "", metadata: Optional[Dict[str, Any]] = None):
    """Send structured error log"""
    sender = _get_debug_sender()
    sender.send_error_log(error_type, error_message, context, traceback_summary, metadata)


def debug_rich_panel(panel: RenderableType):
    """Send Rich Panel object"""
    sender = _get_debug_sender()
    sender.send_rich_panel(panel)


def send_object_over_socket(obj: Any, obj_type: str = "object"):
    """
    Helper function to send any object over socket with proper handling
    
    Args:
        obj: The object to send (can be string, dict, Rich Panel, etc.)
        obj_type: Type identifier for the object
    """
    sender = _get_debug_sender()
    
    if hasattr(obj, '__rich__') or hasattr(obj, '__rich_console__'):
        # It's a Rich object - send as pickle
        sender.send_rich_panel(obj)
    elif isinstance(obj, dict):
        # It's a dictionary - send as structured debug message
        heading = obj.get('heading', 'OBJECT')
        body = obj.get('body', str(obj))
        level = obj.get('level', 'INFO')
        metadata = obj.get('metadata', {})
        sender.send_debug_message(heading, body, level, metadata)
    elif isinstance(obj, str):
        # It's a string - send as plain text
        sender.send_plain_text(obj)
    else:
        # Unknown object - send as plain text representation
        sender.send_plain_text(f"[{obj_type}] {str(obj)}")


def safe_socket_send(message: str):
    """
    Safe helper to send message over socket with proper error handling
    Ensures message is sent as individual transmission
    """
    try:
        if hasattr(settings, 'socket_con') and settings.socket_con and hasattr(settings.socket_con, 'send_error'):
            # Add message separator to prevent concatenation issues
            formatted_message = f"{message}\n"
            settings.socket_con.send_error(formatted_message)
        else:
            # Fallback to console if no socket connection
            print(f"DEBUG: {message}")
    except Exception as e:
        # Ultimate fallback
        print(f"DEBUG_FALLBACK: {message} (Error: {e})")


def debug_plain_text(text: str):
    """Send plain text message (for simple cases)"""
    sender = _get_debug_sender()
    sender.send_plain_text(text)


# Safe replacement for settings.socket_con.send_error calls
def safe_send_error(message: str):
    """Safe replacement for settings.socket_con.send_error that handles None socket_con"""
    try:
        if hasattr(settings, 'socket_con') and settings.socket_con and hasattr(settings.socket_con, 'send_error'):
            settings.socket_con.send_error(message)
        else:
            # Fallback to console if no socket connection
            print(f"DEBUG: {message}")
    except Exception as e:
        # Ultimate fallback
        print(f"DEBUG_FALLBACK: {message} (Error: {e})")


# Legacy compatibility functions for gradual migration
def send_debug_message_legacy(heading: str, body: str, level: str = "INFO", metadata: Dict[str, Any] = None):
    """Legacy compatibility function"""
    level_map = {
        "DEBUG": LogLevel.DEBUG,
        "INFO": LogLevel.INFO,
        "WARNING": LogLevel.WARNING,
        "ERROR": LogLevel.ERROR,
        "CRITICAL": LogLevel.CRITICAL
    }
    
    mapped_level = level_map.get(level.upper(), LogLevel.INFO)
    
    if mapped_level == LogLevel.INFO:
        debug_info(heading, body, metadata)
    elif mapped_level == LogLevel.WARNING:
        debug_warning(heading, body, metadata)
    elif mapped_level == LogLevel.ERROR:
        debug_error(heading, body, metadata)
    elif mapped_level == LogLevel.CRITICAL:
        debug_critical(heading, body, metadata)
    else:
        debug_info(heading, body, metadata)


# Global safe socket connection wrapper to prevent NoneType errors
class SafeSocketConnection:
    """Safe wrapper that prevents NoneType errors when accessing socket_con"""
    
    def send_error(self, message: str):
        """Safely send error message"""
        return safe_send_error(message)
    
    def _is_connected(self):
        """Check if socket is connected"""
        try:
            if hasattr(settings, 'socket_con') and settings.socket_con and settings.socket_con != self:
                if hasattr(settings.socket_con, '_is_connected'):
                    return settings.socket_con._is_connected()
                return True  # Assume connected if method doesn't exist
            return False
        except Exception:
            return False

# Create global safe socket instance
safe_socket_con = SafeSocketConnection()

# Function to ensure settings.socket_con is never None
def ensure_safe_socket_con():
    """Ensure settings.socket_con is never None by providing safe fallback"""
    try:
        if not hasattr(settings, 'socket_con') or settings.socket_con is None:
            settings.socket_con = safe_socket_con
    except Exception:
        pass

# Initialize safe socket connection
ensure_safe_socket_con()