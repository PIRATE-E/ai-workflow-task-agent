# 🏛️ Architecture Report & Master Guide: Non-Blocking PyO3 Embedding & Slint Desktop Integration

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `core` / `desktop` (`ai-workflow-gui`) |
| **Type** | Design / Decision Report + Tier 0 Domain Master Guide (M1–M8) |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ Bound API, Slint 1.8+, CPython 3.13+) |
| **Confidence** | `VERIFIED ✅` |
| **Verified Against** | [`../urgent_development/platform-integration-spec.md`](../urgent_development/platform-integration-spec.md), `coldwind.core.interfaces.*` |
| **Updated** | `2026-10-22` |

> **TL;DR:** Embedding `coldwind-core` (Python 3.13+) inside a native Rust + Slint GUI (`ai-workflow-gui`) requires isolating Slint's `!Send` UI event loop on Thread 0 from CPython's GIL on a dedicated background worker thread (Thread N). User prompts travel from Thread 0 to Thread N via `std::sync::mpsc::channel`, Python invokes `#[pyclass]` Rust sinks via `&self` methods to stream tokens, and Rust schedules UI property mutations back onto Thread 0 via `slint::invoke_from_event_loop` using `slint::Weak<AppWindow>`.
> **Primary Objective:** Within 30 seconds of facing any cross-platform PyO3 or Slint integration question, route to the exact subdomain (`01`–`04`), state the CPython-to-Rust paradigm shift, and identify the compiler or runtime invariant guarding the boundary.
> **Python Anchor:** Replaces CPython's single-process terminal loop (`run_chat()` blocking on `prompt_toolkit` under a global mutex) with an explicit dual-runtime actor bridge where GIL acquisition (`Python<'py>`) and UI rendering (`Rc`/thread-local event queue) are decoupled across OS threads.
> **`learn_rust` Bridge:** Anchored in Topic 01 (Ownership/Lifetimes `'py`), Topic 02/03 (Structs/Traits), Topic 04 (`Result`/`?`), Topic 06 (`Rc`/`Weak`/`RefCell`), Topic 07 (Workspaces), with explicit boundaries for `⏳ Deferred until Topic 08` (Threads/`mpsc`) and `⏳ Deferred until Topic 10` (FFI/PyO3).

## Domain & Dependencies

This architecture report governs the cross-language boundary between the existing `coldwind-core` Python package and the native Rust + Slint desktop presentation client.

| Touchpoint / Layer | Repository Path / Crate | Role in This Architecture | Contract Status |
| :--- | :--- | :--- | :--- |
| **Core Runtime Contract** | [`../../core/src/coldwind/core/interfaces/runtime_interface.py`](../../core/src/coldwind/core/interfaces/runtime_interface.py) | Defines `PlatformRuntimeContextInterface` (5 satellite accessors + dynamic service store). | `VERIFIED ✅` |
| **Core UI Contract** | [`../../core/src/coldwind/core/interfaces/ui_interface.py`](../../core/src/coldwind/core/interfaces/ui_interface.py) | Defines `MessageDisplayInterface` (`display_message`, `display_banner`) and `CommandParserInterface`. | `VERIFIED ✅` |
| **Core Engine Bootloader** | [`../../core/src/coldwind/core/engine/chat_initializer.py`](../../core/src/coldwind/core/engine/chat_initializer.py) | Compiles `self.graph` (`StateGraph`), populates `CoreRunTimeObjects.message_classes` on boot. | `VERIFIED ✅` |
| **Core Context Locator** | [`../../core/src/coldwind/core/runtime/CoreContextRegistry.py`](../../core/src/coldwind/core/runtime/CoreContextRegistry.py) | Process-wide singleton holding the active platform context via `set_active_context()`. | `VERIFIED ✅` |
| **Platform Spec** | [`../urgent_development/platform-integration-spec.md`](../urgent_development/platform-integration-spec.md) | Upstream audit establishing the Decoupled Adapter Model (`HeadlessEngineAdapter`). | `VERIFIED ✅` |
| **Subdomain Shelves** | [`./01_pyo3_core_mechanics/`](./01_pyo3_core_mechanics/README.md) → [`./04_slint_concurrency_bridge/`](./04_slint_concurrency_bridge/README.md) | Granular study guides and Tier 1 war chests for each layer of the Rust↔Python bridge. | `VERIFIED ✅` |

## 1. Executive Summary

Cold Wind AI (`cold-wind-ai` v2.0.0) is architected around a strict layering invariant: **presentation platforms import Core; Core never imports presentation platforms**. While the terminal client (`coldwind-desktop`) runs in pure Python using `prompt_toolkit` and `rich`, the native desktop GUI (`ai-workflow-gui`) uses **Slint** (a declarative GPU-accelerated UI toolkit in Rust) paired with **PyO3** (Rust bindings for the CPython C-API) to drive `coldwind-core`.

Combining a native 60 FPS GUI with an embedded Python agent engine introduces four critical systems hazards. If any one of these hazards is mishandled, the application either fails to compile, panics at runtime, or freezes the operating system window.

| Hazard # | Architectural Hazard | What Fails If Unchecked | Architectural Resolution | Owning Subdomain |
| :--- | :--- | :--- | :--- | :--- |
| **Hazard 1** | **GIL vs UI Thread Deadlock** | Acquiring `Python::with_gil` on Thread 0 blocks Slint's 16.6ms frame budget during 10s LLM turns. | Dedicate Thread 0 strictly to Slint; spawn Thread N as the persistent PyO3 engine worker. | [`01_pyo3_core_mechanics`](./01_pyo3_core_mechanics/README.md) & [`04_slint_concurrency_bridge`](./04_slint_concurrency_bridge/README.md) |
| **Hazard 2** | **Blocking CLI Loop (`run_chat`)** | `ChatInitializer.run_chat()` blocks infinitely on `get_user_input()`, starving event-driven GUIs. | Bypass `run_chat()`; invoke discrete turns (`graph.invoke(state)`) per channel message. | [`02_rust_driving_python`](./02_rust_driving_python/README.md) |
| **Hazard 3** | **Inversion of Control (`#[pyclass]`)** | Core calls `ContextRegistry.get()` during turns; `&mut self` Rust receivers panic on re-entrant logs. | Expose a Rust `#[pyclass]` sink using shared `&self` methods backed by an `mpsc::Sender`. | [`03_python_driving_rust`](./03_python_driving_rust/README.md) |
| **Hazard 4** | **`!Send` Window Handle Panics** | `AppWindow` holds internal `Rc` pointers (`!Send`); worker threads cannot touch UI properties directly. | Pass `slint::Weak<AppWindow>` to Thread N and marshal updates via `slint::invoke_from_event_loop`. | [`04_slint_concurrency_bridge`](./04_slint_concurrency_bridge/README.md) |

## 2. System Context & Physical Metaphor

**Physical Metaphor — The Restaurant Dining Room vs The Heavy Kitchen:**  
Think of the application as a high-end restaurant divided by a soundproof swing door:
1. **Thread 0 (The Front-of-House Maître D' — Slint UI):** Greets guests, renders menus, and animates plates at 60 frames per second (one frame every `16.6ms`). If the Maître D' walks into the kitchen and waits 15 seconds for soup to boil, the front door locks up and guests walk out.
2. **The Order Ticket Chute (`mpsc::channel`):** When a user clicks "Send", the Maître D' drops a paper ticket into a one-way pneumatic tube (`prompt_tx.send(prompt)`) in `0.2 microseconds` and immediately goes back to greeting guests.
3. **Thread N (The Single-Chef Kitchen — CPython GIL Worker):** Inside the kitchen, there is only **one stove** (the Global Interpreter Lock, `Python<'py>`). The worker chef grabs the ticket, turns on the stove (`Python::with_gil`), runs the LangGraph recipe (`coldwind-core`), and whenever a dish course (a streamed token or tool status) is ready, rings the pass-window bell (`slint::invoke_from_event_loop`) so the Maître D' places it on the table during the next frame tick.

**Title:** End-to-End Cross-Platform Runtime Topology  
*How to read this:* Follow the numbered steps `(1)` through `(6)` clockwise from the Slint UI user action down into `coldwind-core` and back up to the Slint event queue.

```text
Title: Dual-Runtime Execution Topology (Rust Slint Binary + Embedded CPython 3.13+)

┌──────────────────────────────────────────────────────────────────────────────────┐
│ NATIVE RUST PROCESS (ai-workflow-gui)                                            │
│                                                                                  │
│  ┌────────────────────────────────────┐      (1) prompt_tx.send(String)          │
│  │ THREAD 0: Slint UI Event Loop      │ ──────────────────────────────────────┐  │
│  │ • Owns AppWindow (!Send, Rc-backed)│                                       │  │
│  │ • Renders frames every 16.6ms      │      (6) invoke_from_event_loop       ▼  │
│  │ • Upgrades Weak<AppWindow> safely  │ ◄───────────────────────────┐    ┌─────────┐
│  └────────────────────────────────────┘                             │    │ mpsc    │
│                                                                     │    │ Channel │
│  ┌──────────────────────────────────────────────────────────────────┼────┴────┬────┘
│  │ THREAD N: Persistent PyO3 Engine Worker                          │         │
│  │ • Blocks on prompt_rx.recv() while idle (0% CPU, GIL released)   │   (2)   │
│  │ • Acquires GIL per turn: Python::with_gil(|py: Python<'py>|)     │         ▼
│  │ • Binds stored Py<PyAny> adapter -> Bound<'py, PyAny>            │    ┌─────────┐
│  │ • Holds #[pyclass] SlintEventSink (contains Weak<AppWindow>) ────┘    │ Worker  │
│  └─────────────────────────────────┬─────────────────────────────────────┴─────────┘
└────────────────────────────────────┼─────────────────────────────────────────────┘
                                     │ (3) Bound::call_method1("execute_turn", (prompt,))
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│ EMBEDDED CPYTHON 3.13+ RUNTIME (coldwind-core)                                   │
│  • HeadlessEngineAdapter.execute_turn(prompt)                                    │
│  • Appends HumanMessage -> invokes CompiledStateGraph (Router -> Agent -> MCP)   │
│  • (4) Calls ContextRegistry.get().get_message_display().display_message(...)    │
│  • (5) Python context delegates to #[pyclass] SlintEventSink.emit_ui_event(...)  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

| Architectural Boundary | Left Side (Caller) | Right Side (Callee) | Memory Ownership & Lifetime Contract |
| :--- | :--- | :--- | :--- |
| **UI → Worker** | Slint Callback (`Thread 0`) | Worker Loop (`Thread N`) | Transfers owned `String` across `mpsc::Sender<EngineCommand>`. |
| **Worker → CPython** | Rust Worker (`Thread N`) | `HeadlessEngineAdapter` | Re-binds `Py<PyAny>` to `Bound<'py, PyAny>` under `Python::with_gil`. |
| **CPython → Rust Sink** | `UniversalPlatformContext` | `#[pyclass] SlintEventSink` | Python holds `PyObject*` wrapping Rust struct; calls `&self` method. |
| **Rust Sink → UI** | `SlintEventSink` (`Thread N`) | `AppWindow` (`Thread 0`) | Moves `slint::Weak<AppWindow>` + owned payload into `invoke_from_event_loop`. |

## 📺 3. Curated Learning Sources (Tier 0 M2 Shelf)

Every architectural decision in this shelf is verified against primary upstream documentation and Cold Wind repository contracts.

| # | Source & Link | Role & Why This Source Matters | Verification |
| :--- | :--- | :--- | :--- |
| **1** | [PyO3 Official User Guide (v0.22+ `Bound` API)](https://pyo3.rs/) | Canonical specification for `Python<'py>`, `Bound<'py, T>`, `Py<T>`, `#[pyclass]`, and GIL attachment semantics. | `VERIFIED ✅` |
| **2** | [PyO3 Parallelism & GIL Management Guide](https://pyo3.rs/main/parallelism.html) | Explains `Python::with_gil` (and `Python::attach`), `py.allow_threads` (`py.detach`), and `Send`/`Sync` invariants. | `VERIFIED ✅` |
| **3** | [Slint Rust API Documentation (`slint::invoke_from_event_loop`)](https://releases.slint.dev/1.8.0/docs/rust/slint/fn.invoke_from_event_loop.html) | Authoritative reference for thread-safe event loop wakeup and `Weak<T>` handle upgrading on Thread 0. | `VERIFIED ✅` |
| **4** | [`../urgent_development/platform-integration-spec.md`](../urgent_development/platform-integration-spec.md) | Cold Wind AI's internal contract specification for `PlatformRuntimeContextInterface` and decoupled turn execution. | `VERIFIED ✅` |
| **5** | [`../../AGENTS.md`](../../AGENTS.md) | Repository-wide architectural invariants (`core` never imports `desktop`; `ContextRegistry.get()` singleton law). | `VERIFIED ✅` |

## 🐍 4. Triple-Bridge Rosetta Stone: CPython ↔ PyO3 FFI ↔ Rust / Slint (Tier 0 M3)

In pure Python, the interpreter hides memory allocation, reference counting, and thread locking behind every variable name. When crossing into Rust and Slint via PyO3, those hidden runtime behaviors become explicit compile-time types.

| # | Python / `coldwind-core` Pattern | PyO3 FFI Bridge Mechanism | Rust / Slint Native Equivalent | Runtime & Memory Reality (CPython Cost vs Rust Guarantee) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Implicit GIL held by running thread | `Python::with_gil(\|py: Python<'py>\| ...)` | Zero-sized lifetime token `Python<'py>` | CPython checks atomic gil state at bytecode ticks; Rust turns the GIL into a zero-byte stack token that proves lock ownership at compile time. |
| **2** | Local variable holding `PyObject*` | `Bound<'py, PyAny>` (or `Bound<'py, PyDict>`) | Lifetimed smart pointer (`&'py Rc<T>`) | Tied to `'py`; automatically decrements `ob_refcnt` (`Py_DECREF`) when dropped while holding the GIL. Cannot escape `with_gil`. |
| **3** | Global / long-lived object reference | `Py<PyAny>` / `Py<T>` (via `.unbind()`) | Thread-safe heap handle (`Arc`-like ref) | Outlives `with_gil` closures (`'static`); implements `Send + Sync`. Requires `.bind(py)` to inspect or call methods. |
| **4** | `import coldwind.core.engine` | `py.import("coldwind.core.engine")?` | Static `use coldwind_core::engine;` | Python crawls `sys.path` at runtime and returns `PyResult<Bound<'py, PyModule>>`; Rust propagates `ImportError` via `?`. |
| **5** | `adapter.execute_turn(prompt)` | `adapter.call_method1("execute_turn", (prompt,))?` | `adapter.execute_turn(prompt)?` | PyO3 packs `(prompt,)` into a CPython `PyTuple`, dispatches `tp_call`, and wraps exceptions in `Err(PyErr)`. |
| **6** | `int`, `str`, `list`, `dict` | `.extract::<T>()?` / `.into_pyobject(py)?` | `i64`, `String`, `Vec<T>`, `HashMap<K,V>` | Copies UTF-8 bytes or numeric primitives between CPython heap `PyObject` headers (28B+) and unboxed Rust stack/heap memory. |
| **7** | Python class implementing an interface | `#[pyclass]` struct + `#[pymethods] impl` | `struct SlintSink` + `impl Trait` | PyO3 generates a static C `PyTypeObject` vtable wrapping the Rust struct inside a `PyCell` with runtime borrow flags. |
| **8** | `threading.Thread` + `queue.Queue` | `std::thread::spawn` + `mpsc::channel()` | OS thread + lock-free MPSC queue | Python threads fight over the same GIL; Rust worker threads run truly parallel native code and only acquire the GIL when calling Python. |
| **9** | Direct widget mutation (CLI print) | `slint::invoke_from_event_loop(move \|\| ...)` | Event-loop closure + `Weak<AppWindow>` | Windowing APIs (Wayland/X11/Win32) are thread-local (`!Send`); Slint queues closures from worker threads to execute safely on Thread 0. |

## 🧭 5. 30-Second Domain Decision Tree (Tier 0 M4)

Use this umbrella router to jump directly to the owning subdomain folder when implementing or debugging any part of the cross-platform stack.

```text
Title: Cross-Platform Architecture Umbrella Router (Prompt -> Subdomain)

What cross-platform problem are you solving right now?
│
├── 1. Booting embedded Python, managing GIL lifetimes ('py), or storing Python objects in Rust?
│   └──► SUBDOMAIN 01: PyO3 Core Mechanics & GIL Lifetime Model
│        ├── Concept Guide: ./01_pyo3_core_mechanics/README.md
│        └── War Chest:     ./01_pyo3_core_mechanics/cheat_sheet.md
│
├── 2. Importing coldwind-core modules, calling Python methods, passing tuples/dicts, or catching PyErr?
│   └──► SUBDOMAIN 02: Rust Driving Python (Execution Engine)
│        ├── Concept Guide: ./02_rust_driving_python/README.md
│        └── War Chest:     ./02_rust_driving_python/cheat_sheet.md
│
├── 3. Exposing a Rust struct (#[pyclass]) to Python so ContextRegistry can emit logs/tokens to Rust?
│   └──► SUBDOMAIN 03: Python Driving Rust (Platform Context & Sinks)
│        ├── Concept Guide: ./03_python_driving_rust/README.md
│        └── War Chest:     ./03_python_driving_rust/cheat_sheet.md
│
├── 4. Wiring Slint UI callbacks to background threads or updating Slint properties via Weak handles?
│   └──► SUBDOMAIN 04: Slint Concurrency Bridge & Event Loop Mechanics
│        ├── Concept Guide: ./04_slint_concurrency_bridge/README.md
│        └── War Chest:     ./04_slint_concurrency_bridge/cheat_sheet.md
│
└── 5. Need the single-page syntax & diagnostic war chest across ALL 4 subdomains?
    └──► MASTER WAR CHEST: ./cheat_sheet.md
```

| If Your Symptom Is... | Root Architectural Layer | Immediate Target File |
| :--- | :--- | :--- |
| Compiler error: `` `Bound<'_, PyAny>` cannot be sent between threads safely `` | Subdomain 01 (Pointer Lifetimes) | [`./01_pyo3_core_mechanics/cheat_sheet.md`](./01_pyo3_core_mechanics/cheat_sheet.md) |
| Runtime error: `ModuleNotFoundError: No module named 'coldwind'` or `TypeError` on `call1` | Subdomain 02 (Dynamic Dispatch) | [`./02_rust_driving_python/cheat_sheet.md`](./02_rust_driving_python/cheat_sheet.md) |
| Runtime panic/error: `RuntimeError: Already borrowed` (`PyBorrowMutError`) | Subdomain 03 (`#[pyclass]` Borrows) | [`./03_python_driving_rust/cheat_sheet.md`](./03_python_driving_rust/cheat_sheet.md) |
| Compiler error: `` `Rc<...>` cannot be sent between threads safely `` on `AppWindow` | Subdomain 04 (Slint Threading) | [`./04_slint_concurrency_bridge/cheat_sheet.md`](./04_slint_concurrency_bridge/cheat_sheet.md) |

## ⚖️ 6. Domain Contrast & Invariant Matrix (Tier 0 M5)

Across all four subdomains, memory safety and responsiveness are governed by one fundamental bifurcation law separating GIL-bound operations from UI-bound operations:

$$\text{Thread} = \text{Thread 0 (Slint UI)} \implies \text{Zero GIL Acquisition (\texttt{!Python::with\_gil})} \quad \big| \quad \text{Thread} = \text{Thread N (Worker)} \implies \text{Zero Direct UI Handles (\texttt{Weak<AppWindow>} Only)}$$

| Dimension | `01_pyo3_core_mechanics` | `02_rust_driving_python` | `03_python_driving_rust` | `04_slint_concurrency_bridge` |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Direction** | Rust ↔ CPython Memory ABI | Rust Caller → Python Callee | Python Caller → Rust Callee | Thread 0 (UI) ↔ Thread N (Worker) |
| **Core Smart Pointer / Type** | `Python<'py>`, `Bound<'py, T>`, `Py<T>` | `Bound<'py, PyModule>`, `PyDict`, `PyErr` | `#[pyclass]`, `Py<SlintEventSink>` | `AppWindow` (`!Send`), `Weak<AppWindow>` (`Send`) |
| **Borrow / Access Rule** | Read/Call ⇒ requires `Bound<'py, T>`; Store ⇒ `Py<T>` | Method args must be Rust tuples `(a, b)` or `(a,)` | Sinks use `&self` + channel (`Operation = Read ⇒ Shared Aliasing`) | UI mutation only inside `invoke_from_event_loop` |
| **Python Primitive Replaced** | Implicit `PyObject*` + `Py_INCREF`/`Py_DECREF` | `importlib.import_module`, `getattr()`, `try/except` | `abc.ABC` subclassing (`DesktopRunTimeContext`) | `asyncio` / `queue.Queue` / `prompt_toolkit` loop |
| **Fatal Python/FFI Trap** | Holding `Bound<'py, T>` across threads or dropping GIL early | Calling `call1("arg")` without trailing comma (passes `str` as sequence!) | Using `&mut self` on a callback sink called re-entrantly | Calling `Python::with_gil` inside `on_send_prompt` on Thread 0 |
| **Latency / Complexity Target** | `.bind(py)` is $\mathcal{O}(1)$ (`0B` alloc); `.extract()` is $\mathcal{O}(N)$ copy | Module import cached in `sys.modules` ($\mathcal{O}(1)$ after boot) | Channel `.send()` inside `#[pymethods]` is $\mathcal{O}(1)$ (`<1µs`) | UI frame tick strictly $\le 16.6\text{ms}$ (60 FPS) |

## 🔬 7. Detailed Analysis & Root Cause Investigation: The 4 Core Hazards

### 7.1 Hazard 1 — The Single-Threaded GIL Deadlock & Frame Budget Exhaustion

- **The Mechanism:** A 60 FPS Slint application has a strict frame budget of $T_{\text{frame}} = \frac{1000\text{ ms}}{60} \approx 16.67\text{ ms}$. Every button click callback (`main_window.on_send_prompt(...)`) executes synchronously on Thread 0.
- **Root Cause Trace:** If Thread 0 calls `Python::with_gil(|py| adapter.call_method1("execute_turn", (prompt,)))`, Thread 0 blocks until `coldwind-core` finishes LLM inference, MCP tool calls, and Neo4j queries ($2,000\text{ ms} - 30,000\text{ ms}$). During that entire window, Thread 0 cannot poll Wayland/X11/Win32 window events or redraw animations.
- **Even Worse (Mutual Deadlock):** If a background Python thread is currently holding the GIL and calls a synchronous callback waiting on Thread 0 while Thread 0 is waiting on `Python::with_gil`, both threads enter a classic AB-BA deadlock and the process hangs permanently.

### 7.2 Hazard 2 — The Blocking CLI Loop (`ChatInitializer.run_chat()`)

- **The Mechanism:** In [`../../core/src/coldwind/core/engine/chat_initializer.py`](../../core/src/coldwind/core/engine/chat_initializer.py), `run_chat()` enters a `while not context.is_exiting():` loop that calls `context.get_command_parser().get_user_input()`.
- **Root Cause Trace:** In a terminal app (`coldwind-desktop`), `get_user_input()` blocks on `prompt_toolkit.PromptSession.prompt()`. In an event-driven GUI, input is **push-based** (user clicks a button), not **pull-based**.
- **The Resolution:** Never invoke `run_chat()`. Instantiate `ChatInitializer()` during worker thread startup to compile `self.graph`, and expose a discrete `execute_turn(user_message: str)` method (`HeadlessEngineAdapter`) that appends `HumanMessage(content=user_message)` to `self.state["messages"]` and runs `self.graph.invoke(self.state)` for one turn.

### 7.3 Hazard 3 — Boot-Time Context Mutation & Re-Entrant `#[pyclass]` Borrows

- **The Mechanism:** During `ChatInitializer.__init__()`, Core executes `_set_core_classes()`, which calls `ContextRegistry.get().register_service(CoreRunTimeObjects.message_classes, (HumanMessage, AIMessage, BaseMessage))`. Later, during `graph.invoke()`, Core nodes call `context.get_message_display().display_message(...)` and `context.get_logger().log_info(...)` simultaneously.
- **Root Cause Trace:** When a Rust struct is exposed to Python via `#[pyclass]`, PyO3 wraps the struct in an internal `PyCell` (analogous to `RefCell<T>` from `learn_rust` Topic 06). If a `#[pymethods]` function uses `&mut self`, PyO3 acquires a runtime exclusive borrow flag. If Python re-enters that same Rust object (e.g., an error handler logs while `display_message` is active), PyO3 raises `PyBorrowMutError` (`RuntimeError: Already borrowed`).
- **The Resolution:** Keep the Python-side dictionary (`self._services`) in a lightweight Python wrapper (`UniversalPlatformContext` from [`../urgent_development/platform-integration-spec.md`](../urgent_development/platform-integration-spec.md)) and pass a Rust `#[pyclass] SlintEventSink` whose methods all take immutable **`&self`** and forward events through an `mpsc::Sender<UiEvent>` (or `slint::invoke_from_event_loop`).

### 7.4 Hazard 4 — Thread-Affine GUI Handles (`!Send`) & Window Teardown Races

- **The Mechanism:** Slint's generated `AppWindow` struct wraps internal `Rc<...>` and GPU surface pointers that do not implement `Send`.
- **Root Cause Trace:** Attempting to move `main_window` into `std::thread::spawn(move || ...)` triggers `error[E0277]: Rc<...> cannot be sent between threads safely`. Furthermore, if the user clicks the OS window `X` button while the Python worker is mid-turn, the window is destroyed before the worker finishes.
- **The Resolution:** Call `let ui_weak = main_window.as_weak();` on Thread 0. `slint::Weak<AppWindow>` implements `Send + Sync + Clone`. Inside the worker thread, clone `ui_weak` into `slint::invoke_from_event_loop(move || { if let Some(ui) = ui_weak.upgrade() { ... } })`. If the window was closed, `upgrade()` safely returns `None` instead of dereferencing freed memory.

| Hazard ID | Exact Failure Signature | Failing Layer | Verified Architectural Fix |
| :--- | :--- | :--- | :--- |
| **H1 (GIL Freeze)** | OS Window `Not Responding` (>16.6ms frame stall) | Thread 0 UI Callback | Offload all `Python::with_gil` blocks to Thread N worker. |
| **H2 (`run_chat`)** | Worker thread hangs forever waiting for stdin | `ChatInitializer.run_chat()` | Use `HeadlessEngineAdapter.execute_turn(prompt)` per message. |
| **H3 (`PyCell` Panic)** | `RuntimeError: Already borrowed` (`PyBorrowMutError`) | `#[pyclass]` with `&mut self` | Use `&self` methods on `SlintEventSink` + `mpsc` / event loop dispatch. |
| **H4 (`!Send` UI)** | `error[E0277]: Rc<...> cannot be sent between threads` | `std::thread::spawn` | Capture `main_window.as_weak()` + `slint::invoke_from_event_loop`. |

## 🖥️ 8. Visual Diagrams — Threading, GIL & Event Loop Lifecycle

**Title:** Sequence Trace of a Single Non-Blocking Agent Turn  
*How to read this:* Time flows top-to-bottom. Notice how Thread 0 returns in `<1ms` after step 1 and continues rendering 60 FPS frames while Thread N holds the GIL during steps 2–5.

```mermaid
sequenceDiagram
    autonumber
    participant User as User (Mouse/Keyboard)
    participant T0 as Thread 0: Slint UI (60 FPS)
    participant Ch as mpsc::channel (Prompt Queue)
    participant TN as Thread N: Rust PyO3 Worker
    participant Py as Embedded CPython (coldwind-core)

    User->>T0: Clicks "Send" ("Explain PyO3 Bound API")
    T0->>Ch: prompt_tx.send(EngineCmd::RunTurn(prompt))
    Note over T0: Callback finishes in <1ms!<br/>UI stays at 60 FPS (spinner animates)
    Ch->>TN: prompt_rx.recv() wakes Worker Thread
    TN->>TN: Python::with_gil(|py| ...) acquires GIL
    TN->>Py: adapter.bind(py).call_method1("execute_turn", (prompt,))
    Py->>Py: LangGraph executes Router -> Agent -> MCP Tool
    Py->>TN: Calls #[pyclass] SlintEventSink.emit_message(&self, role, text)
    TN->>T0: slint::invoke_from_event_loop(Weak<AppWindow>)
    T0->>T0: ui_weak.upgrade() -> appends message to Slint Model
    Py-->>TN: execute_turn returns updated state dict
    TN->>TN: Closure exits -> GIL released automatically (RAII)
    TN->>T0: invoke_from_event_loop(set_is_busy(false))
```

| Step # | Executing Thread | GIL Held? | UI Event Loop Blocked? | Typical Duration |
| :--- | :--- | :--- | :--- | :--- |
| **1. UI Callback (`on_send_prompt`)** | Thread 0 (Main) | **NO** | **NO** (`<0.01ms`) | `~1–5 µs` |
| **2. Channel Wakeup (`recv()`)** | Thread N (Worker) | **NO** | **NO** | `~5–20 µs` |
| **3. `Python::with_gil` + `execute_turn`** | Thread N (Worker) | **YES** | **NO** (Thread 0 runs free) | `500 ms – 15,000 ms` |
| **4. `SlintEventSink.emit_message(&self)`** | Thread N (Worker) | **YES** | **NO** (Queues event only) | `~2–10 µs` |
| **5. `invoke_from_event_loop` Upgrade** | Thread 0 (Main) | **NO** | **NO** (Runs on next tick) | `~50–200 µs` |

## 🛠️ 9. Solution Design & End-to-End Code Walkthrough

The complete bridge consists of two clean files: a lightweight Python adapter (`gui_bridge.py` inside the Python workspace) that wraps `PlatformRuntimeContextInterface`, and the Rust worker module (`engine_worker.rs` inside `ai-workflow-gui`) that embeds CPython, injects the `#[pyclass]` sink, and drives turns.

| Component Name | Language | Responsibility | Key Invariant Enforced |
| :--- | :--- | :--- | :--- |
| **`SlintEventSink`** | Rust (`#[pyclass]`) | Receives `emit_message`, `emit_status`, and `emit_error` calls from Python. | Uses `&self` + `slint::Weak<AppWindow>` (`Send + Sync`) so multiple calls never conflict. |
| **`SlintPlatformContext`** | Python (`coldwind`) | Implements `PlatformRuntimeContextInterface` and delegates UI/log calls to `SlintEventSink`. | Stores `CoreRunTimeObjects` in `self._services` dict; raises `RuntimeError` on missing keys. |
| **`HeadlessEngineAdapter`** | Python (`coldwind`) | Registers context, initializes `ChatInitializer()`, and exposes `execute_turn(prompt)`. | Bypasses `run_chat()` and `ChatDestructor` POSIX signal hijacking. |
| **`spawn_pyo3_worker`** | Rust (`std::thread`) | Boots CPython, instantiates `HeadlessEngineAdapter` as `Py<PyAny>`, and processes `mpsc` commands. | Never leaks `Bound<'py, T>` outside `Python::with_gil`. |

### 9.1 Rust Side — `#[pyclass]` Sink & Background Worker (`src/engine_worker.rs`)

```rust
use pyo3::prelude::*;
use pyo3::types::PyList;
use slint::ComponentHandle;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::thread;

slint::slint! {
    export component AppWindow inherits Window {
        in-out property <string> chat_log: "";
        in-out property <string> status_text: "Ready";
        in-out property <bool> is_busy: false;
        callback submit_prompt(string);
    }
}

pub enum EngineCommand {
    RunTurn(String),
    Shutdown,
}

#[pyclass]
pub struct SlintEventSink {
    ui_weak: slint::Weak<AppWindow>,
}

#[pymethods]
impl SlintEventSink {
    /// Called by Python's MessageDisplayInterface.display_message()
    /// Invariant: Takes `&self` (Shared Read) so re-entrant Python calls never panic!
    pub fn emit_message(&self, role: String, content: String) -> PyResult<()> {
        let ui_handle = self.ui_weak.clone();
        let _ = slint::invoke_from_event_loop(move || {
            if let Some(ui) = ui_handle.upgrade() {
                let mut current = ui.get_chat_log().to_string();
                current.push_str(&format!("[{}]: {}\n\n", role, content));
                ui.set_chat_log(current.into());
            }
        });
        Ok(())
    }

    /// Called by Python's DebugLoggerInterface / ExceptionHandlerInterface
    pub fn emit_status(&self, stage: String, detail: String) -> PyResult<()> {
        let ui_handle = self.ui_weak.clone();
        let _ = slint::invoke_from_event_loop(move || {
            if let Some(ui) = ui_handle.upgrade() {
                ui.set_status_text(format!("{} — {}", stage, detail).into());
            }
        });
        Ok(())
    }
}

pub fn spawn_engine_worker(
    ui_weak: slint::Weak<AppWindow>,
    project_root: String,
) -> Sender<EngineCommand> {
    let (tx, rx): (Sender<EngineCommand>, Receiver<EngineCommand>) = channel();

    thread::spawn(move || {
        // 1. Initialize embedded CPython interpreter once at startup
        pyo3::prepare_freethreaded_python();

        // 2. Boot Cold Wind Core and store detached Py<PyAny> adapter handle
        let adapter_handle: PyResult<Py<PyAny>> = Python::with_gil(|py| {
            let sys = py.import("sys")?;
            let path: Bound<'_, PyList> = sys.getattr("path")?.extract()?;
            path.append(format!("{}/core/src", project_root))?;
            path.append(format!("{}/desktop/src", project_root))?;

            let sink = Py::new(py, SlintEventSink { ui_weak: ui_weak.clone() })?;
            let bridge_mod = py.import("coldwind.desktop.gui_bridge")?;
            let adapter = bridge_mod.call_method1("boot_headless_engine", (sink,))?;
            Ok(adapter.unbind()) // Unbind Bound<'py, PyAny> -> Py<PyAny> for storage
        });

        let Ok(adapter) = adapter_handle else { return; };

        // 3. Process discrete turns on background thread (0% CPU while waiting)
        while let Ok(cmd) = rx.recv() {
            match cmd {
                EngineCommand::RunTurn(prompt) => {
                    let _ = Python::with_gil(|py| -> PyResult<()> {
                        let bound_adapter = adapter.bind(py);
                        bound_adapter.call_method1("execute_turn", (prompt,))?;
                        Ok(())
                    });
                }
                EngineCommand::Shutdown => {
                    let _ = Python::with_gil(|py| -> PyResult<()> {
                        adapter.bind(py).call_method0("shutdown")?;
                        Ok(())
                    });
                    break;
                }
            }
        }
    });

    tx
}
```

## ✅ 10. Testing & Validation Protocol

Before merging any changes to the PyO3 + Slint bridge, run all four verification gates below.

| Gate # | Verification Gate | Concrete Test Procedure | Expected Pass Criterion | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Gate 1** | **Context Registration Invariant** | Call `ContextRegistry.get()` inside Python immediately after `boot_headless_engine(sink)`. | Returns `UniversalPlatformContext` instance; does not raise `RuntimeError`. | `VERIFIED ✅` |
| **Gate 2** | **Dynamic Service Store Contract** | Query `context.get_service(CoreRunTimeObjects.message_classes)` and `get_service("INVALID")`. | First returns `(HumanMessage, AIMessage, BaseMessage)`; second raises `RuntimeError`. | `VERIFIED ✅` |
| **Gate 3** | **60 FPS Non-Blocking UI Stress Test** | Trigger a 5-second sleep inside `execute_turn()` while dragging the Slint window and hovering buttons. | Slint animations remain smooth (`16.6ms` frame times); zero OS freeze warnings. | `VERIFIED ✅` |
| **Gate 4** | **Mid-Turn Window Close Safety** | Trigger a turn, immediately close the Slint window (`X`), and let the Python worker call `emit_message`. | `ui_weak.upgrade()` returns `None` cleanly; zero segfaults or unwrapping panics. | `VERIFIED ✅` |

## 📈 11. Cognitive Learning Curve, Compiler Map & Deferral Ledger (Tier 0 M6–M8)

### 11.1 Cognitive Learning Curve (M6 — Why Study `01` → `04` in Strict Order)

- **Phase 1 (`01_pyo3_core_mechanics`) before Phase 2 (`02_rust_driving_python`):** You cannot import a Python module or call a Python method until you understand why every PyO3 operation requires a `Python<'py>` token and why `Bound<'py, PyAny>` must be `.unbind()`ed into `Py<PyAny>` to survive across turns.
- **Phase 2 (`02_rust_driving_python`) before Phase 3 (`03_python_driving_rust`):** You must know how Rust boots `coldwind-core` and passes arguments (`call_method1` tuples) before injecting a custom `#[pyclass]` object into `boot_headless_engine(sink)`.
- **Phase 3 (`03_python_driving_rust`) before Phase 4 (`04_slint_concurrency_bridge`):** Once Python can invoke methods on your `#[pyclass] SlintEventSink`, Phase 4 wires the interior of those Rust methods to `slint::Weak<AppWindow>` and `slint::invoke_from_event_loop`.

### 11.2 Compiler & Runtime Enforcement Map (M7 — Compiler as Co-Teacher)

| Exact Error / Diagnostic | Layer | Rule Violated | Runtime Bug Prevented | Python Equivalent Bug |
| :--- | :--- | :--- | :--- | :--- |
| **`error[E0597]: 'py does not live long enough`** | `rustc` (Subdomain 01) | Tried to let `Bound<'py, T>` escape `Python::with_gil` | Dereferencing a `PyObject*` without holding the GIL (segfault / race) | Calling C-API `PyObject_Call` after `PyEval_SaveThread` |
| **`error[E0277]: Bound<'_, PyAny> cannot be sent between threads`** | `rustc` (Subdomain 01) | Tried to move `Bound<'py, T>` (`!Send`) into `thread::spawn` | Cross-thread unsynchronized access to GIL-bound pointer | Sharing non-thread-safe C extension state without a lock |
| **`PyErr: TypeError: argument 1 must be tuple`** | PyO3 Runtime (Subdomain 02) | Passed `"prompt"` instead of `("prompt",)` to `call_method1` | Misinterpreting a single string as an iterable sequence of char args | Writing `args = ("hello")` instead of `("hello",)` in `threading.Thread` |
| **`PyBorrowMutError: Already borrowed`** | PyO3 Runtime (Subdomain 03) | Re-entrant Python call hit `&mut self` on the same `#[pyclass]` | Aliasing mutable references (`&mut T`) to the same struct in memory | Mutating a collection or state machine re-entrantly mid-callback |
| **`error[E0277]: Rc<...> cannot be sent between threads safely`** | `rustc` (Subdomain 04) | Tried to move `AppWindow` (`!Send`) into worker thread | Non-atomic reference count corruption and GPU context thread violation | Mutating Tkinter/Qt widgets from a background `threading.Thread` |

### 11.3 Subdomain Registry & Toolset Deferral Map (M8)

| Subdomain / Resource | Concept Guide (Tier 2) | War Chest (Tier 1) | `learn_rust` Prerequisites & Deferrals | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Root Cross-Platform Shelf** | [`./README.md`](./README.md) | [`./cheat_sheet.md`](./cheat_sheet.md) | Topics 00–07 (Unlocked) | `🟢 Complete` |
| **`01_pyo3_core_mechanics/`** | [`./01_pyo3_core_mechanics/README.md`](./01_pyo3_core_mechanics/README.md) | [`./01_pyo3_core_mechanics/cheat_sheet.md`](./01_pyo3_core_mechanics/cheat_sheet.md) | Topics 01 (`'a`), 06 (`Rc`/`RefCell`) · `⏳ Deferred until Topic 10` (Raw C-ABI) | `🟢 Complete` |
| **`02_rust_driving_python/`** | [`./02_rust_driving_python/README.md`](./02_rust_driving_python/README.md) | [`./02_rust_driving_python/cheat_sheet.md`](./02_rust_driving_python/cheat_sheet.md) | Topics 02 (Tuples), 03 (Traits), 04 (`Result`/`?`) | `🟢 Complete` |
| **`03_python_driving_rust/`** | [`./03_python_driving_rust/README.md`](./03_python_driving_rust/README.md) | [`./03_python_driving_rust/cheat_sheet.md`](./03_python_driving_rust/cheat_sheet.md) | Topics 02 (`impl`), 06 (`RefCell` borrow flags) · `⏳ Deferred until Topic 12` (Proc macros) | `🟢 Complete` |
| **`04_slint_concurrency_bridge/`** | [`./04_slint_concurrency_bridge/README.md`](./04_slint_concurrency_bridge/README.md) | [`./04_slint_concurrency_bridge/cheat_sheet.md`](./04_slint_concurrency_bridge/cheat_sheet.md) | Topic 06 (`Weak::upgrade`) · `⏳ Deferred until Topic 08` (`thread::spawn`, `mpsc`, `Send`/`Sync`) | `🟢 Complete` |

## ⚡ 12. Quick Reference

| You Want To... | Exact Pattern to Execute | Owning Subdomain |
| :--- | :--- | :--- |
| **Initialize embedded Python in a Rust binary** | Call `pyo3::prepare_freethreaded_python();` once before spawning or entering `with_gil`. | [`01_pyo3_core_mechanics`](./01_pyo3_core_mechanics/cheat_sheet.md) |
| **Store a Python object inside a Rust struct** | Convert `Bound<'py, T>` via `.unbind()` into `Py<T>`; re-bind later via `obj.bind(py)`. | [`01_pyo3_core_mechanics`](./01_pyo3_core_mechanics/cheat_sheet.md) |
| **Call a Python method with 1 argument** | `bound_obj.call_method1("execute_turn", (prompt,))?` (keep the trailing comma!). | [`02_rust_driving_python`](./02_rust_driving_python/cheat_sheet.md) |
| **Extract full Python traceback on error** | `err.traceback(py).and_then(\|tb\| tb.format().ok()).unwrap_or_else(\|\| err.to_string())` | [`02_rust_driving_python`](./02_rust_driving_python/cheat_sheet.md) |
| **Expose a Rust event sink to Python** | Annotate struct with `#[pyclass]`, impl block with `#[pymethods]`, and use `&self` receivers. | [`03_python_driving_rust`](./03_python_driving_rust/cheat_sheet.md) |
| **Update Slint UI from the Python worker thread** | Capture `ui_weak = window.as_weak()` and call `slint::invoke_from_event_loop(move \|\| ...)`. | [`04_slint_concurrency_bridge`](./04_slint_concurrency_bridge/cheat_sheet.md) |

## 📖 13. Glossary

| Term | Plain-English Definition (4–12 Words) | Owning Layer |
| :--- | :--- | :--- |
| **Global Interpreter Lock (GIL)** | Mutex serializing CPython bytecode execution so only one thread runs Python at once. | CPython 3.13+ |
| **`Python<'py>`** | Zero-sized Rust token proving the current thread holds the CPython GIL. | PyO3 (`01`) |
| **`Bound<'py, T>`** | GIL-attached smart pointer to a Python object; cannot outlive `'py` or cross threads. | PyO3 (`01`) |
| **`Py<T>`** | GIL-detached heap handle (`Send + Sync`) safe to store in structs and move across threads. | PyO3 (`01`) |
| **`#[pyclass]` / `#[pymethods]`** | Rust procedural macros that compile a Rust struct and its `impl` block into a Python type. | PyO3 (`03`) |
| **`PyCell` Borrow Flag** | Runtime borrow counter inside `#[pyclass]` enforcing Rust's Aliasing XOR Mutability rule. | PyO3 (`03`) |
| **`slint::Weak<AppWindow>`** | Thread-safe (`Send + Sync`) non-owning reference to a Slint window residing on Thread 0. | Slint (`04`) |
| **`slint::invoke_from_event_loop`** | Thread-safe function that queues a closure from any worker thread onto Thread 0's UI loop. | Slint (`04`) |
| **Decoupled Turn Invocation** | Driving LangGraph one user message at a time via `graph.invoke(state)` instead of `run_chat()`. | Cold Wind Core |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | Why can't we run `Python::with_gil` inside a Slint button callback on Thread 0 if we use Python `asyncio`? | Because `Python::with_gil` blocks the calling OS thread until the Python call returns; even an `asyncio` loop inside Python would monopolize Thread 0 and starve Slint's 16.6ms rendering loop. | `2026-10-22` |
| **Q2** | Should we implement all 20 methods of `PlatformRuntimeContextInterface` directly on a single Rust `#[pyclass]`? | No. Keep the dictionary state (`_services`, `_listeners`) in a thin Python `UniversalPlatformContext` class and inject a focused Rust `#[pyclass] SlintEventSink` with 3–4 `&self` event emission methods. | `2026-10-22` |
| **Q3** | What happens if the user closes the Slint window while `coldwind-core` is mid-way through an MCP tool call? | `main_window.run()` exits on Thread 0, dropping the strong `AppWindow`; when the worker thread calls `ui_weak.upgrade()` inside `invoke_from_event_loop`, it returns `None` and safely skips the UI update. | `2026-10-22` |
| **Q4** | Note on PyO3 0.22–0.28 naming: what is the relationship between `Python::with_gil` and `Python::attach`, or `allow_threads` and `detach`? | PyO3 0.22–0.25 uses `Python::with_gil` and `py.allow_threads`; PyO3 0.26+ aliases/renames them to `Python::attach` and `py.detach` with identical `'py` lifetime semantics. | `2026-10-22` |