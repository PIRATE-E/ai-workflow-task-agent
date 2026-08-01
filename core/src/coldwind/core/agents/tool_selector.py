import inspect
from dataclasses import dataclass
from typing import Any

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.runtime.runtime_obj_enum import CoreRunTimeObjects
from coldwind.core.prompts.system_prompt_tool_selector import get_tool_selector_prompt
from coldwind.core.tools.lggraph_tools.tool_assign import ToolAssign
from coldwind.desktop.ui.print_message_style import print_message
from coldwind.core.utils.argument_schema_util import get_tool_argument_schema
from coldwind.core.utils.model_manager import ModelManager


@dataclass
class ToolSelection:
    tool_name: str
    reasoning: str = ""
    parameters: dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


def tool_selection_agent(state) -> dict:
    """Selects and invokes the most appropriate tool for the user's request, or returns a message if no tool is needed."""
    # Grab the runtime handles once — console, socket, and the langchain message
    # bundle all live on the active RuntimeContextInterface now (no settings.*).
    context = ContextRegistry.get()
    console = context.get_console()
    socket = context.get_socket_connection()
    HumanMessage, AIMessage, _BaseMessage = context.get_service(
        CoreRunTimeObjects.message_classes
    )
    console.print("\t\t----[bold][green]Node is tool_agent[/bold][/green]")

    # Access state directly from LangGraph parameter (no sync needed)
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    content = last_message.content if last_message else ""
    history = messages
    tools = ToolAssign.get_tools_list()

    tools_context = (
        "\n\n".join(
            [
                f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {get_tool_argument_schema(tool)}"
                for tool in tools
            ],
        )
        if tools
        else (
            socket.send_error("[ERROR] No tools available for selection.")
            if socket
            else print("[ERROR] No tools available for selection.")
        )
    )

    # Use the centralized tool selector prompt
    system_prompt = get_tool_selector_prompt(
        tools_context=tools_context,
        history=history,
        content=content,
    )

    try:
        llm = ModelManager(
            model=ContextRegistry.get().get_settings().gpt_model,
            temperature=0.3,  # Lower temperature for more consistent tool selection
            stream=False,
            max_tokens=1000,  # Allow enough tokens for reasoning and parameters
            top_p=1.0,  # Focus on most likely tokens for better accuracy
        )

        # Add JSON format instruction to system prompt
        enhanced_system_prompt = system_prompt + """

**IMPORTANT:** Respond with valid JSON in this exact format:
{
    "tool_name": "selected_tool_name_or_none",
    "reasoning": "Your reasoning for this selection",
    "parameters": {"param1": "value1", "param2": "value2"}
}

If no tool is needed, use "none" as the tool_name and empty object {} for parameters."""

        with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
            response = llm.invoke(
                [
                    HumanMessage(content=enhanced_system_prompt),
                    HumanMessage(content=content),
                ],
            )

        # Use the new JSON conversion method
        selection_json = ModelManager.convert_to_json(response)

        # Create ToolSelection object from JSON
        # (dataclass + Any imported at module top — preemptively hoisted to fix
        # the pre-existing NameError where @dataclass was referenced before import.)

        selection = ToolSelection(
            tool_name=selection_json.get("tool_name", "none"),
            reasoning=selection_json.get("reasoning", ""),
            parameters=selection_json.get("parameters", {}),
        )

        print("Tool selected:", selection.tool_name)
        print("Reasoning:", selection.reasoning)
        print("Parameters:", selection.parameters)
    except Exception as e:
        if socket:
            socket.send_error(f"[ERROR] Exception in tool_agent: {e}")
        else:
            print(f"[ERROR] Exception in tool_agent: {e}")
        return {
            "messages": [
                AIMessage(content=f"Error processing tool selection: {e!s}"),
            ],
        }
    parameters = selection.parameters
    if isinstance(parameters, str):
        try:
            parameters = ModelManager.convert_to_json(parameters)
        except Exception as e:
            if socket:
                socket.send_error(
                    f"[ERROR] Could not parse parameters: {e}",
                )
            else:
                print(f"[ERROR] Could not parse parameters: {e}")
    #     -------- tool selection and parameter handling --------
    # ( this is still in development, so it may not work as expected )
    if selection.tool_name and selection.tool_name.lower() != "none":
        from coldwind.core.tools.lggraph_tools.tool_response_manager import (
            ToolResponseManager,
        )

        for tool in tools:
            if tool.name.lower() == selection.tool_name.lower():
                try:
                    parameters.update(
                        {"tool_name": tool.name},
                    )  # Ensure tool_name is included in parameters
                    tool.invoke(parameters)
                    result = (
                        ToolResponseManager().get_response()[-1].content
                    )  # Get the last response from the tool manager
                    # Print tool result in modern style
                    print_message(result, sender="tool")
                    if socket:
                        socket.send_error(
                            f"[RESULT] Result from {tool.name}: {result}",
                        )
                    return {
                        "messages": [
                            AIMessage(
                                content=f"Result from {tool.name}: {result}",
                            ),
                        ],
                    }
                except Exception as e:
                    if socket:
                        socket.send_error(
                            f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__} {inspect.trace()}",
                        )
                    else:
                        print(
                            f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__}",
                        )
                    return {
                        "messages": [
                            AIMessage(
                                content=f"Error using {tool.name}: {e!s}",
                            ),
                        ],
                    }
        if socket:
            socket.send_error(
                f"[ERROR] Tool '{selection.tool_name}' not found.",
            )
        else:
            print(f"[ERROR] Tool '{selection.tool_name}' not found.")
        return {
            "messages": [
                AIMessage(content=f"Tool '{selection.tool_name}' not found."),
            ],
        }
    return {"messages": [AIMessage(content="No tool was used.")]}
