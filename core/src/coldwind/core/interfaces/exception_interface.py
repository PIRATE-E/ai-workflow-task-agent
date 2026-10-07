from abc import ABC, abstractmethod
from typing import Any, Optional


class ExceptionHandlerInterface(ABC):
    """
    Contract for global exception handling and formatting.
    
    This replaces direct imports of Desktop's RichTracebackManager.
    Implementations are responsible for presenting the traceback in a 
    platform-appropriate way (e.g., Rich panels or JSON logs).
    """

    @abstractmethod
    def handle_exception(self, error: Exception, context: str = "", extra_context: Optional[dict[str, Any]] = None) -> None:
        """
        Handle and format an exception.
        
        Args:
            error: The exception instance caught.
            context: A brief description of what was happening when the error occurred.
            extra_context: Additional metadata useful for debugging.
        """
        pass


def exception_handler(context_name: str):
    """
    WHAT: Decorator wrapping functions with platform-agnostic exception handling.
    WHY: Decouples Core callers from concrete Desktop RichTracebackManager, enforcing
    the Layering Invariant ('Core NEVER imports Desktop'). Resolves active exception
    handler dynamically through ContextRegistry.get().get_error_handler().
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
                try:
                    ContextRegistry.get().get_error_handler().handle_exception(
                        e,
                        context=context_name,
                        extra_context={
                            "wrapped_function": getattr(func, "__name__", "unknown"),
                            "module": getattr(func, "__module__", "unknown"),
                        },
                    )
                except Exception:
                    pass
                raise
        wrapper.__name__ = getattr(func, "__name__", "wrapped")
        return wrapper
    return decorator


# WHAT: Backward compatibility alias for existing core call sites.
# WHY: Allows seamless transition from desktop's rich_exception_handler to core contract.
rich_exception_handler = exception_handler

