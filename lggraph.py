
from typing import Annotated, Literal
import json

import rich
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import Field, BaseModel
from typing_extensions import TypedDict

llm = ChatOllama(
    model="llava-llama3:latest",
    format="json",
    temperature=0.1,
    stream=True
)

# rich console for better output formatting
console = rich.get_console()

# Define a function to search DuckDuckGo

def search_duckduckgo(query: str) -> any:
    search_tool = DuckDuckGoSearchRun()
    result = search_tool.run(query)
    return result


"""
The AI agent uses both descriptions, but for different purposes:


description in StructuredTool (lines 36-37): 
This is the main description for the tool itself. 
The agent uses this high-level description ("For general web searches (recent info, facts, news).") to decide if it should select the DuckDuckGoSearch
 tool from the available tools.


description in duckduckgo_search class (lines 29-30):
 This describes a specific parameter (query) for the tool.
  Once the agent has decided to use DuckDuckGoSearch, it uses this description ("Search query for DuckDuckGo...") 
  to understand what kind of value it should provide for the query argument.


In summary, one description is for choosing the tool, and the other is for using it correctly.
"""


class duckduckgo_search(BaseModel):
    query: str = Field(
        description="Search query for DuckDuckGo. Use this to find information on the web. provide a clear and concise query.", )


search_tool = StructuredTool.from_function(
    func=search_duckduckgo,
    name="DuckDuckGoSearch",
    description="For general web searches (recent info, facts, news).",
    args_schema=duckduckgo_search,
)

# Register all tools here
tools = [search_tool]


class ToolSelection(BaseModel):
    tool_name: str = Field(description="The name of the tool to use, or 'none' if no tool is needed.")
    reasoning: str = Field(description="Reasoning for selecting this tool.")
    parameters: dict = Field(description="The parameters to pass to the tool.")


class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None


graph_builder = StateGraph(State)


class message_classifier(BaseModel):
    message_type: Literal['llm', 'tool'] = Field(
        description="classify the message as Type of message: 'llm' for LLM response, 'tool' for tool response.")


def classify_message(state: State):
    print("\t\t----Node is classify_message")
    last_message = state["messages"][-1]
    if isinstance(last_message, dict):
        content = last_message.get("content", "")
    else:
        content = getattr(last_message, "content", str(last_message))

    history_parts = []
    for msg in state["messages"][:-1]:
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            msg_content = msg.get("content", "")
        else:
            role = getattr(msg, "type", "unknown")
            msg_content = getattr(msg, "content", "")
        history_parts.append(f"{role}: {msg_content}")
    history = "\n".join(history_parts)

    classified_llm = llm.with_structured_output(message_classifier)

    # Improved system prompt to better handle follow-up questions
    system_prompt = F"""You are a highly intelligent message classifier. Your task is to analyze the user's "Latest Message" in the context of the "Conversation History" and classify it as either 'llm' or 'tool'.

    **Conversation History:**
    {history}

    **Latest Message:**
    {content}

    **Classification Rules:**

    1.  **Classify as 'llm'** if the "Latest Message" is a follow-up question or a command related to the **Conversation History**. This includes requests to:
        - Translate the previous response.
        - Summarize the previous response.
        - Explain the previous response.
        - Reformat the previous response.
        - Any general chat or question about the history.
        - Example: If history has a search result, and the user says "Translate that to Hindi", you MUST classify it as 'llm'.

    2.  **Classify as 'tool'** ONLY IF the "Latest Message" is a request for **new information** that requires a fresh web search.
        - Example: "How many teams won the IPL?"
        - Example: "What is the weather today in London?"

    Analyze the intent. Is the user asking for a new search, or are they asking to process existing information?
    """

    result = classified_llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ])

    console.print(f"[u][red]Message classified as[/u][/red]: {result.message_type}")
    return {"message_type": result.message_type}


def router(state: State):
    console.print("\t\t[bold][green]----Node is router[/bold][/green]")
    message_type = state.get("message_type", "llm")  # Default to 'llm' if not set
    if message_type == "llm":
        return {"next": "chatBot"}
    elif message_type == "tool":
        return {"next": "tool_agent"}
    else:
        raise ValueError("Unknown message type")


def chatBot(state: State) -> dict:
    # the llm response contain title and response because we are using a structured output/make json=true while assigning the llm
    console.print("\t\t----[bold][green]Node is chatBot[/bold][/green]")

    # This is the full list of messages, which provides context.
    messages = state["messages"]

    # Your custom system prompt.
    system_prompt = {
        "role": "system",
        "content": "You are a helpful chat assistant. Respond to the user's last message using the full conversation history provided for context. The history may contain results from tools, which you should use to answer the user's questions about them."
    }

    # Prepend the system prompt to the message history.
    # This is the correct way to structure the input for the LLM.
    messages_with_system_prompt = [system_prompt] + messages

    stream = llm.stream(messages_with_system_prompt)
    content = ""
    for part in stream:
        chunk = part.content if part.content is not None else ""
        content += chunk
        print(chunk, end="", flush=True)
    print()
    return {"messages": [{"role": "assistant", "content": content}]}


def tool_agent(state: State) -> dict:
    console.print("\t\t----[bold][green]Node is tool_agent[/bold][/green]")
    last_message = state["messages"][-1]
    if isinstance(last_message, dict):
        content = last_message.get("content", "")
    else:
        content = getattr(last_message, "content", str(last_message))

    tools_context = "\n\n".join([
        f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {json.dumps(tool.args_schema.model_json_schema())}"
        for tool in tools
    ])

    system_prompt = (
        f"You are an intelligent agent that selects the best tool to use for a user's request.\n"
        f"You have access to the following tools:\n\n"
        f"{tools_context}\n\n"
        f"Based on the user's message, select the most appropriate tool.\n"
        f"The tool name must be one of: {', '.join([tool.name for tool in tools])} or 'none'.\n"
        f"If no tool is suitable, select 'none'.\n"
        # f"IMPORTANT: For DuckDuckGoSearch tool, your reasoning MUST BE the exact search query you want to use.\n"
        f"Your response MUST be in this exact JSON format:\n"
        f"{{\n"
        f'  "tool_name": "TOOL_NAME_HERE",\n'
        f'  "reasoning": "YOUR REASONING HERE",\n'
        f'  "parameters": {{"param1": "value1", "param2": "value2"}}\n'
        f"}}\n"
    )

    # Use non-streaming approach only
    try:
        # Create a non-streaming LLM instance specifically for this task
        structured_llm = ChatOllama(
            model="llava-llama3:latest",
            format="json",
            temperature=0.1,
            stream=False
        ).with_structured_output(ToolSelection)

        selection = structured_llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ])

        print("Tool selected:", selection.tool_name)
        print("Reasoning:", selection.reasoning)
        print("Parameters:", selection.parameters)

    except Exception as e:
        return {"messages": [{"role": "assistant", "content": f"Error processing tool selection: {str(e)}"}]}

    # If parameters are returned as a string, parse them
    parameters = selection.parameters
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except Exception:
            pass

    if selection.tool_name and selection.tool_name.lower() != "none":
        for tool in tools:
            if tool.name.lower() == selection.tool_name.lower():
                try:
                    result = tool.invoke(parameters)
                    # The line below was removed as it caused the error.
                    # The return statement correctly handles adding the message to the state.
                    return {"messages": [{"role": "assistant", "content": f"Result from {tool.name}: {result}"}]}
                except Exception as e:
                    return {"messages": [{"role": "assistant", "content": f"Error using {tool.name}: {str(e)}"}]}
        return {"messages": [{"role": "assistant", "content": f"Tool '{selection.tool_name}' not found."}]}

    return {"messages": [{"role": "assistant", "content": "No tool was used."}]}


# Graph setup
graph_builder.add_node("classifier", classify_message)
graph_builder.add_node("router", router)
graph_builder.add_node("chatBot", chatBot)
graph_builder.add_node("tool_agent", tool_agent)

graph_builder.add_edge(START, "classifier")
graph_builder.add_edge('classifier', 'router')
graph_builder.add_conditional_edges('router', lambda state: state.get("message_type"),
                                    {"llm": "chatBot", "tool": "tool_agent"})
graph_builder.add_edge("chatBot", END)
graph_builder.add_edge("tool_agent", END)
graph = graph_builder.compile()


def runn_chat():
    state = {'messages': [], 'message_type': None}
    print("Welcome to the LangGraph Chatbot!")
    print("Type 'exit' to end the conversation.")

    while True:
        user_input = input('message: ')
        if user_input.lower() == 'exit':
            print("Exiting the chatbot. Goodbye!")
            rich.inspect(state)
            break
        state['messages'].append({"role": "user", "content": user_input})
        state = graph.invoke(state)
        print(state["messages"][-1])


if __name__ == '__main__':
    runn_chat()
