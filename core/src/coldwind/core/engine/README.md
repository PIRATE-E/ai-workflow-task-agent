# 🚂 Engine Package (`coldwind.core.engine`)

> Headless execution engine: compiles the agent graph, initializes core subsystems, processes execution tickets, and coordinates graceful shutdown.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
desktop/main_orchestrator ──► ColdWindEngine ──► GraphBuilder ──► LangGraph
   (host platform /               (headless facade)   (wiring)      (compiled graph)
    turn loop)                           │
                                         └──► ChatDestructor (graceful shutdown)
```

> ⚠️ Legacy `ChatInitializer` and in-memory listeners have been **purged**. Core runs headlessly via `ColdWindEngine.boot()` and processes turns via `process_ticket(ticket: TicketIn) -> TicketOut`.

---

## 🎯 Why This Exists

- **Headless Facade**: Core provides a stateless `process_ticket(TicketIn)` interface that any host (Desktop CLI, Slint native GUI, FastAPI server) can drive.
- **Deterministic Boot**: Boots core dependencies in strict order — message classes, Neo4j, tool registries, logging, MCP servers, and compiled LangGraph.
- **Stateless Turn Processing**: Turns take structured `TicketIn` models and return `TicketOut` results, keeping Core independent of terminal UI loops.
- **Graceful Shutdown**: Coordinates teardown across models, MCP servers, browser workers, and drivers via `ChatDestructor`.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `coldwind_engine.py` | `ColdWindEngine` — headless facade for booting and executing tickets |
| `chat_destructor.py` | `ChatDestructor` — registers + runs every cleanup function |
| `graphs/node_assign.py` | `GraphBuilder` — wires agent nodes into a compiled LangGraph graph |

---

## 🏗️ Boot Sequence (`ColdWindEngine.boot`)

```text
Host calls ColdWindEngine.boot()
        │
        ▼  1. _set_core_classes()        LangChain message classes → dynamic context
        ▼  2. _initialize_neo4j()        Neo4j graph database driver
        ▼  3. _tools_register()          register core tools → ToolAssign registry
        ▼  4. _register_logging()        logging handlers & text formatters
        ▼  5. _initialize_mcp_servers()  external MCP servers + tool discovery
        ▼  6. compile_graph()            GraphBuilder(state).compile_graph()
        ▼  7. save_graph_png()           optional graph visualization (png_file_path)
        │
        ▼  Engine ready for tickets: engine.process_ticket(ticket)
```

---

## 🧩 Graph Wiring (`GraphBuilder`)

```text
GraphBuilder(state)
   ├── _assigning_nodes()   classifier, router, chatBot, tool_agent, agent_node
   ├── _assign_edges()      routing table and conditional edges
   └── compile_graph()      → runnable LangGraph compiled Pregel graph
```

The **nodes themselves** live in `../agents/` — engine only decides how they connect. Behavior (agents) vs wiring (engine) stays cleanly split.

---

## 👋 Graceful Shutdown (`ChatDestructor`)

```text
Ctrl+C or Host Exit
      │
      ▼  ChatDestructor.call_all_cleanup_functions() runs destroyers in order:
            • ModelManager.cleanup_all_models()
            • MCP_Manager.stop_all_servers() / cleanup()
            • BrowserHandler cleanup
            • Neo4j driver close
      ▼  Process exits cleanly — no dangling subprocesses or locks
```

Host platforms register teardown callbacks via `ChatDestructor.add_destroyer_function(fn)`.

---

## 🚀 Quick Start

```python
from coldwind.core.engine.coldwind_engine import ColdWindEngine
from coldwind.core.models.ticket_in import TicketIn

# Boot engine inside active context
engine = ColdWindEngine.boot()

# Execute a turn
ticket = TicketIn(user_prompt="Hello ColdWind", session_state={})
ticket_out = engine.process_ticket(ticket)
print(ticket_out.content)
```

---

## ❓ FAQ

- **Where did `ChatInitializer` go?** It was purged. The chat loop belongs to host platforms (e.g. `desktop/src/coldwind/desktop/main_orchestrator.py`); Core is headless.
- **How do status updates reach the UI?** Presenters subscribe to Core's `OnTimeRegistry` (e.g. `DesktopStatusHandler`), which receives `LogEntry` streams during execution.

---

**Cold Wind AI · `coldwind-core` · Updated to reflect headless facade and purged legacy boot modules.**
