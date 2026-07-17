# AI-Agent-Workflow — Copilot Instructions v4.0

> **Authority:** Developer behavioral instructions for this repository.
> **Scope:** All Copilot agents working in this codebase.
> **Updated:** 2026-07-06

## ⚡ OUTPUT MODE ARCHITECTURE

| Output channel | Brevity? | Rule |
|---|---|---|
| Tool calls / file writes / memory | No | Use full detail |
| Chat text | Yes | Keep it compact |

## 🔴 ALWAYS-ON RULES

1. **Session start:** load context with memory + repo discovery.
2. **Reports/docs:** update indexes after creating a new report or doc.
3. **Code changes:** discuss first when the change is non-trivial; then implement.
4. **Comments:** when editing code, explain what changed and why inside the file.

## 💬 CHAT OUTPUT MODE

- Use short, professional responses.
- Use emojis and bullets when they improve scanability.
- For uncertain technical claims, verify before stating them.

## 🧠 MEMORY & CONTEXT

- Use memory tools when they preserve important context.
- Log meaningful findings, decisions, and outcomes.
- Before compaction, preserve anything that should survive the turn.

## 📂 PROJECT CONTEXT

### Core layout

```text
User Input → Router → Handler → UI Output
                ↓
         StateAccessor() singleton
```

### Stack

Python 3.13+ | LangGraph | Pydantic v2 | prompt_toolkit | rich | MCP | browser-use | OpenAI/Ollama | chromadb

### Key files

| Component | Location | Purpose |
|---|---|---|
| Entry point | `src/main_orchestrator.py` | App startup |
| State | `src/models/state.py` | `StateAccessor()` singleton |
| Graph | `src/core/graphs/node_assign.py` | LangGraph orchestration |
| MCP manager | `src/mcp/manager.py` | Server lifecycle |
| Tool routing | `src/tools/.../universal.py` | MCP tool routing |
| Logging | `src/ui/diagnostics/debug_helpers.py` | `debug_info()` |
| Errors | `src/ui/diagnostics/rich_traceback_manager.py` | Rich exception handling |
| CLI input | `src/ui/chatInputHandler.py` | prompt_toolkit autocomplete |
| Config | `src/config/settings.py` | Environment + MCP config |

### Build / test / lint

```bash
python src/main_orchestrator.py
python tests/run_tests.py
pytest tests/path/test_file.py -v
ruff check src/ tests/
ruff check --fix src/ tests/
```

### Conventions

- Use `pathlib.Path`.
- Prefer single quotes.
- Keep type hints.
- Use `async def` + `await` for async code.

## 🤖 AVAILABLE CUSTOMIZATIONS

| Resource | Type | Purpose |
|---|---|---|
| `learning-tutor` | Skill | Explains concepts and code clearly |
| `mcp-memory-management` | Skill | Memory/entity/relation conventions |
| `report-protocol` | Agent | Deep research and structured reports |
| `project-context-initializer` | Agent | Load project context without edits |
| `memory-optimizer` | Agent | Clean and consolidate memory graph |

**Locations:** repo-level customizations live in `.github/agents`, `.github/skills`, and `.github/hooks`.  
User-level mirrors live in `~/.copilot/agents`, `~/.copilot/skills`, and `~/.copilot/hooks`.

## 🔄 QUICK REFERENCE

```text
Session start → load context + log start
Report request → use report-protocol
Need project context → use project-context-initializer
Memory cleanup → use memory-optimizer
Teaching request → use learning-tutor
Chat-only answer → keep it compact
```

## 🪝 HOOKS

Best-effort hook parity is configured through shell-based hooks that mirror the Qwen workflow:

- session start / end logging
- agent stop reminders
- memory-tool reminders
- pre-compact preservation reminders

## ✅ STATUS

This repository uses the Copilot-native mirror of the Qwen-style workflow.
