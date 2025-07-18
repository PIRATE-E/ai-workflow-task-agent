import json
import os
from typing import Annotated, Literal, List

import httpcore
import requests
import rich
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import StructuredTool
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import Field, BaseModel
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from typing_extensions import TypedDict

import RAG_FILES.rag


# -------------------- STRUCTURED CLASSES --------------------


class TranslationMessage(BaseModel):
    message: str = Field(
        description="The message to translate. Provide the text you want to translate into the targeted language."
    )
    target_language: str = Field(
        description="The language to translate the message into. Use ISO 639-1 codes (e.g., 'en' for English, 'hi' for Hindi)."
    )


class duckduckgo_search(BaseModel):
    query: str = Field(
        description="Search query for DuckDuckGo. Use this to find information on the web. provide a clear and concise query.", )


class rag_search_message(BaseModel):
    query: str = Field(
        description="the query is for searching RAG provide a clear and concise query to search the knowledge base. provide single string with  no use of json object or any special characters.",
    )


class ToolSelection(BaseModel):
    tool_name: str = Field(description="The name of the tool to use, or 'none' if no tool is needed.")
    reasoning: str = Field(description="Reasoning for selecting this tool.")
    parameters: dict = Field(description="The parameters to pass to the tool.")


class State(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage], add_messages]
    message_type: str | None


class message_classifier(BaseModel):
    message_type: Literal['llm', 'tool'] = Field(
        description="classify the message as Type of message: 'llm' for LLM response, 'tool' for tool response.")


# -------------------- FUNCTION DEFINITIONS --------------------

llm = ChatOllama(
    model="llava-llama3:latest",
    format="json",
    temperature=0.1,
    stream=True
)

console = Console()


def print_banner():
    banner = """
 .S_SSSs     .S_SSSs     .S_SSSs     .S_sSSs           .S    S.    .S_SSSs           .S_SSSs     .S         .S_SSSs      sSSs_sSSs    sdSS_SSSSSSbs  
.SS~SSSSS   .SS~SSSSS   .SS~SSSSS   .SS~YS%%b         .SS    SS.  .SS~SSSSS         .SS~SSSSS   .SS        .SS~SSSSS    d%%SP~YS%%b   YSSS~S%SSSSSP  
S%S   SSSS  S%S   SSSS  S%S   SSSS  S%S   `S%b        S%S    S&S  S%S   SSSS        S%S   SSSS  S%S        S%S   SSSS  d%S'     `S%b       S%S       
S%S    S%S  S%S    S%S  S%S    S%S  S%S    S%S        S%S    d*S  S%S    S%S        S%S    S%S  S%S        S%S    S%S  S%S       S%S       S%S       
S%S SSSS%P  S%S SSSS%S  S%S SSSS%S  S%S    d*S        S&S   .S*S  S%S SSSS%S        S%S SSSS%S  S&S        S%S SSSS%P  S&S       S&S       S&S       
S&S  SSSY   S&S  SSS%S  S&S  SSS%S  S&S   .S*S        S&S_sdSSS   S&S  SSS%S        S&S  SSS%S  S&S        S&S  SSSY   S&S       S&S       S&S       
S&S    S&S  S&S    S&S  S&S    S&S  S&S_sdSSS         S&S~YSSY%b  S&S    S&S        S&S    S&S  S&S        S&S    S&S  S&S       S&S       S&S       
S&S    S&S  S&S    S&S  S&S    S&S  S&S~YSSY          S&S    `S%  S&S    S&S        S&S    S&S  S&S        S&S    S&S  S&S       S&S       S&S       
S*S    S&S  S*S    S&S  S*S    S&S  S*S               S*S     S%  S*S    S&S        S*S    S&S  S*S        S*S    S&S  S*b       d*S       S*S       
S*S    S*S  S*S    S*S  S*S    S*S  S*S               S*S     S&  S*S    S*S        S*S    S*S  S*S        S*S    S*S  S*S.     .S*S       S*S       
S*S SSSSP   S*S    S*S  S*S    S*S  S*S               S*S     S&  S*S    S*S        S*S    S*S  S*S        S*S SSSSP    SSSbs_sdSSS        S*S       
S*S  SSY    SSS    S*S  SSS    S*S  S*S               S*S     SS  SSS    S*S        SSS    S*S  S*S        S*S  SSY      YSSP~YSSY         S*S       
SP                 SP          SP   SP                SP                 SP                SP   SP         SP                              SP        
Y                  Y           Y    Y                 Y                  Y                 Y    Y          Y                               Y         
                                                                                                                                                     
    """
    console.print(Align.center(
        Panel.fit(Text(banner, style="bold magenta"), title="LangGraph Chatbot", subtitle="made by pirate",
                  style="bold blue")))


def print_message(msg, sender="user"):
    if sender == "user":
        icon = "👤"
        style = "bold cyan"
        label = "[USER]"
    elif sender == "ai":
        icon = "🤖"
        style = "bold green"
        label = "[AI]"
    elif sender == "tool":
        icon = "🛠️"
        style = "bold yellow"
        label = "[TOOL]"
    else:
        icon = ""
        style = ""
        label = ""
    panel = Panel(
        Align.left(Text(f"{icon} {label} {msg}", style=style)),
        border_style=style,
        padding=(1, 2),
    )
    console.print(panel)


def print_history(messages):
    for msg in messages:
        if isinstance(msg, HumanMessage):
            print_message(msg.content, sender="user")
        elif isinstance(msg, AIMessage):
            print_message(msg.content, sender="ai")
        else:
            print_message(str(msg), sender="tool")


def translate_text(message: str, target_language: str) -> str:
    """
    Translates the given message to the target language using an external translation service.
    """
    url = "http://localhost:5560/translate"  # Replace with actual translation service URL
    data = {
        "q": message,
        "source": "auto",
        "target": target_language,
        "format": "text"
    }
    response = requests.post(url, json=data)
    return f"[Translated to {target_language}]: {response.json().get('translatedText', message)}"


def duckduckgo_web_search(query: str) -> any:
    """
    Performs a web search using DuckDuckGo and returns the result.
    """
    search_tool = DuckDuckGoSearchRun()
    result = search_tool.run(query)
    return result


def rag_search_classifier(query: str) -> str:
    """
    Determines the appropriate RAG (Retrieval-Augmented Generation) search type based on the query and file type,
    and performs the search if supported.
    """
    file_path = Prompt.ask("Enter FILE PATH TO RAG SEARCH",
                           default=r"C:\Users\pirat\PycharmProjects\AI_llm\RAG_FILES\patent_2.pdf")
    system_prompt = (
        "You are an expert RAG (Retrieval-Augmented Generation) search classifier. "
        "Given a user's query and a file name, your task is to decide which type of RAG search to perform based primarily on the file extension and the context of the query. "
        "Supported RAG search types are: image RAG search, text RAG search, PDF RAG search, and audio RAG search. "
        "Determine the RAG type as follows: "
        "- If the file extension is an image format (e.g., .jpg, .jpeg, .png, .gif), select image RAG search. "
        "- If the file extension is a text format (e.g., .txt, .md), select text RAG search. "
        "- If the file extension is .pdf, select PDF RAG search. "
        "- If the file extension is an audio format (e.g., .mp3, .wav), select audio RAG search. "
        "Also consider the user's query: if it clearly asks for a specific type of content (image, text, PDF, or audio), use that to inform your decision. "
        "Return your answer as a JSON object in this format: {\"rag_type\": \"TYPE\", \"reasoning\": \"Your reasoning here.\"} "
        "Be concise and accurate in your reasoning."
    )
    llm_rag = ChatOllama(
        model="llava-llama3:latest",
        format="json",
        temperature=0.1,
        stream=False
    )
    result = llm_rag.invoke([
        HumanMessage(content=system_prompt),
        HumanMessage(content=f"Query: {query}\nFile Name: {file_path}")
    ])
    print(f"rag classification using llm :- {result.content}\n\n\n")
    try:
        rag_result = json.loads(result.content)
    except Exception as e:
        return f"Error: Could not parse LLM output: {e}"

    if not isinstance(rag_result, dict) or "rag_type" not in rag_result:
        return "Error: Unable to classify RAG search type. Please check your query and try again."
    elif rag_result["rag_type"].lower() == "image":
        return "Image RAG search is not implemented yet."
    elif rag_result["rag_type"].lower() == "text":
        return "Text RAG search is not implemented yet."
    elif rag_result["rag_type"].lower() == "pdf":
        similar_search_output = RAG_FILES.rag.find_similar_documents(query, file_path)
        similar_search_output_str = "\n".join(
            [f"Document {i + 1}: {doc.page_content}" for i, doc in enumerate(similar_search_output)]
        )
        gen_ai_search_output = RAG_FILES.rag.search_similar_chunks_genai(query, [doc.page_content for doc in
                                                                                 similar_search_output])
        gen_ai_search_output_str = "\n".join(
            [f"Document {i + 1}: {doc.page_content}" for i, doc in enumerate(gen_ai_search_output)]
        )
        return f"\n\nSimilarity Search Results:\n{similar_search_output_str}\n\nGenAI Search Results:\n{gen_ai_search_output_str}"
    else:
        return "Error: Unsupported RAG search type. Please check your query and file type."


def classify_message_type(state: State):
    """
    Classifies the latest message in the conversation as either requiring an LLM response or a tool response.
    """
    print("\t\t----Node is classify_message")
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
    for msg in state["messages"][:-1]:
        history_parts.append(f"{msg.type}: {msg.content}")
    history = "\n".join(history_parts)

    classified_llm = llm.with_structured_output(message_classifier)

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
5  **RAG Search**: If the user asks for RAG search, classify as 'tool' and use the RAG search tool.
4. Otherwise, classify as 'llm'.

**Examples of 'llm' messages**:
- Greetings (like "hi", "hello")
- General questions or statements
- If user mentioned chatbot, ai, or assistant then must classify as 'llm'
**BE CONSERVATIVE** with tool usage - when in doubt, classify as 'llm'.
If the user says to use the AI or LLM, do NOT use a tool, even if tool keywords are present.
    """
    result = classified_llm.invoke([
        HumanMessage(content=system_prompt),
        HumanMessage(content=content)
    ])
    console.print(f"[u][red]Message classified as[/u][/red]: {result.message_type}")
    return {"message_type": result.message_type}


def route_message(state: State):
    """
    Determines the next node in the workflow based on the classified message type.
    """
    console.print("\t\t[bold][green]----Node is router[/bold][/green]")
    message_type = state.get("message_type", "llm")
    return {'message_type': message_type}


def generate_llm_response(state: State) -> dict:
    """
    Generates a response using the LLM based on the conversation history and the latest user message.
    Shows a spinner while generating the response.
    """
    console.print("\t\t----[bold][green]Node is chatBot[/bold][/green]")
    history = "\n".join(
        f"{msg.type}: {msg.content}" for msg in state["messages"][:-1]
    )
    latest_message = state["messages"][-1].content if state["messages"] else ""
    system_prompt = (
        "You are a next-generation AI assistant that references the full conversation history "
        "and relevant context to provide more natural, context-rich, and accurate answers to user questions. "
        "Leverage any results from available tools in your reasoning. "
        "Always answer the user prompt using a fixed JSON object key `response` with value as your answer. "
        "For example: {\"response\": \"Your answer here.\"}\n\n"
        "Conversation History:\n"
        f"{history}\n\n"
        "Latest Message:\n"
        f"{latest_message}"
    )
    messages_with_system_prompt = [HumanMessage(content=system_prompt)]

    with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
        stream = llm.stream(messages_with_system_prompt)
        content = ""
        for part in stream:
            chunk = part.content if part.content is not None else ""
            content += chunk
    # Print AI message in modern style
    print_message(content, sender="ai")
    return {"messages": [AIMessage(content=content)]}


def tool_selection_agent(state: State) -> dict:
    """
    Selects and invokes the most appropriate tool for the user's request, or returns a message if no tool is needed.
    """
    console.print("\t\t----[bold][green]Node is tool_agent[/bold][/green]")
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
        selection = structured_llm.invoke([
            HumanMessage(content=system_prompt),
            HumanMessage(content=content)
        ])
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
                    result = tool.invoke(parameters)
                    # Print tool result in modern style
                    print_message(result, sender="tool")
                    return {"messages": [AIMessage(content=f"Result from {tool.name}: {result}")]}
                except Exception as e:
                    print(f"[ERROR] Error using tool {tool.name}: {e}")
                    return {"messages": [AIMessage(content=f"Error using {tool.name}: {str(e)}")]}
        print(f"[ERROR] Tool '{selection.tool_name}' not found.")
        return {"messages": [AIMessage(content=f"Tool '{selection.tool_name}' not found.")]}
    return {"messages": [AIMessage(content='No tool was used.')]}


def on_exit(state: State):
    """
    Handles cleanup and saving of conversation history when the chatbot session ends.
    """
    console.print("\t\t----[bold][red]Node is onExit[/bold][red]")
    history = []
    for msg in state["messages"]:
        history.append(
            {
                "type": msg.type,
                "content": msg.content
            }
        )
    json.dump(history, open("conversation_history.json", "w"), indent=2)
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
    state = {'messages': [], 'message_type': None}
    print_banner()
    console.print(Align.center("[bold blue]Welcome to the LangGraph Chatbot![/bold blue]"))
    console.print(Align.center("Type '[bold red]exit[/bold red]' to end the conversation.\n"))

    while True:
        user_input = Prompt.ask("[bold cyan]You[/bold cyan]", default="", show_default=False)
        if user_input.lower() == 'exit':
            print_message("Exiting the chatbot. Goodbye!", sender="ai")
            if state["messages"]:
                print_history(state["messages"])
            on_exit(state)
            rich.inspect(state)
            save_png("conversation_history.png")
            break
        state['messages'].append(HumanMessage(content=user_input))
        # Print user message in modern style
        print_message(user_input, sender="user")
        state = graph.invoke(state)
        # The AI/tool message is printed inside generate_llm_response/tool_selection_agent


# -------------------- TOOL ASSIGNMENTS --------------------

translate_tool = StructuredTool.from_function(
    func=translate_text,
    name="Translatetool",
    description="For translating messages into different languages.",
    args_schema=TranslationMessage,
)

search_tool = StructuredTool.from_function(
    func=duckduckgo_web_search,
    name="DuckDuckGoSearch",
    description="For general web searches (recent info, facts, news).",
    args_schema=duckduckgo_search,
)

rag_search_tool = StructuredTool.from_function(
    func=rag_search_classifier,
    name="RAGSearch",
    description="For searching the knowledge base (RAG search).",
    args_schema=rag_search_message,
)

tools = [search_tool, translate_tool, rag_search_tool]

# -------------------- GRAPH SETUP --------------------

graph_builder = StateGraph(State)
graph_builder.add_node("classifier", classify_message_type)
graph_builder.add_node("router", route_message)
graph_builder.add_node("chatBot", generate_llm_response)
graph_builder.add_node("tool_agent", tool_selection_agent)

graph_builder.add_edge(START, "classifier")
graph_builder.add_edge('classifier', 'router')
graph_builder.add_conditional_edges(
    'router',
    lambda state_updates: state_updates["message_type"],
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
    except httpcore.ConnectError:
        print("\nConnection error. Please turn on the Ollama server and try again.")
