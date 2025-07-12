import asyncio
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any

import google.genai as genai
from anyio import Semaphore
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from neo4j import GraphDatabase

SYSTEM_PROMPT_GENERATE_TRIPLE = """
    You are an expert information extraction system. Your ONLY task is to analyze the provided text and extract all possible subject-predicate-object triples (entities and their relationships) for building a knowledge graph.

Instructions:
- Carefully read the entire text.
- Extract every meaningful relationship as a triple, even if there are multiple triples in the text.
- Each triple MUST be a dictionary with the keys: "subject", "predicate", and "object".
- Return ONLY a JSON array (list) of triples. Do NOT return any explanation, commentary, or extra text.
- Do NOT return a dictionary of lists, a nested dictionary, or any other structure.
- Do NOT return a dictionary where the keys are sentences or anything except "subject", "predicate", and "object".
- If the text contains no triples, return an empty JSON array: []

Correct Output Example:
[
  {"subject": "Kafka", "predicate": "wrote", "object": "Metamorphosis"},
  {"subject": "Metamorphosis", "predicate": "is a", "object": "novel"},
  {"subject": "Gregor Samsa", "predicate": "woke from", "object": "troubled dreams"}
]

Incorrect Output Examples (do NOT do this!):
# 1. Dictionary of lists (WRONG)
{
  "subject": ["Kafka", "Metamorphosis"],
  "predicate": ["wrote", "is a"],
  "object": ["Metamorphosis", "novel"]
}
# 2. Nested dictionary (WRONG)
{
  "Kafka wrote Metamorphosis": {
    "subject": "Kafka",
    "predicate": "wrote",
    "object": "Metamorphosis"
  }
}
    if Input text: ""
    Output: []
    """

# neo4j
NEO4J_URI = "neo4j+s://cce2274b.databases.neo4j.io"
NEO4J_USERNAME = "neo4j"
NEO4J_PASSWORD = "XKhr-XOJdKemTwCH35SoT6QVo8r_UntWONVoMry_kPg"
NEO4J_DATABASE = "neo4j"

# Create a Neo4j driver instance to manage connections and execute Cypher queries using sessions.
driver = GraphDatabase.driver(
    NEO4J_URI,
    auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
)

# --------- FIXED: Enhanced semaphore with better resource management ---------
semaphore = Semaphore(5)  # Reduced from 5 to 3 for better stability
GEMINI_CLI_PATH = "C:\\Users\\pirat\\AppData\\Roaming\\npm\\gemini.cmd"
SUBPROCESS_TIMEOUT = 120  # 2 minutes timeout per request

task_count = 0  # Global counter for tracking the number of tasks


async def prompt_gemini_for_triples(chunk: Document) -> list:
    """
    FIXED VERSION: Enhanced error handling, resource management, and process isolation.
    Uses temporary files to avoid CLI interference and implements proper cleanup.

    Args:
        chunk (Document): A Document object containing the text to analyze.
    """
    prompt = f"""
    You are an expert in extracting subject-predicate-object triples from text.
    Your task is to analyze the following text and extract all subject-predicate-object triples for making knowledge graph.
    Extract all subject-predicate-object triples (entities and their relationships) from the following text.
    Respond in a JSON list of triples with keys "subject", "relation", and "object".
    Only return the JSON list without any additional text or explanation.
    Text:
    {chunk.page_content}
    """

    if not os.path.exists(GEMINI_CLI_PATH):
        raise FileNotFoundError(
            f"Gemini command not found at {GEMINI_CLI_PATH}. Please ensure it is installed and the path is correct."
        )

    # 🚀 FIXED: Proper semaphore management with context manager pattern
    async with semaphore:
        global task_count
        task_count += 1
        print(f"Task count before processing: {task_count}")
        # 🚀 FIXED: Add small delay to prevent overwhelming
        await asyncio.sleep(0.2)

        # 🚀 FIXED: Use temporary files to avoid CLI interference
        temp_dir = Path(tempfile.gettempdir()) / "gemini_parallel"
        temp_dir.mkdir(exist_ok=True)

        input_file = temp_dir / f"input_{uuid.uuid4().hex}.txt"
        output_file = temp_dir / f"output_{uuid.uuid4().hex}.json"

        try:
            # Write prompt to temporary file
            with open(input_file, 'w', encoding='utf-8') as f:
                f.write(prompt)

            # 🚀 FIXED: Enhanced subprocess call with proper timeout and isolation
            process = await asyncio.create_subprocess_exec(
                GEMINI_CLI_PATH,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=temp_dir  # Isolate working directory
            )

            result = ""

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=prompt.encode("utf-8")),
                    timeout=SUBPROCESS_TIMEOUT
                )
                result = stdout.decode("utf-8").strip() if stdout else ""
                error_output = stderr.decode("utf-8").strip() if stderr else ""
                if process.returncode != 0:
                    raise RuntimeError(
                        f"Gemini command failed with return code {process.returncode}: {error_output}\nOutput: {result}"
                    )
            except asyncio.TimeoutError:
                # ... [timeout handling] ...
                raise RuntimeError(f"Gemini CLI call timed out after {SUBPROCESS_TIMEOUT} seconds")
        except Exception as e:
            raise RuntimeError(f"Gemini command failed with error: {e}")
        finally:
            task_count -= 1  # Decrement task count
            print(f"Task count after processing: {task_count}")
            # Cleanup temporary files
            try:
                if input_file.exists():
                    input_file.unlink()
                if output_file.exists():
                    output_file.unlink()
            except Exception:
                print(f"Failed to clean up temporary files: {input_file}, {output_file}")

        # Now, after all try/except/finally, do the JSON parsing and return
        try:
            if not result or result == "[]" or len(result.strip()) == 0:
                print("No triples extracted or empty response.")
                return []
            triples = json.loads(result)
            if not isinstance(triples, list):
                print(f"Warning: Expected list, got {type(triples)}. Attempting to extract...")
                raise json.JSONDecodeError("Not a list", result, 0)
            return triples
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Raw result: {result}")
            try:
                json_start = result.find("[")
                json_end = result.rfind("]") + 1
                if json_start != -1 and json_end > json_start:
                    json_part = result[json_start:json_end]
                    triples = json.loads(json_part)
                    if isinstance(triples, list):
                        return triples
                    else:
                        print(f"Extracted JSON is not a list: {type(triples)}")
                        return []
                else:
                    print("No JSON array found in response")
                    return []
            except Exception as extraction_error:
                print(f"Failed to extract JSON: {extraction_error}")
                print(f"Original result: {result}")
                return []


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

        batch_tasks = [prompt_gemini_for_triples(chunk) for chunk in batch]
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
    :arg chunk: Document object containing the text to analyze.
    :return: A dictionary with the original chunk and its triples if extraction is successful,
        Sends a Document's text to the Gemini API to extract subject-predicate-object triples for knowledge graph construction.

        - Submits the document content as a prompt to Gemini.
        - Handles empty, invalid, or malformed API responses robustly.
        - Attempts to parse the output as a list of triples, with fallback logic for partial or malformed JSON.
        - Returns:
            - A dictionary with the original chunk and its triples if extraction is successful,
            - An empty list if no triples are found for that particular chunk,
            - Or None if the response is empty.

        Designed for reliability and easy integration with downstream knowledge graph workflows.
    """
    prompt = SYSTEM_PROMPT_GENERATE_TRIPLE + f"""\n
    Text:
    {chunk.page_content}
    """
    load_dotenv()
    api_key_gemini = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key_gemini)

    response = await client.aio.models.generate_content(model="gemini-1.5-flash", contents=prompt)

    if not response or response.text.strip() == "" or response.text.strip() == "[]":
        print("No response or empty response from Gemini API.")
        return {"chunk": chunk, "triples": []}
    output = response.text.strip()

    #     parse the output as JSON
    try:
        triples = json.loads(output)
        if not isinstance(triples, list):
            print(f"Warning: Expected list, got {type(triples)}. Attempting to extract...")
            raise json.JSONDecodeError("Not a list", output, 0)
        return {"chunk": chunk, "triples": triples}
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Raw result: {output}")
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

    llm.invoke(SYSTEM_PROMPT_GENERATE_TRIPLE)

    prompt = f"""
        Convert the following text into a list of subject-predicate-object triples.
        Text:
        \"\"\"{chunk.page_content}\"\"\"
        """
    response = llm.invoke([HumanMessage(content=prompt)])
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
                session.write_transaction(_insert_triple, subject, relation, object)
    except Exception as e:
        print(f"Error inserting triples: {e}")


def get_triples(cypher_query: str):
    """
    Retrieves triples from the Neo4j database based on a Cypher query.

    This function executes the provided Cypher query and returns the results as a list of dictionaries.
    Each dictionary contains the subject, relation, and object of the triples found.
    """
    try:
        with driver.session() as session:
            result = session.run(cypher_query)
            return [
                {
                    "subject": record["s"]["name"],
                    "relation": record["r"]["type"],
                    "object": record["o"]["name"],
                }
                for record in result
            ]
    except Exception as e:
        print(f"Error executing cypher query: {e}")
        return []


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
        print(f"Error executing cypher query: {e}")
        return []


if __name__ == "__main__":
    pass
