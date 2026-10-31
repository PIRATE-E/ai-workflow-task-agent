from collections.abc import Callable
from enum import Enum
from typing import TypedDict


class Command(str, Enum):
    # package manager or command to run the server
    NPX = "npx"
    UVX = "uvx"
    PIPX = "pipx"
    PIP = "pip"
    PYTHON = "python"


class ServerConfig(TypedDict):
    name: str
    command: Command
    # package: str   ## e.g ("@modelcontextprotocol/server-github@latest")  now package would be included in the args of that mcp.md
    args: list[str]
    env: dict[str, str]
    wrapper: Callable
    status: str | None  # e.g., "running", "stopped"
    pid: int | None  # Process ID if the server is running


MPC_TOOL_SERVER_MAPPING: dict[str, str] = {}  # key: tool_name, value: server_name
