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
