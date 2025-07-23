from rich.console import Console

with Console().status("[bold green]Loading LangGraph Chatbot...[/bold green]", spinner="dots"):
    import json
    import os
    from typing import Annotated, Literal, List
    import httpx
    import requests
    import winsound
    from langchain_core.messages import HumanMessage, AIMessage
    from langchain_core.tools import StructuredTool
    from src.utils.model_manager import ModelManager
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from pydantic import Field, BaseModel
    from rich.align import Align
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from typing_extensions import TypedDict
    from rich import inspect

    # project imports
    from src.config import settings as config
    from src.RAG.RAG_FILES import neo4j_rag
    from src.RAG.RAG_FILES import rag
    from src.tools.lggraph_tools.tools import search_google_tool
    # Import socket manager
    from src.utils.socket_manager import socket_manager

# Get the shared socket connection
socket_con = socket_manager.get_socket_connection()


# -------------------- STRUCTURED CLASSES --------------------


class TranslationMessage(BaseModel):
    message: str = Field(
        description="The message to translate. Provide the text you want to translate into the targeted language."
    )
    target_language: str = Field(
        description="The language to translate the message into. Use ISO 639-1 codes (e.g., 'en' for English, 'hi' for Hindi)."
    )


class google_search(BaseModel):
    query: str = Field(
        description="Search query for GoogleSearch. Use this to find information on the web. provide a clear and concise query.", )


class rag_search_message(BaseModel):
    query: str = Field(
        description="the query for the RAG search, Provide the meaningful query to search in the knowledge base. with no special characters or symbols. or json objects",
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

llm = ModelManager(
    model=config.DEFAULT_MODEL,
    format="json",
    temperature=0.7,
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
    if config.ENABLE_SOUND_NOTIFICATIONS:
        winsound.Beep(7200, 200)  # Play a sound for new message


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
    url = config.TRANSLATION_API_URL
    data = {
        "q": message,
        "source": "auto",
        "target": target_language,
        "format": "text"
    }
    response = requests.post(url, json=data)
    return f"[Translated to {target_language}]: {response.json().get('translatedText', message)}"


def google_web_search(query: str) -> any:
    """
    Performs a web search using DuckDuckGo and returns the result.
    """
    response = search_google_tool(query)
    snippets_in_response = ""
    if 'items' in response:
        "".join([f"\n{item['snippet']}" for item in response['items']])
    print(snippets_in_response)
    system_prompt = (
        "You are an intelligent web search assistant that provides comprehensive, accurate answers based on search results.\n\n"

        "**Your Task:**\n"
        "Analyze the user's search query and the web search results to provide a clear, informative response that directly answers their question.\n\n"

        "**What You'll Receive:**\n"
        "- User's original search query\n"
        "- Search results with snippets from various web sources\n\n"

        "**Your Response Should:**\n"
        "1. **Directly answer the user's question** based on the search results\n"
        "2. **Synthesize information** from multiple sources when relevant\n"
        "3. **Provide context and explanation** to help the user understand\n"
        "4. **Be comprehensive but concise** - aim for 300-600 words\n"
        "5. **Focus on the most current and relevant information**\n\n"

        "**Response Style:**\n"
        "- Write in a conversational, helpful tone\n"
        "- Organize information logically\n"
        "- Include specific details and facts from the search results\n"
        "- If information is conflicting or unclear, mention this\n"
        "- If search results don't fully answer the query, acknowledge this\n\n"

        "**Output Format:**\n"
        "Return a JSON object with this structure:\n"
        "{\n"
        '  \"feature_snippet\": \"Your comprehensive, well-organized answer here\"\n'
        "}\n\n"

        "Remember: Your goal is to be as helpful as possible by providing the user with exactly the information they're looking for, presented in a clear and understandable way."
    )
    with console.status("[bold green]Searching...[/bold green]", spinner="dots"):
        llm = ModelManager(model=config.CLASSIFIER_MODEL, temperature=0.7, format="json")
        result = llm.invoke(
            [HumanMessage(content=system_prompt),
             HumanMessage(content=f"Query: {query}\nResponse: {snippets_in_response}")])
    #     we can also return the result as AIMessage and its metadata
    return result.content


def retrieve_knowledge_graph(query: str) -> str:
    """
    Retrieves information from the knowledge graph based on a query.
    Convert the user's query to the Cypher query format and return the results from the knowledge graph.
    """
    get_all_l_n = neo4j_rag.get_all_labels_and_names()
    labels = get_all_l_n.get("labels", [])
    names = get_all_l_n.get("names", [])

    socket_con.send_error(f"[LOG] CYPHER QUERY GENERATION STARTED with {len(labels)} labels, {len(names)} names")

    # If no names available, return early
    if not names:
        socket_con.send_error("[ERROR] No entity names available in knowledge graph")
        return "[ERROR] Knowledge graph appears to be empty. Please ensure data is loaded."

    # Get actual relationship types from database
    relationship_types = neo4j_rag.get_all_relationship_types()

    socket_con.send_error(f"[LOG] Available relationship types: {relationship_types[:10]}... (total {len(relationship_types)})")

    # Debug: Check if (user query name) and email-related terms exist
    name_found = any(query in name.lower() for name in names)
    email_relations = [rt for rt in relationship_types if "email" in rt.lower()]

    socket_con.send_error(f"[DEBUG] '{query}' found in entity names: {name_found}")
    socket_con.send_error(f"[DEBUG] Email-related relationships: {email_relations}")
    socket_con.send_error(f"[DEBUG] User query: '{query}'")

    # Create enhanced prompt with complete workflow and decision logic
    SYSTEM_PROMPT_CYPHER_GENERATION = f"""
═══════════════════════════════════════════════════════════════════════════════
🧠 INTELLIGENT NEO4J CYPHER QUERY GENERATOR WITH ENHANCED WORKFLOW
═══════════════════════════════════════════════════════════════════════════════

**MISSION:** You are an intelligent Cypher query generator that follows a structured workflow to understand user intent and generate optimal queries.

**DATABASE SCHEMA (MANDATORY - NO EXCEPTIONS):**
- ALL nodes have label "Entity" with property "name"
- ALL relationships have label "RELATION" with property "type"
- NO other labels exist in this database

**AVAILABLE DATA CONTEXT:**
📋 ENTITY NAMES: {names}
🔗 RELATIONSHIP TYPES: {relationship_types}
🏷️ LABELS: {labels}

**USER QUERY:** "{query}"

═══════════════════════════════════════════════════════════════════════════════
🔄 ENHANCED WORKFLOW - FOLLOW THIS EXACT PROCESS:
═══════════════════════════════════════════════════════════════════════════════

**STEP 1: PARSE QUERY TOKENS**
- Break down user query into individual words/tokens
- Identify potential entity names and relationship hints

**STEP 2: MATCH AGAINST AVAILABLE DATA**
- Match tokens against AVAILABLE ENTITY NAMES (use fuzzy matching for misspellings)
- Match tokens against AVAILABLE RELATIONSHIP TYPES (use fuzzy matching)
- Example: "email" → matches "has email address" from relationship types

**STEP 3: DETERMINE QUERY TYPE USING LLM DECISION LOGIC**

🎯 **TYPE 1: ENTITY_ONLY_SEARCH**
- **Condition:** User mentions entity name(s) only, no relationship hints
- **Pattern:** MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('ENTITY_NAME') RETURN s, r, o
- **Example:** Query "raghav" → Find all connections for raghav

🎯 **TYPE 2: RELATIONSHIP_ONLY_SEARCH**  
- **Condition:** User mentions relationship type only, no specific entity
- **Pattern:** MATCH (s:Entity)-[r:RELATION]-(o:Entity) WHERE toLower(r.type) CONTAINS toLower('RELATIONSHIP_TYPE') RETURN s, r, o
- **Example:** Query "email" → Find all email relationships

🎯 **TYPE 3: COMBINED_SEARCH**
- **Condition:** User mentions both entity name(s) AND relationship type
- **Pattern:** MATCH (s:Entity)-[r:RELATION]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('ENTITY_NAME') AND toLower(r.type) CONTAINS toLower('RELATIONSHIP_TYPE') RETURN s, r, o
- **Example:** Query "raghav email" → Find raghav's email specifically

**STEP 4: GENERATE CYPHER PATTERN**
Based on determined query type, generate appropriate Cypher query.

═══════════════════════════════════════════════════════════════════════════════
📚 MANDATORY EXAMPLES - FOLLOW THESE PATTERNS:
═══════════════════════════════════════════════════════════════════════════════

**ENTITY_ONLY_SEARCH Examples:**
Query: "raghav"
Analysis: Found "raghav" in entity names, no relationship detected
Type: ENTITY_ONLY_SEARCH
Response: {{"cypher_query": "MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('raghav') RETURN s, r, o LIMIT 20", "reasoning": "Entity-only search for raghav and all connections"}}

Query: "Microsoft Azure"  
Analysis: Found "Microsoft" and "Azure" in entity names, no relationship detected
Type: ENTITY_ONLY_SEARCH
Response: {{"cypher_query": "MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('Microsoft') OR toLower(o.name) CONTAINS toLower('Azure') RETURN s, r, o LIMIT 20", "reasoning": "Entity search for Microsoft and Azure related connections"}}

**RELATIONSHIP_ONLY_SEARCH Examples:**
Query: "email" or "has email address"
Analysis: "email" matches "has email address" in relationship types, no specific entity
Type: RELATIONSHIP_ONLY_SEARCH  
Response: {{"cypher_query": "MATCH (s:Entity)-[r:RELATION]-(o:Entity) WHERE toLower(r.type) CONTAINS toLower('has email address') RETURN s, r, o LIMIT 20", "reasoning": "Relationship-only search for all email address connections"}}

Query: "works at" or "employment"
Analysis: "works at" found in relationship types, no specific entity
Type: RELATIONSHIP_ONLY_SEARCH
Response: {{"cypher_query": "MATCH (s:Entity)-[r:RELATION]-(o:Entity) WHERE toLower(r.type) CONTAINS toLower('works at') RETURN s, r, o LIMIT 20", "reasoning": "Relationship-only search for all employment connections"}}

**COMBINED_SEARCH Examples:**
Query: "raghav email" or "raghav has email"
Analysis: "raghav" in entity names + "email" matches "has email address" in relationships
Type: COMBINED_SEARCH
Response: {{"cypher_query": "MATCH (s:Entity)-[r:RELATION]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('raghav') AND toLower(r.type) CONTAINS toLower('has email address') RETURN s, r, o LIMIT 20", "reasoning": "Combined search for raghav's email address relationships"}}

Query: "john works at"
Analysis: "john" in entity names + "works at" in relationship types  
Type: COMBINED_SEARCH
Response: {{"cypher_query": "MATCH (s:Entity)-[r:RELATION]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('john') AND toLower(r.type) CONTAINS toLower('works at') RETURN s, r, o LIMIT 20", "reasoning": "Combined search for john's employment relationships"}}

═══════════════════════════════════════════════════════════════════════════════
⚠️ CRITICAL RULES - NEVER VIOLATE THESE:
═══════════════════════════════════════════════════════════════════════════════

1. **FORBIDDEN LABELS:** NEVER use :User, :Person, :Company, :Organization - ONLY use :Entity and :RELATION
2. **FUZZY MATCHING:** Use your intelligence to match user terms to available data (handle misspellings)
3. **CASE INSENSITIVE:** ALWAYS use toLower() for all string comparisons
4. **JSON FORMAT:** ALWAYS return valid JSON with "cypher_query" and "reasoning" keys
5. **LIMIT RESULTS:** ALWAYS add LIMIT 20 to prevent overwhelming results
6. **USE AVAILABLE DATA:** Only reference entities and relationships from the provided lists
7. **FLEXIBLE MATCHING:** Use CONTAINS instead of exact matches for better results

═══════════════════════════════════════════════════════════════════════════════
🎯 SMART MATCHING LOGIC:
═══════════════════════════════════════════════════════════════════════════════

**Entity Matching:**
- "raghav" → exact match in entity names
- "micro" → fuzzy match to "Microsoft" in entity names
- "john" → exact match in entity names

**Relationship Matching:**
- "email" → fuzzy match to "has email address" in relationship types
- "work" → fuzzy match to "works at" in relationship types  
- "phone" → fuzzy match to "has phone number" in relationship types
- "manage" → fuzzy match to "manages" in relationship types

**OUTPUT FORMAT (MANDATORY):**
Return ONLY valid JSON: {{"cypher_query": "YOUR_CYPHER_HERE", "reasoning": "YOUR_REASONING_HERE"}}

**FINAL INSTRUCTION:** Analyze the user query "{query}" using the workflow above and generate the most appropriate Cypher query based on available data and detected intent.
"""

    def try_generate_cypher(model_name, temperature=0.3):
        """Try to generate cypher with a specific model"""
        try:
            llm = ModelManager(
                model=model_name,
                temperature=temperature,
                format="json"
            )

            result = llm.invoke([HumanMessage(content=SYSTEM_PROMPT_CYPHER_GENERATION)])
            socket_con.send_error(f"[DEBUG] generating cypher queries response: {result.content}")

            # Parse JSON response
            try:
                parsed = json.loads(result.content.strip())

                # Check for correct key and fix if needed
                if "cypher_query" in parsed:
                    cypher_query_text = parsed["cypher_query"]
                elif "query" in parsed:
                    # Fix the wrong key
                    socket_con.send_error("[WARNING] Model used 'query' instead of 'cypher_query', fixing...")
                    cypher_query_text = parsed["query"]
                else:
                    socket_con.send_error(f"[ERROR] No valid query key found in: {parsed}")
                    return None

                # Validate and fix the cypher query structure
                if cypher_query_text:
                    # Check if it uses wrong labels like :User, :Person, etc.
                    import re
                    wrong_labels = re.findall(r':(?:User|Person|Company|Organization|Node)', cypher_query_text,
                                              re.IGNORECASE)
                    if wrong_labels:
                        socket_con.send_error(f"[WARNING] Found wrong labels {wrong_labels}, fixing to :Entity")
                        # Replace wrong labels with :Entity
                        cypher_query_text = re.sub(r':(?:User|Person|Company|Organization|Node)', ':Entity',
                                                   cypher_query_text, flags=re.IGNORECASE)

                    # Check if it uses the correct pattern
                    if not re.search(r'MATCH\s*\([^)]*:Entity[^)]*\)', cypher_query_text, re.IGNORECASE):
                        socket_con.send_error("[WARNING] Query doesn't use correct Entity pattern, generating fallback")
                        # Generate a proper fallback query
                        query_words = [word.lower() for word in query.split() if len(word) > 2]
                        if query_words and names:
                            search_term = query_words[0]
                            cypher_query_text = f"MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('{search_term}') RETURN s, r, o LIMIT 20"
                            socket_con.send_error(f"[WARNING] Generated fallback query: {cypher_query_text}")

                    return {"cypher_query": cypher_query_text,
                            "reasoning": parsed.get("reasoning", "Generated cypher query")}

            except json.JSONDecodeError as e:
                socket_con.send_error(f"[ERROR] JSON parsing failed for {model_name}: {e}")

                # Try to extract cypher query manually
                import re
                cypher_match = re.search(r'MATCH.*?RETURN.*?(?:LIMIT.*?)?', result.content, re.IGNORECASE | re.DOTALL)
                if cypher_match:
                    extracted_query = cypher_match.group().strip()
                    socket_con.send_error(f"[WARNING] Extracted cypher manually: {extracted_query}")
                    return {"cypher_query": extracted_query, "reasoning": f"Manually extracted for query: {query}"}

                return None

        except Exception as e:
            socket_con.send_error(f"[ERROR] Model {model_name} failed completely: {e}")
            return None

    # Try different models in order of preference
    cypher_result = None

    # Try CLASSIFIER_MODEL first (usually most reliable for structured output)
    cypher_result = try_generate_cypher(config.CLASSIFIER_MODEL)

    # Try CYPHER_MODEL if first failed
    if not cypher_result:
        socket_con.send_error("[WARNING] Trying CYPHER_MODEL")
        cypher_result = try_generate_cypher(config.CYPHER_MODEL)

    # Try DEFAULT_MODEL if still failed
    if not cypher_result:
        socket_con.send_error("[WARNING] Trying DEFAULT_MODEL")
        cypher_result = try_generate_cypher(config.DEFAULT_MODEL)

    # Generate fallback query if all models failed
    if not cypher_result:
        socket_con.send_error("[WARNING] All models failed, generating smart fallback")

        # Find relevant entities based on query keywords
        query_words = [word.lower() for word in query.split() if len(word) > 2]
        relevant_entities = []

        for name in names[:50]:
            name_lower = name.lower()
            for word in query_words:
                if word in name_lower:
                    relevant_entities.append(name)
                    break

        if relevant_entities:
            target_entity = relevant_entities[0]
            fallback_query = f"MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('{target_entity}') RETURN s, r, o LIMIT 20"
        else:
            # Use first available entity as last resort
            target_entity = names[0]
            fallback_query = f"MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('{target_entity}') RETURN s, r, o LIMIT 20"

        cypher_result = {
            "cypher_query": fallback_query,
            "reasoning": f"Fallback query using entity '{target_entity}' for user query: {query}"
        }
        socket_con.send_error(f"[WARNING] Using fallback query: {fallback_query}")

    # Extract final query
    final_cypher = cypher_result.get("cypher_query", "")
    reasoning = cypher_result.get("reasoning", "")

    if not final_cypher:
        return f"[ERROR] Failed to generate any valid cypher query for: {query}"

    socket_con.send_error(f"[LOG] FINAL CYPHER QUERY: {final_cypher}")
    socket_con.send_error(f"[LOG] REASONING: {reasoning}")

    # Execute the cypher query
    receive_triples = neo4j_rag.get_retrieve_triples(final_cypher)

    if not receive_triples:
        return f"[ERROR] No results found for the query: {query}. Please try a different query."

    # Convert the triples to a readable format by llm                   
    triples_text = "\n".join(
        [neo4j_rag.extract_triple_text(triple) for triple in receive_triples])

    # Create a simple, user-friendly explanation prompt
    explanation_prompt = (
        f"You are an AI assistant explaining knowledge graph results in simple language. (never say that to user that yuo are explaining the nodes/database )\n\n"
        f"ORIGINAL USER QUESTION: {_state['messages'][-1].content}\n"
        f"SEARCH QUERY USED: '{query}'\n\n"
        f"KNOWLEDGE GRAPH CONNECTIONS FOUND:\n{triples_text}\n\n"
        "INSTRUCTIONS:\n"
        "1. Focus specifically on answering the user's original question\n"
        "2. Explain these connections in simple, everyday language\n"
        "3. Highlight relationships that are most relevant to what the user asked\n"
        "4. Avoid technical terms like 'knowledge graph', 'triple', 'cypher', or 'database'\n"
        "5. Use conversational language as if explaining to someone new to this topic\n"
        "6. Focus on what these things are, how they relate, and why they matter\n\n"
        "Now, provide a clear, friendly explanation that directly addresses what the user wanted to know:\n"
        """
        **Reasoning:**
          - Clearly separates the user's question, search query, and results for better context
          - Provides explicit instructions to focus on the user's original intent
          - Structures the prompt to emphasize answering what the user asked, not just explaining the triples
          - Maintains requirements for simple, non-technical language
          - Uses a numbered list format for clearer instructions to the LLM
          - Removes awkward phrasing from the original prompt
          - Ends with a direct call to action that reinforces addressing the user's query
          
        **OUTPUT FORMAT:**
        Return a JSON object with this structure:
        {
          "explanation": "Your clear, friendly explanation here"
        }
        """)

    # Use a non-JSON format LLM for better natural language response
    explanation_llm = ModelManager(
        model=config.CLASSIFIER_MODEL,
        temperature=0.6,
        format="json"  # Remove JSON formatting for natural response
    )

    with console.status("[bold green]Generating explanation...[/bold green]", spinner="dots"):
        explanation_result = explanation_llm.invoke([HumanMessage(content=explanation_prompt)])

    # Clean up the response and return just the explanation
    explanation = explanation_result.content.strip()

    # Remove any JSON formatting if it accidentally appears
    if explanation.startswith('{"explanation":') and explanation.endswith('}'):
        try:
            parsed = json.loads(explanation)
            explanation = parsed.get("explanation", explanation)
        except json.JSONDecodeError:
            pass  # Keep original if parsing fails

    return explanation


def rag_search_classifier(query: str) -> str:
    """
    Determines the appropriate RAG (Retrieval-Augmented Generation) search type based on the query and file type,
    and performs the search if supported.
    """
    if config.ENABLE_SOUND_NOTIFICATIONS:
        winsound.Beep(7200, 200)  # Play a sound to indicate the start of RAG search
    file_path = Prompt.ask("Enter FILE PATH TO RAG SEARCH",
                           default=str(config.DEFAULT_RAG_EXAMPLE_FILE_PATH))
    system_prompt = """
    You are an intelligent RAG system selector that understands both user intent and document characteristics.
    
    **Your Mission:**
    Analyze the user's question and the document content to choose the most effective search approach.
    
    **Understanding the User's Intent:**
    - Look at their current question AND the conversation history
    - Consider what type of answer they're seeking
    - Understand if they're asking about relationships, facts, summaries, or explanations
    
    **Available RAG Types:**
    
    1. **Knowledge Graph RAG** - Best for:
       - Questions about relationships: "How is X connected to Y?"
       - Entity-focused queries: "What companies work with Microsoft?"
       - Network analysis: "Show me the connections between..."
       - Structured data with clear entities and relationships
    
    2. **Text RAG** - Best for:
       - Content summaries: "What is this document about?"
       - Detailed explanations: "Explain how X works"
       - Narrative information: stories, procedures, descriptions
       - Unstructured text content
    
    **Smart Decision Making:**
    - If the user previously mentioned a specific RAG type, respect their preference
    - Consider the document structure - does it contain entities and relationships, or is it narrative text?
    - Think about what would give the user the most useful answer
    
    **Context Awareness:**
    - Review the conversation history to understand the user's ongoing needs
    - If they're building on a previous question, consider continuity
    - Look for implicit preferences based on their question style
    
    **EXPLICIT INSTRUCTIONS:**
    - If the user explicitly asks for a knowledge graph search, prioritize that
    - If they ask for a text search, prioritize that
    
    **Response Format:**
    {
      "selected_rag_type": "knowledge_graph" or "text",
      "reasoning": "Clear explanation of why this choice best serves the user's needs, considering both their question and the document characteristics"
    }
    
    Make the choice that will be most helpful to the user based on what they're actually trying to accomplish.
"""
    prompt = f"""
    available_RAG_types: {"knowledge_graph", "text"}
    user_query: "{query}"
    chunks: "{rag.load_pdf_document(file_path)[0:5]}"
    history: {_state['messages']}
"""

    llm = ModelManager(
        model=config.CLASSIFIER_MODEL,
        temperature=0.7,
        format="json",
    )
    prompt_list = [HumanMessage(content=system_prompt),
                   HumanMessage(content=prompt)]
    with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
        llm_response = llm.invoke(prompt_list)
    print("\n\nLLM Response:", llm_response.content)

    try:
        response_json = json.loads(llm_response.content)
    except json.JSONDecodeError:
        return f"[ERROR] Failed to parse LLM response: {llm_response.content}. Please check the LLM output format."

    selected_rag_type = response_json.get("selected_rag_type")
    reasoning = response_json.get("reasoning", "No reasoning provided.")
    if selected_rag_type == "knowledge_graph":
        if config.ENABLE_SOUND_NOTIFICATIONS:
            winsound.Beep(7200, 200)  # Play a sound to indicate knowledge graph RAG search
        if Prompt.ask("LLm selected knowledge graph RAG type", choices=["yes", "no"], default="no") == "no":
            exit()
        # clear the knowledge graph and save the new one
        rag.save_knowledge_graph_gemini_api(file_path)
        result = retrieve_knowledge_graph(query)
        return f"Knowledge Graph Search Results for '{query}':\n\n{result}"
    elif selected_rag_type == "text":
        return f"{rag.text_rag_search_using_llm(query, rag.load_pdf_document(file_path))}"
    else:
        return f"[ERROR] Unsupported RAG type: {selected_rag_type}. Reasoning: {reasoning}"


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
            if socket_con:
                socket_con.send_error(f"[LOG] Removing explicit AI phrase: {phrase}")
            else:
                print(f"[LOG] Removing explicit AI phrase: {phrase}")
            last_message.content = last_message.content.replace(phrase, "")
            console.print(f"[u][red]Message classified as[/u][/red]: llm (explicit user request override)")
            return {"message_type": "llm"}

    explicit_tool_phrases = ["/search", "/use tool"]
    for phrase in explicit_tool_phrases:
        if phrase in lowered_content:
            if socket_con:
                socket_con.send_error(f"[LOG] Removing explicit tool phrase: {phrase}")
            else:
                print(f"[LOG] Removing explicit tool phrase: {phrase}")
            last_message.content = last_message.content.replace(phrase, "")
            console.print(f"[u][red]Message classified as[/u][/red]: tool (explicit user request override)")
            return {"message_type": "tool"}

    history_parts = []
    for msg in state["messages"][:-1]:
        history_parts.append(f"{msg.type}: {msg.content}")
    history = "\n".join(history_parts)

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
        "You are an intelligent AI assistant with deep reasoning capabilities and full conversation awareness.\n\n"

        "**Your Core Abilities:**\n"
        "- Understand context from the entire conversation, not just the latest message\n"
        "- Reason about relationships between different parts of our discussion\n"
        "- Explain complex topics in simple, clear language\n"
        "- Reference and build upon previous exchanges naturally\n"
        "- Provide thoughtful analysis and insights\n\n"

        "**Context Analysis:**\n"
        "- When users refer to 'that', 'it', 'the previous result', or 'what we discussed', understand what they mean\n"
        "- Connect current questions to earlier topics in our conversation\n"
        "- Explain how different pieces of information relate to each other\n"
        "- Clarify and expand on previous responses when asked\n\n"

        "**Available Capabilities:**\n"
        f"I have access to these tools when needed: {', '.join([tool.name for tool in tools])}\n"
        "But right now, you're asking me to think and reason, not to use external tools.\n\n"

        "**Our Conversation So Far:**\n"
        f"{history}\n\n"

        "**Your Current Question/Request:**\n"
        f"{latest_message}\n\n"

        "**Instructions:**\n"
        "- Respond naturally and conversationally\n"
        "- Reference our conversation history when relevant\n"
        "- Explain your reasoning clearly\n"
        "- If you're unsure about something from our conversation, ask for clarification\n"
        "- Always return a valid JSON object: {{\"response\": \"Your thoughtful response here\"}}\n\n"

        "Think about what the user really wants to know, considering everything we've discussed together."
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
            model=config.CLASSIFIER_MODEL,
            format="json",
            temperature=0.7,
            stream=False
        ).with_structured_output(ToolSelection)
        with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
            selection = structured_llm.invoke([
                HumanMessage(content=system_prompt),
                HumanMessage(content=content)
            ])
        print("Tool selected:", selection.tool_name)
        print("Reasoning:", selection.reasoning)
        print("Parameters:", selection.parameters)
    except Exception as e:
        if socket_con:
            socket_con.send_error(f"[ERROR] Exception in tool_agent: {e}")
        else:
            print(f"[ERROR] Exception in tool_agent: {e}")
        return {"messages": [AIMessage(content=f"Error processing tool selection: {str(e)}")]}
    parameters = selection.parameters
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except Exception as e:
            if socket_con:
                socket_con.send_error(f"[ERROR] Could not parse parameters: {e}")
            else:
                print(f"[ERROR] Could not parse parameters: {e}")
            pass
    #     -------- tool selection and parameter handling --------
    if selection.tool_name and selection.tool_name.lower() == "GoogleSearch":
        query = parameters.get("query")
        if isinstance(query, dict):
            query_str = query.get("value") or query.get("example") or ""
            if not query_str:
                query_str = input("Please enter your search query for GoogleSearch: ")
            parameters["query"] = query_str
        elif not isinstance(query, str):
            parameters["query"] = input("Please enter your search query for GoogleSearch: ")
    if selection.tool_name and selection.tool_name.lower() != "none":
        for tool in tools:
            if tool.name.lower() == selection.tool_name.lower():
                try:
                    result = tool.invoke(parameters)
                    # Print tool result in modern style
                    print_message(result, sender="tool")
                    return {"messages": [AIMessage(content=f"Result from {tool.name}: {result}")]}
                except Exception as e:
                    if socket_con:
                        socket_con.send_error(
                            f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__}")
                    else:
                        print(f"[ERROR] Error using tool {tool.name}: {e} function: {tool.func.__name__}")
                    return {"messages": [AIMessage(content=f"Error using {tool.name}: {str(e)}")]}
        if socket_con:
            socket_con.send_error(f"[ERROR] Tool '{selection.tool_name}' not found.")
        else:
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
    global _state
    global tools_context
    tools_context = "\n\n".join([
        f"Tool: {tool.name}\nDescription: {tool.description}\nParameters: {json.dumps(tool.args_schema.model_json_schema())}"
        for tool in tools
    ])
    os.system("cls" if os.name == 'nt' else "clear")
    _state = {'messages': [], 'message_type': None}
    print_banner()
    console.print(Align.center("[bold blue]Welcome to the LangGraph Chatbot![/bold blue]"))
    console.print(Align.center("Type '[bold red]exit[/bold red]' to end the conversation.\n"))

    while True:
        user_input = Prompt.ask("[bold cyan]You[/bold cyan]", default="", show_default=False)
        if user_input.lower() == 'exit':
            print_message("Exiting the chatbot. Goodbye!", sender="ai")
            if _state["messages"]:
                print_history(_state["messages"])
            on_exit(_state)
            inspect(_state)
            # save_png("conversation_history.png")
            break
        _state['messages'].append(HumanMessage(content=user_input))
        # Print user message in modern style
        print_message(user_input, sender="user")
        _state = graph.invoke(_state)
        # The AI/tool message is printed inside generate_llm_response/tool_selection_agent


# -------------------- TOOL ASSIGNMENTS --------------------

translate_tool = StructuredTool.from_function(
    func=translate_text,
    name="Translatetool",
    description="For translating messages into different languages.",
    args_schema=TranslationMessage,
)

search_tool = StructuredTool.from_function(
    func=google_web_search,
    name="GoogleSearch",
    description="For general web searches (recent info, facts, news).",
    args_schema=google_search,
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
    except httpx.ConnectError:
        if socket_con:
            socket_con.send_error("\nConnection error. Please turn on the Ollama server and try again.")
        else:
            print("\nConnection error. Please turn on the Ollama server and try again.")
# todo next we could make related to any social media tool like open insta or what's app search or message them