import json
import os
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

# from IPython.display import Image, display

llm = ChatOllama(  #
    model="llava-llama3:latest",
    format="json",
    temperature=0.1,
    stream=True
)

# rich console for better output formatting
console = rich.get_console()

# Define a function to translate messages
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

def rag_search(query: str) -> str:
    """
    here we will implement the RAG search logic. that will search the knowledge base and return relevant information.
    this is not actual RAG it is RAG classifier that which RAG search to use. [image RAG,text RAG,PDF RAG etc.]
    --Placeholder function for RAG search.
    This should be replaced with actual RAG search logic.
    """
    return f"[RAG Search Result for '{query}']"

class rag_search_message(BaseModel):
    query: str = Field(
        description="Search query for RAG search. Use this to find information in the knowledge base. provide a clear and concise query.", )

rag_search_tool = StructuredTool.from_function(
    func=rag_search,
    name="RAGSearch",
    description="For searching the knowledge base (RAG search).",
    args_schema=rag_search_message,
)

# Register all tools here
tools = [search_tool, translate_tool, rag_search_tool]


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
    # print(f"[LOG] classify_message state: {state}")
    last_message = state["messages"][-1]
    content = last_message.content

    explicit_ai_phrases = ["/use ai", "/use llm"]
    lowered_content = content.lower()
    for phrase in explicit_ai_phrases:
        if phrase in lowered_content:
            print(f"[LOG] Removing explicit AI phrase: {phrase}")
            last_message.content = last_message.content.replace(phrase, "")
            console.print(f"[u][red]Message classified as[/u][/red]: llm (explicit user request override)")
            return {"message_type": "llm"}

    explicit_tool_phrases = ["/search", "/use tool"]
    for phrase in explicit_tool_phrases:
        if phrase in lowered_content:
            print(f"[LOG] Removing explicit tool phrase: {phrase}")
            last_message.content = last_message.content.replace(phrase, "")
            console.print(f"[u][red]Message classified as[/u][/red]: tool (explicit user request override)")
            return {"message_type": "tool"}

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

**Classification Rules**:

1. **If the user explicitly requests or instructs to use 'AI', 'assistant', or 'LLM', always classify as 'llm', even if tool keywords are present.**
2. **Classify as 'tool'** if the user explicitly mentions these keywords: "search", "web", or "internet" or asks for fresh online data.
3. **Classify as 'tool'** if the user explicitly mentions these keywords: "translate" regarding translating the current or previous message. Use the translation tool.
4. Otherwise, classify as 'llm'.

**Examples of 'llm' messages**:
- Greetings (like "hi", "hello")
- General questions or statements
- If user mentioned chatbot, ai, or assistant then must classify as 'llm'
**BE CONSERVATIVE** with tool usage - when in doubt, classify as 'llm'.
If the user says to use the AI or LLM, do NOT use a tool, even if tool keywords are present.
    """
    # print(f"[LOG] classify_message system_prompt: {system_prompt}")
    # <-- CHANGE: Pass messages as a list of objects
    result = classified_llm.invoke([
        HumanMessage(content=system_prompt),
        HumanMessage(content=content)
    ])
    # print(f"[LOG] classify_message result: {result}")
    console.print(f"[u][red]Message classified as[/u][/red]: {result.message_type}")
    return {"message_type": result.message_type}


def router(state: State):
    console.print("\t\t[bold][green]----Node is router[/bold][/green]")
    # print(f"[LOG] router state: {state}")
    message_type = state.get("message_type", "llm")
    # print(f"[LOG] router message_type: {message_type}")
    return {'message_type': message_type}


def chatBot(state: State) -> dict:
    console.print("\t\t----[bold][green]Node is chatBot[/bold][/green]")
    # print(f"[LOG] chatBot state: {state}")
    system_prompt = ("You are a next-generation AI assistant that references the full conversation history"
                     " and relevant context to provide more natural, context-rich, and accurate answers to user questions."
                     " Leverage any results from available tools in your reasoning."
                     "make sure always answer user prompt using fixed json object key 'response' value 'your answer'"
                     "for example {\"response\": \"Your answer here.\"}")
    messages = state["messages"]
    # <-- CHANGE: Prepend system prompt as a HumanMessage for consistency, though a simple dict also works here
    messages_with_system_prompt = [HumanMessage(content=system_prompt)] + messages

    stream = llm.stream(messages_with_system_prompt)
    content = ""
    for part in stream:
        chunk = part.content if part.content is not None else ""
        content += chunk
        print(chunk, end="", flush=True)
    print()
    # print(f"[LOG] chatBot response content: {content}")
    # <-- CHANGE: Return an AIMessage object
    return {"messages": [AIMessage(content=content)]}


def tool_agent(state: State) -> dict:
    console.print("\t\t----[bold][green]Node is tool_agent[/bold][/green]")
    # print(f"[LOG] tool_agent state: {state}")
    last_message = state["messages"][-1]
    content = last_message.content
    history = state["messages"]

    tools_context = "\n\n".join([
        f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {json.dumps(tool.args_schema.model_json_schema())}"
        for tool in tools
    ])

    system_prompt = (
        "You are an expert AI agent responsible for selecting the most appropriate tool to fulfill a user's request, "
        "using deep reasoning and full awareness of the conversation context.\n\n"
        "You have access to the following tools:\n\n"
        f"{tools_context}\n\n"
        "Your task:\n"
        f"- Carefully analyze the user's latest message and the entire conversation history {history}.\n"
        "- Select the single best tool for the user's request, or 'none' if no tool is suitable.\n"
        "- Only select a tool if it is clearly required to answer the user's request or perform an action.\n"
        "- If the user refers to previous messages, use the 'messages' field to access and reason over them.\n"
        "- If the user asks for translation, searching, or any action matching a tool's description, select that tool.\n"
        "- If the user asks for general conversation, advice, or information not requiring a tool, select 'none'.\n"
        "- Be conservative: only use a tool if it is clearly needed.\n\n"
        f"The tool name must be one of: {', '.join([tool.name for tool in tools])} or 'none'.\n"
        "If no tool is suitable, select 'none'.\n\n"
        "Your response MUST be a valid JSON object in this exact format:\n"
        "{\n"
        '  "tool_name": "TOOL_NAME_HERE",\n'
        '  "reasoning": "Explain clearly why you selected this tool (or none), referencing the user\'s request and conversation history.",\n'
        '  "parameters": { "param1": "value1", "param2": "value2" } // Fill with required parameters for the tool, or leave empty if none.\n'
        "}\n\n"
        "Guidelines:\n"
        "- Use the 'messages' field to access the full conversation as a list of objects (each with 'type' and 'content').\n"
        "- If the tool requires parameters, extract them from the user's message or conversation context.\n"
        "- If the user refers to previous messages, use them to inform your reasoning and parameter selection.\n"
        "- Always provide clear, step-by-step reasoning for your choice.\n"
    )

    try:
        structured_llm = ChatOllama(
            model="llava-llama3:latest",
            format="json",
            temperature=0.1,
            stream=False
        ).with_structured_output(ToolSelection)
        # print(f"[LOG] tool_agent system_prompt: {system_prompt}")
        selection = structured_llm.invoke([
            HumanMessage(content=system_prompt),
            HumanMessage(content=content)
        ])
        # print(f"[LOG] tool_agent selection: {selection}")
        print("Tool selected:", selection.tool_name)
        print("Reasoning:", selection.reasoning)
        print("Parameters:", selection.parameters)
    except Exception as e:
        print(f"[ERROR] Exception in tool_agent: {e}")
        return {"messages": [AIMessage(content=f"Error processing tool selection: {str(e)}")]}
    parameters = selection.parameters
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except Exception as e:
            print(f"[ERROR] Could not parse parameters: {e}")
            pass
    if selection.tool_name and selection.tool_name.lower() == "duckduckgosearch":
        query = parameters.get("query")
        if isinstance(query, dict):
            query_str = query.get("value") or query.get("example") or ""
            if not query_str:
                query_str = input("Please enter your search query for DuckDuckGo: ")
            parameters["query"] = query_str
        elif not isinstance(query, str):
            parameters["query"] = input("Please enter your search query for DuckDuckGo: ")
    if selection.tool_name and selection.tool_name.lower() != "none":
        for tool in tools:
            if tool.name.lower() == selection.tool_name.lower():
                try:
                    # print(f"[LOG] Invoking tool: {tool.name} with parameters: {parameters}")
                    result = tool.invoke(parameters)
                    # print(f"[LOG] Tool result: {result}")
                    return {"messages": [AIMessage(content=f"Result from {tool.name}: {result}")]}
                except Exception as e:
                    print(f"[ERROR] Error using tool {tool.name}: {e}")
                    return {"messages": [AIMessage(content=f"Error using {tool.name}: {str(e)}")]}
        print(f"[ERROR] Tool '{selection.tool_name}' not found.")
        return {"messages": [AIMessage(content=f"Tool '{selection.tool_name}' not found.")]}
    # print("[LOG] No tool was used.")
    return {"messages": [AIMessage(content='No tool was used.')]}


# ...existing code...


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
    # print(f"[LOG] onExit state: {state}")
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
    # print("[LOG] Conversation history saved to conversation_history.json")
    # <-- CHANGE: Return an AIMessage object
    return {"messages": [AIMessage(content="Thank you for using the LangGraph Chatbot!")]}


def savePng(path: str):
    """
Saves the conversation history as a PNG image.
    :param path:
    :return:
    """

    with open(path, "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())

    # os.system('start ' + path)  # Opens the PNG file in the default viewer
    if os.name == 'posix':
        os.system(f'xdg-open {path}')
    else:
        os.system(f'start {path}')
    pass


def runn_chat():
    state = {'messages': [], 'message_type': None}
    print("Welcome to the LangGraph Chatbot!")
    print("Type 'exit' to end the conversation.")

    while True:
        user_input = input('message: ')
        # print(f"[LOG] User input: {user_input}")
        if user_input.lower() == 'exit':
            print("Exiting the chatbot. Goodbye!")
            onExit(state)
            rich.inspect(state)
            # display(Image(graph.get_graph().draw_mermaid_png()))
            savePng("conversation_history.png")
            break
        # <-- CHANGE: Append a HumanMessage object instead of a dictionary
        state['messages'].append(HumanMessage(content=user_input))
        # print(f"[LOG] State before graph.invoke: {state}")
        state = graph.invoke(state)
        # print(f"[LOG] State after graph.invoke: {state}")
        console.print(state["messages"][-1].content)


if __name__ == '__main__':
    try:
        runn_chat()
    except KeyboardInterrupt:
        print("\nExiting the chatbot. Goodbye!")
    except httpcore.ConnectError:
        print("\nConnection error. Please turn on the Ollama server and try again.")
