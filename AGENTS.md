# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## ⚡ Output Mode Architecture

Brevity constraints apply **ONLY to chat text output**. Tool calls and file writes are unrestricted.

## 🔴 Always-On Rules

- **Code changes → verbose comments**: When modifying code, explain WHAT changed and WHY inside the file.
- **Code change protocol**: STOP → Analyze → Discuss with user → Get approval → Implement → Explain changes. Never modify code without discussing first (trivial/explicitly-requested changes excepted).
- **Zero hallucination**: Never invent APIs, functions, syntax, or facts. Verify through documentation or web search. Say "I need to research this" rather than guess.
- **Learning-first**: Explain WHY, not just WHAT. Provide context for design decisions.
- **Follow user instructions literally**: If user says "explain every line" → explain EVERY line.

## 💬 Chat Output Format

- Emojis for section headers. Structured with headers, bullets, code blocks.
- Short (< 200 words): direct answer. Medium (200–800): topic → key points → important note. Long (800+): add TL;DR box.
- Uncertain claims: search 2-3 web sources, include confidence line.

## 🎨 Warp Visual Response Formatting

**Applies to all chat text output in Warp's dark UI.** Goal: responses that are visually appealing, rich, and easy to scan — without losing accuracy, completeness, or signal. Form over function is never acceptable; pretty must not mean shallow.

### 🖥️ Dark-Mode Visual Rules (every response)

- Open every new idea with a `##` or `###` header. Never bury a new topic inside a paragraph.
- **Bold** every command, filename, flag, and key term the first time it appears.
- Put every command or snippet in its own fenced code block with a language tag (` ```bash `, ` ```python `). Never inline more than 2–3 words of code in running text.
- Use a `>` blockquote for exactly ONE thing per reply: the single tip or warning that matters most. Do not stack blockquotes.
- Separate major sections (Summary → Key Points → Questions, etc.) with a `---` horizontal rule for a clean visual break on a dark background.
- Tables: max 3 columns, max 6 rows, short cells. Bigger → split into two tables.
- No paragraph longer than 3 sentences. Longer → convert to bullets, or cut.
- Use ONLY these emoji, and only as section markers: 📌 Summary · 🔑 Key Points · ❓ Questions · 💡 Suggestions · ⚠️ Warning · 🖥️ Visual · 🎨 Style. No decorative emoji elsewhere.

### ✨ Rich Visuals & ASCII Art (when they add value, not for decoration)

- **Prefer Mermaid diagrams** for flows, sequences, dependencies, and state — they render inline in Warp !!
- **Use ASCII art / box drawings** for short structural sketches when a diagram is overkill (e.g., a quick tree, a call-stack sketch, a side-by-side comparison). Keep ASCII art inside a fenced ` ```text ` block so it aligns correctly in the dark UI.
- **Character/emoji accents** are allowed as section markers (see the allowed emoji list above) but must never decorative-spam the prose. Characters do not replace explanation.
- **Readability over flair:** ASCII art must use standard box-drawing characters only where they help alignment (`├──`, `│`, `└──`, `─`, `│`). Do NOT draw big logo banners in ASCII — they eat vertical space and add no information.
- **Quality protection rule:** visuals are a _layer on top of_ the answer, never a substitute. Every diagram, ASCII sketch, or table must be accompanied by the same technical depth a plain-text answer would have had. If a visual would force trimming technical content, drop the visual, keep the content.
- **Inline images:** when a local screenshot/diagram file exists and would clarify, use `![alt](path/to/file.png)` inline — Warp renders it.

### 📌 TL;DR Box Convention (Long Answers)

For any response ~400 words or longer, open with a `>` blockquote TL;DR box (1–3 lines), then continue with structured sections. For shorter responses, skip the TL;DR box.

### 🔒 Visual Rules Never Override

- Safety warnings stay plain and immediate even if ugly.
- Real code, real file paths, real command output are never paraphrased or prettified at the cost of accuracy.
- Citation XML at the end of a response is never wrapped in a visual block.

## 📦 Project Identity

**Cold Wind AI** (`cold-wind-ai`) — multi-platform AI system (desktop current; server + mobile planned). Architecturally: multi-agent orchestration, dynamic MCP integration, hybrid AI models (Ollama + cloud APIs), and browser automation. Current migration state lives in the memory graph.

**Long-term vision** (see `reports/new_wind_ai/COLD_WIND_AI_VISION.md`): Multi-platform AI platform — desktop (current), mobile (planned, Flutter), cloud backend (planned, FastAPI) — with a tool marketplace where users click to install tools instead of editing `.mcp.json`.

**Tech stack:** Python 3.13+ | uv workspaces | LangGraph | Pydantic v2 (pydantic-settings) | prompt_toolkit | rich | MCP | browser-use | chromadb | Neo4j

Project version is the source of truth in `pyproject.toml` — do not inline a version number here (it rots on every release).

## 🗺️ Architecture

This is a **uv workspace mono-repo** with namespace packages under `coldwind.*`:

```
core/     → coldwind-core       Shared agent layer: config, state, MCP protocol, tools, RAG, logging, engine, agents, interfaces
desktop/  → coldwind-desktop    Desktop CLI layer: entry point, slash commands, UI (prompt_toolkit + rich), runtime context
server/   (planned, empty skeleton — not yet created)
```

**Runtime flow** (desktop entry):

```
desktop/src/coldwind/desktop/main_orchestrator.py   → Entry. Creates DesktopConfig, DesktopRunTimeContext, ChatDestructor
  ↓                                                     Registers cleanup for SocketManager, ModelManager, MCP_Manager, BrowserHandler
core/engine/chat_initializer.py                     → Boots LangGraph graph, registers tools + slash commands
core/engine/graphs/node_assign.py                   → GraphBuilder(State).compile_graph()
agents/classify_agent.py                            → Routes input: chat | tool | agent-mode | slash command
agents/agentic_orchestrator/                        → Hierarchical sub-agent spawning (AgentGraphCore → spawn_agent)
```

## 🧱 Architectural Invariants

Invariants must hold **across every phase and every platform**. They are not current-state context — they are architectural rules the agent must respect when writing or refactoring any code, regardless of where migration currently stands.

- **Layering direction**: Desktop imports Core. **Core NEVER imports Desktop.** Core only knows the contracts defined in `core/interfaces/` (RuntimeContextInterface, CoreSettinngs, etc.), never concrete platform implementations.
- **Config vs runtime split**: Pure configuration lives in pydantic-settings (`CoreSettinngs` → `DesktopConfig`, etc.). Live runtime objects live on the active runtime context accessed via `ContextRegistry.get()`. Never re-introduce a flat global settings module that mixes both.
- **Active context lookup**: Runtime state is obtained through `ContextRegistry.get()` — the active `RuntimeContextInterface`. Never re-introduce a separate singleton/service-locator for the same purpose.
- **Dynamic service store**: Core-only runtime objects (Neo4j driver, langchain message-class bundle, etc.) are registered and retrieved via the enum-keyed dynamic store on the context: `context.register_service(CoreRunTimeObjects.<name>, value)` / `context.get_service(CoreRunTimeObjects.<name>)`.
- **No circular dependencies** across the `coldwind.*` namespace packages (core, desktop, server). Platform-specific code depends on core contracts; core depends only on its own interfaces.

File-by-file configuration summaries and current migration state live in `reports/` and the memory graph, not inline here — those describe the _current snapshot_, which shifts per phase.

## 💻 Commands

```bash
# Install workspace dependencies
uv sync

# Activate venv
source .venv/bin/activate

# Run the application
python desktop/src/coldwind/desktop/main_orchestrator.py

# Run all tests (no --asyncio-mode flag needed; already in pyproject)
pytest tests/ -v

# Run single test
pytest tests/path/test_file.py -v

# Skip slow/integration tests
pytest tests/ -v -m "not slow and not integration"

# Lint
ruff check core/src/ desktop/src/ tests/

# Auto-fix lint
ruff check --fix core/src/ desktop/src/ tests/
```

**Package manager:** `uv` (not pip). Dependencies declared per workspace member in `pyproject.toml`. **Pytest:** configured in `pyproject.toml` (`asyncio_mode = "auto"`, markers: `slow`, `integration`, `requires_api`, `requires_mcp`; shared fixtures in `tests/conftest.py`). Do not pass `--asyncio-mode` on the CLI.

## 🎨 Core Module Layout

Per-module / per-file summaries are **not inlined here** — they shift every phase, and inline snapshots rot. The accurate current map lives in:

- **`reports/`** — long-form architecture reports under topic folders (`reports/agents/`, `reports/mcp/`, `reports/browser/`, `reports/logging/`, `reports/new_wind_ai/`, etc.). See `reports/README.md` for the index.
- **Memory graph (memory MCP)** — entities keyed by component capture the architectural insight, not the file inventory. Query live entity names at runtime; do not encode snapshot names here (they shift per phase).

Use these sources on demand when a task actually needs the file-by-file map — do not pre-load them at session start.

## 🎨 Code Conventions

Rules the agent must follow when **writing or modifying code** in this repo:

- **Paths:** `pathlib.Path`, not `os.path`
- **Type hints:** required on all functions
- **Async:** `async def` + `await`
- **Config access:** `ContextRegistry.get().get_settings()` returns a `CoreSettinngs`-typed object (subclasses get desktop/server fields by inheritance).
- **Runtime-object access:** `ContextRegistry.get().get_service(CoreRunTimeObjects.<name>)` for registered runtime objects (e.g. `message_classes`, `neo4j_driver`). Pass the enum, not a string.
- **Tools:** `@tool("tool_name")` from langchain, registered via `tool_assign.py`
- **Models:** Pydantic `BaseModel`; settings use `pydantic-settings` `BaseSettings` inheritance
- **.mcp.json:** MCP server definitions at project root, loaded by `core/mcp/load_config.py`

Quote style and lint-only conventions are enforced via `pyproject.toml` ruff config — refer to the config file rather than restating rule details here.

## 📂 Context Library

The `reports/` directory contains ~99 analysis documents across 14 folders — the project's "high-cost context library." These capture every architectural decision, bug investigation, and migration plan. See `reports/README.md` for the full index. Key navigation:

- **`reports/new_wind_ai/`** — Cold Wind AI vision, roadmap, repo strategy, stratified settings design
- **`reports/mcp/`** — MCP infrastructure audit, cascade failure root cause
- **`reports/agents/`** — Hierarchical agent architecture, failure analyses, SKIP status feature
- **`reports/browser/`** — Browser automation, subprocess vs multiprocess, signal handling
- **`reports/logging/`** — Logging refactor, current architecture

## 🧠 Knowledge Base Rule (Memory MCP)

**This is a mandatory rule, not a suggestion.** Warp agents in this repo MUST use the **memory MCP** as the single source of truth for project context — architectural decisions, status, insights, patterns, and relations. Do NOT use Linear (removed from MCP support). Do NOT read `QWEN.md` or other context files to rebuild context (context bloat) — the memory graph already holds this.

Required session pattern:

1. **Session start:** load project context from memory before doing anything else.
2. **While working:** log meaningful findings, decisions, and outcomes to memory.
3. **Session end / before compaction:** preserve key outcomes to memory.

## 🧩 Skills Rule (Warp-Native, Auto-Discovered)

Warp auto-discovers skills from `.agents/skills/` (Warp's recommended primary location). Mirrors exist at `.github/skills/`, `.github/agents/`, `~/.copilot/skills/`, and `~/.copilot/agents/` for Copilot compatibility — when editing a skill, update `.agents/skills/` first (Warp's source of truth) and sync the mirrors. Warp deduplicates by name and keeps the `.agents/skills/` copy (highest precedence).

These skills are **declared as rules Warp must follow** when their trigger conditions are met — they invoke without an explicit user prompt because their descriptions mark them "Use PROACTIVELY."

All Warp-native skills in this repo (5 total):

- `mcp-memory-management` — memory-graph conventions specialist. **Apply on every memory operation** to keep the graph consistent.
  - **Entity types:** `project`, `module`, `pattern`, `solution`, `decision`, `status`, `insight`, `standard`, `workflow`
  - **Relation types:** `depends_on`, `uses`, `implements`, `relates_to`, `evolved_from`, `resolves`, `contradicts`, `enhances`, `replaces`
  - **Change tracking:** preserve before/after history when a change matters; keep historical observations that explain a decision; remove stale debugging traces once resolved.
- `learning-tutor` — explain, teach, walk through, analyze code, answer questions, give reasoning, or respond to "why / what / how".
- `project-context-initializer` — load project context read-only at session start or when context appears stale.
- `memory-optimizer` — prune/consolidate the memory graph when stale, duplicate, or redundant entries are detected.
- `report-protocol` — deep research and structured report generation.

Warp has no separate "agents" concept — every invokable unit above is a Skill. The former Copilot `.agent.md` files (`memory-optimizer`, `project-context-initializer`, `report-protocol`) were converted to Warp skills by renaming to `SKILL.md` and moving into `.agents/skills/<name>/`; their bodies are byte-identical to the originals, so behavior is unchanged.
