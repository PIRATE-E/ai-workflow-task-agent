# 🚂 Engine Package (`coldwind.core.engine`)

> The boot sequence and the main loop: builds the graph, registers everything, runs the chat — and cleans up on the way out.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
desktop/main_orchestrator ──► ChatInitializer ──► GraphBuilder ──► LangGraph
   (entry point,                (boot + chat loop)    (wiring)      (compiled graph)
    desktop layer)                     │
                                       └──► ChatDestructor (graceful shutdown)
```

> ⚠️ The old docs placed `main_orchestrator` here — it actually lives in the **desktop** layer now (`desktop/src/coldwind/desktop/main_orchestrator.py`). Core never imports desktop.

---

## 🎯 Why This Exists

- Somebody has to **boot everything in the right order** — settings, graph, tools, MCP, logging, slash commands.
- The chat loop must **react to signals** (Ctrl+C) instead of dying mid-write.
- Shutdown must **release resources** (models, MCP servers, browser, Neo4j) — that's the destructor's job.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `chat_initializer.py` | `ChatInitializer` — boots the app and runs the chat loop |
| `chat_destructor.py` | `ChatDestructor` — registers + runs every cleanup function |
| `graphs/node_assign.py` | `GraphBuilder` — wires agent nodes into a compiled LangGraph graph |

---

## 🏗️ Boot Sequence (`ChatInitializer`)

```text
desktop calls ChatInitializer
        │
        ▼  1. _set_core_classes()        runtime context, message classes, listeners
        ▼  2. initialize_neo4j()         graph database driver
        ▼  3. tools_register()           every tool → ToolAssign registry
        ▼  4. _register_slash_commands() /exit, /agent, … (desktop layer supplies them)
        ▼  5. _register_logging_handlers()  text handlers → basic_logs/*.txt
        ▼  6. _initialize_mcp_servers_sync() external MCP servers + tool discovery
        ▼  7. set_graph()                GraphBuilder(state).compile_graph()
        ▼  8. set_exit() + on_exit()     wire the exit tickets
        ▼  9. save_graph_png()           optional graph picture (png_file_path)
        │
        ▼  run_chat()                    ◄── THE MAIN LOOP lives here
```

---

## 🧩 Graph Wiring (`GraphBuilder`)

```text
GraphBuilder(state)
   ├── _assigning_nodes()   classifier, router, chat, tool, agent nodes…
   ├── _assigning_edges()   who points to whom (routing table)
   └── compile_graph()      → runnable LangGraph, handed back via set_graph()
```

The **nodes themselves** live in `agents/` — engine only decides how they connect. Behavior (agents) vs wiring (engine) stays cleanly split.

---

## 👋 Graceful Shutdown (`ChatDestructor`)

```text
Ctrl+C or /exit
      │
      ▼  register_cleanup_handlers() had already installed a signal handler
      ▼  call_all_cleanup_functions()   runs every registered destroyer in order:
            • ModelManager.cleanup_all_models()
            • MCP_Manager.stop_all_servers() / cleanup()
            • BrowserHandler cleanup
            • ExitListener final ticket
      ▼  process exits — no dangling processes, no orphaned temp files
```

Anyone can add cleanup: `chat_destructor.add_destroyer_function(my_cleanup)` — the desktop entry point uses exactly that for its resources.

---

## 🚀 Quick Start

```python
# This is what the desktop entry point does (simplified):
from coldwind.core.engine.chat_initializer import ChatInitializer

chat = ChatInitializer(context)      # boots steps 1–8 above
chat.run_chat()                     # main loop until /exit
```

---

## ❓ FAQ

- **Why is the entry point not here?** Layering rule: desktop imports core, never the reverse. The desktop layer owns process-level concerns; engine owns boot **inside** core.
- **Where do logs about boot go?** `basic_logs/` — see the system_logging README.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (old paths predate the workspace restructure; reallocated main_orchestrator to the desktop layer).**
