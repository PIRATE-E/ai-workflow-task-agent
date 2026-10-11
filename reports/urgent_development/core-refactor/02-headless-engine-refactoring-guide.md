# 🛠️ Cold Wind AI — Headless Engine Refactoring & Ticket Architecture Guide

**Cold Wind AI** (`cold-wind-ai`) · **Status:** Active Architectural Blueprint · **Target Phase:** Core Decoupling (Phase 2)  
**Parent Specification:** [`01-platform-integration-spec.md`](01-platform-integration-spec.md) · **System Shelf:** [`README.md`](README.md)

## Domain & Dependencies

**Domain:** `core` / `shared` / `engine-architecture`  
This document defines the architectural refactoring of `coldwind-core`'s execution engine (`ChatInitializer` and `ChatDestructor`) to transition from a CLI-biased terminal harness into a stateless, headless turnkey engine (`ColdWindEngine`).

**Dependencies:**
- **Core Interfaces** ([`../../../core/src/coldwind/core/interfaces/`](../../../core/src/coldwind/core/interfaces/)): `runtime_interface.py`, `ui_interface.py`, `exception_interface.py`, `logging_interface.py`.
- **Core Engine Legacy** ([`../../../core/src/coldwind/core/engine/`](../../../core/src/coldwind/core/engine/)): `chat_initializer.py`, `chat_destructor.py`, `graphs/node_assign.py`.
- **Architecture Base Reference** ([`../../new_wind_ai/COLD_WIND_ARCHITECTURE_BASE.md`](../../new_wind_ai/COLD_WIND_ARCHITECTURE_BASE.md)): §5 Core Engine Contracts & Invariants.
- **In-Package Core Platform Docs** ([`../../core-platform-docs/README.md`](../../core-platform-docs/README.md)): Runtime context, configuration schema, and service store contracts.

---

## 1. Executive Summary

Cold Wind AI Core is evolving from a terminal-centric chat loop into a pure **headless agentic engine**. Under the repository's architectural invariants, Core is the brain, not the body: it executes agent graphs, coordinates MCP tools, and queries knowledge stores, but it **never owns the application loop, blocks on terminal prompts, or dumps history files to disk**.

To achieve multi-platform integration across Desktop CLI, native Slint + Rust GUI (`ai-workflow-gui`), and headless FastAPI servers without code duplication or architectural drift, we introduce the **Turnkey Headless Engine Model**:
1. **Contract Handshake (Boot Phase):** The host platform activates its concrete runtime context via `ContextRegistry.activate_context(platform_context)` and calls `engine.boot()`. Core discovers tools, wires MCP servers, and compiles LangGraph internally.
2. **Execution Handshake (Turn Phase):** The host platform dispatches an immutable **`Ticket`** to `engine.process_ticket(ticket)`. Core runs LangGraph for that single interaction, streams real-time events to the platform's registered display and logging handlers, and returns a structured **`TurnResult`**. Core then forgets the turn state completely.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PLATFORM AMBASSADORS                            │
│    Desktop CLI  │  Slint + Rust GUI (ai-workflow-gui)  │ FastAPI Server │
└──────────┬─────────────────────────────┬───────────────────────┬───────┘
           │ 1. Boot Handshake           │ 2. Ticket Handshake   │
           ▼                             ▼                       │
┌────────────────────────────────────────────────────────────────────────┐
│                    COLDWIND CORE HEADLESS ENGINE                       │
│                        (class ColdWindEngine)                          │
├────────────────────────────────────────────────────────────────────────┤
│  • boots MCP tool servers & ModelManager                              │
│  • compiles LangGraph StateGraph (GraphBuilder)                       │
│  • executes turns: process_ticket(ticket) -> TurnResult                │
│  • zero CLI prompts  •  zero OS signal hijacking  •  zero JSON dumps   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Platform-Provided Dependencies (What Core Needs to Boot)

Core does not run in a vacuum. Before `ColdWindEngine` can boot its internal graph, the host platform must provide configuration, handlers, and a dynamic backing dictionary via the `PlatformRuntimeContextInterface`.

```text
┌────────────────────────────────────────────────────────────────────────┐
│             PLATFORM-PROVIDED DEPENDENCIES (Required to Boot Core)     │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Configuration (Subclass of CoreSettinngs via pydantic-settings)     │
│    • settings.mcp_enabled          ──► Decides whether to boot MCP     │
│    • settings.mcp_config_path      ──► Path to .mcp.json               │
│    • settings.neo4j_uri / password ──► Credentials for knowledge graph │
│    • settings.project_root         ──► Root path for tools & logs      │
│    • settings.default_model        ──► Active LLM identifier           │
│                                                                        │
│ 2. Diagnostics & Handlers (Platform-Specific Implementations)          │
│    • get_logger()                  ──► Receives Core's startup logs    │
│    • get_error_handler()           ──► Catches @rich_exception_handler │
│    • get_message_display()         ──► Receiver for system banners     │
│                                                                        │
│ 3. Dynamic Storage Dict (The Backing Store for Core Services)          │
│    • register_service(key, val)    ──► Core injects message_classes    │
│    • get_service(key)              ──► Core retrieves message_classes  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Legacy Engine Autopsy: What Must Be Deleted / Extracted

The legacy `ChatInitializer` ([`../../../core/src/coldwind/core/engine/chat_initializer.py`](../../../core/src/coldwind/core/engine/chat_initializer.py)) and `ChatDestructor` ([`../../../core/src/coldwind/core/engine/chat_destructor.py`](../../../core/src/coldwind/core/engine/chat_destructor.py)) were written with terminal CLI assumptions baked in. 

To make Core headless and compliant with [`COLD_WIND_ARCHITECTURE_BASE.md`](../../new_wind_ai/COLD_WIND_ARCHITECTURE_BASE.md) §5, we extract and remove three specific pieces:

| Code in `chat_initializer.py` / `chat_destructor.py` | Why It Is Fragile / Biased | What Replaces It |
|---|---|---|
| **`run_chat()`** (`chat_initializer.py:648–730`) | Blocks synchronously on `context.get_command_parser().get_user_input()`. Assumes Core owns the process thread and drives a terminal CLI loop. | Extracted to `engine.process_ticket(ticket: Ticket) -> TurnResult`. Loop ownership moves to Platform. |
| **`conversation_history.json` write** (`chat_initializer.py:261`) | Dumps conversation history to a hardcoded local file on disk during `on_exit()`. Breaks statelessness and server pods. | Deleted from Core. History persistence belongs exclusively to the Platform (SQLite, DB, or disk). |
| **`ChatDestructor` signal binding** (`chat_destructor.py:30–45`) | Core directly binds `signal.signal(SIGINT)` / `SIGTERM`, crashing on background threads in embedded hosts (e.g. Rust/Slint via PyO3). | Automatic binding removed. Signal handling is governed by the Platform host entry point. |

> [!WARNING]
> **Core Invariant:** Core must never manage the conversation loop or disk persistence. Core receives the ticket, executes the graph for that single turn, streams progress events, returns the updated state, and forgets it.

---

## 4. The Turnkey Generator Architecture

A common architectural pitfall is "over-decoupling": stripping Core of its setup logic and forcing each platform (Desktop CLI, Slint Rust GUI, FastAPI server) to wire tools, connect MCP servers, and compile LangGraph manually.

### The Physical Metaphor: The Turnkey Power Generator
Think of `coldwind-core` as a **portable power generator** (an enclosed engine in a steel frame):
- The manufacturer pre-assembles the internal cylinders (LangGraph), the fuel injection (ModelManager), the battery (Neo4j), and the auxiliary outlets (MCP tool discovery).
- The homeowner does not need to learn how to wind copper coils or solder wiring harnesses.
- The homeowner simply bolts the generator down (Boot Handshake) and plugs their appliances into the universal power receptacle (Ticket Handshake).

If we stripped setup from Core, every single platform would end up copying and pasting 300+ lines of identical LangGraph compilation and tool wiring code. When a tool changes or a graph edge is modified, every platform would have to be patched simultaneously. By keeping assembly inside `ColdWindEngine.boot()`, Core remains turnkey and maintainable.

---

## 5. End-to-End Execution Trace: How Platforms Drive It

Here is the exact step-by-step lifecycle showing how any host platform (Desktop CLI, Slint GUI in Rust, or FastAPI web service) initializes Core and runs conversational turns:

```text
STEP 1: BOOT PHASE (Runs Once at App Startup)

Platform (Desktop / Server / Slint)
  ├── 1. Instantiates PlatformConfig (inherits CoreSettinngs)
  ├── 2. Instantiates PlatformContext (implements 5 interfaces + dynamic dict)
  ├── 3. Calls ContextRegistry.activate_context(platform_context)
  └── 4. Calls engine = ColdWindEngine(); engine.boot()
             │
             ▼
        ColdWindEngine.boot() in Core
             ├── Reads platform_context.get_settings()
             ├── Logs startup via platform_context.get_logger()
             ├── Registers message_classes into platform_context._services
             ├── Discovers & boots MCP tool servers
             └── Compiles LangGraph (GraphBuilder)

─────────────────────────────────────────────────────────────────────────

STEP 2: TURN PHASE (Runs Whenever User Sends Input)

Platform
  ├── 1. Fetches current session's working_state from DB/memory
  ├── 2. Packages ticket: Ticket(user_message, working_state, ...)
  └── 3. Calls result = engine.process_ticket(ticket)
             │
             ▼
        ColdWindEngine.process_ticket() in Core
             ├── Injects ticket.user_message into ticket.working_state
             ├── Runs compiled_graph.invoke(working_state)
             ├── Emits read-only progress events to platform display handler
             └── Packages and returns TurnResult(new_working_state, final_response)
             │
             ▼
Platform
  ├── 4. Saves new_working_state to session database
  └── 5. Displays result in UI (Slint window, Terminal, or HTTP response)
```

---

## 6. Conceptual Data Models (Pseudo-Code)

Core communicates with platforms exclusively through structured, immutable data transfer objects.

### 6.1 `Ticket` (Input Specification)

```python
# Conceptual Schema: core/models/ticket.py
class Ticket:
    ticket_id: str          # Unique UUID for turn tracking
    session_id: str         # Conversation session identifier
    user_message: str       # Raw user query or slash command
    working_state: dict     # Current conversation state (e.g. LangChain messages list)
    allowed_tools: list     # Optional whitelist of tool names (None = allow all)
    limits: dict            # Execution boundaries: max_iterations, timeout_seconds
```

### 6.2 `TurnResult` (Output Specification)

```python
# Conceptual Schema: core/models/ticket.py
class TurnStatus(Enum):
    SUCCESS = "success"
    ERROR = "error"
    INTERRUPTED = "interrupted"
    CIRCUIT_BROKEN = "circuit_broken"

class TurnResult:
    ticket_id: str          # Matches input ticket_id
    status: TurnStatus      # Outcome classification
    new_working_state: dict # Updated state to be stored by the platform
    final_response: str     # Extracted assistant response for immediate display
    error_detail: str       # Human-readable failure explanation if status != SUCCESS
    usage_metrics: dict     # Latency, tokens consumed, tool invocation counts
```

---

## 7. Pseudo-Code Blueprint: The `ColdWindEngine` Facade

This pseudo-code demonstrates how `ColdWindEngine` acts as the clean, headless facade wrapping the internal LangGraph compilation and tool assignment, using the platform context's own diagnostic logger:

```python
# Conceptual Blueprint: core/engine/coldwind_engine.py

class ColdWindEngine:
    def __init__(self):
        self._is_booted = False
        self._compiled_graph = None
        self._destructor = ChatDestructor()

    def boot(self) -> None:
        """Bootstraps Core internals using the active platform context."""
        context = ContextRegistry.get()
        if context is None:
            raise RuntimeError("ContextRegistry must have an active context before boot().")

        logger = context.get_logger()
        if logger:
            logger.log_info("Booting ColdWindEngine infrastructure...")

        # 1. Register LangChain message classes in platform's dynamic service store
        context.register_service(
            CoreRunTimeObjects.message_classes,
            (HumanMessage, AIMessage, BaseMessage)
        )

        # 2. Discover and assign tools (Native tools + dynamic MCP servers)
        tools = ToolAssigner().discover_all_tools()

        # 3. Compile LangGraph StateGraph
        self._compiled_graph = GraphBuilder(tools=tools).compile_graph()
        self._is_booted = True

        if logger:
            logger.log_info("ColdWindEngine booted; LangGraph compiled successfully.")

    def process_ticket(self, ticket: Ticket) -> TurnResult:
        """Executes a single conversational turn statelessly."""
        if not self._is_booted:
            raise RuntimeError("ColdWindEngine must be booted before processing tickets.")

        context = ContextRegistry.get()
        HumanMessage, _, _ = context.get_service(CoreRunTimeObjects.message_classes)

        # Prepare working state
        state = copy_dict(ticket.working_state)
        state["messages"].append(HumanMessage(content=ticket.user_message))

        try:
            # Synchronous or worker-thread graph execution
            updated_state = self._compiled_graph.invoke(state)
            assistant_reply = extract_last_assistant_message(updated_state)

            return TurnResult(
                ticket_id=ticket.ticket_id,
                status=TurnStatus.SUCCESS,
                new_working_state=updated_state,
                final_response=assistant_reply
            )
        except Exception as exc:
            context.get_error_handler().handle_exception(exc, context="engine.process_ticket")
            return TurnResult(
                ticket_id=ticket.ticket_id,
                status=TurnStatus.ERROR,
                new_working_state=state,
                error_detail=str(exc)
            )

    def shutdown(self) -> None:
        """Explicit graceful teardown called by the host platform."""
        self._destructor.destroy()
        self._is_booted = False
```

---

## 8. Step-by-Step Refactoring Order for Python Team

To implement this architecture safely without breaking existing Desktop CLI workflows, execute in this precise order:

```text
Phase 2.1: Data Models
  └── Define Ticket and TurnResult Pydantic models in core/models/ticket.py

Phase 2.2: Destructor Sanitization
  └── Remove automatic signal.signal() bindings from core/engine/chat_destructor.py
      (Host platform entry points become the sole owners of OS signals)

Phase 2.3: Headless Facade Implementation
  └── Author ColdWindEngine in core/engine/coldwind_engine.py
      (Encapsulate boot(), process_ticket(), and shutdown())

Phase 2.4: Headless Validation Script
  └── Build a standalone headless verification script (demo_headless_turn.py)
      (Boots engine, passes a Ticket, asserts TurnResult, verifies zero disk files)

Phase 2.5: Desktop CLI Adapter Alignment
  └── Refactor desktop/main_orchestrator.py to drive the interactive loop
      via ColdWindEngine.process_ticket() instead of chat.run_chat()

Phase 2.6: Deprecation of Legacy ChatInitializer
  └── Mark chat_initializer.py deprecated; purge run_chat() and local disk writes
```

---

## 9. Testing & Validation Checklist

Before certifying the headless engine for the Slint + Rust GUI (`ai-workflow-gui`) or server deployments, verify:

1. **Headless Execution Verification:**
   - Execute `demo_headless_turn.py` with standard input redirected to `/dev/null`. Verify the process boots, finishes a turn, and terminates cleanly with exit code 0.
2. **Zero Disk Pollution:**
   - Confirm that running 10 turns creates **zero** local files (no `conversation_history.json`, no stray `.txt` files) in the working directory.
3. **Secondary Thread Execution:**
   - Run `engine.process_ticket()` on a background `threading.Thread`. Confirm that no `ValueError: signal only works in main thread` is raised.
4. **Context Logger Verification:**
   - Confirm startup messages appear via `context.get_logger()` rather than standard root logger `print` statements.

---

## 10. Learning Outcomes & Architectural Invariants

- **The Invariant Bifurcation:** Core owns *graph logic, tool discovery, and turn execution*. Platforms own *the event loop, user prompt rendering, persistence, and operating system signals*.
- **Stateless Turns:** Core never "remembers" across turns on its own. It receives working state in the Ticket, modifies it in LangGraph, returns it in the TurnResult, and forgets it.
- **Turnkey Setup Protection:** Core keeps its internal wiring centralized. Decoupling does not mean making platforms assemble the engine; it means giving platforms a clean button to start it and an outlet to plug into.

---

## 11. Glossary

- **Ticket:** An immutable data packet containing a user prompt, conversation working state, and execution limits passed from a Platform to Core.
- **TurnResult:** A structured response containing the outcome status, updated working state, and assistant response returned from Core to a Platform.
- **Platform Ambassador:** A platform-side adapter (Desktop CLI loop, Slint Rust PyO3 wrapper, or FastAPI route) that translates platform events into Tickets.
- **Turnkey Engine:** A self-contained software component that manages its own internal setup and compilation, requiring only configuration and satellite handlers from the caller.

---

## 12. Q&A Log

> **Q: Why shouldn't Core save conversation history to disk automatically?**  
> Because Core cannot know what storage architecture a platform uses. A desktop app might use a local JSON file, an embedded GUI might use SQLite, and a multi-user server might use Postgres or Redis. Forcing a local file dump creates file-lock race conditions and violates server statelessness.

> **Q: How does Slint Rust GUI receive streaming tokens if `process_ticket()` returns only at the end of the turn?**  
> Streaming tokens are dispatched in real-time during graph execution via `context.get_message_display().display_message()`. The platform's display implementation forwards those tokens directly across a thread-safe channel to the UI event loop, while `TurnResult` delivers the final consolidated state summary when the turn completes.
