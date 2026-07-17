def universal_tool(**kwargs):
    """
    Universal tool for interacting with any MCP server.

    This function allows you to call any MCP server with the provided parameters.
    It abstracts the details of the MCP server interaction, making it easy to use.

    :param kwargs: Dynamic parameters that vary by MCP tool
    :return: Result from the specific MCP tool operation
    """
    from coldwind.core.mcp.manager import MCP_Manager
    from coldwind.desktop.ui.diagnostics.debug_helpers import (
        debug_info,
        debug_critical,
        debug_warning,
    )
    from coldwind.core.mcp.mcp_register_structure import MPC_TOOL_SERVER_MAPPING

    # 🔧 FIX: Enhanced tool_name extraction with validation
    tool_name = kwargs.pop("tool_name", None)

    # Critical validation: tool_name must be provided
    if not tool_name or tool_name == "unknown tool":
        debug_critical(
            heading="MCP_UNIVERSAL • MISSING_TOOL_NAME",
            body="No valid tool_name provided - this will cause MCP server errors",
            metadata={
                "provided_tool_name": tool_name,
                "kwargs_keys": list(kwargs.keys()),
                "error_prevention": "returning_error_immediately",
            },
        )
        return {
            "success": False,
            "error": f"Invalid tool_name: '{tool_name}'. Tool name is required for MCP operations.",
            "available_tools": list(MPC_TOOL_SERVER_MAPPING.keys())[
                :10
            ],  # Show first 10 for reference
        }

    arguments = kwargs

    # Use dynamic tool-to-server mapping (populated by tool_discovery during startup)
    server_name = MPC_TOOL_SERVER_MAPPING.get(tool_name)

    if not server_name:
        # Tool not found in any discovered server
        available_tools = list(MPC_TOOL_SERVER_MAPPING.keys())[:20]  # Show first 20
        debug_warning(
            heading="MCP_UNIVERSAL • TOOL_NOT_FOUND",
            body=f"Tool '{tool_name}' not found in any running server",
            metadata={
                "tool_name": tool_name,
                "running_servers": list(MCP_Manager.running_servers.keys()),
                "available_tools_count": len(MPC_TOOL_SERVER_MAPPING),
            },
        )
        return {
            "success": False,
            "error": f"Tool '{tool_name}' not found. Server may have failed to start or tool discovery failed.",
            "available_tools": available_tools,
            "running_servers": list(MCP_Manager.running_servers.keys()),
        }

    debug_info(
        heading="MCP_UNIVERSAL • TOOL_ROUTING",
        body=f"Routing tool '{tool_name}' to server '{server_name}'",
        metadata={
            "tool_name": tool_name,
            "server_name": server_name,
        },
    )

    # 🔧 FIX: Enhanced error handling for MCP server calls
    try:
        response = MCP_Manager.call_mcp_server(server_name, tool_name, arguments)
    except Exception as call_error:
        debug_critical(
            heading="MCP_UNIVERSAL • SERVER_CALL_EXCEPTION",
            body=f"Exception calling MCP server: {call_error}",
            metadata={
                "tool_name": tool_name,
                "server_name": server_name,
                "error_type": type(call_error).__name__,
                "arguments": str(arguments)[:200],
            },
        )
        return {
            "success": False,
            "error": f"Server call failed: {str(call_error)}",
            "server": server_name,
            "tool": tool_name,
        }

    if response is None:
        debug_critical(
            heading="MCP_UNIVERSAL • ERROR",
            body="No response from MCP server",
            metadata={
                "tool_name": tool_name,
                "server_name": server_name,
                "arguments": arguments,
            },
        )
        return {"success": False, "error": "No response from MCP server"}

    if response.get("success"):
        # Extract the actual content from the structured response
        data = response.get("data")
        # handle for uri type response
        if isinstance(data, dict) and data.get('method') == 'notifications/resources/updated':
            uri = data.get('params', {}).get('uri')
            if uri:
                # now it is confirmed that it is uri ##
                debug_info(
                    heading="MCP_UNIVERSAL • URI_DETECTED",
                    body=f"URI detected in MCP response: {uri}",
                    metadata={
                        "tool_name": tool_name,
                        "server_name": server_name,
                    },
                )
                resolved_uri = MCP_Manager.read_uri_resource(server_name, uri).get('data', None)
                if resolved_uri:
                    return resolved_uri
                else:
                    return {"success": False, "error": f"Failed to resolve URI: {uri}"}
            pass
        debug_info(
            heading="MCP_UNIVERSAL • SUCCESS",
            body="Response received from MCP server",
            metadata={
                "tool_name": tool_name,
                "server_name": server_name,
                "data_type": type(data).__name__,
                "has_content": "content" in data if isinstance(data, dict) else False,
            },
        )
        return data["content"] if isinstance(data, dict) and "content" in data else data
    else:
        # Handle error response
        error_msg = response.get("error", "Unknown error occurred")
        debug_info(
            heading="MCP_UNIVERSAL • ERROR",
            body=f"Error from MCP server: {error_msg}",
            metadata={
                "tool_name": tool_name,
                "server_name": server_name,
                "error_message": error_msg,
            },
        )
        return response
