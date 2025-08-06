import inspect
import json

from src.agents.agents_schema.agents_schema import ToolSelection
from src.config import settings
from src.prompts.system_prompt_tool_selector import get_tool_selector_prompt
from src.tools.lggraph_tools.tool_assign import ToolAssign
from src.ui.print_message_style import print_message
from src.utils.model_manager import ModelManager
from src.utils.argument_schema_util import get_tool_argument_schema
def tool_selection_agent(state) -> dict:
    """
    Selects and invokes the most appropriate tool for the user's request, or returns a message if no tool is needed.
    """
    console = settings.console
    console.print("\t\t----[bold][green]Node is tool_agent[/bold][/green]")

    # Access state directly from LangGraph parameter (no sync needed)
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    content = last_message.content if last_message else ""
    history = messages
    tools = ToolAssign.get_tools_list()

    tools_context = "\n\n".join([
        f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {get_tool_argument_schema(tool)}"
        for tool in tools
    ]) if tools else settings.socket_con.send_error("[ERROR] No tools available for selection.") if settings.socket_con else print("[ERROR] No tools available for selection.")

    # Use the centralized tool selector prompt
    system_prompt = get_tool_selector_prompt(
        tools_context=tools_context,
        history=history,
        content=content
    )

    try:
        structured_llm = ModelManager(
            model=settings.CLASSIFIER_MODEL,
            format="json",
            temperature=0.3, # Lower temperature for more consistent tool selection
            stream=False,
            max_tokens=1000,  # Allow enough tokens for reasoning and parameters
            top_p=1.0,        # Focus on most likely tokens for better accuracy
        ).with_structured_output(ToolSelection)
        with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
            selection = structured_llm.invoke([
                settings.HumanMessage(content=system_prompt),
                settings.HumanMessage(content=content)
            ])
        print("Tool selected:", selection.tool_name)
        print("Reasoning:", selection.reasoning)
        print("Parameters:", selection.parameters)
    except Exception as e:
        if settings.socket_con:
            settings.socket_con.send_error(f"[ERROR] Exception in tool_agent: {e}")
        else:
            print(f"[ERROR] Exception in tool_agent: {e}")
        return {"messages": [settings.AIMessage(content=f"Error processing tool selection: {str(e)}")]}
    parameters = selection.parameters
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except Exception as e:
            if settings.socket_con:
                settings.socket_con.send_error(f"[ERROR] Could not parse parameters: {e}")
            else:
                print(f"[ERROR] Could not parse parameters: {e}")
            pass
    #     -------- tool selection and parameter handling --------
    # ( this is still in development, so it may not work as expected )
    if selection.tool_name and selection.tool_name.lower() != "none":
        from src.tools.lggraph_tools.tool_response_manager import ToolResponseManager
        for tool in tools:
            if tool.name.lower() == selection.tool_name.lower():
                try:
                    tool.invoke(parameters)
                    result = ToolResponseManager().get_response()[
                        -1].content  # Get the last response from the tool manager
                    # Print tool result in modern style
                    print_message(result, sender="tool")
                    if settings.socket_con:
                        settings.socket_con.send_error(f"[RESULT] Result from {tool.name}: {result}")
                    return {"messages": [settings.AIMessage(content=f"Result from {tool.name}: {result}")]}
                except Exception as e:
                    if settings.socket_con:
                        settings.socket_con.send_error(
                            f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__} {inspect.trace()}")
                    else:
                        print(f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__}")
                    return {"messages": [settings.AIMessage(content=f"Error using {tool.name}: {str(e)}")]}
        if settings.socket_con:
            settings.socket_con.send_error(f"[ERROR] Tool '{selection.tool_name}' not found.")
        else:
            print(f"[ERROR] Tool '{selection.tool_name}' not found.")
        return {"messages": [settings.AIMessage(content=f"Tool '{selection.tool_name}' not found.")]}
    return {"messages": [settings.AIMessage(content='No tool was used.')]}
