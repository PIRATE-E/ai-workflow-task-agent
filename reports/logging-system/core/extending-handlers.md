# 🧱 Core: Writing Your Own Handler (Full Tutorial)

## Domain & Dependencies

**Domain:** `core` — this document covers the platform-agnostic handler contract and registration.

**Dependencies:**
- **Runtime Context** (`ContextRegistry`): provides `settings.project_root` for file-based handlers.
- **Router**: stamps `LOG_TYPE` on `LogEntry` before handlers are consulted.
- **OnTimeRegistry**: the singleton that holds all registered handlers.

---

## 1. Executive Summary

To add a new log destination (Slack, a JSON-lines file, a database, a beeper — anything), you do exactly three things:

1. **Subclass** `Handler` and give it a **unique `name`** class attribute.
2. **Implement** two methods: `should_handle()` (do I want this log?) and `handle()` (what do I do with it?).
3. **Register** an instance in the `OnTimeRegistry` singleton — once, at startup.

Nothing else in the codebase changes. The Dispatcher and Router already know how to find and feed your handler.

**Metaphor:** the registry is a mail-room clipboard. Adding your handler is writing your name on the clipboard: from then on, the sorter (Router) hands you every letter you ask for, forever.

---

## 2. The Contract You Sign

File: `core/src/coldwind/core/system_logging/handlers/handler_base.py`

```python
class Handler(ABC):

    def __init_subclass__(cls) -> None:
        if not hasattr(cls, "name"):
            raise KeyError(...)          # no name → class can't even be defined
    name: str

    @abstractmethod
    def should_handle(self, log_entry: LogEntry, *args) -> bool: ...

    @abstractmethod
    def handle(self, log_entry: LogEntry, *args) -> None: ...
```

Three hard rules, plain English:

- **`name` is mandatory.** Not a convention — a *definition-time* error. There is no way to smuggle in a nameless handler.
- **`should_handle` is your filter.** Run as cheaply as possible; it's called for *every* log entry. A "yes" means your `handle()` runs immediately after.
- **`handle` is your work.** It receives the *same* `LogEntry` object every other consenting handler got. Treat it as read-only: mutate your own data, not the entry (`LOG_TYPE` is already stamped by the Router — changing it poisons downstream handlers).

---

## 3. What You Receive — The `LogEntry`

```python
@dataclass
class LogEntry:
    LOG_TYPE: LogCategory      # stamped by Router — e.g. API_CALL
    LOG_LEVEL: LogLevel        # DEBUG / INFO / WARNING / ERROR / CRITICAL
    TIME_STAMP: str            # ready-formatted string
    MESSAGE: str               # "heading | body"
    METADATA: Dict[str, Any]   # caller-provided extras; often has "heading"
```

Everything you need to filter and to write is already on this object. You never re-parse text.

---

## 4. Recipe — A Minimal Handler, Line by Line

Goal: an `ErrorJsonlHandler` that writes **only** error-level logs to `basic_logs/errors.jsonl`, one JSON object per line.

```python
# core/src/coldwind/core/system_logging/handlers/error_jsonl.py
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
from coldwind.core.system_logging.debug_protocol import LogEntry, LogLevel
from coldwind.core.system_logging.handlers.handler_base import Handler


class ErrorJsonlHandler(Handler):
    name = "ErrorJsonlHandler"          # ← Rule 1: unique, truthful name

    def __init__(self) -> None:
        self._handle = None             # lazy: don't touch disk until needed

    # Rule 2a — the filter. Cheap, synchronous, no I/O.
    def should_handle(self, log_entry: LogEntry, *args) -> bool:
        return log_entry.LOG_LEVEL in (LogLevel.ERROR, LogLevel.CRITICAL)

    # Rule 2b — the work.
    def handle(self, log_entry: LogEntry, *args) -> None:
        if self._handle is None:
            log_dir = (
                ContextRegistry.get().get_settings().project_root
                / "basic_logs"
            )
            log_dir.mkdir(parents=True, exist_ok=True)
            self._handle = (log_dir / "errors.jsonl").open(
                "a", buffering=1, encoding="utf-8"     # line-buffered, UTF-8
            )

        payload = asdict(log_entry)      # dataclass → dict
        payload["LOG_TYPE"] = log_entry.LOG_TYPE.value    # enums → strings
        payload["LOG_LEVEL"] = log_entry.LOG_LEVEL.value
        self._handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
```

Line-by-line reasoning:

- **`should_handle` returns in microseconds.** No `open()`, no JSON, just an enum comparison — that's the entire spirit of the filter step.
- **Open the file lazily, once.** Creating files at *registration* time would leave empty files on `grep`-free quiet runs; the lazy pattern means the file only exists if an error actually happened.
- **`buffering=1` (line buffered).** Each log lands on disk immediately — critical for capturing the *last* error before a crash.
- **`asdict` + enum-to-`.value`.** JSON cannot serialize enums; convert first. (This is the exact class of bug fixed in LogEntry's earlier `to_dict` work.)

## 5. Registration — Where the `OnTimeRegistry` Meets Your Class

Pick **one** of the two existing registration points:

### Option A — Core-side (alongside `TextHandler`)

`core/engine/chat_initializer.py`, inside `_register_logging_handlers()`:

```python
OnTimeRegistry().register(ErrorJsonlHandler())
```

### Option B — Desktop boot (alongside `DashBoardHandler`)

`desktop/main_orchestrator.py`, inside `boot()`:

```python
handler_registry = OnTimeRegistry()
handler_registry.register(DashBoardHandler())
handler_registry.register(ErrorJsonlHandler())
```

Both write to the **same singleton**. Rule of thumb: core-pure handlers go in Option A; desktop-coupled ones in Option B.

⚠️ **Never register twice.** `register()` raises `RegistryError` on a duplicate `name`. If you hot-reload code, unregister first: `OnTimeRegistry().unregister(old)`.

---

## 6. How Routing Reaches You — The Decision Table

`Router.get_appropriate_handlers()` calls `should_handle` on **every** handler in registration order. So the real question is not "do I get called?" but "what did I say yes to?"

| Your `should_handle` returns… | You receive… |
|---|---|
| `True` always (like DashBoardHandler) | every log — you are a *fan-out* handler |
| `LOG_LEVEL >= ERROR` | only errors — a *severity filter* handler |
| `LOG_TYPE == LogCategory.MCP_SERVER` | only one category — a *category filter* handler |
| `"even" in LOG_LEVEL.value.lower()` | a mistake — stay data-driven |

You *cannot* change what the Router stamps (that belongs to `Router.DEFAULT_KEYWORD_MAP` / `custom_routes`), and you don't need to: reading `log_entry.LOG_TYPE` post-stamp gives you everything.

### Adding a routing keyword (optional)

If your domain needs a fresh category rule — say logs whose heading contains `"CACHE"` should become `API_CALL` — attach it where the Router is built (or globally on the class):

```python
Router._custom_routes["CACHE"] = LogCategory.API_CALL
```

Custom routes **override** defaults for the same keyword. Do this once at startup, before traffic starts.

---

## 7. Lifecycle Management — Being a Good Citizen

A handler lives as long as the process, and long-lived handlers hold resources (sockets, files). Two patterns from the built-ins worth copying:

- **Lazy acquisition** — `TextHandler` opens files inside `handle()`, not at registration. Our JSONL handler copies that.
- **Explicit cleanup** — `TextHandler.clean_up()` closes/flushed every writer. If your handler holds resources, offer the same and plug it into the shutdown path (`ChatDestructor` in `main_orchestrator.boot()`):

```python
destructor.add_destroyer_function(ErrorJsonlHandler.clean_up)  # classmethod
```

Known pitfall: cleanup code that itself logs **must** have its settings still valid at that point — this is the `project_root` bug from `handler-architecture.md` §6. In cleanup, never rely on config fields added after the ones cleanup reads.

---

## 8. Testing Your Handler

A handler is pure I/O; keep tests hermetic:

```python
def test_error_jsonl_only_writes_errors(tmp_path, monkeypatch):
    # point basic_logs at tmp_path via settings stub, or monkeypatch
    # ContextRegistry.get().get_settings().project_root
    ...
    debug_error("TEST ERR", "boom")            # goes through full pipeline
    debug_info("TEST OK", "fine")
    lines = (tmp_path / "basic_logs/errors.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["LOG_LEVEL"] == "ERROR"
```

Whether you stub the context or run against the real one, the invariant to assert is: **exactly the logs your `should_handle` said yes to appear in your output** — no more, no less.

---

## 9. Quick Reference

| Task | One-liner |
|---|---|
| Define a handler | `class MyHandler(Handler): name="MyHandler"` … implement 2 methods |
| Must-have attribute | `name` — missing → `KeyError` at class-definition time |
| Filter method | `should_handle(log_entry) -> bool` (cheap!) |
| Work method | `handle(log_entry) -> None` |
| Register (core) | `OnTimeRegistry().register(MyHandler())` in `_register_logging_handlers` |
| Register (boot) | `handler_registry.register(MyHandler())` in `boot()` |
| Unregister | `OnTimeRegistry().unregister(handler)` |
| Cleanup hook | `destructor.add_destroyer_function(MyHandler.clean_up)` |

---

## 10. Glossary

- **Fan-out** — one event, many receivers (every consenting handler runs).
- **Lazy acquisition** — opening a resource only when first truly needed.
- **Line-buffered** — write through to disk on every newline.
- **Stamping** — the Router assigning `LOG_TYPE` before handlers run.

## 11. Q&A Log

> Q: Can a handler ever see a log before the Router stamps it?
> No. `Dispatcher.dispatch_v2` calls `router.get_LOG_TYPE()` before asking any handler `should_handle`. Category is always final by delivery time.

> Q: Can my handler *block* delivery to another handler?
> No. Handlers are independent; `should_handle` only affects whether *you* run. (The Router's keyword map decides category, not handler selection.)

> Q: What if my `handle()` raises?
> There's no per-handler try/except in the dispatcher loop today — an exception aborts delivery to later handlers. Keep `handle()` defensive; swallow your own recoverable errors.