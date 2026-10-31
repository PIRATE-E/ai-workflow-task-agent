# 🗃️ Models Package (`coldwind.core.models`)

> The shared data shapes: what flows between graph nodes, and the one place to safely read live state.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
┌──────────────┐   state flows through   ┌───────────────────┐
│ agents/      │ ──────────────────────► │ LangGraph nodes   │
│ (read/write) │        State            │ (chat, tool, …)   │
└──────┬───────┘                          └───────────────────┘
       │ reads live state
       ▼
  StateAccessor  ← the ONLY sanctioned window into running state
```

---

## 🎯 Why This Exists

- Graph nodes pass data through a **typed state** — no dicts-with-wings.
- Code *outside* the graph (tools, UI) still needs to peek at the conversation — `StateAccessor` is that **safe, single window**.
- One definition of "the message list" means every feature agrees on history.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `state.py` | `State` TypedDict — the graph's message carrier |
| `state_accessor.py` | `StateAccessor` — singleton view over the live state |

> ⚠️ Old docs described a `core/models` holding `AgentState` and `tool_models.py`. Those never existed here: **workflow models** live in `agents/agentic_orchestrator/pydantic_models.py`, and **tool schemas** in `tools/lggraph_tools/tool_schemas/`.

---

## 🏗️ The State (what flows node-to-node)

```python
from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage

class State(TypedDict):
    messages: Annotated[list[HumanMessage | AIMessage], add_messages]  # the chat history
    message_type: str    # "chat" | "tool" | "agent" | … (set by classify_message_type)
```

Two fields, that's all:

```text
   ┌──────────────────────────────────────┐
   │  State                                │
   │  ├─ messages      (grows via          │
   │  │                 add_messages)      │
   └─ ├─ message_type  (router's signal)   │
      └────────────────────────────────────┘
```

`add_messages` (LangGraph reducer) is why the history **accumulates** instead of being overwritten — each node's return value is *merged in*, not *replacing*.

---

## 🏗️ StateAccessor (the safe window)

```python
from coldwind.core.models.state_accessor import StateAccessor

accessor = StateAccessor()                  # singleton
accessor.sync_with_langgraph(state)          # nodes keep it in sync

messages = accessor.get_messages()           # full history
last     = accessor.get_last_message()       # newest message
who      = accessor.get_message_type()       # last classification
human    = accessor.get_last_human_message() # newest thing the user said
accessor.clear_state()                       # reset (e.g., /clear command)
```

```text
 LangGraph node finishes ──sync_with_langgraph──► StateAccessor ──► tools, UI, listeners
 (the only writer)                                (many readers, no mutation)
```

---

## 🚀 Quick Start (for a new node)

```python
def my_node(state: State) -> dict:
    history = state["messages"]
    return {"messages": [AIMessage(content="done")]}   # merged via add_messages
```

Return only the **changes** — LangGraph merges them into state for you.

---

## ❓ FAQ

- **State vs settings?** State changes every second during a run; settings are fixed at boot (see the config README).
- **Why a singleton accessor?** The graph owns state mutation; everyone else reads through one thread-safe window instead of smuggling raw state around.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (old file documented nonexistent `AgentState`/`tool_models.py`; rebuilt around the real `State` + `StateAccessor`).**
