import os

import dotenv
import google.generativeai as genai
import numpy as np
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws.utilities.math import cosine_similarity
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings


def load_pdf_document(doc_path: str = r"C:\Users\pirat\PycharmProjects\AI_llm\RAG_FILES\patent_2.pdf") -> list:
    """
    Loads a PDF document from the specified file path and returns its contents as a list of Document objects.

    Args:
        doc_path (str): The file path to the PDF document.

    Returns:
        list: A list of Document objects representing the loaded PDF content.
    """
    loader = PyPDFLoader(doc_path)
    return loader.load()


def split_into_unique_chunks(documents: list) -> list[Document]:
    """
    Splits a list of Document objects into unique text chunks using a recursive character splitter.

    Args:
        documents (list): List of Document objects to be split.

    Returns:
        list[Document]: List of unique Document chunks.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
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
        persist_directory="./RAG_FILES/chromaDB_patents"
    )
    return vector_store.similarity_search(query)


def get_genai_embedding(texts: list[str], task: str = "RETRIEVAL_QUERY") -> list:
    """
    Retrieves embeddings for a list of texts using Google Generative AI embedding API.

    Args:
        texts (list[str]): List of input texts to embed.
        task (str): The embedding task type (e.g., "RETRIEVAL_QUERY" or "RETRIEVAL_DOCUMENT").

    Returns:
        list: Embedding vectors for the input texts.
    """
    dotenv.load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    response = genai.embed_content(
        model="models/text-embedding-004",
        content=texts,
        task_type=task
    )
    if 'embedding' not in response:
        raise ValueError("Embedding not found in the API response.")
    return response['embedding']


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


if __name__ == '__main__':
    query_text = "SEMICONDUCTOR DEVICE"
    print("----- GenAI cosine similarity search -----")
    docs = split_into_unique_chunks(load_pdf_document())
    for doc in search_similar_chunks_genai(query_text, [chunk.page_content for chunk in docs]):
        print(doc)
    print("----- Ollama vector store similarity search -----")
    for doc in find_similar_documents(query_text, r"C:\Users\pirat\PycharmProjects\AI_llm\RAG_FILES\patent_2.pdf"):
        print(doc)
