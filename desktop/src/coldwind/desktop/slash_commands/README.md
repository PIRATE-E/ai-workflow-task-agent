# ⌨️ Slash Commands (`coldwind.desktop.slash_commands`)

> Discord-style `/` commands for the desktop chat: type `/`, get autocomplete, run a command.

**Part of:** `coldwind-desktop` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
you type "/agent --high analyze this"
        │
        ▼
ui/chatInputHandler (autocomplete dropdown)   ◄─ reads registry live
        │
        ▼
runtime/DesktopContext ─ DesktopCommandParser.parse_and_execute()
        │                        │
        ▼                        ▼
   ParseCommand.get_command()   ExecutionAr.execute() ──► handler ──► CommandResult
        (parse + validate)          (look up in OnRunTimeRegistry)

core never imports desktop — it reaches this package only through the
CommandParserInterface contract (core/interfaces/ui_interface.py).
```

---

## 🎯 Why This Exists

- **One uniform way** to invoke features: `/command --option value`.
- **Discoverable**: `/help` lists everything; the input box autocompletes as you type.
- **Extensible**: drop a new command file in `commands/`, register it — agents and UI pick it up automatically.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `protocol.py` | The data shapes: `SlashCommand`, `CommandOption`, `CommandResult`, `SlashOptionValueType` |
| `parser.py` | `ParseCommand` — turns `/text` into a validated `SlashCommand` |
| `executionar.py` | `ExecutionAr` — finds the command in the registry and runs its handler |
| `registry.py` | `Registry` ABC + the three command exceptions |
| `on_run_time_register.py` | `OnRunTimeRegistry` — thread-safe **singleton** holding every registered command |
| `commands/` | One file per command (`help`, `clear`, `exit` + `core_slashs/` routing commands) |

---

## 📜 The Data Shapes (`protocol.py`)

```text
SlashCommand ──────────────────────────────────────────
  command       "/agent" → "agent" (no slash)
  options       [CommandOption, …]
  requirements  placeholder for future permissions (Requirements)
  description   shown by /help and autocomplete
  handler       the function to call
CommandOption ──────────────────────────────────────────
  name, type, value, description, required, default
CommandResult ──────────────────────────────────────────
  success, message, data, additional_warnings, error
```

**Option types** (`SlashOptionValueType`):

```bash
/agent --high analyze this     # STRING → value = ["analyze this"] (joined)
/read  --files a.txt,b.txt     # CHARACTER → value = ["a.txt", "b.txt"] (comma-split)
```

The parser infers the type: multiple words after `--name` → `STRING`; a single word → `CHARACTER` (which then splits on commas in `CommandOption.__post_init__`).

---

## 🏗️ How One Command Travels (step by step)

```text
 1. Type "/agent --high analyze the market"
 2. ChatCompleter (ui/) shows ❓/🤖/🧹…-styled suggestions from the registry
 3. DesktopCommandParser.parse_and_execute(raw_input)      (runtime/DesktopContext.py)
 4.     ▼  ParseCommand.get_command()
        rejects anything not starting with "/" (ValueError)
        → SlashCommand(command="agent", options=[...], handler=None)
 5.     ▼  ExecutionAr.execute(slash_cmd)
        looks up "agent" in OnRunTimeRegistry
        not found → CommandResult(success=False, error=...)
 6.     ▼  agent_handler(command, options)      (commands/core_slashs/agent.py)
 7.     ▼  CommandResult(success=True, data={"message_type": "agent"})
        → the chat router uses data["message_type"] to route the message
```

**Who registers the commands?** `DesktopCommandParser.register_default_commands()` in `runtime/DesktopContext.py` calls all six `register_*_command()` functions at boot — **not** core (layering rule: desktop owns its commands).

---

## 📚 Available Commands (verified)

| Command | What it does | Options |
|---------|--------------|---------|
| `/help` | List all commands, or one command's details | `--command <name>` |
| `/agent` | Route a task to agent mode | `--low` / `--medium` / `--high` |
| `/llm` | Route a message to plain LLM chat | none |
| `/tool` | Route to tool mode | none (options planned — see todo in `use_tool.py`) |
| `/clear` | Wipe chat state, tool responses, and the screen | none |
| `/exit` | Issue an exit ticket — graceful shutdown | none |

> ⚠️ Old docs listed a `/chat` command — the real command is **`/llm`** (`core_slashs/chat_llm.py`), and old docs showed `/tool --name <tool>` options that don't exist yet.

### Behind the scenes

- **`/clear`** calls `ToolResponseManager().clear_response()` + `StateAccessor().clear_state()` + a terminal clear.
- **`/exit`** doesn't kill the app directly — it emits an **exit ticket** through the `ExitListener` from `ContextRegistry.get().get_listeners()['exit']`, so cleanup runs first.
- **`/agent`** complexity handlers (`_handle_low/medium/high_option`) are placeholders; today it just routes with `data={"message_type": "agent"}`.

---

## 🚀 Quick Start: Add Your Own Command

```python
# 1) Create commands/my_command.py
from ..protocol import SlashCommand, CommandOption, CommandResult
from ..on_run_time_register import OnRunTimeRegistry

def register_my_command() -> None:
    registry = OnRunTimeRegistry()
    try:
        registry.register(SlashCommand(
            command="my_command",
            options=[CommandOption(name="value", description="…")],
            requirements=None,
            description="What my command does",
            handler=my_command_handler,
        ))
    except registry.CommandAlreadyRegisteredError:
        pass

def my_command_handler(command: SlashCommand, options: CommandOption | None) -> CommandResult:
    try:
        return CommandResult(success=True, message="Done!", data={"message_type": "…"})
    except Exception as e:
        return CommandResult(success=False, message="Failed.", error={"error": str(e)})
```

2) Add `register_my_command` to the list in `DesktopCommandParser.register_default_commands()` (`runtime/DesktopContext.py`).
3) Type `/my_command` — autocomplete, `/help`, and routing all pick it up automatically.

---

## 🔑 API Reference (verified signatures)

```python
SlashCommand = ParseCommand.get_command("/agent --high text")   # classmethod
result = ExecutionAr().execute(slash_command)                    # → CommandResult

registry = OnRunTimeRegistry()          # thread-safe singleton
registry.register(cmd)                  # raises CommandAlreadyRegisteredError
registry.get("agent")                   # raises CommandNotFoundError
len(registry)  |  "agent" in registry  |  del registry["agent"]  |  iter(registry)
```

Exceptions live as nested classes on `Registry`: `CommandNotFoundError`, `CommandAlreadyRegisteredError`, `CommandExecutionError`.

---

## ❓ FAQ

- **"Command not found"?** It was never registered — check `register_default_commands()` and the try/except there.
- **Why a singleton registry?** The UI completer, the executor, and `/help` all read the same live list at runtime.

---

**Cold Wind AI · `coldwind-desktop` · Updated in the v2.0.0 docs pass (fixed /chat → /llm, real registration path, ticket-based /exit, removed dead `src.*` imports).**
