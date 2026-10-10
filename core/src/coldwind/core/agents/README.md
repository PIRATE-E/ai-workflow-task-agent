# 🤖 Agents Package (`coldwind.core.agents`)

> The routing brain: reads your message, decides what kind of work it is, and sends it down the right path.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
user message
     │
     ▼
classify_agent ──► "what type of message is this?"
     │
     ├─ 💬 chat   ──► chat_llm.py          (just talk to the model)
     ├─ 🛠️ tool   ──► tool_selector.py     (pick + run ONE tool)
     ├─ ⚡ agent  ──► agent_mode_node.py    (multi-step mission)
     │                    └─► agentic_orchestrator/  (hierarchical sub-agents)
     └─ ⚡ slash  ──► desktop slash_commands  (handled by the desktop layer)
```

---

## 🎯 Why This Exists

- **One question decides everything:** "is this small talk, a quick tool call, or a whole mission?"
- Small jobs stay **fast** (chat / single tool). Big jobs get the **full orchestrator**.
- LangGraph wires these pieces into one compiled graph — each function is a graph **node**.

---

## 📦 Module Map (all real, all current)

| File | What it does |
|------|--------------|
| `classify_agent.py` | `classify_message_type(state)` — the front door; tags each message |
| `router.py` | `route_message(state)` — reads the tag, picks the next node |
| `chat_llm.py` | `generate_llm_response(state)` — plain chat reply |
| `tool_selector.py` | `tool_selection_agent(state)` + `ToolSelection` — chooses a tool for tool-mode |
| `agent_mode_node.py` | `agent_node(state)` — the `/agent` entry; hands big tasks to the orchestrator |
| `node_factory.py` | `NodeFactory` + `create_*_node()` helpers — builds graph nodes |
| `agents_schema/agents_schema.py` | `ToolSelection`, `message_classifier` — typed Pydantic outputs |
| `agentic_orchestrator/` | The hierarchical multi-agent engine → **has its own README** |

---

## 🏗️ How One Message Travels (step by step)

```text
 1. You type: "research the top 3 competitors and save a summary"
        │
 2.     ▼  classify_message_type(state)
        message_type = "agent"        (it's a mission, not small talk)
        │
 3.     ▼  route_message(state)
        routes to agent_node
        │
 4.     ▼  agent_node(state)
        hands the goal to agentic_orchestrator
        │
 5.     ▼  … planning, spawning sub-agents, tool calls …
        │
 6.     ▼  final response lands in state["messages"]
```

**The state** that flows between nodes is the `State` TypedDict from `coldwind.core.models.state` (see the models README) — messages plus the current `message_type`.

---

## 🧩 The Graph Behind It

The nodes above are wired together by the **engine package**: `GraphBuilder` (in `engine/graphs/node_assign.py`) assembles them and calls `compile_graph()`. Agents define the **behavior**; engine defines the **wiring**.

```text
        ┌──────────────┐
        │  classifier  │  classify_agent.py
        └──────┬───────┘
               ▼
        ┌──────────────┐
        │    router    │  router.py ──► chat / tool / agent
        └──────┬───────┘
      ┌────────┼────────────┐
      ▼        ▼            ▼
   chat_llm  tool_selector  agent_node ──► agentic_orchestrator/
```

---

## 🚀 Quick Start (for developers)

You rarely call agents directly — the desktop app feeds them. But the pieces are plain functions over `state`:

```python
from coldwind.core.agents.classify_agent import classify_message_type
from coldwind.core.agents.router import route_message

result = classify_message_type(state)   # {"message_type": "chat" | "tool" | "agent" | ...}
```

- Need to **add a new route?** Add a branch in the classifier prompt + `router.py`, then a node for it.
- Need **multi-step autonomy?** That's `agentic_orchestrator/` — see its README.

---

## ❓ FAQ

- **What happened to `ToolAgent`?** It never existed in this codebase — old docs described an imagined API. The real flow is the one diagrammed above.
- **Where are tool definitions?** In `tools/lggraph_tools/` (see the tools README).

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (file was in reversed line order and documented a nonexistent `ToolAgent` — rebuilt from the real routing flow).**
