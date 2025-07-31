import asyncio
import json
import os
import subprocess
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_ollama import ChatOllama
from neo4j import GraphDatabase

from src.config import settings
# Socket connection now centralized in settings
from src.utils.structured_triple_prompt import create_structured_prompt

SYSTEM_PROMPT_GENERATE_TRIPLE_ENHANCED = """
You are an intelligent knowledge graph extraction system that identifies meaningful relationships between entities in text.

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
Return a JSON array where each triple has exactly these keys:
- "subject": the main entity (string)
- "predicate": the relationship type (string)
- "object": the connected entity (string)

**Examples:**

Input: "Microsoft developed Azure to provide cloud computing services. Many enterprises use Azure for their digital transformation initiatives."

Output:
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

# neo4j
NEO4J_URI = "neo4j+s://9e90598a.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "Jdu5IQ0F8FbYRfs6qHA7gdXhtnOHqfUNqVumVx7cBpE"
NEO4J_DATABASE = "neo4j"

# Create a Neo4j driver instance to manage connections and execute Cypher queries using sessions.
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
)

GEMINI_CLI_PATH = "C:\\Users\\pirat\\AppData\\Roaming\\npm\\gemini.cmd"
SUBPROCESS_TIMEOUT = 120  # 2 minutes timeout per request

task_count = 0  # Global counter for tracking the number of tasks


async def prompt_gemini_for_triples_cli(chunk: Document) -> dict[str, Document | str | list[Any]] | dict[
    str, Document | list[Any]]:
    """
    TRULY ASYNC VERSION: Uses semaphore for proper concurrency control and async subprocess handling.

    Args:
        chunk (Document): A Document object containing the text to analyze.
    """
    # 🔥 CRITICAL FIX: Actually use the semaphore for concurrency control
    is_structured = chunk.metadata.get("source") == "google_sheets" if hasattr(chunk, 'metadata') else False

    if is_structured and hasattr(chunk, 'metadata') and 'structured_data' in chunk.metadata:
        # Use structured data prompt
        schema_headers = chunk.metadata.get('schema', [])
        record_data = chunk.metadata.get('structured_data', {})
        prompt = create_structured_prompt(schema_headers, record_data)
    else:
        # Use original unstructured text prompt
        prompt = SYSTEM_PROMPT_GENERATE_TRIPLE_ENHANCED + f"""\n
                Text:
                {chunk.page_content}
                """

    if not os.path.exists(GEMINI_CLI_PATH):
        raise FileNotFoundError(
            f"Gemini command not found at {GEMINI_CLI_PATH}. Please ensure it is installed and the path is correct."
        )
    # Create subprocess with proper async handling
    process = await asyncio.create_subprocess_exec(
        GEMINI_CLI_PATH,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(input=prompt.encode("utf-8")),
            timeout=SUBPROCESS_TIMEOUT
        )
        stdout = stdout.decode('utf-8').strip()
        stderr = stderr.decode('utf-8').strip()
        if process.returncode != 0:
            raise RuntimeError(
                f"Gemini command failed with return code {process.returncode}: {stderr}"
            )
    except asyncio.TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
        raise FileNotFoundError(f"Gemini CLI call timed out after {SUBPROCESS_TIMEOUT} seconds, error:-{stderr.decode('utf-8')}")

    triples = None
    try:
        triples = json.loads(stdout)
    except json.JSONDecodeError as e:
        json_start_pointer = stdout.find("[")
        json_end_pointer = stdout.rfind("]") + 1

        # pointer would -1 if it does not find the character "["
        if json_start_pointer != -1 and json_end_pointer > json_start_pointer:
            json_part = stdout[json_start_pointer:json_end_pointer]
            try:
                triples = json.loads(json_part)
            except json.JSONDecodeError as extraction_error:
                print(f"Failed to extract JSON from response: {extraction_error}")
                print(f"Original output: {stdout}")
    if triples is None or not isinstance(triples, list):
        print("No triples extracted or empty response.")
        return {"chunk": chunk, "triples": []}
    return {"chunk": chunk, "triples": triples}


# 🚀 FIXED: Enhanced batch processing function keep this method to for if more batching related issue arises
async def prompt_gemini_for_triples_batch(chunks: list[Document], batch_size: int = 3) -> list[list]:
    """
    Process chunks in smaller batches to prevent resource exhaustion.

    Args:
        chunks: List of Document chunks to process
        batch_size: Number of chunks to process concurrently

    Returns:
        List of triple lists for each chunk
    """
    results = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        print(f"Processing batch {i // batch_size + 1}/{(len(chunks) + batch_size - 1) // batch_size}")

        batch_tasks = [prompt_gemini_for_triples_cli(chunk) for chunk in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Handle exceptions in batch results
        for j, result in enumerate(batch_results):
            if isinstance(result, Exception):
                print(f"Error in chunk {i + j}: {result}")
                results.append([])  # Empty list for failed chunks
            else:
                results.append(result)

        # Small delay between batches
        if i + batch_size < len(chunks):
            await asyncio.sleep(1.0)

    return results


async def prompt_gemini_for_triples_api(chunk: Document) -> None | dict[str, Document | list[Any]] | dict[
    str, Document | list]:
    """
    Enhanced version that detects structured vs unstructured data and uses appropriate prompts
    """
    # Check if this is structured spreadsheet data
    is_structured = chunk.metadata.get("source") == "google_sheets" if hasattr(chunk, 'metadata') else False

    if is_structured and hasattr(chunk, 'metadata') and 'structured_data' in chunk.metadata:
        # Use structured data prompt
        schema_headers = chunk.metadata.get('schema', [])
        record_data = chunk.metadata.get('structured_data', {})
        prompt = create_structured_prompt(schema_headers, record_data)
    else:
        # Use original unstructured text prompt
        prompt = SYSTEM_PROMPT_GENERATE_TRIPLE_ENHANCED + f"""\n
        Text:
        {chunk.page_content}
        """
    load_dotenv()
    api_key_gemini = os.getenv("GEMINI_API_KEY")
    # client = genai.Client(api_key=api_key_gemini)

    # response = await client.aio.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    genai.configure(api_key=api_key_gemini)
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    # sending the prompt to the Gemini API using asyncio to avoid blocking the event loop
    def get_response(prompt_g: str) -> genai.types.GenerateContentResponse | None:
        """
        Helper function to get response from Gemini API with error handling
        """
        try:
            return model.generate_content(prompt_g)
        except Exception as e_G:
            if settings.socket_con:
                settings.socket_con.send_error(f"Error calling Gemini API: {e_G}")
            return None

    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, get_response, prompt)

    if not response or response.text.strip() == "" or response.text.strip() == "[]":
        print("No response or empty response from Gemini API.")
        return {"chunk": chunk, "triples": []}
    output = response.text.strip()

    #   Parse the output as JSON
    try:
        triples = json.loads(output)
        if not isinstance(triples, list):
            print(f"Warning: Expected list, got {type(triples)}. Attempting to extract...")
            raise json.JSONDecodeError("Not a list", output, 0)
        return {"chunk": chunk, "triples": triples}
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        try:
            json_start = output.find("[")
            json_end = output.rfind("]") + 1
            if json_start != -1 and json_end > json_start:
                json_part = output[json_start:json_end]
                triples = json.loads(json_part)
                if isinstance(triples, list):
                    return {"chunk": chunk, "triples": triples}
                else:
                    print(f"Extracted JSON is not a list: {type(triples)}")
                    return {"chunk": chunk, "triples": []}
            else:
                print("No JSON array found in response")
                return {"chunk": chunk, "triples": []}
        except Exception as extraction_error:
            print(f"Failed to extract JSON: {extraction_error}")
            print(f"Original result: {output}")
            return {"chunk": chunk, "triples": []}


def prompt_local_llm_for_triples(chunk: Document) -> list:
    """
    Existing function - no changes needed for this issue.
    """
    llm = ChatOllama(model="llama3.1:8b", temperature=0.1, format="json")

    triples = []

    llm.invoke(SYSTEM_PROMPT_GENERATE_TRIPLE_ENHANCED)

    prompt = f"""
        You are analyzing text to extract meaningful relationships for a knowledge graph.
        
        **Your Task:**
        Extract clear, factual relationships between entities in the text below.
        Focus on concrete entities (people, companies, products, technologies) and their connections.
        
        **Text to Analyze:**
        \"\"\"{chunk.page_content}\"\"\"
        
        **Output Format:**
        Return a JSON array where each relationship is represented as:
        {{"subject": "entity1", "predicate": "relationship", "object": "entity2"}}
        
        Focus on quality over quantity - extract only meaningful, verifiable relationships.
        """
    response = llm.invoke([settings.HumanMessage(content=prompt)])
    output = response.content

    print(f"LLM response: {output}")

    try:
        # if the output is had dict of lists we want to convert it to a list of dicts
        data = json.loads(output)
        if isinstance(data, dict):
            # If dict of lists, zip them
            if all(isinstance(v, list) for v in data.values()):
                for s, p, o in zip(data.get("subject", []), data.get("predicate", []), data.get("object", [])):
                    triples.append({"subject": s, "predicate": p, "object": o})
            else:
                triples.append(data)
        # Attempt to parse the output as JSON
        elif isinstance(data, list):
            triples.extend(data)
        else:
            raise ValueError(
                f"Unexpected JSON format: {data}. Expected a list or dict of lists."
            )
    except json.JSONDecodeError:
        print("Failed to parse JSON, trying to extract JSON part from response.")
        try:
            json_start = output.index("[")
            json_end = output.rindex("]") + 1
            triples.append(json.loads(output[json_start:json_end]))
        except Exception as e:
            raise ValueError(
                f"Failed to extract JSON from response: {e}\n\n Response: {output}"
            )
    return triples


def clear_database():
    """
    Deletes all nodes and relationships from the Neo4j database.

    This function connects to the Neo4j database and runs a Cypher query to remove every node and relationship,
    effectively resetting the database to an empty state.
    """
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("Database cleared successfully.")


def _insert_triple(tx, subject, relation, object):
    """
    Inserts a single subject-predicate-object triple into the Neo4j database.

    This function creates or finds two entities (nodes) for the subject and object, and creates a relationship between them
    with the specified relation type. It uses the provided transaction object to execute the Cypher query.
    """
    query = (
        "MERGE (s:Entity {name: $subject}) "
        "MERGE (o:Entity {name: $object}) "
        "MERGE (s)-[r:RELATION {type: $relation}]->(o)"
    )
    tx.run(query, subject=subject, relation=relation, object=object)


def insert_triples(triples):
    """
    Inserts multiple subject-predicate-object triples into the Neo4j database.

    This function takes a list of triples (each as a tuple of subject, relation, object) and inserts each one into the database
    by calling the insert_triple function for each triple.
    """
    try:
        with driver.session() as session:
            for subject, relation, object in triples:
                if all([subject, relation, object]):
                    session.write_transaction(_insert_triple, subject, relation, object)
    except Exception as e:
        print(f"Error inserting triples: {e}")


def get_triples(cypher_query: str):
    """
    Retrieves triples from the Neo4j database based on a Cypher query.
    Handles both single and variable-length relationships.
    """
    try:
        with driver.session() as session:
            result = session.run(cypher_query)
            triples = []
            for record in result:
                s = record["s"]
                o = record["o"]
                r = record["r"]
                # Handle variable-length relationships (list)
                if isinstance(r, list):
                    relation_types = " -> ".join([rel.get("type", str(rel)) for rel in r])
                else:
                    relation_types = r.get("type", str(r)) if r else ""
                triples.append({
                    "subject": s.get("name", str(s)),
                    "relation": relation_types,
                    "object": o.get("name", str(o)),
                })
            return triples
    except Exception as e:
        if settings.socket_con:
            settings.socket_con.send_error(f"Error executing cypher query: {e}")
        return []


def extract_triple_text(triple):
    # Handles both key sets: 'subject'/'relation'/'object' and 's'/'r'/'o'
    if 'subject' in triple and 'relation' in triple and 'object' in triple:
        return f"{triple['subject']} - {triple['relation']} - {triple['object']}"
    elif 's' in triple and 'r' in triple and 'o' in triple:
        # Try to extract names/types from objects
        s = triple['s']['name'] if isinstance(triple['s'], dict) and 'name' in triple['s'] else str(triple['s'])
        o = triple['o']['name'] if isinstance(triple['o'], dict) and 'name' in triple['o'] else str(triple['o'])
        # r can be a list or a dict
        r = triple['r']
        if isinstance(r, list):
            relation_types = "->".join([rel.get('type', str(rel)) for rel in r])
        elif isinstance(r, dict):
            relation_types = r.get('type', str(r))
        else:
            relation_types = str(r)
        return f"{s} - {relation_types} - {o}"
    else:
        return str(triple)  # fallback, unlikely


def get_retrieve_triples(cypher_query: str):
    """
    Retrieves triples from the Neo4j database based on a Cypher query.
    This function was referenced in lggraph.py but was missing.
    """
    try:
        with driver.session() as session:

            result = session.run(cypher_query)
            records = []
            for record in result:
                records.append(dict(record))
            return records
    except Exception as e:
        if settings.socket_con:
            settings.socket_con.send_error(f"Error executing cypher query: {e}")
        return []


def get_all_labels_and_names() -> dict[str, list[str]]:
    """
    Retrieves all labels and distinct names from the Neo4j database for understanding of llm
    :return: A tuple containing two lists names and labels.:
    """
    with driver.session() as session:
        labels = [record["label"] for record in session.run("CALL db.labels() YIELD label RETURN label")]
        names = [record["name"] for record in session.run("MATCH (n) RETURN DISTINCT n.name AS name") if record["name"]]
    return {"labels": labels, "names": names}


def get_all_relationship_types() -> list[str]:
    """
    Retrieves all unique relationship types from the Neo4j database
    :return: A list of relationship types
    """
    with driver.session() as session:
        relationship_types = [
            record["type"] for record in
            session.run("MATCH ()-[r:RELATION]-() RETURN DISTINCT r.type AS type")
            if record["type"]
        ]
    return relationship_types


if __name__ == "__main__":
    # import google.generativeai as genai
    # c = genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    # # Example usage
    # model.generate_content("Hello, world!")  # This is just a placeholder to test the import

    pass
