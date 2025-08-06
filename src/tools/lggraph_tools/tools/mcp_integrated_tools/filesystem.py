
from typing import Any

from src.config import settings
from src.mcp.manager import MCP_Manager


def file_system_tool(**kwargs) -> str | dict | list[dict[str, Any]]:
    """
    Universal MCP filesystem tool that handles all MCP operations dynamically.

    This function automatically detects which MCP tool to call based on the
    tool name stored in the ToolAssign instance, then routes parameters accordingly.

    :param kwargs: Dynamic parameters that vary by MCP tool
    :return: Result from the specific MCP tool operation
    """

    try:
        # Call MCP server with structured response
        settings.socket_con.send_error(f"\tCalling MCP server with parameters: {kwargs}")

        tool_name = kwargs.pop('tool_name', 'unknown tool')  # Extract tool name from kwargs
        arguments = kwargs
        response = MCP_Manager.call_mcp_server("filesystem", tool_name, arguments)
        settings.socket_con.send_error('kwargs: ' + str(kwargs))  # Log the parameters for debugging
        
        if response is None:
            return "Error: No response from MCP server"
        
        if response.get("success"):
            # Extract the actual content from the structured response
            data = response.get("data")
            # settings.socket_con.send_error(f"\tResponse from MCP server: \n{data}")  # Log the response for debugging
            return data['content'] if isinstance(data, dict) and 'content' in data else "No content returned"
        else:
            # Handle error response
            error_msg = response.get("error", "Unknown error occurred")
            settings.socket_con.send_error(f"\tError from MCP server: {error_msg}")
            return response
            
    except Exception as e:
        return f"Error: Exception in filesystem tool: {str(e)}"
