from src.config import settings
from src.tools.lggraph_tools.tool_assign import ToolAssign
from src.ui.diagnostics.debug_helpers import debug_info
from src.utils.model_manager import ModelManager


def classify_message_type(state) -> dict:
    """
    Classifies the latest message in the conversation as either requiring an LLM response or a tool response.
    """
    print("\t\t----Node is classify_message")
    console = settings.console

    # Access state directly from LangGraph parameter (no sync needed)
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    content = last_message.content if last_message else ""

    explicit_ai_phrases = ["/use ai", "/use llm", "/llm", "/ai", "/assistant"]
    lowered_content = content.lower()
    for phrase in explicit_ai_phrases:
        if phrase in lowered_content:
            if settings.socket_con:
                settings.socket_con.send_error(
                    f"[LOG] Removing explicit AI phrase: {phrase}"
                )
            else:
                debug_info(
                    "Explicit AI Phrase Detected",
                    f"Removing explicit AI phrase: {phrase}",
                    {"phrase": phrase},
                )
            last_message.content = last_message.content.replace(phrase, "")
            console.print(
                "[u][red]Message classified as[/u][/red]: llm (explicit user request override)"
            )
            return {"message_type": "llm"}

    explicit_tool_phrases = ["/use tool", "/tool"]
    for phrase in explicit_tool_phrases:
        if phrase in lowered_content:
            if settings.socket_con:
                settings.socket_con.send_error(
                    f"[LOG] Removing explicit tool phrase: {phrase}"
                )
            else:
                debug_info(
                    "Explicit Tool Phrase Detected",
                    f"Removing explicit tool phrase: {phrase}",
                    {"phrase": phrase},
                )
            last_message.content = last_message.content.replace(phrase, "")
            console.print(
                "[u][red]Message classified as[/u][/red]: tool (explicit user request override)"
            )
            return {"message_type": "tool"}
    explicit_agent_phrases = ["/use agent", "/agent", "/tool chain", "/agent mode"]
    for phrase in explicit_agent_phrases:
        if phrase in lowered_content:
            if settings.socket_con:
                settings.socket_con.send_error(
                    f"[LOG] Removing explicit agent phrase: {phrase}"
                )
            else:
                debug_info(
                    "Explicit Agent Phrase Detected",
                    f"Removing explicit agent phrase: {phrase}",
                    {"phrase": phrase},
                )
            last_message.content = last_message.content.replace(phrase, "")
            console.print(
                "[u][red]Message classified as[/u][/red]: agent (explicit user request override)"
            )
            return {"message_type": "agent"}

    # Build history from state messages directly
    history_parts = []
    for msg in messages[:-1]:
        history_parts.append(f"{msg.type}: {msg.content}")
    history = "\n".join(history_parts)

    llm = ModelManager(model=settings.GPT_MODEL, temperature=0.5)

    system_prompt = """You are an intelligent conversation analyzer that understands context and user intent.

**Your Task:** Analyze the user's message within the full conversation context to determine if they need:
- 'llm': Direct conversation, reasoning, or explanation
- 'tool': External information or specific actions


**Smart Classification Rules:**

1. **Context-Aware Analysis:**
   - Consider what the user discussed previously
   - Look for references to earlier messages ("that", "it", "the previous", "what we talked about")
   - Understand follow-up questions and clarifications

2. **Tool Usage Indicators:**
   - Explicit requests: "search", "find", "look up", "translate", "rag search"
   - Need for current/external information: "latest news", "recent updates", "current price"
   - Document analysis: "search in the document", "find in the knowledge base"

3. **LLM Usage Indicators:**
   - Explanations of previous results: "explain that", "what does this mean", "clarify"
   - Reasoning about conversation: "why did you say", "how does this relate"
   - General conversation: greetings, opinions, analysis of provided information
   - Follow-up questions about tool results
   
4. **Agent Usage Indicators:**
    - Explicit requests: agent, tool chain, agent mode
    - Need for complex reasoning or multi-step tasks: "perform web search", "write content in the text file", "analyze data"
    - General agent tasks that require combining multiple tools or reasoning steps
    - User asks for agent to perform a task that requires multiple steps or tools
    

4. **Override Rules:**
   - User explicitly says "use AI/assistant/LLM" → always 'llm'
   - User explicitly says "search/tool" → always 'tool'
    - User explicitly says "agent" → always 'agent'

**Key Insight:** If the user is asking about or referencing something already discussed or provided in the conversation, they likely want explanation/reasoning (llm), not new information (tool).
**Key Insight:** USER WILL BE PROVIDE THE (LAST MESSAGE), (CONVERSATION HISTORY) AND (TOOL CONTEXT), SO YOU CAN MAKE A DECISION BASED ON THE LAST MESSAGE AND TOOL CONTEXT.

**IMPORTANT:** Respond with valid JSON in this exact format:
{"message_type": "llm", "reasoning": "Your reasoning here"}
OR
{"message_type": "tool", "reasoning": "Your reasoning here"}
OR
{""message_type": "agent", "reasoning": "your reasoning here"}

Classify thoughtfully based on true user intent, not just keywords."""
    # modify the content and provide the history and tool context
    if not history:
        history = "No previous messages in this conversation."
    if not content:
        content = "No current message provided."
    # Add conversation context and tool context to the content
    tool_context = (
        "No tools available"
        if not ToolAssign.get_tools_list()
        else "\n".join(
            [
                f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {tool.args_schema}"
                for tool in ToolAssign.get_tools_list()
            ]
        )
    )

    content = f"""

        **Conversation Context:**
        {history}

        **Current Message:**
        {content}
        
        **Tool Context:**
        {tool_context}
    """

    response = llm.invoke(
        [
            settings.HumanMessage(content=system_prompt),
            settings.HumanMessage(content=content),
        ]
    )

    # Use the new JSON conversion method
    result_json = ModelManager.convert_to_json(response)

    # Create message_classifier object from JSON
    from dataclasses import dataclass

    @dataclass
    class MessageClassifier:
        message_type: str
        reasoning: str = ""

    result = MessageClassifier(
        message_type=result_json.get("message_type", "llm"),
        reasoning=result_json.get("reasoning", ""),
    )
    console.print(f"[u][red]Message classified as[/u][/red]: {result.message_type}")
    return {"message_type": result.message_type}
