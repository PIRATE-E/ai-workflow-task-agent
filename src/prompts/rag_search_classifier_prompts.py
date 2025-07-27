class Prompts:
    @staticmethod
    def get_system_prompt_cypher(names, relationship_types, labels, query):
        return f"""
        🧠 SIMPLIFIED ENTITY-FOCUSED CYPHER GENERATOR
        
        **MISSION:** Generate simple entity-focused queries to fetch ALL relationships, then let LLM reason about results.
        
        **DATABASE SCHEMA:**
        - Nodes: Entity (with property "name")
        - Relationships: RELATION (with property "type")
        
        **AVAILABLE ENTITY NAMES:** {names[:20]}... (showing first 20 of {len(names)} total)
        
        **USER QUERY:** "{query}"
        
        **🎯 NEW SIMPLIFIED APPROACH:**
        Instead of trying to match thousands of relationship types, we:
        1. Extract entity name from user query
        2. Fetch ALL relationships for that entity using [r*1..2]
        3. Let LLM reason about which relationships answer the user's question
        
        **ANALYSIS STEPS:**
        1. **Find Entity:** Look for entity name in user query from the provided names list
        2. **Generate Simple Query:** Create query to get all relationships for that entity
        3. **Use Variable-Length:** Use [r*1..2] to get comprehensive relationship data
        
        **SINGLE QUERY PATTERN:**
        MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('ENTITY_NAME') RETURN s, r, o LIMIT 50
        
        **EXAMPLES:**
        
        Query: "phone number of piyush"
        Analysis: Found "piyush" in entity names
        Response: {{"cypher_query": "MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('piyush') RETURN s, r, o LIMIT 50", "reasoning": "Fetching all piyush's relationships to let LLM find phone-related information"}}
        
        Query: "email of shreya"  
        Analysis: Found "shreya" in entity names
        Response: {{"cypher_query": "MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('shreya') RETURN s, r, o LIMIT 50", "reasoning": "Fetching all shreya's relationships to let LLM find email-related information"}}
        
        Query: "john works where"
        Analysis: Found "john" in entity names
        Response: {{"cypher_query": "MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('john') RETURN s, r, o LIMIT 50", "reasoning": "Fetching all john's relationships to let LLM find work-related information"}}
        
        Query: "microsoft projects"
        Analysis: Found "microsoft" in entity names  
        Response: {{"cypher_query": "MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('microsoft') RETURN s, r, o LIMIT 50", "reasoning": "Fetching all microsoft's relationships to let LLM find project-related information"}}
        
        **CRITICAL RULES:**
        1. **ALWAYS use [r*1..2]** - We want comprehensive relationship data
        2. **FOCUS on entity extraction** - Don't try to match relationship types
        3. **LIMIT 50** - Get enough data for LLM reasoning without overwhelming
        4. **Use CONTAINS** - Handle partial name matches and variations
        5. **toLower()** - Case insensitive matching
        
        **ENTITY EXTRACTION LOGIC:**
        - Look for any word in user query that matches names in the provided list
        - Use fuzzy matching: "piyush" matches "Piyush Kumar" 
        - Handle variations: "micro" can match "Microsoft"
        - If multiple entities found, use the first/most relevant one
        
        **OUTPUT FORMAT:**
        {{"cypher_query": "MATCH (s:Entity)-[r*1..2]-(o:Entity) WHERE toLower(s.name) CONTAINS toLower('ENTITY_NAME') RETURN s, r, o LIMIT 50", "reasoning": "Fetching all ENTITY_NAME's relationships to let LLM find QUERY_TYPE-related information"}}
        
        **FOR QUERY "{query}":**
        Extract entity name and generate the simple comprehensive query pattern above.
                """

    @staticmethod
    def get_system_prompt_classifier(StateAccessor, triples_text, query):
        return (
        f"You are a helpful person who knows information about people and can answer questions naturally.\n\n"
        f"Someone asked you: {StateAccessor().get_last_message()}\n"
        f"You searched for: '{query}'\n\n"
        f"Here's what you found:\n{triples_text}\n\n"
        "🚨 IMPORTANT - Read this carefully:\n"
        "1. Look through ALL the information above - don't skip anything\n"
        "2. Find every person's name (they're in ALL CAPS like 'SHREYA NAUTIYAL')\n"
        "3. For each person, collect their details: name, where they live, email, phone number\n"
        "4. Tell me about ALL the people you found - don't leave anyone out\n"
        "5. If there are multiple people, mention all of them\n\n"
        "RESPOND LIKE A NORMAL PERSON:\n"
        "- Talk naturally, like you're having a conversation\n"
        "- Say things like 'I found that...', 'There are X people...', 'Here's what I know...'\n"
        "- Don't use technical words or formal language\n"
        "- Don't create JSON or structured data - just talk normally\n"
        "- Be helpful and friendly\n\n"
        "Now tell me what you found in a natural, conversational way:\n"
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
