from src.agents.agents_schema.agents_schema import message_classifier
from src.config import settings
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

    explicit_ai_phrases = ["/use ai", "/use llm"]
    lowered_content = content.lower()
    for phrase in explicit_ai_phrases:
        if phrase in lowered_content:
            if settings.socket_con:
                settings.socket_con.send_error(f"[LOG] Removing explicit AI phrase: {phrase}")
            else:
                print(f"[LOG] Removing explicit AI phrase: {phrase}")
            last_message.content = last_message.content.replace(phrase, "")
            console.print(f"[u][red]Message classified as[/u][/red]: llm (explicit user request override)")
            return {"message_type": "llm"}

    explicit_tool_phrases = ["/search", "/use tool"]
    for phrase in explicit_tool_phrases:
        if phrase in lowered_content:
            if settings.socket_con:
                settings.socket_con.send_error(f"[LOG] Removing explicit tool phrase: {phrase}")
            else:
                print(f"[LOG] Removing explicit tool phrase: {phrase}")
            last_message.content = last_message.content.replace(phrase, "")
            console.print(f"[u][red]Message classified as[/u][/red]: tool (explicit user request override)")
            return {"message_type": "tool"}

    # Build history from state messages directly
    history_parts = []
    for msg in messages[:-1]:
        history_parts.append(f"{msg.type}: {msg.content}")
    history = "\n".join(history_parts)

    llm = ModelManager(model=settings.CLASSIFIER_MODEL, temperature=0.5, format="json")

    classified_llm = llm.with_structured_output(message_classifier)

    system_prompt = F"""You are an intelligent conversation analyzer that understands context and user intent.

**Your Task:** Analyze the user's message within the full conversation context to determine if they need:
- 'llm': Direct conversation, reasoning, or explanation
- 'tool': External information or specific actions

**Conversation Context:**
{history}

**Current Message:**
{content}

**Smart Classification Rules:**

1. **Context-Aware Analysis:**
   - Consider what the user discussed previously
   - Look for references to earlier messages ("that", "it", "the previous", "what we talked about")
   - Understand follow-up questions and clarifications

2. **Tool Usage Indicators:**
   - Explicit requests: "search", "find", "look up", "translate", "rag search"
   - Need for current/external information: "latest news", "recent updates", "current price"
   - Document analysis: "search in the document", "find in the knowledge base"

3. **LLM Response Indicators:**
   - Explanations of previous results: "explain that", "what does this mean", "clarify"
   - Reasoning about conversation: "why did you say", "how does this relate"
   - General conversation: greetings, opinions, analysis of provided information
   - Follow-up questions about tool results

4. **Override Rules:**
   - User explicitly says "use AI/assistant/LLM" → always 'llm'
   - User explicitly says "search/tool" → always 'tool'

**Key Insight:** If the user is asking about or referencing something already discussed or provided in the conversation, they likely want explanation/reasoning (llm), not new information (tool).

Classify thoughtfully based on true user intent, not just keywords."""
    result = classified_llm.invoke([
        settings.HumanMessage(content=system_prompt),
        settings.HumanMessage(content=content)
    ])
    console.print(f"[u][red]Message classified as[/u][/red]: {result.message_type}")
    return {"message_type": result.message_type}
