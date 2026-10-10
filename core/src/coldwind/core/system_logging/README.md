# 📝 System Logging Package (`coldwind.core.system_logging`)

> Call one function, get a clean categorized log file — plus a live dashboard feed.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
your code ──► debug_info() ──► LogEntry ──► Dispatcher ──► Router ──► TextHandler ──► basic_logs/*.txt
                                              │
                                              └──► dashboard_transport ──► desktop dashboard (live view)
```

---

## 🎯 Why This Exists

- Logs from **different parts of the system go to different files** — MCP junk never drowns your API logs.
- **One function** to log anything; routing and files are automatic.
- Easy to **add new destinations** (files, databases, dashboards) without touching callers.

---

## 🚀 The Only API You Normally Need

```python
from coldwind.core.system_logging.debug_protocol.debug_callers_api import (
    debug_info,
    debug_warning,
    debug_error,
    debug_critical,
)

debug_info("MCP • SERVER_STARTED", "GitHub server started", {"server": "github"})
```

That's it. Everything below happens automatically.

---

## 🏗️ What Happens When You Call `debug_info(...)` (step by step)

```text
 1. debug_info("MCP • SERVER_STARTED", "GitHub server started")
        │
 2.     ▼  builds a typed LogEntry
        LogEntry(category, level, timestamp, "heading | body", metadata)
        │
 3.     ▼  Dispatcher.dispatch_v2(log_entry)
        hands the entry to the routing system
        │
 4.     ▼  Router reads the heading keywords
        "MCP" → LogCategory.MCP_SERVER
        │
 5.     ▼  asks OnTimeRegistry for all registered handlers
        │
 6.     ▼  TextHandler formats the entry (TextFormater)
        │
 7.     ▼  writes to basic_logs/log_MCP_SERVER.txt   ✅ done
```

---

## 📂 Where Logs Land (one file per category)

| `LogCategory` | File in `basic_logs/` | What lands there |
|---|---|---|
| `MCP_SERVER` | `log_MCP_SERVER.txt` | MCP server lifecycle |
| `API_CALL` | `log_API_CALL.txt` | Cloud model requests |
| `TOOL_EXECUTION` | `log_TOOL_EXECUTION.txt` | Tool runs |
| `AGENT_WORKFLOW` | `log_AGENT_WORKFLOW.txt` | Agent/orchestrator steps |
| `ERROR_TRACEBACK` | `log_ERROR_TRACEBACK.txt` | Crashes + tracebacks |
| `OTHER` | `log_OTHER.txt` | Everything else |

Levels (`LogLevel`): `DEBUG` → `INFO` → `WARNING` → `ERROR` → `CRITICAL`.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `debug_protocol/debug_callers_api.py` | **Your entry point** — `debug_info/warning/error/critical` |
| `debug_protocol/__init__.py` | `LogEntry`, `LogLevel`, `LogCategory` (+ JSON `to_/from_` helpers) |
| `debug_protocol/dashboard_transport/` | Streams entries to the desktop dashboard (live view) |
| `dispatcher.py` | `Dispatcher.dispatch_v2(entry)` — the mail room |
| `router.py` | `Router` — keyword map decides the category (`DEFAULT_KEYWORD_MAP`, plus `custom_routes`) |
| `registry.py` + `on_time_registry.py` | `Registry` ABC + `OnTimeRegistry` singleton holding all handlers |
| `handlers/handler_base.py` | `Handler` ABC + `TextHandler` (file writer with **rotation**) |
| `formatter.py` | `OutPutFormater` ABC + `TextFormater` — makes entries readable |
| `protocol.py` | Legacy protocol definitions (`LogLevel`, `LogCategory`, `LogEntry`) |
| `adapter.py` | `ProtocolAdapter` — converts old-style debug JSON → `LogEntry` |

---

## 🔧 Extending: Add Your Own Handler

Want logs in a database? Subclass `Handler`:

```python
from coldwind.core.system_logging.handlers.handler_base import Handler

class DatabaseHandler(Handler):
    def should_handle(self, log_entry, *args) -> bool:
        return log_entry.level.value in ("ERROR", "CRITICAL")

    def handle(self, log_entry, *args) -> None:
        ...  # write to your database
```

`Handler` uses `__init_subclass__`, so subclasses are wired up automatically — handlers are registered at startup in `ChatInitializer._register_logging_handlers()`.

**Log rotation** is controlled by desktop settings: `log_text_handler_rotation_size_limit_mb`, `log_text_handler_rotation_time_limit_hours`, `log_rotation_always_on`.

---

## ❓ FAQ

- **Heading format?** `CATEGORY • WHAT_HAPPENED` — the category word is what the Router keys on.
- **Old socket/`error_transfer.py` pipeline?** Removed in v2.0.0 — the subprocess debug window is now the desktop dashboard.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (rewritten from the purged socket pipeline to the real debug_callers_api flow).**
