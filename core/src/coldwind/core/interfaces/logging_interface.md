# 📋 Logging Contract — The Diagnostic Stream

> `DebugLoggerInterface` — the 5-level, heading-+body structured diagnostic channel every platform must provide.

**Source:** [`logging_interface.py`](logging_interface.py) · **Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## Domain & Dependencies

**Domain:** `core` / `shared`.
Handed out by the master context ([`runtime_interface.md`](runtime_interface.md))
via `get_logger()`. Desktop's reference implementation routes into Core's
own debug protocol (`debug_info` / `debug_warning` / `debug_error` /
`debug_critical`) — see
[`../system_logging/README.md`](../system_logging/README.md) for that
machinery.

---

## 📌 Executive Summary

Core needs a way to narrate what it is doing *without* knowing where the
narration lands. The logger contract is deliberately **structured**: every
call is a `(heading, body, metadata)` triple, not a flat message string —
because GUI debug panels and dashboards want fields, not prose.

```text
Core module                     Your platform's implementation
───────────────                 ──────────────────────────────
log_warning(                    ┌─────────────────────────────┐
  "MCP Boot",                    │ Desktop: Rich debug console │
  "server X timed out",   ──────►│ GUI:     JSON event → panel │
  {"server": "fetch",             │ Server:  log file / stdout  │
   "timeout": 30}                 └─────────────────────────────┘
)
```

---

## 🔑 The Five Levels

| Method | Use it for | Desktop renders as |
|--------|-----------|--------------------|
| `log_debug(heading, body, metadata)` | Fine-grained internals, flow traces | `debug_info` panel entry (see mapping note) |
| `log_info(heading, body, metadata)` | Normal narration — "booted", "connected" | `debug_info` panel entry |
| `log_warning(heading, body, metadata)` | Recoverable oddity — "retrying", "fallback used" | `debug_warning` panel entry |
| `log_error(heading, body, metadata)` | Operation failed, execution continues | `debug_error` panel entry |
| `log_critical(heading, body, metadata)` | Severe, possibly unrecoverable | `debug_critical` panel entry |

> 💡 **Desktop mapping note (honest detail):** the desktop implementation
> routes `log_debug` to the debug protocol's `debug_info` function — the
> underlying protocol has no separate debug tier. Callers should still use
> `log_debug` semantically; the mapping is a platform choice.

**Level discipline:** pick the level by *consequence*, not by mood —
`log_error` means "this operation failed but the app runs on";
`log_critical` means "the app may not survive this". If the failure is an
exception that must be *presented*, that belongs to the
[exception contract](exception_interface.md) — the logger is the narration
channel, the handler is the presentation channel.

---

## 🧱 The `(heading, body, metadata)` Shape

| Field | Type | Role |
|-------|------|------|
| `heading` | `str` | Short fixed label — the panel section title ("MCP Boot") |
| `body` | `str` | The human-readable one-liner of what happened |
| `metadata` | `dict \| None` | Optional structured extras — IDs, counts, timings |

`metadata` is the field the platform-integration audit called out: it is the
**machine-readable lane** riding along every log call. Implementations
should treat it as first-class, not stringify it into the body.

---

## 🖥️ Structured Metadata Routing (the GUI debug-panel pattern)

The audit gap: "lacks documentation on structured JSON metadata routing to
GUI debug panels." The intended pattern — serialize the full triple as one
JSON object and hand it to the platform's event channel:

```python
import json, time

class JsonLinesLogger(DebugLoggerInterface):
    """Headless/server-grade logger: one JSON object per line."""

    def __init__(self, sink):          # sink: file handle, queue, socket…
        self._sink = sink

    def _emit(self, level, heading, body, metadata):
        self._sink(json.dumps({
            "ts": time.time(),
            "level": level,
            "heading": heading,
            "body": body,
            "metadata": metadata or {},
        }))

    def log_debug(self, heading, body, metadata=None):
        self._emit("DEBUG", heading, body, metadata)

    def log_info(self, heading, body, metadata=None):
        self._emit("INFO", heading, body, metadata)

    def log_warning(self, heading, body, metadata=None):
        self._emit("WARNING", heading, body, metadata)

    def log_error(self, heading, body, metadata=None):
        self._emit("ERROR", heading, body, metadata)

    def log_critical(self, heading, body, metadata=None):
        self._emit("CRITICAL", heading, body, metadata)
```

A GUI debug panel then subscribes to the sink and gets filterable rows
(level / heading / metadata keys) with zero prose-parsing. The desktop
equivalent is the existing debug-protocol → dashboard handler pipeline
([`../system_logging/README.md`](../system_logging/README.md)).

---

## 🧵 Thread-Safety Note

Under the [decoupled turn model](../../../../../reports/urgent_development/platform-integration-spec.md)
(§5.2), graph turns run on a **background worker thread** while the UI thread
renders. Log calls therefore arrive from at least two threads. Your
implementation must either:

- be internally thread-safe (a `queue`-based sink is the easy answer — the
  worker enqueues, the UI thread drains), or
- marshal to the UI thread before touching shared state (same event-sink
  convention as [`ui_interface.md`](ui_interface.md)).

The desktop implementation is safe here by construction: it forwards to the
core debug protocol, which already serializes through its handler pipeline.

---

## 📊 Logger vs Exception Handler — who says what

| Situation | Which contract | Why |
|----------|----------------|-----|
| "Connected to Neo4j in 120ms" | `log_info` | Narration, app healthy |
| "Retrying MCP server after timeout" | `log_warning` | Degraded but running |
| Exception caught and being **shown** to someone | `ExceptionHandlerInterface` | Presentation is the handler's job |
| Exception caught, noted in diagnostics, execution continues | `log_error` **and** handler (if user-visible) | Narration is the logger's job |

---

## ✅ Testing Checklist

1. **All five levels emit:** each method produces one record with the correct
   `level` field.
2. **Metadata survives:** `metadata={"k": "v"}` arrives on the consumer side
   as a dict, not a stringified blob.
3. **`metadata=None` tolerated:** default route works, no `AttributeError`.
4. **Cross-thread safety:** firing `log_info` from a worker thread while the
   UI thread drains the sink never interleaves a record.

---

## 📖 Glossary

- **Diagnostic stream** — the continuous narration channel; distinct from
  the exception presentation channel.
- **JSON-lines** — one serialized JSON object per line; the recommended wire
  format for headless sinks.
- **Event sink** — the thread-safe callback/queue a platform injects so
  records cross from worker thread to UI thread safely.

---

## ❓ Q&A Log

> **Q: Why `(heading, body)` instead of a single message?**
> Headings are stable keys a panel can group and filter on; bodies are the
  human detail. Flat strings force every consumer to parse prose.

> **Q: Can one implementation serve both a debug panel and a file?**
> Yes — fan out inside `_emit` (write the JSON line, also push the event).
  The contract does not constrain the sink topology, only the call shape.

> **Q: Where does the desktop `log_debug` actually land?**
> In the `debug_info` tier of the core debug protocol — see the mapping note
> in the levels table and
> [`../system_logging/README.md`](../system_logging/README.md).

---

**Cold Wind AI · `coldwind-core` · Created in the platform-docs pass (2026-10-10).**
