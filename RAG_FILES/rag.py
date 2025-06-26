import os.path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, UnstructuredPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings


def load_pdf(doc_path: str = r"C:\Users\pirat\PycharmProjects\AI_llm\RAG_FILES\patent_2.pdf") -> list:
    print(os.path.exists(doc_path))
    loader = PyPDFLoader(doc_path)
    doc = loader.load()
    # doc is now list of doc object, each with .page_content
    return doc


# not use this
def load_pdf_un_structured(doc_path: str = "") -> list:
    # for ocr
    loader = UnstructuredPDFLoader(
        file_path=doc_path,
        mode="elements",
        strategy="ocr"
    )
    doc = loader.load()
    return doc


def extract_doc(loaded_doc: list) -> list:
    # splitter is to split doc into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    doc_splits = splitter.split_documents(loaded_doc)
    return doc_splits


def embedding_store() -> Chroma:
    # ---placeholder--- embedding_store need path of pdf
    # load doc from pdf_loader
    document = load_pdf()
    # split the pdf into chunks
    document_splits = extract_doc(document)

    # embedded the pdf and store it into vector
    embeddings = OllamaEmbeddings(model="nomic-embed-text:v1.5")
    vector_store_doc = Chroma.from_documents(document_splits, embeddings, persist_directory="./chromaDB_patents")
    return vector_store_doc


if __name__ == '__main__':
    query = """
    SEMICONDUCTOR DEVICE, 
SEMICONDUCTOR PACKAGE AND 
METHOD OF MANUFACTURING THE SAME 
    """
    # print(extract_doc(load_pdf(r"C:\Users\pirat\PycharmProjects\AI_llm\RAG_FILES\patent_2.pdf")))
    result = embedding_store().similarity_search_with_score(query)
    for item in result:
        print(item[0].page_content)
    print(result)
