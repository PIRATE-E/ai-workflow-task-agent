# 🔧 Utils Package (`coldwind.core.utils`)

> The shared toolbox — model access, cloud API calls, event listeners, and small helpers.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
agents/ ──────► ModelManager ──────► Ollama (local)  ┐
                    │                                ├─ one unified interface
tools/  ──────►     └── openai_chat ──► OpenAIIntegration ──► cloud APIs ┘

system_logging/ ──► timestamp_util (log timestamps)
agents/tools ────► argument_schema_util (tool schemas)

anyone ◄────────── listeners/ (events, exit tickets, status spinners)
```

---

## 🎯 Why This Exists

- **One door to every AI model** — local Ollama or cloud OpenAI/NVIDIA/Kimi, same API.
- **One place for cross-cutting helpers** instead of copy-pasted snippets everywhere.
- **Event listeners** let far-apart code talk without importing each other.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `model_manager.py` | `ModelManager` — one object that talks to ANY model (Ollama or cloud) |
| `open_ai_integration.py` | `OpenAIIntegration` — cloud API client with rate limiting + circuit breaker |
| `argument_schema_util.py` | `get_tool_argument_schema(tool)` — read a tool's parameter schema |
| `timestamp_util.py` | `get_formatted_timestamp()` — consistent timestamps for logs |
| `listeners/event_listener.py` | `EventListener` — the event hub everything else plugs into |
| `listeners/exit_listener.py` | `ExitListener` — two-ticket exit: one "get ready", one "go" |
| `listeners/rich_status_listen.py` | `RichStatusListener` — animated status spinner in the terminal |

> 💡 The old `socket_manager.py` and `error_transfer.py` are **gone** (removed in the v2.0.0 purge). For logging, see `system_logging/debug_protocol/debug_callers_api.py`.

---

## 🏗️ How ModelManager Works (the star of this package)

`ModelManager` **inherits from `ChatOllama`** — so it behaves exactly like a normal LangChain chat model, no matter which engine is behind it.

```text
              ModelManager  (singleton)
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
   Ollama (local)            OpenAIIntegration (cloud)
   qwen, llama, deepseek…    openai/gpt-oss, nvidia, kimi…
        │                           │
        └───────────┬───────────────┘
                    ▼
        .invoke()  /  .stream()   — same calls, any model
```

```python
from coldwind.core.utils.model_manager import ModelManager

model = ModelManager(model="qwen2.5:32b-instruct")   # local Ollama
response = model.invoke([HumanMessage(content="What is 2+2?")])

for chunk in model.stream([...]):     # streaming works too
    print(chunk.content, end="")

data = ModelManager.convert_to_json(response)  # pull JSON out of a reply
```

Other key methods: `load_model(name)` to switch models, `cleanup_all_models()` on shutdown, and the `openai_chat` property that exposes the cloud client.

---

## 🛡️ OpenAIIntegration — built to survive bad API days

```text
           request ──► rate limiter (max calls per minute)
                            │
                            ▼
                    circuit breaker open? ──yes──► fast-fail response
                            │ no
                            ▼
                       cloud API call
                       │         │
                   success      failure × 5
                       │         │
                       ▼         ▼
                  _record_     breaker OPENS
                   success()    (cooldown, then retries)
```

```python
from coldwind.core.utils.open_ai_integration import OpenAIIntegration

ai = OpenAIIntegration(api_key="...", model="openai/gpt-oss-120b")
text = ai.generate_text("Translate: hello")          # plain
for chunk in ai.generate_text("Tell a story", stream=True):  # streaming
    print(chunk, end="")
```

---

## 📡 Listeners — how far-apart code talks

```text
┌──────────────────────────────────────────────────┐
│                 EventListener (hub)               │
│                                                   │
│  RichStatusListener ── "status changed!" ──► 🌀 spinner updates │
│  ExitListener ─────── two exit tickets ──► 👋 graceful shutdown │
└──────────────────────────────────────────────────┘
```

- **`ExitListener`** requires **two tickets** before shutting down (first `emit_exit_ticket()` = warn everyone, second = actually exit) — no accidental quits.
- **`RichStatusListener`** starts/stops an animated spinner: `start_status("Working…")` → `stop_status_display()`, and can read `get_last_event()`.

---

## ❓ FAQ

- **Where did the socket debug logging go?** → `system_logging/debug_protocol/debug_callers_api.py` (`debug_info`, `debug_error`, …).
- **Why singletons?** One model manager, one API client, one event hub — they own resources that must not be duplicated.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (removed deleted socket_manager/error_transfer chapters; documented the real 7 modules).**
