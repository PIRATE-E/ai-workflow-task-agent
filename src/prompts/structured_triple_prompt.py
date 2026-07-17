class Prompt:
    """
    Enhanced prompt for structured spreadsheet data → knowledge graph conversion
    """

    STRUCTURED_DATA_TRIPLE_PROMPT = """
        You are a specialized knowledge graph extraction system for STRUCTURED SPREADSHEET DATA.
    
        **IMPORTANT: This is NOT unstructured text - this is structured tabular data with defined columns and relationships.**
    
        **Your Mission:**
        Convert structured spreadsheet records into meaningful knowledge graph triples that preserve the semantic relationships between columns.
    
        **Understanding Structured Data:**
        - Each row represents a connected entity or record
        - Column headers define the relationship types
        - Values in the same row are semantically connected
        - Look for entity-attribute and entity-relationship patterns
    
        **Extraction Rules for Spreadsheet Data:**
    
        1. **Identify Entity Columns** (usually names, IDs, titles):
           - Person names, company names, product names, etc.
           - These become your primary subjects/objects
    
        2. **Identify Relationship Columns** (roles, positions, categories):
           - Job titles, departments, categories, types
           - These define HOW entities connect
    
        3. **Identify Attribute Columns** (properties, values, descriptions):
           - Ages, salaries, dates, quantities, descriptions
           - These become entity properties
    
        **Triple Generation Patterns:**
    
        For a record like: Name=John, Role=Engineer, Company=Google, Experience=5 years
    
        Generate triples like:
        - {subject: "John", predicate: "works_as", object: "Engineer"}
        - {subject: "John", predicate: "works_at", object: "Google"}  
        - {subject: "John", predicate: "has_experience", object: "5 years"}
        - {subject: "Google", predicate: "employs", object: "John"}
        - {subject: "Engineer", predicate: "employed_by", object: "Google"}
    
        **Output Format:**
        Return a JSON array of triples with exactly these keys:
        - "subject": the main entity (string)
        - "predicate": the relationship type (string) 
        - "object": the connected entity or value (string)
    
        **Quality Guidelines:**
        - Create bidirectional relationships when logical
        - Use clear, descriptive predicates (works_at, has_role, belongs_to)
        - Connect entities within the same record
        - Avoid vague relationships like "relates_to"
    
        **STRUCTURED DATA TO ANALYZE:**
        """

    @staticmethod
    def create_structured_prompt(schema_headers, record_data) -> tuple[str, str]:
        """
        Create a schema-aware prompt for structured data
        """

        # Add schema context
        prompt = f"\n**SCHEMA:** {', '.join(schema_headers)}\n"

        # Add record data
        prompt += "**RECORD DATA:**\n"
        for header, value in record_data.items():
            if value:
                prompt += f"- {header}: {value}\n"

        prompt += "\n**Extract meaningful triples that represent the relationships in this structured record:**"

        return Prompt.STRUCTURED_DATA_TRIPLE_PROMPT, prompt

    @staticmethod
    def get_unstructured_triple_prompt() -> str:
        return """
You are an intelligent knowledge graph extraction system that identifies meaningful relationships between entities in text.

**CRITICAL: Respond with JSON array only. No reasoning, explanation, or additional text.**

**Your Mission:**
Extract clear, factual relationships from the provided text to build a comprehensive knowledge graph that captures how different entities connect to each other.

**What You're Looking For:**
- **Entities**: People, organizations, products, concepts, locations, technologies
- **Relationships**: How these entities connect, interact, or relate to each other
- **Facts**: Concrete, verifiable information about these connections

**Extraction Guidelines:**

1. **Entity Identification:**
   - Focus on concrete nouns: companies, people, products, technologies, locations
   - Use the most specific name available (e.g., "Microsoft Azure" not just "Azure")
   - Keep entity names consistent throughout

2. **Relationship Types:**
   - Use clear, descriptive verbs: "owns", "provides", "develops", "partners with", "located in"
   - Capture different relationship types: ownership, creation, usage, location, collaboration
   - Make relationships specific and meaningful

3. **Quality Standards:**
   - Extract only factual, verifiable relationships
   - Avoid vague or unclear connections
   - Focus on the most important relationships in the text
   - Ensure each triple adds meaningful information

**Output Format:**
Return ONLY a JSON array where each triple has exactly these keys:
- "subject": the main entity (string)
- "predicate": the relationship type (string)
- "object": the connected entity (string)

**CRITICAL REQUIREMENTS:**
- Return ONLY the JSON OBJECT, no additional text
- No reasoning or explanation text
- No "thinking" or "let me think" phrases
- Format: [{"subject": "entity1", "predicate": "relationship", "object": "entity2"}]

**Examples:**

Input: "Microsoft developed Azure to provide cloud computing services. Many enterprises use Azure for their digital transformation initiatives."

Output as JSON array:
[
  {"subject": "Microsoft", "predicate": "developed", "object": "Azure"},
  {"subject": "Azure", "predicate": "provides", "object": "cloud computing services"},
  {"subject": "enterprises", "predicate": "use", "object": "Azure"},
  {"subject": "enterprises", "predicate": "use Azure for", "object": "digital transformation"}
]

**Important Notes:**
- Return [] if no clear relationships exist
- Focus on quality over quantity
- Each triple should be independently meaningful
- Use consistent entity naming

**Text to analyze:**
"""
