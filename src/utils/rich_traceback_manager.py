# 🎨 Rich Traceback Manager - Comprehensive Error Handling System
"""
Rich Traceback Manager for AI-Agent-Workflow Project

This module provides centralized rich traceback functionality across the entire application.
It enhances error handling with beautiful, informative tracebacks that show:
- Exact line numbers and file locations
- Variable values at the time of error
- Call stack with context
- Syntax highlighting for better readability
- Integration with socket logging system

Usage:
    from src.utils.rich_traceback_manager import RichTracebackManager
    
    # Initialize at application start
    RichTracebackManager.initialize()
    
    # Use in try-catch blocks
    try:
        risky_operation()
    except Exception as e:
        RichTracebackManager.handle_exception(e, context="Operation description")
"""

import sys
import traceback
from typing import Optional, Dict, Any, Callable
from rich.console import Console
from rich.traceback import install, Traceback
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich import print as rich_print
import inspect
import os
from datetime import datetime

# Import settings for socket integration
from src.config import settings


class RichTracebackManager:
    """
    Centralized Rich Traceback Manager for enhanced error handling across the application.
    
    Features:
    - Beautiful, informative tracebacks with syntax highlighting
    - Integration with socket logging system
    - Context-aware error reporting
    - Variable inspection at error points
    - Automatic error categorization
    - Performance impact tracking
    """
    
    _initialized = False
    _console: Optional[Console] = None
    _error_count = 0
    _error_categories: Dict[str, int] = {}
    
    @classmethod
    def initialize(cls, 
                   show_locals: bool = True,
                   max_frames: int = 20,
                   theme: str = "monokai",
                   width: Optional[int] = None,
                   extra_lines: int = 3,
                   word_wrap: bool = False,
                   indent_guides: bool = True,
                   suppress_modules: Optional[list] = None) -> None:
        """
        Initialize Rich Traceback system with comprehensive configuration.
        
        Args:
            show_locals: Show local variables in traceback
            max_frames: Maximum number of frames to show
            theme: Syntax highlighting theme
            width: Console width (None for auto)
            extra_lines: Extra lines of context around error
            word_wrap: Enable word wrapping
            indent_guides: Show indent guides
            suppress_modules: List of modules to suppress in traceback
        """
        if cls._initialized:
            return
            
        # Create console instance
        cls._console = Console(
            width=width,
            force_terminal=True,
            color_system="auto"
        )
        
        # Set up default suppressed modules
        if suppress_modules is None:
            suppress_modules = [
                "click",
                "rich",
                "__main__",
                "runpy",
                "threading",
                "concurrent.futures",
                "asyncio"
            ]
        
        # Install rich traceback globally
        install(
            console=cls._console,
            show_locals=show_locals,
            max_frames=max_frames,
            width=width,
            extra_lines=extra_lines,
            word_wrap=word_wrap,
            indent_guides=indent_guides,
            suppress=suppress_modules
        )
        
        # Set up exception hook for uncaught exceptions
        sys.excepthook = cls._global_exception_handler
        
        cls._initialized = True
        
        # Log initialization
        if settings.socket_con:
            settings.socket_con.send_error("🎨 Rich Traceback Manager initialized successfully")
        else:
            print("🎨 Rich Traceback Manager initialized successfully")
    
    @classmethod
    def _global_exception_handler(cls, exc_type, exc_value, exc_traceback):
        """
        Global exception handler for uncaught exceptions.
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle Ctrl+C gracefully
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        cls.handle_exception(
            exc_value, 
            context="Uncaught Exception",
            exc_type=exc_type,
            exc_traceback=exc_traceback
        )
    
    @classmethod
    def handle_exception(cls, 
                        exception: Exception,
                        context: str = "Unknown Context",
                        exc_type: Optional[type] = None,
                        exc_traceback: Optional[Any] = None,
                        show_locals: bool = True,
                        extra_context: Optional[Dict[str, Any]] = None) -> None:
        """
        Handle and display exception with rich formatting.
        
        Args:
            exception: The exception that occurred
            context: Description of what was happening when error occurred
            exc_type: Exception type (auto-detected if None)
            exc_traceback: Exception traceback (auto-detected if None)
            show_locals: Whether to show local variables
            extra_context: Additional context information to display
        """
        if not cls._initialized:
            cls.initialize()
        
        # Auto-detect exception info if not provided
        if exc_type is None or exc_traceback is None:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            if exc_value is None:
                exc_value = exception
        
        # Increment error tracking
        cls._error_count += 1
        error_category = exc_type.__name__ if exc_type else type(exception).__name__
        cls._error_categories[error_category] = cls._error_categories.get(error_category, 0) + 1
        
        # Create rich traceback
        if exc_traceback:
            rich_traceback = Traceback.from_exception(
                exc_type,
                exception,
                exc_traceback,
                show_locals=show_locals
            )
        else:
            # Fallback for cases where traceback is not available
            rich_traceback = Traceback(
                trace=traceback.extract_tb(sys.exc_info()[2]) if sys.exc_info()[2] else [],
                exc_type=exc_type.__name__ if exc_type else type(exception).__name__,
                exc_value=str(exception),
                show_locals=show_locals
            )
        
        # Create error panel with context
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build context information
        context_info = [
            f"🕒 Time: {timestamp}",
            f"📍 Context: {context}",
            f"🔢 Error #{cls._error_count}",
            f"📊 Category: {error_category}"
        ]
        
        # Add extra context if provided
        if extra_context:
            context_info.append("📋 Additional Context:")
            for key, value in extra_context.items():
                context_info.append(f"   • {key}: {value}")
        
        # Add caller information
        caller_info = cls._get_caller_info()
        if caller_info:
            context_info.extend([
                "📞 Called from:",
                f"   • File: {caller_info['file']}",
                f"   • Function: {caller_info['function']}",
                f"   • Line: {caller_info['line']}"
            ])
        
        context_text = "\n".join(context_info)
        
        # Create the error panel
        error_panel = Panel(
            rich_traceback,
            title=f"🚨 {error_category}: {str(exception)[:100]}{'...' if len(str(exception)) > 100 else ''}",
            subtitle=context_text,
            border_style="red",
            padding=(1, 2)
        )
        
        # Display the error
        if cls._console:
            cls._console.print(error_panel)
        else:
            rich_print(error_panel)
        
        # Send to socket logging if available
        if settings.socket_con:
            try:
                # Create a simplified version for socket logging
                socket_message = f"""
🚨 ERROR OCCURRED 🚨
Time: {timestamp}
Context: {context}
Error: {error_category}: {str(exception)}
File: {caller_info['file'] if caller_info else 'Unknown'}
Line: {caller_info['line'] if caller_info else 'Unknown'}
Function: {caller_info['function'] if caller_info else 'Unknown'}
Total Errors: {cls._error_count}
"""
                settings.socket_con.send_error(socket_message)
            except Exception as socket_error:
                print(f"Failed to send error to socket: {socket_error}")
    
    @classmethod
    def _get_caller_info(cls) -> Optional[Dict[str, str]]:
        """
        Get information about the caller that triggered the exception.
        """
        try:
            # Get the current frame
            frame = inspect.currentframe()
            if frame is None:
                return None
            
            # Go up the call stack to find the actual caller
            # Skip our own frames and rich/traceback frames
            while frame:
                frame = frame.f_back
                if frame is None:
                    break
                    
                filename = frame.f_code.co_filename
                function_name = frame.f_code.co_name
                line_number = frame.f_lineno
                
                # Skip internal frames
                if any(skip in filename for skip in ['rich', 'traceback', __file__]):
                    continue
                
                # Skip if it's in site-packages (external libraries)
                if 'site-packages' in filename:
                    continue
                
                return {
                    'file': os.path.basename(filename),
                    'function': function_name,
                    'line': str(line_number),
                    'full_path': filename
                }
            
            return None
        except Exception:
            return None
    
    @classmethod
    def create_context_decorator(cls, context_name: str):
        """
        Create a decorator that automatically adds context to exceptions.
        
        Args:
            context_name: Name of the context for error reporting
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Get function signature for additional context
                    sig = inspect.signature(func)
                    bound_args = sig.bind(*args, **kwargs)
                    bound_args.apply_defaults()
                    
                    extra_context = {
                        'function': func.__name__,
                        'module': func.__module__,
                        'arguments': {k: str(v)[:100] for k, v in bound_args.arguments.items()}
                    }
                    
                    cls.handle_exception(
                        e, 
                        context=f"{context_name} -> {func.__name__}",
                        extra_context=extra_context
                    )
                    raise  # Re-raise the exception
            return wrapper
        return decorator
    
    @classmethod
    def log_performance_warning(cls, operation: str, duration: float, threshold: float = 1.0):
        """
        Log performance warnings with rich formatting.
        
        Args:
            operation: Description of the operation
            duration: Time taken in seconds
            threshold: Warning threshold in seconds
        """
        if duration > threshold:
            warning_panel = Panel(
                f"⚠️ Performance Warning\n\n"
                f"Operation: {operation}\n"
                f"Duration: {duration:.2f}s\n"
                f"Threshold: {threshold:.2f}s\n"
                f"Exceeded by: {duration - threshold:.2f}s",
                title="🐌 Slow Operation Detected",
                border_style="yellow"
            )
            
            if cls._console:
                cls._console.print(warning_panel)
            
            if settings.socket_con:
                settings.socket_con.send_error(
                    f"⚠️ PERFORMANCE WARNING: {operation} took {duration:.2f}s (threshold: {threshold:.2f}s)"
                )
    
    @classmethod
    def get_error_statistics(cls) -> Dict[str, Any]:
        """
        Get error statistics for debugging and monitoring.
        
        Returns:
            Dictionary with error statistics
        """
        return {
            'total_errors': cls._error_count,
            'error_categories': cls._error_categories.copy(),
            'most_common_error': max(cls._error_categories.items(), key=lambda x: x[1])[0] if cls._error_categories else None,
            'initialized': cls._initialized
        }
    
    @classmethod
    def reset_statistics(cls):
        """
        Reset error statistics (useful for testing or periodic resets).
        """
        cls._error_count = 0
        cls._error_categories.clear()
        
        if settings.socket_con:
            settings.socket_con.send_error("📊 Error statistics reset")
    
    @classmethod
    def create_safe_wrapper(cls, func: Callable, context: str, default_return=None):
        """
        Create a safe wrapper that catches exceptions and returns a default value.
        
        Args:
            func: Function to wrap
            context: Context description for error reporting
            default_return: Value to return if exception occurs
            
        Returns:
            Wrapped function
        """
        def safe_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                cls.handle_exception(e, context=f"Safe Wrapper: {context}")
                return default_return
        return safe_func


# Convenience functions for common use cases
def rich_exception_handler(context: str = "Unknown Context"):
    """
    Decorator for automatic rich exception handling.
    
    Usage:
        @rich_exception_handler("Database Operation")
        def risky_database_operation():
            # Your code here
            pass
    """
    return RichTracebackManager.create_context_decorator(context)


def safe_execute(func: Callable, context: str, default_return=None, *args, **kwargs):
    """
    Safely execute a function with rich error handling.
    
    Args:
        func: Function to execute
        context: Context description
        default_return: Value to return on error
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        RichTracebackManager.handle_exception(e, context=context)
        return default_return


# Initialize on import if not already done
if not RichTracebackManager._initialized:
    RichTracebackManager.initialize()