import json
import os
from typing import Any

from src.config import settings
from src.mcp.manager import MCP_Manager


def file_system_tool(file_path: str, action: str) -> str | dict | list[dict[str, Any]]:
    """
    Perform filesystem operations using MCP server.
    :param file_path: Path to the file to operate on.
    :param action: Action to perform (read_file, write_file, delete_file).
    :return: Result content as string, or error message.
    """
    if not file_path:
        return "Error: File path cannot be empty"

    try:
        # Add and start MCP server if needed
        MCP_Manager.add_server("filesystem", "npx", "@modelcontextprotocol/server-filesystem", ["."])
        
        if not MCP_Manager.start_server("filesystem"):
            return "Error: Failed to start MCP filesystem server"
        
        # Use provided path or fallback to tech.txt
        target_path = file_path if os.path.exists(file_path) else str(settings.BASE_DIR / 'RAG' / 'RAG_FILES' / 'tech.txt')
        
        # Call MCP server with structured response
        response = MCP_Manager.call_mcp_server("filesystem", action, {"path": target_path})
        
        if response is None:
            return "Error: No response from MCP server"
        
        if response.get("success"):
            # Extract the actual content from the structured response
            data = response.get("data")
            settings.socket_con.send_error(f"\tResponse from MCP server: \n{data}")  # Log the response for debugging
            return data['content'] if isinstance(data, dict) and 'content' in data else "No content returned"
        else:
            # Handle error response
            error_msg = response.get("error", "Unknown error occurred")
            settings.socket_con.send_error(f"\tError from MCP server: {error_msg}")
            return response
            
    except Exception as e:
        return f"Error: Exception in filesystem tool: {str(e)}"
