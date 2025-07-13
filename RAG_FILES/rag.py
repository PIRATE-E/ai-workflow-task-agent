import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import hashlib
import json
import socket
import dotenv
import google.generativeai as genai
import numpy as np
import rich.progress
import rich.prompt
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from torch import cosine_similarity
from utils.error_transfer import SocketCon
from RAG_FILES import neo4j_rag

try:
    socket_req = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_req.connect(("localhost", 5390))
    socket_con = SocketCon(socket_req)
except Exception as e:
    print(f"Error connecting to socket: {e}")
    socket_con = None


def load_pdf_document(
        doc_path: str = r"C:\Users\pirat\PycharmProjects\AI_llm\RAG_FILES\kafka.pdf",
) -> list:
    """
    Loads a PDF document from the specified file path and returns its contents as a list of Document objects.

    Args:
        doc_path (str): The file path to the PDF document.

    Returns:
        list: A list of Document objects representing the loaded PDF content.
    """
    loader = PyPDFLoader(doc_path)
    return loader.load()


# @functools.lru_cache(maxsize=1)
def split_into_unique_chunks(documents: list, chunking_size: int) -> list[Document]:
    """
    Splits a list of Document objects into unique text chunks using a recursive character splitter.

    Args:
        documents (list): List of Document objects to be split.
        chunking_size (int): The size of each chunk to be created.

    Returns:
        list[Document]: List of unique Document chunks.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunking_size, chunk_overlap=chunking_size // 10
    )
    doc_splits = splitter.split_documents(documents)
    seen = set()
    unique_chunks = []
    for doc in doc_splits:
        if doc.page_content not in seen:
            seen.add(doc.page_content)
            unique_chunks.append(doc)
    return unique_chunks


def find_similar_documents(query: str, file_path: str) -> list:
    """
    Finds and returns documents from a PDF file that are most similar to the given query using vector similarity search.

    Args:
        query (str): The search query.
        file_path (str): Path to the PDF file.

    Returns:
        list: List of Document objects most similar to the query.
    """
    documents = load_pdf_document(file_path)
    chunks = split_into_unique_chunks(documents)
    vector_store = Chroma.from_documents(
        chunks,
        OllamaEmbeddings(model="nomic-embed-text:v1.5"),
        persist_directory="./RAG_FILES/chromaDB_patents",
    )
    return vector_store.similarity_search(query)


def get_genai_embedding(texts: list[str], task: str = "RETRIEVAL_QUERY") -> list:
    """
    Retrieves embeddings for a list of texts using Google Generative AI embedding API.
    This function is explicitly designed to handle different embedding tasks because the Google charge 0 for converting embeddings
    by which the conversation is fast and efficient.

    Args:
        texts (list[str]): List of input texts to embed.
        task (str): The embedding task type (e.g., "RETRIEVAL_QUERY" or "RETRIEVAL_DOCUMENT").

    Returns:
        list: Embedding vectors for the input texts.
    """
    dotenv.load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    response = genai.embed_content(
        model="models/text-embedding-004", content=texts, task_type=task
    )
    if "embedding" not in response:
        raise ValueError("Embedding not found in the API response.")
    return response["embedding"]


def search_similar_chunks_genai(query: str, chunks: list[str], top_k=5) -> list:
    """
    Searches for the top-k most similar text chunks to a query using GenAI embeddings and cosine similarity.

    Args:
        query (str): The search query.
        chunks (list[str]): List of text chunks to compare.
    """
    query_embedding = get_genai_embedding([query], task="RETRIEVAL_QUERY")
    chunk_embeddings = get_genai_embedding(chunks, task="RETRIEVAL_DOCUMENT")
    chunk_embeddings_np = np.array(chunk_embeddings)
    query_embedding_np = np.array(query_embedding).reshape(1, -1)
    similarities = cosine_similarity(chunk_embeddings_np, query_embedding_np).flatten()
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    return [Document(page_content=chunks[i]) for i in top_indices]


# graph rag implementation
async def save_knowledge_graph_local_llm(file_path: str):
    """
    Save the knowledge graph to the neo4j database using gemini cli.
    Get the triple, save it to the json file, then mark the chunk as processed.
    If all the chunks are processed then save the knowledge graph to the neo4j database.
    """

    document_pdf = load_pdf_document(file_path)

    processed_chunks = get_processed_chunks()
    print(f"no of words: {sum(len(doc.page_content.split()) for doc in document_pdf)}")
    print(f"total no of characters: {sum(len(doc.page_content.strip()) for doc in document_pdf)}")

    if rich.prompt.Prompt.ask("do you want chunking? (y/n)", default="y") == "y":
        no_of_chunks = int(rich.prompt.Prompt.ask("enter how many chunks you want", default=10))
        chunking_size = sum(len(doc.page_content.strip()) for doc in document_pdf) // no_of_chunks
        all_text_doc = ""
        for doc in document_pdf:
            all_text_doc += doc.page_content
    else:
        all_text_doc = ""
        no_of_char = 0
        for doc in document_pdf:
            all_text_doc += doc.page_content
            no_of_char += len(doc.page_content)
        chunking_size = no_of_char
    chunks = split_into_unique_chunks([Document(page_content=all_text_doc.strip())], chunking_size)
    print(f"Total chunks created: {len(chunks)}")
    print(f"Total processed chunks: {len(processed_chunks)}")
    if rich.prompt.Prompt.ask(f"do you want to over write the processed chunks? (y/n)") == "y":
        with open("processed_hash_chunks.txt", "w") as file:
            file.write("")
        with open("processed_triple.json", "w") as file:
            file.write("[]")

    for chunk in rich.progress.track(chunks):
        if not hashlib.sha256(chunk.page_content.encode()).hexdigest() in processed_chunks:
            triples = neo4j_rag.prompt_local_llm_for_triples(chunk)
            chunk_hash = hashlib.sha256(
                chunk.page_content.encode()).hexdigest()  # Create a unique hash for the chunk content
            mark_triple_chunk(triples, chunk_hash)
            print(f"Processed chunk: {chunk.page_content[:50]}... with hash {chunk_hash}")
        else:
            continue
    processed_chunks = get_processed_chunks()
    print(f"Processed chunks after processing: {len(processed_chunks)}")

    for triple in get_all_triples():
        subject = triple.get("subject") or triple.get("Subject")
        predicate = (
                triple.get("predicate")
                or triple.get("relation")
                or triple.get("Predicate")
                or triple.get("Relation")
        )
        object = triple.get("object") or triple.get("Object")
        if subject and predicate and object is not None:
            neo4j_rag.insert_triples([(subject, predicate, object)])

    if len(processed_chunks) == len(chunks):
        print("All chunks processed, saving knowledge graph to Neo4j database.")
    else:
        print(
            f"Not all chunks processed. Processed: {len(processed_chunks)}, Total: {len(chunks)}"
        )


def save_knowledge_graph_gemini_cli(file_path: str):
    documents = load_pdf_document(file_path)
    processed_chunks = get_processed_chunks()

    print(f"Total words: {sum(len(doc.page_content.split()) for doc in documents)}")
    print(f"Total characters: {sum(len(doc.page_content.strip()) for doc in documents)}")

    all_text_doc = "".join(doc.page_content.strip() for doc in documents)
    if rich.prompt.Prompt.ask("Do you want chunking? (y/n)", default="y") == "y":
        no_of_chunks = int(rich.prompt.Prompt.ask("Enter how many chunks you want", default=10))
        chunking_size = len(all_text_doc) // no_of_chunks

    else:
        chunking_size = len(all_text_doc)  # no chunking, use the whole document as one chunk

    if rich.prompt.Prompt.ask("Do you want to overwrite the processed chunks? (y/n)") == "y":
        with open("processed_hash_chunks.txt", "w") as file:
            file.write("")
        with open("processed_triple.json", "w") as file:
            file.write("[]")

    chunks = split_into_unique_chunks([Document(page_content=all_text_doc.strip())], chunking_size)
    print(f"Total chunks created: {len(chunks)}")

    print(f"Total processed chunks: {len(processed_chunks)}")
    # remove the processed chunks from the chunks list (this is unique chunk that has to be processed)
    chunks_to_process = [chunk for chunk in chunks if
                         hashlib.sha256(chunk.page_content.encode()).hexdigest() not in processed_chunks]

    asyncio.run(process_chunks_with_immediate_saving(chunks_to_process, neo4j_rag.prompt_gemini_for_triples_cli))


async def process_chunks_with_immediate_saving(chunks_to_process: list[Document], function=neo4j_rag.prompt_gemini_for_triples_api):
    """
    Process chunks with true parallelism (up to semaphore limit) and save results immediately.
    """
    print(f"Starting parallel processing of {len(chunks_to_process)} chunks with up to 10 concurrent tasks...")

    # Create semaphore with correct limit of 10
    semaphore = asyncio.Semaphore(5)
    lock = asyncio.Lock()
    active_task = 0

    async def using_semaphore(chunk: Document):
        """Process a single chunk within semaphore limit"""
        async with semaphore:
            nonlocal active_task
            active_task += 1
            print(f"🔄 Active tasks before processing: {active_task}")
            print(f"🚀 Starting processing chunk: {chunk.page_content[:50]}...")
            start_time = asyncio.get_event_loop().time()

            try:
                # Call Gemini API (properly awaiting the async function)
                result = await function(chunk)

                # Log completion with timing information
                duration = asyncio.get_event_loop().time() - start_time
                print(f"✅ Completed chunk in {duration:.2f}s: {chunk.page_content[:50]}...")

                return result
            except Exception as e:
                socket_con.send_error(f"❌ Error processing chunk, active taskc count {active_task}: {e}")
                return {"chunk": chunk, "triples": []}

            finally:
                async with lock:
                    active_task -= 1
                    print(f"🔄 Active tasks after completion: {active_task}")

    # ⚠️ CRITICAL: Create ALL tasks first before awaiting any
    tasks = [using_semaphore(chunk) for chunk in chunks_to_process]
    print(f"Created {len(tasks)} tasks for parallel execution")

    # Track progress and timing
    start_time = asyncio.get_event_loop().time()
    completed_tasks_count = 0
    saved_results = []

    # Process results as they complete (not in sequential order)
    for completed_task in asyncio.as_completed(tasks):
        result = await completed_task  # This allows parallel execution
        completed_tasks_count += 1
        saved_results.append(result.get('chunk'))
        print(f"✅ Processed chunk #{completed_tasks_count}/{len(tasks)}: {result['chunk'].page_content[:20]}...")

        # if len(saved_results) == get_processed_chunks():
        #     print("All chunks processed, exiting early.")
        #     if result.get("triples") and isinstance(result["triples"], list):
        #         triples = result["triples"]
        #         chunk = result["chunk"]
        #         if triples or len(triples) > 0:
        #             print("💾 Saving triples immediately...")
        #             try:
        #                 mark_triple_chunk(triples, hashlib.sha256(chunk.page_content.encode()).hexdigest())
        #             except Exception as e:
        #                 SocketCon.send_error(f"❌ Error saving triples: {e} chunk : {chunk.page_content[:20]}")
        #         else:
        #             print("⚠️ No triples found in this chunk, skipping save. for chunk: ", result['chunk'].page_content[:20])
        # else:
        #     print(f"❌ No result for chunk #{completed_tasks_count}/{len(tasks)}")

        if result.get("triples") and isinstance(result["triples"], list):
            triples = result["triples"]
            chunk = result["chunk"]
            if triples or len(triples) > 0:
                print("💾 Saving triples immediately...")
                try:
                    mark_triple_chunk(triples, hashlib.sha256(chunk.page_content.encode()).hexdigest())
                except Exception as e:
                    socket_con.send_error(f"❌ Error saving triples: {e} chunk : {chunk.page_content[:20]}")
            else:
                print("⚠️ No triples found in this chunk, skipping save. for chunk: ",
                      result['chunk'].page_content[:20])

    # save triples to Neo4j immediately
    if len(saved_results) == len(chunks_to_process):
        print("All chunks processed, saving triples to Neo4j database...")
        for triples in get_all_triples():
            subject = triples.get("subject") or triples.get("Subject")
            predicate = (
                    triples.get("predicate") or triples.get("relation") or
                    triples.get("Predicate") or triples.get("Relation")
            )
            object_val = triples.get("object") or triples.get("Object")
            if subject and predicate and object_val is not None:
                try:
                    neo4j_rag.insert_triples([(subject, predicate, object_val)])
                except Exception as e:
                    socket_con.send_error(f"❌ Error inserting triples to Neo4j:"
                                          f" {e} \n subject: {subject}, predicate: {predicate}, object: {object_val}")

        #   # Show progress
    elapsed = asyncio.get_event_loop().time() - start_time
    print(f"⏱️ Progress: {completed_tasks_count}/{len(tasks)} chunks processed in {elapsed:.2f}s")

    # Save result immediately (no waiting for other tasks)

    #     if result and result.get("triples"):
    #         triples = result["triples"]
    #         # Save to Neo4j or JSON file
    #         try:
    #             # Extract subject-predicate-object triples and insert into Neo4j
    #             formatted_triples = [
    #                 (triple.get("subject", ""), triple.get("predicate", ""), triple.get("object", ""))
    #                 for triple in triples
    #             ]
    #             neo4j_rag.insert_triples(formatted_triples)
    #             saved_results.append(result)
    #             print(f"💾 Saved {len(triples)} triples from chunk #{completed}/{len(tasks)}")
    #         except Exception as e:
    #             print(f"❌ Error saving triples: {e}")
    #
    #     # Show progress
    #     elapsed = asyncio.get_event_loop().time() - start_time
    #     print(f"⏱️ Progress: {completed}/{len(tasks)} chunks processed in {elapsed:.2f}s")
    #
    # # Final statistics
    # total_time = asyncio.get_event_loop().time() - start_time
    # print(f"🎉 Completed processing all {len(tasks)} chunks in {total_time:.2f}s")
    # print(f"📊 Average time per chunk: {total_time / len(tasks):.2f}s")
    # print(f"💾 Successfully saved {len(saved_results)} results with triples")

    return saved_results


def save_knowledge_graph_gemini_api(filepath: str):
    documents = load_pdf_document(filepath)
    processed_chunks = get_processed_chunks()

    print(f"Total words: {sum(len(doc.page_content.split()) for doc in documents)}")
    print(f"Total characters: {sum(len(doc.page_content.strip()) for doc in documents)}")

    all_text_doc = "".join(doc.page_content.strip() for doc in documents)
    if rich.prompt.Prompt.ask("Do you want chunking? (y/n)", default="y") == "y":
        no_of_chunks = int(rich.prompt.Prompt.ask("Enter how many chunks you want", default=10))
        chunking_size = len(all_text_doc) // no_of_chunks

    else:
        chunking_size = len(all_text_doc)  # no chunking, use the whole document as one chunk

    if rich.prompt.Prompt.ask("Do you want to overwrite the processed chunks? (y/n)") == "y":
        with open("processed_hash_chunks.txt", "w") as file:
            file.write("")
        with open("processed_triple.json", "w") as file:
            file.write("[]")

    chunks = split_into_unique_chunks([Document(page_content=all_text_doc.strip())], chunking_size)
    print(f"Total chunks created: {len(chunks)}")

    print(f"Total processed chunks: {len(processed_chunks)}")
    # remove the processed chunks from the chunks list (this is unique chunk that has to be processed)
    chunks_to_process = [chunk for chunk in chunks if
                         hashlib.sha256(chunk.page_content.encode()).hexdigest() not in processed_chunks]

    asyncio.run(process_chunks_with_immediate_saving(chunks_to_process))


def extract_triples_process_query():
    """
    here we will get the query form tne user and then retrieve the triples from the knowledge graph
    then we will use llm to process the triples and relation with the query and return the result
    like if query is "who is Elon Musk?" then we will return the llm response of the triples related to Elon Musk
    :return:
    """
    pass


def get_all_triples() -> list:
    """
    Retrieves all triples from the processed_triple.json file.
    Returns:
        list: A list of all triples.
    """
    if not os.path.exists("processed_triple.json"):
        raise FileNotFoundError(
            "Processed triples file not found. Please run the processing function first."
        )

    with open("processed_triple.json", "r") as file:
        return json.load(file)


def mark_triple_chunk(triples: list, chunk_hash: str):
    with open("processed_hash_chunks.txt", "a") as file:
        file.write(chunk_hash + "\n")

    if os.path.exists("processed_triple.json"):
        with open("processed_triple.json", "r") as file:
            existing_triples = json.load(file)

        existing_triples.extend(triples)

        with open("processed_triple.json", "w") as file:
            json.dump(existing_triples, file, indent=4)
    else:
        with open("processed_triple.json", "w") as file:
            json.dump(triples, file, indent=4)


def get_processed_chunks() -> set:
    """
    Retrieves a set of processed chunks from a txt file.
    :return: set: A set of processed chunk identifiers.
    """
    if not os.path.exists("processed_hash_chunks.txt"):
        open(
            "processed_hash_chunks.txt", "w"
        ).close()  # Create the file if it doesn't exist
        # raise FileNotFoundError("Processed chunks file not found. Please run the processing function first.")
    with open("processed_hash_chunks.txt", "r") as file:
        return {line.strip() for line in file if line.strip()}


if __name__ == "__main__":
    pass
