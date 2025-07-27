import gc

from rich.console import Console

from src.models.state import State
from src.ui.print_banner import print_banner
from src.ui.print_history import print_history
from src.ui.print_message_style import print_message

with Console().status("[bold green]Loading LangGraph Chatbot...[/bold green]", spinner="dots"):
    import json
    import os
    import httpx
    from langchain_core.messages import HumanMessage, AIMessage
    from langgraph.graph import StateGraph, START, END
    from rich.align import Align
    from rich.prompt import Prompt
    from rich import inspect
    from src.utils.socket_manager import socket_manager
    from src.models.state import StateAccessor

# Get the shared socket connection
socket_con = socket_manager.get_socket_connection()

# Initialize StateAccessor singleton
state_accessor = StateAccessor()

console = Console()

def on_exit(state: State):
    """
    Handles cleanup and saving of conversation history when the chatbot session ends.
    """
    console.print("\t\t----[bold][red]Node is onExit[/bold][red]")
    # 🔄 Sync StateAccessor with final LangGraph state
    state_accessor.sync_with_langgraph(state)
    history = []
    messages = state_accessor.get_messages()
    for msg in messages:
        history.append(
            {
                "type": msg.type,
                "content": msg.content
            }
        )
    json.dump(history, open("conversation_history.json", "w"), indent=2)
    # Clean up socket connection
    socket_manager.close_connection()

    return {"messages": [AIMessage(content="Thank you for using the LangGraph Chatbot!")]}


def save_png(path: str):
    """
    Saves the conversation history graph as a PNG image.
    """
    with open(path, "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())
    if os.name == 'posix':
        os.system(f'xdg-open {path}')
    else:
        os.system(f'start {path}')
    pass


def run_chat():
    """
    Main loop for running the chatbot, handling user input and conversation flow.
    Modernized with banner, styled prompts, and message history.
    """
    os.system("cls" if os.name == 'nt' else "clear")
    _state = {'messages': [], 'message_type': None}
    print_banner()
    console.print(Align.center("[bold blue]Welcome to the LangGraph Chatbot![/bold blue]"))
    console.print(Align.center("Type '[bold red]exit[/bold red]' to end the conversation.\n"))

    while True:
        user_input = Prompt.ask("[bold cyan]You[/bold cyan]", default="", show_default=False)
        if user_input.lower() == 'exit':
            state_accessor.sync_with_langgraph(_state)
            print_message("Exiting the chatbot. Goodbye!", sender="ai")
            if state_accessor.get_messages():
                print_history(state_accessor.get_messages())
            on_exit(_state)
            inspect(_state)
            # save_png("conversation_history.png")
            break
        _state['messages'].append(HumanMessage(content=user_input))
        # Print user message in modern style
        print_message(user_input, sender="user")
        _state = graph.invoke(_state)
        state_accessor.sync_with_langgraph(_state)
        gc.collect()  # Collect garbage to free memory
        # The AI/tool message is printed inside generate_llm_response/tool_selection_agent


# -------------------- TOOL ASSIGNMENTS --------------------

from src.tools.lggraph_tools.tool_assign import ToolAssign
from src.tools.lggraph_tools.wrappers.google_wrapper import GoogleSearchToolWrapper
from src.tools.lggraph_tools.wrappers.translate_wrapper import TranslateToolWrapper
from src.tools.lggraph_tools.wrappers.rag_search_classifier_wrapper import RagSearchClassifierWrapper
# schema
from src.tools.lggraph_tools.tool_schemas.tools_structured_classes import google_search, rag_search_message, \
    TranslationMessage
tools = [
    # google search tool assigning
    ToolAssign(func=GoogleSearchToolWrapper,
               name="GoogleSearch",
               description="For general web searches (recent info, facts, news).",
               args_schema=google_search, ),
    # rag search tool assigning
    ToolAssign(func=RagSearchClassifierWrapper,
               name="RAGSearch",
               description="For searching the knowledge base (RAG search).",
               args_schema=rag_search_message, ),
    # translate tool assigning
    ToolAssign(func=TranslateToolWrapper,
               name="Translatetool",
               description="For translating messages into different languages.",
               args_schema=TranslationMessage, )
]

ToolAssign.set_tools_list(tools)

# -------------------- GRAPH SETUP --------------------
from src.agents.node_factory import (classify_message_type, route_message, tool_selection_agent, generate_llm_response)

graph_builder = StateGraph(State)
graph_builder.add_node("classifier", classify_message_type)
graph_builder.add_node("router", route_message)
graph_builder.add_node("chatBot", generate_llm_response)
graph_builder.add_node("tool_agent", tool_selection_agent)

graph_builder.add_edge(START, "classifier")
graph_builder.add_edge('classifier', 'router')


def route_by_message_type(state):
    return state["message_type"]


graph_builder.add_conditional_edges(
    'router',
    route_by_message_type,
    {"llm": "chatBot", "tool": "tool_agent"}
)
graph_builder.add_edge("chatBot", END)
graph_builder.add_edge("tool_agent", END)
graph = graph_builder.compile()

# -------------------- MAIN --------------------

if __name__ == '__main__':
    try:
        run_chat()
    except KeyboardInterrupt:
        print("\nExiting the chatbot. Goodbye!")
    except httpx.ConnectError:
        if socket_con:
            socket_con.send_error("\nConnection error. Please turn on the Ollama server and try again.")
        else:
            print("\nConnection error. Please turn on the Ollama server and try again.")
# todo next we could make related to any social media tool like open insta or what's app search or message them
