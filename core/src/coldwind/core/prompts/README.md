# 💬 Prompts Package (`coldwind.core.prompts`)

> Every word the system says to a model, organized: one module per job, no giant prompt blobs.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits — Who Feeds Whom

```text
                        ┌────────────────────────┐
      user message ───► │ classify_message_type   │ ◄── system_prompts.message_classifier
                        └───────────┬────────────┘
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                      ▼
        💬 chat reply         🛠️ tool pick          ⚡ agent mission
   chat_prompts            system_prompt_       agent_mode_prompts
   .get_chat_system_prompt  tool_selector        + hierarchical_agent_prompts
              │                     │                      │        (orchestrator)
              ▼                     ▼                      ▼
        open_ai_prompt          tools/            spawn / plan / execute
        (JSON extraction)       (ToolAssign)

   🔎 web search: web_search_prompts          📚 RAG: rag_prompts
   🧮 knowledge graph: system_prompts.cypher_query_generator + rag_search_classifier_prompts
   🧾 triples: structured_triple_prompt       🧠 assistant: system_prompts.ai_assistant
```

---

## 🎯 Why This Exists

- Prompts rot when scattered — **one module per job** makes them findable and fixable.
- Each class is a **prompt factory**: call a method, get the exact text for that stage.
- Prompts reference **real runtime data** (tool lists, history) instead of placeholders.

---

## 📦 Module Map (all 9, verified)

| Module | Class | What it generates |
|--------|-------|-------------------|
| `system_prompts.py` | `SystemPrompts` + `PromptTemplates` + `PromptManager` | Core personas: `web_search_assistant`, `cypher_query_generator`, `knowledge_graph_explainer`, `rag_system_selector`, `message_classifier`, `ai_assistant` |
| `chat_prompts.py` | `ChatPrompts` | `get_chat_system_prompt(tools_context, history, latest_message_content)` |
| `agent_mode_prompts.py` | `Prompt` | Agent-mode: `generate_tool_list_prompt`, `generate_parameter_prompt`, `evaluate_in_end`, `evaluate_final_response` |
| `system_prompt_tool_selector.py` | `get_tool_selector_prompt(...)` | "Which tool should we use?" |
| `web_search_prompts.py` | `WebSearchPrompts` | `search_result_processor`, `query_enhancer`, `search_result_validator` |
| `rag_prompts.py` | `RAGPrompts` + `KnowledgeGraphPrompts` | `document_analyzer`, `knowledge_graph_builder`, `text_chunk_processor`, `get_json_text_rag_search_prompt`, `hybrid_rag_coordinator`; `entity_resolver`, `relationship_validator` |
| `rag_search_classifier_prompts.py` | `Prompts` | `get_system_prompt_cypher`, `get_system_prompt_classifier` |
| `structured_triple_prompt.py` | `Prompt` | `STRUCTURED_DATA_TRIPLE_PROMPT`, `create_structured_prompt`, `get_unstructured_triple_prompt` |
| `open_ai_prompt.py` | `Prompt` | `get_json_extraction_prompts`, `get_extracted_json_prompt` |

---

## 🏗️ The Pattern: Prompt Factory

Every module follows the same shape — **no exceptions, no giant string blobs in business code**:

```python
from coldwind.core.prompts.chat_prompts import ChatPrompts

prompt = ChatPrompts().get_chat_system_prompt(
    tools_context=tool_context,          # real tool descriptions
    history=history,                      # real conversation so far
    latest_message_content=user_text,     # the new message
)
```

```text
 call a method ──► get the exact prompt text (data baked in) ──► send to model
```

Need every persona in one place? `PromptManager` bundles the `get_*_prompt` accessors from `system_prompts.py`.

---

## 🚀 Quick Start: Add or Edit a Prompt

1. Find the module that owns the stage you're changing (map above).
2. Edit (or add) a `generate_*` / `get_*` method there — keep it a **pure function**: inputs in, text out.
3. Call it from your node/tool. Never inline prompt text in agent code.

---

## ❓ FAQ

- **Where are the orchestrator's prompts?** In the orchestrator itself: `agents/agentic_orchestrator/hierarchical_agent_prompts.py` (`HierarchicalAgentPrompt`) — they're stage-specific, so they live with the pipeline.
- **Why `Prompt` classes instead of constants?** Prompts need runtime data (tool lists, history) — methods take parameters; constants can't.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (old file listed APIs that don't exist; rebuilt from the verified 9-module inventory).**
