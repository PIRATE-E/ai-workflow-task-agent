# 🎨 UI Package (`coldwind.desktop.ui`)

> Everything the user sees and types in the terminal: the input box with autocomplete, styled message panels, the boot banner, and pretty crash reports.

**Part of:** `coldwind-desktop` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
        ┌─────────────── you ───────────────┐
        ▼                                  ▲
  chatInputHandler.py              print_message_style.py
  (type + autocomplete)            (styled reply panels)
        │                                  ▲
        ▼                                  │
  slash_commands/  ──► core chat loop ─────┘
                            │
        print_banner.py      │ crashes go to…
        (boot ASCII art)     ▼
                    rich_traceback_manager.py ──► system_logging ──► dashboard window
```

> 💡 The old debug-window socket pipeline (`debug_helpers.py`, `debug_message_protocol.py`, `rich_error_print.py`, `error_transfer.py`) was **removed in the v2.0.0 purge**. Logging is now core's `system_logging` package, and the live "debug window" is the **dashboard** (`../dashboard/`).

---

## 🎯 Why This Exists

- A plain `input()` box can't autocomplete, can't recall history — **prompt_toolkit can**.
- Raw prints are unreadable — **rich panels** give user/AI/tool messages distinct looks.
- Crashes should be **informative, not scary** — rich tracebacks with context, routed to the dashboard.

---

## 📦 Module Map (the real 4)

| File | Plain-English job |
|------|-------------------|
| `chatInputHandler.py` | `InputHandler` — the prompt_toolkit input box with slash-command autocomplete + history |
| `print_message_style.py` | `print_message(msg, sender)` — styled panels for user / AI / tool |
| `print_banner.py` | `print_banner()` — the ASCII boot banner |
| `diagnostics/rich_traceback_manager.py` | `RichTracebackManager` + `rich_exception_handler` — pretty, tracked crash reports |

---

## ⌨️ The Input Box (`chatInputHandler.py`)

```text
┌───────────────────────────────────────────────┐
│ you ➜  /ag█                                   │
├───────────────────────────────────────────────┤
│  🤖 /agent   Invoke a specific agent to…      │  ◄── live from OnRunTimeRegistry
│  ⚡ …                                         │
└───────────────────────────────────────────────┘
 TAB    → accept suggestion
 ENTER  → apply selected completion (keep typing) — or submit
 ESC    → close the dropdown        RIGHT → accept ghost text
```

- **`ChatCompleter`** reads the slash-command registry live — new commands appear in the dropdown without touching UI code.
- **`InputHandler`** is a singleton owning one `PromptSession` (history + auto-suggest + `MODERN_STYLE` theme).
- **Fallbacks**: not a TTY → plain `input('you ➜ ')`; EOF (Ctrl+D) → returns `'/exit'` so the app shuts down cleanly.

```python
from coldwind.desktop.ui.chatInputHandler import InputHandler

user_input = InputHandler().get_user_input()   # prompt: "you ➜ "
```

---

## 💬 Message Panels & Banner

```python
from coldwind.desktop.ui.print_message_style import print_message
from coldwind.desktop.ui.print_banner import print_banner

print_message("Hello!", sender="user")   # 👤 [USER] cyan panel
print_message("Hi there.", sender="ai")  # 🤖 [AI]  green panel
print_message("Done.", sender="tool")    # 🛠️ [TOOL] yellow panel

print_banner()   # the ASCII art boot banner (no arguments)
```

- The rich `Console` comes from **`ContextRegistry.get().get_console()`** — never a global.
- Optional **sound notification** on each message when `enable_sound_notifications` is on (Windows only, via `winsound`).

---

## 🚨 Crash Reports (`diagnostics/rich_traceback_manager.py`)

```python
from coldwind.desktop.ui.diagnostics.rich_traceback_manager import (
    RichTracebackManager,
    rich_exception_handler,
)

# at boot (main_orchestrator.py does exactly this):
RichTracebackManager.initialize(
    show_locals=False, max_frames=10, suppress_modules=[...],
)

# manual handling with context:
try:
    risky()
except Exception as e:
    RichTracebackManager.handle_exception(e, context="My Operation",
                                           extra_context={"user": 123})

# or just decorate:
@rich_exception_handler("Main Chat Application")
def run_chat(): ...
```

What it gives you:

| API | Plain-English job |
|-----|-------------------|
| `initialize(...)` | Boot for the main process: installs `sys.excepthook` + starts error tracking |
| `initialize_debug_process(console, ...)` | Boot for the debug/dashboard process: rich visual tracebacks |
| `handle_exception(e, context, extra_context)` | Format + log one exception (re-entrancy guarded) |
| `rich_exception_handler("Name")` | Decorator: catch → log with context → re-raise |
| `create_safe_wrapper(func, ctx, default_return)` | Wrap a function so failures return a default instead of crashing |
| `log_performance_warning(op, duration, threshold)` | Warn when an operation is slower than the threshold |
| `get_error_statistics()` / `reset_statistics()` | Error counts per category (monitoring/testing) |

> ⚠️ Old docs claimed `RichTracebackManager.install()` — that method doesn't exist; the real entry points are **`initialize()`** (main process) and **`initialize_debug_process()`** (debug window). Display goes through core's `debug_error` → the dashboard handler, never the user's chat window.

---

## 🧩 How Core Sees This Package

Core never imports these files directly. The **runtime adapters** in `runtime/DesktopContext.py` wrap them behind core's UI contracts:

```text
core contract                    desktop adapter            wraps (this package)
MessageDisplayInterface   ──►  DesktopMessageDisplay  ──►  print_message / print_banner
ExceptionHandlerInterface ──►  DesktopExceptionHandler ──►  RichTracebackManager
CommandParserInterface    ──►  DesktopCommandParser    ──►  InputHandler + slash execution
DebugLoggerInterface      ──►  DesktopDebugLogger      ──►  core system_logging debug_*
```

That's the layering invariant in action: **core defines the contracts, desktop supplies the looks.**

---

## ❓ FAQ

- **Where do my debug messages go now?** Call core's `debug_info/debug_error/...` (`coldwind.core.system_logging`) — they land in `basic_logs/*.txt` and stream to the dashboard window.
- **Why does the input box sometimes fall back to plain input?** prompt_toolkit needs a real TTY — scripts, pipes, and some IDEs don't have one; the fallback keeps the app usable.

---

**Cold Wind AI · `coldwind-desktop` · Updated in the v2.0.0 docs pass (old file documented the purged debug_helpers/socket pipeline; rebuilt from the 4 real modules + dashboard flow).**
