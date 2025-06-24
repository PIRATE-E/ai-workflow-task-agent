import json
from typing import Annotated, Literal, List

import httpcore
import requests
import rich
from langchain_community.tools import DuckDuckGoSearchRun
# <-- CHANGE: Import message objects
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import Field, BaseModel
from typing_extensions import TypedDict

llm = ChatOllama(  #
    model="llava-llama3:latest",
    format="json",
    temperature=0.1,
    stream=True
)

# rich console for better output formatting
console = rich.get_console()


def translate_message(message: str, target_language: str) -> str:
    """
    Translates the given message to the target language.
    This is a placeholder function; actual translation logic should be implemented.
    """

    url = "http://localhost:5500/translate"  # Replace with actual translation service URL
    data = {
        "q": message,
        "source": "auto",  # Assuming the source language is English
        "target": target_language,
        "format": "text"
    }

    # api_headers = {
    #     "Content-Type": "application/json"
    # }

    response = requests.post(url, json=data)

    # For now, just return the original message with a note
    return f"[Translated to {target_language}]: {response.json().get('translatedText', message)}"


class TranslationMessage(BaseModel):
    message: str = Field(
        description="The message to translate. Provide the text you want to translate into the targeted language."
    )
    target_language: str = Field(
        description="The language to translate the message into. Use ISO 639-1 codes (e.g., 'en' for English, 'hi' for Hindi)."
    )


translate_tool = StructuredTool.from_function(
    func=translate_message,
    name="Translatetool",
    description="For translating messages into different languages.",
    args_schema=TranslationMessage,
)


# Define a function to search DuckDuckGo
def search_duckduckgo(query: str) -> any:
    search_tool = DuckDuckGoSearchRun()
    result = search_tool.run(query)
    return result


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
tools = [search_tool, translate_tool]


class ToolSelection(BaseModel):
    tool_name: str = Field(description="The name of the tool to use, or 'none' if no tool is needed.")
    reasoning: str = Field(description="Reasoning for selecting this tool.")
    parameters: dict = Field(description="The parameters to pass to the tool.")


class State(TypedDict):
    # <-- CHANGE: Define the list to contain message objects
    messages: Annotated[List[HumanMessage | AIMessage], add_messages]
    message_type: str | None


graph_builder = StateGraph(State)


class message_classifier(BaseModel):
    message_type: Literal['llm', 'tool'] = Field(
        description="classify the message as Type of message: 'llm' for LLM response, 'tool' for tool response.")


def classify_message(state: State):
    print("\t\t----Node is classify_message")
    last_message = state["messages"][-1]
    # <-- CHANGE: Access content directly using the .content attribute
    content = last_message.content

    history_parts = []
    # <-- CHANGE: Access message type and content directly
    for msg in state["messages"][:-1]:
        history_parts.append(f"{msg.type}: {msg.content}")
    history = "\n".join(history_parts)

    classified_llm = llm.with_structured_output(message_classifier)

    # Improved system prompt to better handle follow-up questions
    system_prompt = F"""You are a highly intelligent message classifier.
    Your task is to analyze the user's \"Latest Message\" in the context of the \"Conversation History\" and classify it as 'llm' or 'tool'.
    
        **Conversation History:**
        {history}
    
        **Latest Message:**
        {content}
    
        **Classification Rules:**
    
        1.  **Classify as 'llm'** if the "Latest Message" is a follow-up question or a command related to the **Conversation History**. This includes requests to:
            - Summarize the previous response.
            - Explain the previous response.
            - Reformat the previous response.
            - Any general chat or question about the history.
            - Example: If history has a search result, and the user says "Translate that to Hindi", you MUST classify it as 'llm'.
    
        2.  **Classify as 'tool'** ONLY IF the "Latest Message" is a request for **new information** that requires a fresh web search.
            - Example: "How many teams won the IPL?"
            - Example: "What is the weather today in London?"
            - Example: "Translate 'Hello' to Hindi" is a tool request, but if the user says "Translate the last message to Hindi", it is a follow-up and should be classified as 'llm'.
    
        Analyze the intent. Is the user asking for a new search, or are they asking to process existing information?
        """

    # <-- CHANGE: Pass messages as a list of objects
    result = classified_llm.invoke([
        HumanMessage(content=system_prompt),
        HumanMessage(content=content)
    ])

    console.print(f"[u][red]Message classified as[/u][/red]: {result.message_type}")
    return {"message_type": result.message_type}


def router(state: State):
    console.print("\t\t[bold][green]----Node is router[/bold][/green]")
    message_type = state.get("message_type", "llm")  # Default to 'llm' if not set
    # if message_type == "llm":
    #     return "chatBot"  # <-- CHANGE: Conditional edges now use string keys
    # elif message_type == "tool":
    #     return "tool_agent"  # <-- CHANGE: Conditional edges now use string keys
    # else:
    #     raise ValueError("Unknown message type")

    #   <-- now we use a dictionary to map message types to node names

    return {'message_type': message_type}


def chatBot(state: State) -> dict:
    console.print("\t\t----[bold][green]Node is chatBot[/bold][/green]")
    messages = state["messages"]
    system_prompt = "You are a helpful chat assistant. Respond to the user's last message using the full conversation history provided for context. The history may contain results from tools, which you should use to answer the user's questions about them."

    # <-- CHANGE: Prepend system prompt as a HumanMessage for consistency, though a simple dict also works here
    messages_with_system_prompt = [HumanMessage(content=system_prompt)] + messages

    stream = llm.stream(messages_with_system_prompt)
    content = ""
    for part in stream:
        chunk = part.content if part.content is not None else ""
        content += chunk
        print(chunk, end="", flush=True)
    print()
    # <-- CHANGE: Return an AIMessage object
    return {"messages": [AIMessage(content=content)]}


def tool_agent(state: State) -> dict:
    console.print("\t\t----[bold][green]Node is tool_agent[/bold][/green]")
    last_message = state["messages"][-1]
    # <-- CHANGE: Access content directly
    content = last_message.content

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
        f"Your response MUST be in this exact JSON format:\n"
        f"{{\n"
        f'  "tool_name": "TOOL_NAME_HERE",\n'
        f'  "reasoning": "YOUR REASONING HERE",\n'
        f'  "parameters": {{"param1": "value1", "param2": "value2"}}\n'
        f"}}\n"
    )

    try:
        structured_llm = ChatOllama(
            model="llava-llama3:latest",
            format="json",
            temperature=0.1,
            stream=False
        ).with_structured_output(ToolSelection)

        # <-- CHANGE: Pass messages as objects
        selection = structured_llm.invoke([
            HumanMessage(content=system_prompt),
            HumanMessage(content=content)
        ])

        print("Tool selected:", selection.tool_name)
        print("Reasoning:", selection.reasoning)
        print("Parameters:", selection.parameters)

    except Exception as e:
        # <-- CHANGE: Return an AIMessage object
        return {"messages": [AIMessage(content=f"Error processing tool selection: {str(e)}")]}

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
                    # <-- CHANGE: Return an AIMessage object
                    return {"messages": [AIMessage(content=f"Result from {tool.name}: {result}")]}
                except Exception as e:
                    # <-- CHANGE: Return an AIMessage object
                    return {"messages": [AIMessage(content=f"Error using {tool.name}: {str(e)}")]}
        # <-- CHANGE: Return an AIMessage object
        return {"messages": [AIMessage(content=f"Tool '{selection.tool_name}' not found.")]}

    # <-- CHANGE: Return an AIMessage object
    return {"messages": [AIMessage(content="No tool was used.")]}


# Graph setup
graph_builder.add_node("classifier", classify_message)
graph_builder.add_node("router", router)
graph_builder.add_node("chatBot", chatBot)
graph_builder.add_node("tool_agent", tool_agent)

graph_builder.add_edge(START, "classifier")
graph_builder.add_edge('classifier', 'router')

# <-- CHANGE: Conditional edges now map string return values to node names
graph_builder.add_conditional_edges(
    'router',
    # This function extracts the routing value from state updates
    lambda state_updates: state_updates["message_type"],
    {"llm": "chatBot", "tool": "tool_agent"}
)

graph_builder.add_edge("chatBot", END)
graph_builder.add_edge("tool_agent", END)
graph = graph_builder.compile()


def onExit(state: State):
    console.print("\t\t----[bold][red]Node is onExit[/bold][/red]")

    history = []
    for msg in state["messages"]:
        history.append(
            {
                "type": msg.type,
                "content": msg.content
            }
        )

    # save the conversation history to a file
    json.dump(history, open("conversation_history.json", "w"), indent=2)

    # <-- CHANGE: Return an AIMessage object
    return {"messages": [AIMessage(content="Thank you for using the LangGraph Chatbot!")]}


def runn_chat():
    state = {'messages': [], 'message_type': None}
    print("Welcome to the LangGraph Chatbot!")
    print("Type 'exit' to end the conversation.")

    while True:
        user_input = input('message: ')
        if user_input.lower() == 'exit':
            print("Exiting the chatbot. Goodbye!")
            onExit(state)
            rich.inspect(state)
            break
        # <-- CHANGE: Append a HumanMessage object instead of a dictionary
        state['messages'].append(HumanMessage(content=user_input))
        state = graph.invoke(state)
        console.print(state["messages"][-1].content)  # <-- CHANGE: Access .content


if __name__ == '__main__':
    try:
        runn_chat()
    except KeyboardInterrupt:
        print("\nExiting the chatbot. Goodbye!")
    except httpcore.ConnectError:
        print("\nConnection error. Please turn on the Ollama server and try again.")
