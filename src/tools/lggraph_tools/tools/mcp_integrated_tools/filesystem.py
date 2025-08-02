import os

from src.config import settings
from src.mcp.manager import MCP_Manager


def file_system_tool(file_path: str, action:str) -> str:
    """
    Read the content of a file using the MCP server.
    :param file_path: Path to the file to read.
    :param action: Action to perform, e.g., "read_file".
    :return: Content of the file as a string.
    """
    if not file_path:
        raise ValueError("File path cannot be empty.")

    MCP_Manager.add_server("filesystem", "npx", "@modelcontextprotocol/server-filesystem@latest", ["--path", "."])
    MCP_Manager.start_server("filesystem")
    response = MCP_Manager.call_mcp_server("filesystem", f"{action}",
                                           {"path": file_path if os.path.exists(file_path) else f"{settings.BASE_DIR / 'RAG' / 'RAG_FILES' / 'tech.txt'}"})
    return response
