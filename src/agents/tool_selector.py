import json

from src.agents.agents_schema.agents_schema import ToolSelection
from src.config import settings
from src.tools.lggraph_tools.tool_assign import ToolAssign
from src.ui.print_message_style import print_message
from src.utils.model_manager import ModelManager


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
        f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {json.dumps(tool.args_schema.model_json_schema())}"
        for tool in tools
    ]) if tools else settings.socket_con.send_error("[ERROR] No tools available for selection.") if settings.socket_con else print("[ERROR] No tools available for selection.")

    system_prompt = (
        "You are an intelligent tool selection agent with deep contextual understanding and reasoning capabilities.\n\n"

        "**Your Mission:**\n"
        "Analyze the user's request within the full conversation context to determine if they need a specific tool or if their question can be answered without external tools.\n\n"

        "**Available Tools:**\n"
        f"{tools_context}\n\n"

        "**Conversation Context Analysis:**\n"
        f"Full conversation history: {history}\n"
        f"Current user request: {content}\n\n"

        "**Smart Tool Selection Logic:**\n\n"

        "1. **Context-Aware Reasoning:**\n"
        "   - If the user references previous messages ('that result', 'the search we did', 'translate that'), understand what they're referring to\n"
        "   - Consider the flow of conversation - are they asking for new information or clarification of existing information?\n"
        "   - Look for implicit requests based on conversation context\n\n"

        "2. **Tool Selection Criteria:**\n"
        "   - **GoogleSearch**: For current information, facts, news, or anything requiring web search\n"
        "   - **RAGSearch**: For document analysis, knowledge base queries, or file-specific searches\n"
        "   - **Translatetool**: For language translation requests\n"
        "   - **'none'**: For explanations, clarifications, reasoning, or general conversation\n\n"

        "3. **Context-Sensitive Examples:**\n"
        "   - User: 'search for AI news' → GoogleSearch with query 'AI news'\n"
        "   - User: 'what does that mean?' (after a search result) → 'none' (explanation needed)\n"
        "   - User: 'translate the previous message to Spanish' → Translatetool with message from history\n"
        "   - User: 'find information about quantum computing in the document' → RAGSearch\n"
        "   - User: 'explain how that works' (referring to previous content) → 'none'\n\n"

        "4. **Parameter Extraction Intelligence:**\n"
        "   - Extract parameters from current message AND conversation history when relevant\n"
        "   - If user says 'translate that', find the 'that' in conversation history\n"
        "   - If user says 'search for more about X' where X was mentioned before, use context\n\n"
        "   - If user says 'RAG SEARCH :- {query}', extract the query and use it for RAG search\n"
        "   - If user says 'search on web  :- {query}', extract the query and use it for RAG search\n"

        "**Response Format:**\n"
        "Return a JSON object with this exact structure:\n"
        "{\n"
        '  "tool_name": "TOOL_NAME or none",\n'
        '  "reasoning": "Clear explanation of your decision based on context and user intent",\n'
        '  "parameters": {"param": "value"} // Extract from message and/or conversation history\n'
        "}\n\n"

        "**Key Principle:** Think like a human assistant who understands context, references, and the natural flow of conversation. Don't just match keywords - understand intent."
    )

    try:
        structured_llm = ModelManager(
            model=settings.CLASSIFIER_MODEL,
            format="json",
            temperature=0.7,
            stream=False
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
                            f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__}")
                    else:
                        print(f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__}")
                    return {"messages": [settings.AIMessage(content=f"Error using {tool.name}: {str(e)}")]}
        if settings.socket_con:
            settings.socket_con.send_error(f"[ERROR] Tool '{selection.tool_name}' not found.")
        else:
            print(f"[ERROR] Tool '{selection.tool_name}' not found.")
        return {"messages": [settings.AIMessage(content=f"Tool '{selection.tool_name}' not found.")]}
    return {"messages": [settings.AIMessage(content='No tool was used.')]}
