from src.config import settings
from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
from src.tools.lggraph_tools.tools.mcp_integrated_tools import filesystem

class FileSystemWrapper:
    """
    Wrapper class for filesystem operations using MCP server.
    Follows the same pattern as GoogleSearchToolWrapper and TranslateToolWrapper.
    """

    def __init__(self, file_path: str, action: str = "read_file"):
        """
        Initialize the FileSystemWrapper with a file path and action.

        :param file_path: The path to the file to operate on.
        :param action: The action to perform (read_file, write_file, delete_file).
        """
        self.file_path = file_path
        self.action = action

        # Call the filesystem tool
        result = filesystem.file_system_tool(self.file_path, action)

        if result and not result.startswith("Error:"):
            # Success - set the response
            ToolResponseManager().set_response([
                settings.AIMessage(content=f"MCP Filesystem Result:\n{result}")
            ])
        else:
            # Error or no result
            error_msg = result if result else "Unknown error occurred"
            ToolResponseManager().set_response([
                settings.AIMessage(content=f"Filesystem operation failed: {error_msg}")
            ])
