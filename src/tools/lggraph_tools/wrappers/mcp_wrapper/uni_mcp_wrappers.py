"""
Universal MCP Wrapper

This module provides a universal wrapper for Modular Control Platform (MCP) servers.
It allows seamless integration with any MCP server, regardless of the specific tools or APIs provided.
By using this wrapper, developers can avoid creating and maintaining separate wrappers for each unique MCP server implementation.
"""

class UniversalMCPWrapper:
    """
    Universal wrapper for MCP servers.
    This class allows interaction with any MCP server without needing to create specific wrappers for each server.
    """

    def __init__(self, **kwargs):
        from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
        from src.tools.lggraph_tools.tools.mcp_integrated_tools.universal import universal_tool
        from src.config import settings
        self.server_url = kwargs.get('server_url', None)
        self.action = kwargs.get('tool_name', None)
        self.params = kwargs.get('params', {})

        # Call the MCP server with the provided parameters
        result = universal_tool(**kwargs)

        # Safe debug logging
        from src.ui.diagnostics.debug_helpers import debug_info
        debug_info(
            heading="MCP_WRAPPER • UNIVERSAL",
            body=f"MCP server result received",
            metadata={
                "result_preview": str(result),
                "result_type": type(result).__name__
            }
        )

        # Handle the result and create appropriate AI message
        if result and not str(result).startswith("Error:"):
            content = f"✅ **Action '{self.action}' completed successfully.**\n\nResult: {result}"
            ToolResponseManager().set_response([
                settings.AIMessage(content=content)
            ])
        else:
            error_msg = result if result else "Unknown error occurred"
            ToolResponseManager().set_response([
                settings.AIMessage(content=f"❌ **Error:** {error_msg}")
            ])