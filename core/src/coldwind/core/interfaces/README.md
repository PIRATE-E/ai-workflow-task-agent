# 🔌 Interfaces Package (`coldwind.core.interfaces`)

> The five contracts every platform must speak — Core's **only** window to the outside world.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
        ┌───────────────────────────────────────────────┐
        │            PRESENTATION PLATFORM              │
        │  (Desktop CLI · Slint+Rust GUI · FastAPI …)   │
        │                                               │
        │   implements the contracts below  ─────────────┼───┐
        └───────────────────────────────────────────────┘   │
                                                            ▼
┌────────────────────────────────────────────────────────────────────┐
│                       COLDWIND CORE ENGINE                          │
│                                                                    │
│   ContextRegistry.get() ──► PlatformRuntimeContextInterface        │
│         ├── get_settings()          ──► CoreSettinngs               │
│         ├── get_logger()            ──► DebugLoggerInterface       │
│         ├── get_error_handler()      ──► ExceptionHandlerInterface  │
│         ├── get_message_display()    ──► MessageDisplayInterface   │
│         ├── get_command_parser()     ──► CommandParserInterface    │
│         ├── register_service()/get_service()  ──► dynamic store     │
│         ├── is_exiting()/request_exit()/reset_exit_request()       │
│         └── console/debug_console/socket/listener mutable slots    │
└────────────────────────────────────────────────────────────────────┘
```

**Domain & Dependencies:** `core` / `shared`. These ABCs sit at the very bottom of
Core's dependency graph — everything in the engine (`engine/`, `agents/`, `tools/`)
consumes them; they import nothing except each other and
[`coreSettings.py`](../config/coreSettings.py). External platforms (desktop, GUI,
server) import and *implement* them.

---

## 🎯 Why This Exists

- **The Layering Invariant lives or dies here**: Desktop imports Core, **Core
  NEVER imports Desktop**. These abstract contracts are the "ports" in a
  ports-and-adapters architecture — Core codes against the port, each platform
  supplies the adapter.
- Core contains **zero UI assumptions**. No terminal, no window, no prompt.
  Whatever looks like UI in Core's eyes is just an interface method call.
- **Swapping the platform swaps only the adapters.** The engine, graphs, tools,
  and MCP wiring never change when a new presentation layer is added.

---

## 📦 Module Map

| File | Contract defined | Deep documentation |
|------|------------------|--------------------|
| [`runtime_interface.py`](runtime_interface.py) | `PlatformRuntimeContextInterface` — the master contract bundling every service Core can touch | [`runtime_interface.md`](runtime_interface.md) |
| [`ui_interface.py`](ui_interface.py) | `MessageDisplayInterface` + `CommandParserInterface` (+ the `print_message` utility) | [`ui_interface.md`](ui_interface.md) |
| [`exception_interface.py`](exception_interface.py) | `ExceptionHandlerInterface` + the `@exception_handler` decorator | [`exception_interface.md`](exception_interface.md) |
| [`logging_interface.py`](logging_interface.py) | `DebugLoggerInterface` — the 5-level diagnostic stream | [`logging_interface.md`](logging_interface.md) |

> 💡 The master contract (`runtime_interface.py`) is the one a **new platform
> implements**; the four satellite interfaces are the ones that contract
> **hands back** to Core. Implement the satellites first, then wire them into
> one context class.

---

## 🏗️ The Platform Checklist

Any presentation platform (GUI, server, CLI) binds to Core in seven moves:

```text
1. Subclass CoreSettinngs          → add platform-only config keys
2. Implement DebugLoggerInterface   → 5 log levels
3. Implement ExceptionHandlerInterface → how errors are presented
4. Implement MessageDisplayInterface   → where messages land
5. Implement CommandParserInterface    → how input is routed
6. Assemble a PlatformRuntimeContextInterface subclass (owns all of the above)
7. ContextRegistry.activate_context(your_context) — then boot the engine
```

Details, contracts, failure modes, and reference code for every step live in the
deep docs listed in the Module Map above. The canonical worked example for the
whole checklist is the desktop implementation:
[`../../../../../desktop/src/coldwind/desktop/runtime/DesktopContext.py`](../../../../../desktop/src/coldwind/desktop/runtime/DesktopContext.py).

---

## 🔗 Related

- The audit + blueprint that motivated these docs:
  [Platform Integration Spec](../../../../../reports/urgent_development/platform-integration-spec.md)
- The registry that binds your context at boot:
  [`../runtime/README.md`](../runtime/README.md)
- The config you subclass: [`../config/coreSettings.md`](../config/coreSettings.md)
- Link hub for all platform docs:
  [`../../../../../reports/core-platform-docs/README.md`](../../../../../reports/core-platform-docs/README.md)

---

**Cold Wind AI · `coldwind-core` · Created in the platform-docs pass (2026-10-10), closing the platform-integration-spec audit gap "zero shelf READMEs in core/interfaces/".**
