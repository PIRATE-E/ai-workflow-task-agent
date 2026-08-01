"""mcp_manager_util.py

Utility module for MCP (Model Context Protocol) Manager operations.

This module provides utility classes that extend the base MCP_Manager functionality
with additional features like timeout handling, async execution wrappers, and
enhanced error recovery mechanisms.

Features:
    - Async wrapper for server startup with timeout control
    - Enhanced exception handling for MCP server operations
    - Thread-safe server initialization patterns

Classes:
    Utils: Utility class extending MCP_Manager with timeout and async capabilities
"""

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.mcp.manager import MCP_Manager
import asyncio




class Utils(MCP_Manager):
    """Utility class for MCP Manager providing enhanced async operations and timeout handling.

    This class extends MCP_Manager to provide wrapper methods with better exception
    handling, timeout controls, and async execution patterns. It's designed to make
    MCP server management more robust and predictable.

    Attributes:
        Inherits all attributes from MCP_Manager parent class.

    Methods:
        start_server_async_with_timeout: Async wrapper for starting MCP servers with timeout

    Notes:
        This class uses classmethod decorators to allow usage without instantiation
        while maintaining proper inheritance from MCP_Manager.

    Warning:
        Timeout errors are logged but not re-raised, which may mask failures.
        Calling code should check server status independently.
    """

    def __init__(self):
        """Initialize the Utils instance by calling parent MCP_Manager constructor.

        This constructor ensures proper initialization chain through the MCP_Manager
        parent class, maintaining all required state and configuration.

        Args:
            None

        Returns:
            None

        Raises:
            Any exceptions from parent MCP_Manager.__init__()
        """
        super().__init__()

    @classmethod
    async def start_server_async_with_timeout(cls, name: str, time: int):
        """Start an MCP server asynchronously with a configurable timeout.

        This method wraps the synchronous start_server method in an async context
        with timeout protection. It runs the server startup in a separate thread
        to avoid blocking the async event loop, and enforces a maximum wait time.

        Args:
            name (str): The name/identifier of the MCP server to start. Must match
                a server registered in MCP_Manager.mcp_servers dictionary.
            time (int): Maximum time in seconds to wait for server startup. If the
                server doesn't complete initialization within this time, a timeout
                error is triggered.

        Returns:
            bool: True if the server started successfully within the timeout, False
                if a timeout occurred.

        Raises:
            asyncio.TimeoutError: When server startup exceeds the specified timeout.
                Note: This exception is caught internally and logged, not re-raised.

        Notes:
            - Uses asyncio.to_thread() to run blocking start_server in thread pool
            - Timeout is enforced via asyncio.wait_for() wrapper
            - Server startup includes process spawning, stdio pipe setup, and
              initial handshake which can be time-consuming
            - Typical startup time varies: npx servers 15-30s, uvx servers 5-10s

        Warning:
            This method catches and logs TimeoutError but does NOT re-raise it.
            Callers using asyncio.gather() may not detect failures unless they
            inspect individual task results with return_exceptions=True.

        Examples:
            >>> await Utils.start_server_async_with_timeout("github", 30)
            >>> # Server starts in background, logs on timeout
        """
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(super().start_server, name), timeout=time
            )
        except asyncio.TimeoutError:
            ContextRegistry.get().get_logger().log_error(
                f"MCP * START ERROR",
                f"Server '{name}' failed to start within {time} seconds.",
            )
            return False
