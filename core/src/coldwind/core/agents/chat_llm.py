from langchain_core.messages import AIMessage, HumanMessage

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.tools.lggraph_tools.tool_assign import ToolAssign
from coldwind.desktop.ui.print_message_style import print_message
from coldwind.core.utils.model_manager import ModelManager


def generate_llm_response(state) -> dict:
    """Generates a response using the LLM based on the conversation history and the latest user message.
    Shows a spinner while generating the response.
    """
    console = settings.console
    console.print("\t\t----[bold][green]Node is chatBot[/bold][/green]")
    # Access state directly from LangGraph parameter
    messages = state.get("messages", [])
    history = "\n".join(f"{msg.type}: {msg.content}" for msg in messages[:-1])
    latest_message_content = messages[-1].content if messages else ""

    tools = ToolAssign.get_tools_list()

    tools_context = (
        "\n\n".join(
            [f"Tool: {tool.name}\nDescription: {tool.description}" for tool in tools],
        )
        if tools
        else "No tools available."
    )

    from coldwind.core.prompts.chat_prompts import ChatPrompts
    system_prompt = ChatPrompts.get_chat_system_prompt(tools_context, history, latest_message_content)
    messages_with_system_prompt = [HumanMessage(content=system_prompt)]
    llm = ModelManager(temperature=0.7, format="json")

    with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
        stream = llm.stream(messages_with_system_prompt)
        content = ""
        for part in stream:
            chunk = part.content if part.content is not None else ""
            content += chunk
    # Print AI message in modern style
    # now we will not print raw json now we will extract the response from the content
    json_content = llm.convert_to_json(content)
    if json_content and "response" in json_content:
        content = json_content["response"]
    else:
        # If the response is not in the expected format, print the raw content
        pass
    print_message(content.strip(), sender="ai")
    return {"messages": [AIMessage(content=content.strip())]}
