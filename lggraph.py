from threading import Thread
from typing import Annotated, Literal
import json
import threading

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
    classified_llm = llm.with_structured_output(message_classifier)

    # More comprehensive system prompt with examples
    system_prompt = """You are a message classifier. Classify the user message as either 'llm' or 'tool'.
    
    Available tools:
    - DuckDuckGoSearch: For searching the web for information, facts, recent events, or anything not in your knowledge.
    
    Classify as 'tool' when:
    - The user is asking for web search results
    - The user is asking about current events, sports scores, or recent information
    - The user asks to "search for" or "find information about" something
    - The query specifically mentions using a search engine
    - The request is about factual information you might not know
    
    Classify as 'llm' when:
    - The user wants a chat response, opinion, or explanation
    - The user is asking about topics you should know about
    - The user is having a conversation or asking for creative content
    
    Examples:
    - "What is the weather in New York?" -> 'tool' (needs web search)
    - "Tell me about the latest iPhone" -> 'tool' (needs recent information)
    - "What is machine learning?" -> 'llm' (concept explanation)
    - "Write a poem about stars" -> 'llm' (creative task)
    """

    result = classified_llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ])

    print(f"Message classified as: {result.message_type}")
    return {"message_type": result.message_type}


def router(state: State):
    print("\t\t----Node is router")
    message_type = state.get("message_type", "llm")  # Default to 'llm' if not set
    if message_type == "llm":
        return {"next": "chatBot"}
    elif message_type == "tool":
        return {"next": "tool_agent"}
    else:
        raise ValueError("Unknown message type")


def chatBot(state: State) -> dict:
    print("\t\t----Node is chatBot")
    last_message = state["messages"][-1]
    messages = [
        {"role": "system",
         "content": "You are a helpful chat assistant. Respond to the user's message. using you internal knowledge and the context provided."},
        {"role": "user", "content": last_message.content}
    ]
    stream = llm.stream(messages)
    content = ""
    for part in stream:
        chunk = part.content if part.content is not None else ""
        content += chunk
        print(chunk, end="", flush=True)  # Print chunks as they arrive
    print()  # New line after streaming completes
    return {"messages": [{"role": "assistant", "content": content}]}


def tool_agent(state: State) -> dict:
    print("\t\t----Node is tool_agent")
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
            break
        state['messages'].append({"role": "user", "content": user_input})
        state = graph.invoke(state)
        print(state["messages"][-1])


if __name__ == '__main__':
    runn_chat()
