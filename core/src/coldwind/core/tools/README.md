# 🛠️ Tools Package (`coldwind.core.tools`)

> The AI's hands: Google Search, shell commands, translation, RAG lookups, and browser automation — plus a registry that makes them all discoverable.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
agents (tool mode) ──► tool_selector ──► ToolAssign (registry) ──► the right tool
                                                          │
                              ┌───────────┬───────────┬───┴────────┬───────────┐
                              ▼           ▼           ▼            ▼           ▼
                           Google      Shell      Translate     RAG        Browser
                           search     command      text       lookup     automation
```

---

## 🎯 Why This Exists

- The model can't touch the world by itself — **tools are the bridge from words to actions**.
- One **registry** (`ToolAssign`) keeps every tool discoverable with name, description, and argument schema.
- New tools (including MCP server tools) **plug in without touching the agents**.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `lggraph_tools/tool_assign.py` | `ToolAssign` — the registry every agent reads |
| `lggraph_tools/google_search_tool.py` | `search_google_tool(query)` — live Google results |
| `lggraph_tools/run_shell_command_tool.py` | `run_shell_command(command)` — run shell commands |
| `lggraph_tools/translate_tool.py` | `translate_text(message, target_language)` |
| `lggraph_tools/rag_search_classifier_tool.py` | `rag_search_classifier_tool(query)` + `retrieve_knowledge_graph` — ask your stored knowledge |
| `lggraph_tools/browser_tool_main.py` | `browser_use_tool(...)` + `BrowserHandler` — drive a real browser |
| `lggraph_tools/tool_wrappers/` | One wrapper per tool (safety + normalization layer) |
| `lggraph_tools/mcp_wrapper/` | `UniversalMCPWrapper` + `filesystem_wrapper` — MCP tools become normal tools |
| `lggraph_tools/tool_schemas/` | `tools_structured_classes.py` — typed argument schemas |
| `lggraph_tools/tool_response_manager.py` | Normalizes tool responses for the agents |
| `lggraph_tools/tool_selector.py` | Helps pick the right tool for a request |

---

## 🏗️ The Two-Layer Design

```text
┌─────────────────────────────────────────────────┐
│  LAYER 2 — WHAT AGENTS SEE                      │
│  ToolAssign registry: name + description + args  │
│  (the "menu" the model chooses from)             │
└───────────────────────┬─────────────────────────┘
                        │ wrapper picks the real function
┌───────────────────────▼─────────────────────────┐
│  LAYER 1 — WHAT ACTUALLY RUNS                   │
│  search_google_tool()  run_shell_command()  …    │
│  wrapped in GoogleSearchToolWrapper etc.         │
│  (validation, error handling, logging)           │
└─────────────────────────────────────────────────┘
```

Why layers? The **registry** can list a tool and its schema even before it's called; the **wrapper** keeps the raw function clean and crash-safe.

---

## 🚀 Quick Start: Use The Built-ins

```python
from coldwind.core.tools.lggraph_tools.google_search_tool import search_google_tool
from coldwind.core.tools.lggraph_tools.run_shell_command_tool import run_shell_command

results = search_google_tool("cold wind ai github")
output  = run_shell_command("ls -la")
```

In the running app you rarely call these directly — tool mode + the orchestrator pick them for you.

---

## 🔧 Quick Start: Add Your Own Tool

```python
# 1) Write the raw function
def get_weather(city: str) -> str:
    """Fetch the weather for a city."""
    ...

# 2) Give it a typed schema (tool_schemas/tools_structured_classes.py)
# 3) Wrap it (tool_wrappers/) and register:
from coldwind.core.tools.lggraph_tools.tool_assign import ToolAssign

registry = ToolAssign(name="get_weather", description="Get current weather", func=get_weather)
registry.set_tools_list([...])      # or append_tools_list(your_tool)
```

Once registered, agents discover it through the tool-selection prompts — **no agent code changes needed**.

---

## 🌐 MCP Tools Are Tools Too

The `mcp/` package discovers external MCP servers and registers their tools via `DynamicToolRegister`; `UniversalMCPWrapper` (here, in `mcp_wrapper/`) adapts any MCP tool into the same shape as the built-ins. **One menu, zero special cases.**

---

## ❓ FAQ

- **What happened to `neo4j_tool` / `file_reader` / `code_executor` / `get_all_tools`?** They never existed here — old docs were fiction. Neo4j access lives in `RAG/neo4j_rag.py`, file reading in `mcp_wrapper/filesystem_wrapper.py`, and the registry is `ToolAssign`.
- **Is shell execution safe?** It runs in a subprocess with response management and logging — treat it like any shell access: be deliberate about what you run.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (old file documented fictional tools; rebuilt from the five real tools + registry design).**
