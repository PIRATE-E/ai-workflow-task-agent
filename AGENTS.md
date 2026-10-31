# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## ⚡ Output Mode Architecture

Brevity constraints apply **ONLY to chat text output**. Tool calls and file writes are unrestricted.

## 👥 Team Modes

This project runs in **two interaction modes**. The mode controls _how_ the AI communicates; it never changes _what_ the architecture/convention rules below require.

| Mode                   | How it's triggered                                                                                                                                     | Communication style                                                                                                                                                                                 |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Engineer** (default) | The default for all sessions in this repo                                                                                                              | Direct, fast, code-forward. No metaphors, no 1-concept-per-reply pacing, no response skeleton. Assume expert familiarity with the codebase. Brevity rules and Warp Visual Formatting still apply.   |
| **Tutor** (on demand)  | User says something like "teach me", "explain like I'm learning", "walk me through", "tutor me on X", or explicitly invokes the `learning-tutor` skill | Full learning protocol from `.agents/skills/learning-tutor/SKILL.md`: metaphor-first, plain English before code, 1 concept per reply, labeled blockquote, ❓ Questions pause, Beginner-First depth. |

**Rules:**

- Mode only changes when the user explicitly switches it. Do not guess.
- `learning-tutor` fires automatically on question/explanation prompts per its own description; in those replies follow the tutor protocol fully. Toggling to Tutor mode keeps it on for sustained teaching sessions.
- Safety warnings stay immediate and unstyled in BOTH modes.

## 🔴 Always-On Rules

- **Code changes → verbose comments**: When modifying code, explain WHAT changed and WHY inside the file.
- **Code change protocol**: STOP → Analyze → Discuss with user → Get approval → Implement → Explain changes. Never modify code without discussing first (trivial/explicitly-requested changes excepted).
- **Zero hallucination**: Never invent APIs, functions, syntax, or facts. Verify through documentation or web search. Say "I need to research this" rather than guess.
- **Learning-first**: Explain WHY, not just WHAT. Provide context for design decisions.
- **Follow user instructions literally**: If user says "explain every line" → explain EVERY line.
- **Documentation paths → strictly relative**: Every file path, reference, or markdown hyperlink in documentation and reports (`reports/`, `docs/`, `README.md`) MUST be a relative path (e.g., `../../core/src/...` or `./01-doc.md`), NEVER an absolute path (`/home/...` or `file:///...`), so that links render and navigate as clickable hyperlinks in all markdown viewers and editors.
- **RAG Subsystem Frozen / Legacy**: The legacy RAG subsystem (`core/src/coldwind/core/RAG/` and `rag_search_classifier_tool.py`) is completely frozen and deprecated pending the future Phase 2 rewrite. NEVER suggest, query, or refactor legacy RAG files during active development.

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

- **Prefer Mermaid diagrams** for structural flows, sequences, and dependencies — they render inline in Warp. **Exception:** step-by-step _teaching traces_ (tutor mode, Learning Protocol) use ASCII art in fenced ```text blocks, per the `learning-tutor` skill.
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

## ⚙️ Development Protocol

For any non-trivial change (new feature, refactor, migration step), work in this order. Each step is a checkpoint, not a suggestion.

1. **Phase 0 — Impact Gate:** Before writing any code, identify what the change touches. Query the memory graph for related entities (roadmaps, decisions, insights under `ai-workflow-task-agent`). If the change conflicts with an existing decision or depends on an unfinished roadmap step, surface that FIRST — do not silently proceed.
2. **Phase 1 — Map Current State:** State the current phase the change belongs to (e.g., "Logging Rewrite Phase 1", "API Server roadmap — blocked by AgentGraphCore"). Know what is done vs. pending before acting.
3. **Phase 2 — Execute:** Make the change following the Code Change Protocol (STOP → Analyze → Discuss → Approve → Implement). Respect the Architectural Invariants at all times.
4. **Phase 3 — Validate:** Run the relevant tests/lint commands from the Commands section. Update the affected roadmap/status entities in the memory graph and any related docs in `reports/`.

## 🔧 Failure & Debug Protocol

When something breaks or behaves unexpectedly, follow this exact order. Never jump to fixing before diagnosing.

1. **Trace the exact path:** Identify the full call path where the failure occurs (entry point → which module → which function). Quote the real file and line.
2. **Reproduce minimally:** Create or identify the smallest input/command that reproduces the failure.
3. **Isolate root cause:** State what the code _was doing_ vs. _what it should do_. Explain WHY it fails, not just WHERE. Use Python internals comparisons when helpful (e.g., "this fails the same way CPython's GIL would block two threads on one object").
4. **Log the pattern:** Record the bug, root cause, and fix in the memory graph (a `status` or `insight` entity under the project). Failed approaches get logged too — they prevent re-trying them later.
5. **Fix last:** Only now implement the fix. If the fix touches an invariant or a decision entity, note that explicitly.

## 📦 Project Identity & Long-Term Vision

**Cold Wind AI** (`cold-wind-ai`) — multi-platform AI agent framework modernizing beyond CLI into native, platform-specific desktop and server environments. Architecturally: multi-agent orchestration via LangGraph, dynamic MCP integration, hybrid AI models (Ollama + cloud APIs), browser automation, and ambassador-based microkernel ETL pipelines. Current migration state lives in the memory graph.

**Long-Term Vision & Strategic Specifications**:
- **Vision Foundation** (`reports/new_wind_ai/COLD_WIND_AI_VISION.md`): Multi-platform AI platform — desktop CLI, native GUI, mobile (planned, Flutter), cloud backend (planned, FastAPI) — with a tool marketplace where users click to install tools instead of editing `.mcp.json`.
- **Architecture Base** (`reports/new_wind_ai/COLD_WIND_ARCHITECTURE_BASE.md`): Stratified configuration model, dynamic runtime service registry, and headless engine turns.
- **Platform Integration Specifications** (`reports/urgent_development/platform-integration-spec.md` & `reports/urgent_development/core-refactor/01-platform-integration-spec.md`): Master contract defining platform runtime context boundaries, presentation decoupling, and headless engine execution.
- **RAG & Document ETL Conveyor Belt Architecture** (`reports/urgent_development/rag-ETL-infra/01-legacy-rag-bottlenecks-and-architectural-autopsy.md` & `reports/urgent_development/rag-ETL-infra/02-ambassador-conveyor-architecture-specification.md`): Future Phase 2 microkernel conveyor belt where platforms supply sovereign *Ambassadors* for document domain parsing and streaming progress. *(Note: Legacy procedural files in `core/RAG/` remain frozen pending this rewrite).*

**Active Platform Deployments**:
- **Platform 1 — Desktop CLI (`coldwind-desktop`)**: Full-featured terminal interface built with `prompt_toolkit` and `rich`, powered by `DesktopRunTimeContext`.
- **Platform 2 — Native Slint GUI (`coldwind-slint-gui`) (v0.0.1 Milestone Shipped)**: Hybrid Rust + Slint desktop GUI platform. Embeds headless `ColdWindEngine` via PyO3 FFI, executing prompt turns via `TicketIn`/`TicketOut` from a dedicated actor thread with `SlintRuntimeContext`.
- **Platform 3 — Cloud Backend (`coldwind-server`)**: Planned FastAPI service (skeleton).
- **Platform 4 — Mobile Client**: Planned Flutter mobile interface.

**Paired Companion Workspace — `/home/pirate/development/ai-workflow-gui`**:
External Rust workspace housing the native desktop GUI binary for Platform 2.
- **Tech Stack**: Rust 2024 edition, Slint UI (v1.16.0), PyO3 (v0.30.1) with `auto-initialize`.
- **Dual-Thread Concurrency Model**:
  - **Thread 0 (UI Thread)**: Dedicated 60 FPS Slint rendering, window lifecycle, and user input. Holds `!Send` models (`AppWindow` and `Rc<VecModel<ChatMessage>>`). Never touches the Python GIL.
  - **Thread N (Worker OS Thread)**: Dedicated background thread hosting embedded CPython. Blocks at 0% idle CPU on an `mpsc::sync_channel::<WorkerState>(1)` waiting for user prompts. Calls `SlintRuntime.process_ticket(TicketIn)` and marshals `Send`-safe `ChatMessage` records back to Thread 0 via `slint::invoke_from_event_loop`.
- **Dynamic FFI Descriptor Hooking**: During boot, Rust injects native closures into `RustGuiEventHandler.handle` and `swap_display_message_overrite` at the Python runtime level, piping log entries and streaming messages directly into the Rust event loop.

**Tech stack (Monorepo)**: Python 3.13+ | uv workspaces | LangGraph | Pydantic v2 (pydantic-settings) | prompt_toolkit | rich | MCP | browser-use | chromadb | Neo4j

Project version is the source of truth in `pyproject.toml` — do not inline a version number here (it rots on every release).

## 🗺️ Architecture

This is a **uv workspace mono-repo** with namespace packages under `coldwind.*`:

```text
core/        → coldwind-core       Shared headless agent engine: LangGraph nodes, tools, MCP protocols, logging, engine facade, interfaces (RAG frozen/deprecated)
desktop/     → coldwind-desktop    Platform 1: Desktop CLI layer (main_orchestrator, prompt_toolkit + rich, DesktopRunTimeContext)
slint_gui/   → coldwind-slint-gui  Platform 2: Slint GUI platform layer (SlintRuntimeContext, SlintGuiConfig, RustGuiEventHandler; main_orchestrator as future CLI setup/installer)
server/      → coldwind-server     Platform 3: Planned FastAPI backend skeleton
```

**Runtime Flows**:

1. **Desktop CLI Flow** (`coldwind-desktop`):
   ```text
   desktop/src/coldwind/desktop/main_orchestrator.py   → Entry. Creates DesktopConfig, DesktopRunTimeContext, ChatDestructor
     ↓                                                     Registers cleanup for SocketManager, ModelManager, MCP_Manager, BrowserHandler
   core/engine/chat_initializer.py                     → Boots LangGraph graph, registers tools + slash commands
   core/engine/graphs/node_assign.py                   → GraphBuilder(State).compile_graph()
   agents/classify_agent.py                            → Routes input: chat | tool | agent-mode | slash command
   agents/agentic_orchestrator/                        → Hierarchical sub-agent spawning (AgentGraphCore → spawn_agent)
   ```

2. **Native Slint GUI Flow** (Embedded PyO3 / `coldwind-slint-gui`):
   ```text
   ai-workflow-gui (Rust: src/main.rs)                 → Spawns background Worker Thread (Thread N)
     ↓ (PyO3 attach + FFI descriptor injection)
   coldwind.slint_gui.runtime.SlintGuiContext          → Initializes SlintRuntimeContext + SlintGuiConfig (".env.slint")
     ↓ (ColdWindEngine boot)
   coldwind.core.engine.coldwind_engine                → Headless ColdWindEngine compiles LangGraph workflow
     ↓ (Worker Actor Loop via sync_channel)
   ColdWindEngine.process_ticket(TicketIn)             → Runs turn; emits progress via print_message(..., sender="system")
     ↓ (slint::invoke_from_event_loop)
   ai-workflow-gui (Slint: ui/app-window.slint)        → Updates Thread 0 ListView message stack at 60 FPS
   ```

## 🧱 Architectural Invariants

Invariants must hold **across every phase and every platform**. They are not current-state context — they are architectural rules the agent must respect when writing or refactoring any code, regardless of where migration currently stands.

- **Layering direction**: Platform packages (`desktop`, `slint_gui`, `server`) import Core. **Core NEVER imports any Platform package.** Core only knows contracts defined in `core/interfaces/` (`PlatformRuntimeContextInterface`, `CoreSettings`, `MessageDisplayInterface`, `CommandParserInterface`, etc.), never concrete platform implementations.
- **Zero Presentation Leak Invariant**: Core agents and nodes MUST NEVER use direct platform presentation APIs (no `console.print`, no direct Rich Console checks). All progress and status updates must route through `print_message(content, sender="system")` via `MessageDisplayInterface`.
- **Platform-Scoped Runtime Context**: Each platform registers a concrete `PlatformRuntimeContextInterface` instance in `ContextRegistry`:
  - Desktop CLI: `DesktopRunTimeContext`
  - Slint Native GUI: `SlintRuntimeContext`
- **Config vs runtime split**: Pure configuration lives in pydantic-settings (`CoreSettings` → `DesktopConfig`, `SlintGuiConfig`, etc.). Live runtime objects live on the active runtime context accessed via `ContextRegistry.get()`. Never re-introduce a flat global settings module that mixes both.
- **Active context lookup**: Runtime state is obtained through `ContextRegistry.get()` — the active platform's `PlatformRuntimeContextInterface`. Never re-introduce a separate singleton/service-locator for the same purpose.
- **Dynamic service store**: Core-only runtime objects (Neo4j driver, langchain message-class bundle, etc.) are registered and retrieved via the enum-keyed dynamic store on the context: `context.register_service(CoreRunTimeObjects.<name>, value)` / `context.get_service(CoreRunTimeObjects.<name>)`.
- **No circular dependencies** across the `coldwind.*` namespace packages (`core`, `desktop`, `slint_gui`, `server`). Platform-specific code depends on core contracts; core depends only on its own interfaces.

File-by-file configuration summaries and current migration state live in `reports/` and the memory graph, not inline here — those describe the _current snapshot_, which shifts per phase.

## 💻 Commands

```bash
# Install workspace dependencies
# read the pyproject.toml first at any cost !! of all the workspaces
uv sync

# Run the application (CLI)
uv run --package coldwind-desktop coldwind

# Verify Slint GUI platform context import
uv run python -c "from coldwind.slint_gui.runtime.SlintGuiContext import SlintRuntimeContext"

# Lint important !!
ruff check core/src/ desktop/src/ slint_gui/src/ tests/
ty check

# Auto-fix lint
ruff check --fix core/src/ desktop/src/ slint_gui/src/ tests/
```

**Package manager:** `uv` (not pip). Dependencies declared per workspace member in `pyproject.toml`. **Pytest:** configured in `pyproject.toml` (`asyncio_mode = "auto"`, markers: `slow`, `integration`, `requires_api`, `requires_mcp`; shared fixtures in `tests/conftest.py`). Do not pass `--asyncio-mode` on the CLI.

## 🎨 Core Module Layout

Per-module / per-file summaries are **not inlined here** — they shift every phase, and inline snapshots rot. The accurate current map lives in:

- **`reports/`** — long-form architecture reports under topic folders (`reports/agents/`, `reports/mcp/`, `reports/browser/`, `reports/logging/`, `reports/new_wind_ai/`, `reports/urgent_development/`, etc.). See `reports/README.md` for the index.
- **Memory graph (memory MCP)** — entities keyed by component capture the architectural insight, not the file inventory. Query live entity names at runtime; do not encode snapshot names here (they shift per phase).

Use these sources on demand when a task actually needs the file-by-file map — do not pre-load them at session start.

## 🎨 Code Conventions

Rules the agent must follow when **writing or modifying code** in this repo:

- **Paths:** `pathlib.Path`, not `os.path`
- **Type hints:** required on all functions
- **Async:** `async def` + `await`
- **Config access:** `ContextRegistry.get().get_settings()` returns a `CoreSettings`-typed object (subclasses get desktop/server/gui fields by inheritance).
- **Runtime-object access:** `ContextRegistry.get().get_service(CoreRunTimeObjects.<name>)` for registered runtime objects (e.g. `message_classes`, `neo4j_driver`). Pass the enum, not a string.
- **Tools:** `@tool("tool_name")` from langchain, registered via `tool_assign.py`
- **Models:** Pydantic `BaseModel`; settings use `pydantic-settings` `BaseSettings` inheritance
- **.mcp.json:** MCP server definitions at project root, loaded by `core/mcp/load_config.py`
- **Doc links:** Markdown links in `reports/` and `docs/` MUST always be relative paths (`../../core/src/...`), never absolute paths (`file:///...` or `/home/...`).

Quote style and lint-only conventions are enforced via `pyproject.toml` ruff config — refer to the config file rather than restating rule details here.

## 📂 Context Library

The `reports/` directory contains ~99 analysis documents across 14 folders — the project's "high-cost context library." These capture every architectural decision, bug investigation, and migration plan. See `reports/README.md` for the full index. Key navigation:

- **`reports/new_wind_ai/`** — Cold Wind AI vision (`COLD_WIND_AI_VISION.md`), architecture base (`COLD_WIND_ARCHITECTURE_BASE.md`), roadmap, repo strategy, stratified settings design
- **`reports/urgent_development/`** — Platform integration specs (`platform-integration-spec.md`), and Next-Gen RAG & ETL Conveyor Belt architecture (`rag-ETL-infra/01-legacy-rag-bottlenecks-and-architectural-autopsy.md` & `02-ambassador-conveyor-architecture-specification.md`)
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

## 📊 Roadmap & Current State

Roadmaps and per-phase status live in the **memory graph**, not inline here — inline snapshots rot every phase.

- Query the `Roadmap: *` entities under `ai-workflow-task-agent` for long-term initiatives (API Server, AgentGraphCore refactor, Browser UX, RAG simplification, Prompts consolidation, Security hygiene).
- Query `status`/`insight`/`decision` entities for the current phase's state (e.g., Logging Rewrite Phase 1 progress, open blockers, verified percentages).
- Update these entities as work completes. Do not create an inline "Current Status" section here — it will go stale.

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
