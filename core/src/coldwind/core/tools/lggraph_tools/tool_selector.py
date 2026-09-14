"""
Tool Selector & Execution Module for LangGraph Tools.

WHAT CHANGED:
- Completely purged legacy `socket` parameter and raw `socket.send_error` calls.
- Unified all event and diagnostic reporting through `ContextRegistry.get().get_logger()`.
- Preserved strict dictionary validation, parameter normalization, and tool invocation.
- User-facing tool results route through `context.get_message_display().display_message()`.

WHY:
- In the refactored architecture, `DashBoardHandler` automatically serializes structured
  `LogEntry` objects and ships them over IPC to the dashboard window. Direct `socket.send_error`
  calls were obsolete artifacts from the pre-workspace codebase that bypassed the logging pipeline.
"""

from typing import Any
import inspect

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.runtime.runtime_obj_enum import CoreRunTimeObjects
from coldwind.core.tools.lggraph_tools.tool_response_manager import ToolResponseManager
from coldwind.core.utils.model_manager import ModelManager


def execute_selected_tool(
    selection: Any,
    tools: list,
    parameters: dict | Any,
) -> dict:
    """
    Executes the chosen tool safely with strict parameter validation and structured logging.

    :param selection: ToolSelection dataclass containing tool_name and reasoning.
    :param tools: List of available LangChain tools.
    :param parameters: Tool parameters extracted from the LLM or user message.
    :return: State dictionary containing the resulting AIMessage.
    """
    context = ContextRegistry.get()
    logger = context.get_logger()
    _HumanMessage, AIMessage, _BaseMessage = context.get_service(
        CoreRunTimeObjects.message_classes
    )

    # 1. Guard against empty or 'none' tool selections
    if not selection or not getattr(selection, "tool_name", None) or selection.tool_name.lower() == "none":
        return {"messages": [AIMessage(content="No tool was used.")]}

    # 2. Defensively convert stringified parameters into a dictionary
    if isinstance(parameters, str):
        try:
            parameters = ModelManager.convert_to_json(parameters)
        except Exception as err:
            logger.log_error(
                heading="TOOL_SELECTOR - PARSE_ERROR",
                body=f"Failed to parse string parameters into JSON dictionary: {err}",
                metadata={"raw_parameters": parameters, "error": str(err)},
            )
            parameters = {}

    # 3. Locate matching tool in registered tool list
    for tool in tools:
        if tool.name.lower() == selection.tool_name.lower():
            try:
                # 4. Validate that parameters is a dictionary; recover if malformed
                if not isinstance(parameters, dict):
                    logger.log_warning(
                        heading="TOOL_SELECTOR - INVALID_PARAMETERS",
                        body=f"Expected parameters as dict, got {type(parameters).__name__}; creating empty dict fallback.",
                        metadata={
                            "tool_name": tool.name,
                            "parameters_type": type(parameters).__name__,
                            "fallback_action": "creating_empty_dict",
                        },
                    )
                    parameters = {}

                # 5. Ensure tool_name is explicitly included in parameters for schema compliance
                parameters["tool_name"] = tool.name

                logger.log_info(
                    heading="TOOL_SELECTOR - TOOL_EXECUTION",
                    body=f"Executing tool '{tool.name}' with validated parameters.",
                    metadata={
                        "tool_name": tool.name,
                        "parameter_count": len(parameters),
                        "has_tool_name": "tool_name" in parameters,
                        "context": "tool_selector_execution",
                    },
                )

                # 6. Invoke tool and capture the response
                tool.invoke(parameters)
                result = ToolResponseManager().get_response()[-1].content

                # 7. Route user-facing output through MessageDisplayInterface (no desktop UI imports)
                context.get_message_display().display_message("tool", result)

                return {
                    "messages": [
                        AIMessage(content=f"Result from {tool.name}: {result}"),
                    ],
                }

            except Exception as e:
                logger.log_error(
                    heading="TOOL_SELECTOR - EXECUTION_ERROR",
                    body=f"Error executing tool '{tool.name}': {e}",
                    metadata={
                        "tool_name": tool.name,
                        "error": str(e),
                        "func": getattr(tool, "func", None).__name__ if hasattr(tool, "func") else "unknown",
                        "trace": inspect.trace(),
                    },
                )
                return {
                    "messages": [
                        AIMessage(content=f"Error using {tool.name}: {e!s}"),
                    ],
                }

    # 8. Handle unknown or unregistered tool name
    logger.log_warning(
        heading="TOOL_SELECTOR - TOOL_NOT_FOUND",
        body=f"Tool '{selection.tool_name}' was selected but not found in registered tool list.",
        metadata={"tool_name": selection.tool_name},
    )

    return {
        "messages": [
            AIMessage(content=f"Tool '{selection.tool_name}' not found."),
        ],
    }


# Convenience alias matching original naming pattern
execute_tool = execute_selected_tool