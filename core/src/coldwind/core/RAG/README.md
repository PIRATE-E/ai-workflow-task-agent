# 📚 RAG Package (`coldwind.core.RAG`)

> Give the AI long-term memory: turn documents and spreadsheets into knowledge it can search.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
PDFs / Google Sheets          Neo4j knowledge graph
        │                            ▲
        ▼                            │ save_knowledge_graph_*
   rag.py (chunks + triples) ────────┘
        │
        ▼
rag_search_classifier_tool (tools/) ──► answers questions with REAL data
```

---

## 🎯 Why This Exists

- Models forget everything between chats — **RAG stores facts outside the model** and fetches them on demand.
- Two memory styles: **vector search** (find similar text chunks) and **knowledge graph** (find structured facts/triples).
- Sources aren't just PDFs — **Google Sheets** can become a knowledge graph too.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `rag.py` | Ingest documents: load, chunk, embed, extract triples |
| `neo4j_rag.py` | Store + query triples in Neo4j (the graph database) |
| `sheets_rag.py` | `GoogleSheetsRAG` — turn a Google Sheet into knowledge-graph documents |

> ⚠️ A major **RAG ETL refinement** is the next big work item on the roadmap — expect this package's internals to modernize. The flows below describe today's pipeline.

---

## 🏗️ Pipeline 1: PDF → Searchable Knowledge (rag.py)

```text
 load_pdf_document            split_into_unique_chunks
┌──────────────┐            ┌──────────────────┐
│  PDF file    │──────────► │  small text       │
└──────────────┘            │  chunks          │
                            └────────┬─────────┘
              ┌──────────────────────┼──────────────────────┐
              ▼                                            ▼
   get_genai_embedding                         extract_triples_process_query
   (vector embeddings)                          (facts: subject → relation → object)
              │                                            │
              ▼                                            ▼
   search_similar_chunks_genai                save_knowledge_graph_gemini_cli
   text_rag_search_using_llm                  save_knowledge_graph_gemini_api
   (answer questions)                         save_knowledge_graph_open_ai
```

Key functions: `find_similar_documents`, `get_processed_chunks`, `get_all_triples_from_file` (reads saved triples), `text_rag_search_using_llm` (LLM-driven search over chunks).

---

## 🏗️ Pipeline 2: Triples → Neo4j (neo4j_rag.py)

```text
 triples from rag.py
        │
        ▼
 insert_triples ──► Neo4j graph ──► get_retrieve_triples ──► context for answers
                    (nodes + relationships)
 clear_database                    get_all_labels_and_names
 prompt_local_llm_for_triples      get_all_relationship_types
                                   get_response (ask the graph a question)
```

Cypher generation prompts live in `prompts/` (`rag_search_classifier_prompts`, `system_prompts.cypher_query_generator`).

---

## 🏗️ Pipeline 3: Google Sheets (sheets_rag.py)

```python
from coldwind.core.RAG.sheets_rag import GoogleSheetsRAG

sheets_rag = GoogleSheetsRAG(
    sheets_url="https://docs.google.com/spreadsheets/d/…",
    schema_config={...},          # which columns mean what
)
documents = sheets_rag.get_structured_documents_for_kg()   # → knowledge-graph ready
```

---

## 🔗 Where Paths Are Configured

The RAG file paths live on `DesktopConfig` (not hardcoded): `rag_example_file_path`, `rag_hash_file_path`, `rag_triples_file_path`.

**Who consumes this package?** The `rag_search_classifier_tool` in `tools/` — it decides whether your query needs a vector search, a knowledge-graph lookup, or plain LLM.

---

## ❓ FAQ

- **Vector search vs knowledge graph?** Vector = "find text like this" (fuzzy, great for documents). Graph = "find facts connected to this" (precise, great for structured data).
- **Why Neo4j?** Triples (subject → relation → object) map perfectly onto a graph database.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (old file documented six modules that never existed; rebuilt from the three real modules).**
