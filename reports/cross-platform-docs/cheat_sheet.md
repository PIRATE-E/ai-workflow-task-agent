# 🧩 PyO3 + Slint Cross-Platform Integration Cheat Sheet & 30-Second Invariants

| Field | Value |
| :--- | :--- |
| **Tier** | `1 — Master War Chest (Cross-Cutting C1–C12)` · per `cheatsheet_for_cheatsheet.md` |
| **Domain** | `shared` / `core` / `desktop` (`cross-platform-docs`) |
| **Verified** | `2026-10-22` — verified against PyO3 0.22+ `Bound<'py, T>` API, Slint 1.8+, and `coldwind-core` contracts |
| **Confidence** | `VERIFIED ✅` |

> **TL;DR:** Never acquire the Python GIL on Slint's Thread 0, never move a strong `AppWindow` (`!Send`) to the Python worker thread, never let `Bound<'py, T>` escape `Python::with_gil` without `.unbind()`, and always use `&self` receivers on `#[pyclass]` UI sinks.
> **Primary Objective:** Within 30 seconds, select the exact cross-boundary syntax (Rust-to-Python call, Python-to-Rust `#[pyclass]` callback, or Worker-to-Slint `invoke_from_event_loop` dispatch) and verify its borrow/thread invariant without compiler errors.
> **Master Guide:** [`./00_pyo3_slint_architecture_report.md`](./00_pyo3_slint_architecture_report.md) · **Shelf Index:** [`./README.md`](./README.md) · **Subdomain War Chests:** [`01`](./01_pyo3_core_mechanics/cheat_sheet.md) · [`02`](./02_rust_driving_python/cheat_sheet.md) · [`03`](./03_python_driving_rust/cheat_sheet.md) · [`04`](./04_slint_concurrency_bridge/cheat_sheet.md)

## 📺 1. Curated Learning Sources

Every pattern in this war chest is backed by official upstream guides and verified Cold Wind specifications.

| Source | Why This Source | Verification |
| :--- | :--- | :--- |
| [PyO3 Guide — GIL, Lifetimes & `Bound<'py, T>`](https://pyo3.rs/main/memory.html) | Explains the exact memory layout of `Bound<'py, T>` vs `Py<T>` and reference count rules. | `VERIFIED ✅` |
| [PyO3 Guide — Python Classes in Rust (`#[pyclass]`)](https://pyo3.rs/main/class.html) | Covers `PyCell` interior mutability, `&self` vs `&mut self` borrows, and `Send + Sync` bounds. | `VERIFIED ✅` |
| [Slint Rust Docs — `invoke_from_event_loop` & `Weak`](https://releases.slint.dev/1.8.0/docs/rust/slint/fn.invoke_from_event_loop.html) | Thread-safety rules for dispatching UI updates from background worker threads. | `VERIFIED ✅` |
| [`../urgent_development/platform-integration-spec.md`](../urgent_development/platform-integration-spec.md) | Cold Wind AI contract for `PlatformRuntimeContextInterface` and `HeadlessEngineAdapter`. | `VERIFIED ✅` |

## 🧭 2. 30-Second Decision Tree

Choose the exact FFI or concurrency primitive by identifying where execution starts and where data must land.

```text
Title: Cross-Platform Action Router -> Exact PyO3 / Slint Pattern

What cross-boundary operation are you writing right now?
├─ 1. Managing Python objects in Rust memory:
│  ├─ Active inside Python::with_gil(|py| ...)? ──► Bound<'py, T> (zero-cost GIL-tied borrow)
│  ├─ Storing in a Rust struct or sending across threads? ──► obj.unbind() -> Py<T> (Send + Sync)
│  └─ Reactivating stored Py<T> inside with_gil? ──► stored_py.bind(py) -> &Bound<'py, T>
│
├─ 2. Calling Python (coldwind-core) from Rust worker thread:
│  ├─ 0 arguments: obj.method()? ──► bound_obj.call_method0("method")?
│  ├─ Positional args: obj.step(a, b)? ──► bound_obj.call_method1("step", (a, b))? (1-arg needs `(a,)`)
│  └─ Extracting return value to Rust type? ──► py_any.extract::<RustType>()?
│
├─ 3. Exposing Rust sink to Python (ContextRegistry callbacks):
│  ├─ Struct declaration ──► #[pyclass] pub struct SlintEventSink { ui_weak: Weak<AppWindow> }
│  └─ Method receiver ──► #[pymethods] fn emit(&self, msg: String) (ALWAYS `&self`, NEVER `&mut self`)
│
└─ 4. Crossing between Slint Thread 0 and PyO3 Worker Thread N:
   ├─ UI Button -> Worker Thread ──► prompt_tx.send(EngineCommand::RunTurn(text))
   └─ Worker Thread -> Slint UI ──► slint::invoke_from_event_loop(move || { ui_weak.upgrade()... })
```

| Direction | Origin Thread | Target Thread | Required Handle Type | Forbidden Type (`rustc` Error) |
| :--- | :--- | :--- | :--- | :--- |
| **UI → Worker** | Thread 0 (Slint) | Thread N (PyO3) | `mpsc::Sender<EngineCommand>` | `Python::with_gil` on Thread 0 (Freezes UI) |
| **Worker → Python** | Thread N (PyO3) | Thread N (CPython) | `Bound<'py, PyAny>` (via `.bind(py)`) | Unbound `Py<T>` without `.bind(py)` (`E0599`) |
| **Python → Rust** | Thread N (CPython) | Thread N (Rust) | `#[pyclass]` with `&self` receiver | `&mut self` on re-entrant callback (`PyBorrowMutError`) |
| **Worker → UI** | Thread N (PyO3) | Thread 0 (Slint) | `slint::Weak<AppWindow>` (`Send`) | `AppWindow` (`error[E0277]: !Send`) |

## ⚖️ 3. Invariant & Operations Matrix

Every operation across PyO3 and Slint obeys a strict compile-time or runtime access law based on whether the operation reads/dispatches through a shared channel or mutates thread-local state:

$$\text{Operation} = \text{Cross-Boundary Callback} \implies \text{Shared Borrow (\texttt{\&self}) + Channel} \quad \big| \quad \text{Operation} = \text{UI Property Write} \implies \text{Thread 0 Exclusive (\texttt{invoke\_from\_event\_loop})}$$

| Primitive / API | Holds GIL? | `Send` Across Threads? | Aliasing Allowed? | Mutation Model | Complexity & Memory Overhead |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`Python<'py>`** | **YES** | ❌ **NO** (`!Send + !Sync`) | Shared copy (`Copy`) | Grants access to CPython API | `0 bytes` (ZST compile-time proof token) |
| **`Bound<'py, T>`** | **YES** | ❌ **NO** (`!Send`) | Shared (`Clone` = `Py_INCREF`) | Mutates Python heap via GIL | `8 bytes` (thin pointer to `PyObject`) |
| **`Py<T>`** | **NO** | ✅ **YES** (`Send + Sync`) | Shared (`Clone` with GIL) | Must `.bind(py)` first | `8 bytes` (detached `PyObject*` handle) |
| **`#[pyclass]` (`&self`)** | Caller holds | ✅ **YES** (requires `Send`) | Multiple readers allowed | Interior via `mpsc` / `Mutex` | Wrapped in `PyCell` (runtime borrow counter) |
| **`AppWindow`** | **NO** | ❌ **NO** (`!Send`, `Rc`-backed) | Thread 0 `Clone` only | Direct `.set_prop()` on Thread 0 | Strong `Rc` reference to Slint component tree |
| **`Weak<AppWindow>`** | **NO** | ✅ **YES** (`Send + Sync`) | Unlimited across threads | Must `.upgrade()` on Thread 0 | Atomic weak count; returns `Option<AppWindow>` |

## 🐍 4. Python & `learn_rust` Bridge Delta

This table links each cross-platform mechanism to both what CPython does under the hood and the exact `learn_rust` topic that owns the Rust mental model.

| Mechanism | CPython 3.13+ Runtime Reality | Rust + PyO3 + Slint Reality | Owning `learn_rust` Topic |
| :--- | :--- | :--- | :--- |
| **GIL Lifetime (`Python<'py>`)** | Thread state (`PyThreadState*`) checked dynamically in C; segfaults if C-API is called without GIL. | Lifetime `'py` binds every `Bound<'py, T>` to the lexical scope of `Python::with_gil`. | **Topic 01:** Lifetimes (`'a`) & Borrow Checker |
| **Bound vs Unbound (`Bound` / `Py`)** | Every variable is a raw `PyObject*` whose `ob_refcnt` must be manually incremented/decremented in C. | `Bound<'py, T>` is a lifetimed handle; `.unbind()` converts it to `Py<T>` so structs stay `'static`. | **Topic 06:** Smart Pointers (`Rc<T>` & `Drop`) |
| **`#[pyclass]` Borrow Guard** | Any Python reference can mutate `obj.attr` at any time while holding the GIL. | `#[pyclass]` wraps the Rust struct in a `RefCell`-like `PyCell` that tracks shared vs exclusive borrows. | **Topic 06:** Interior Mutability (`RefCell<T>`) |
| **`Weak<AppWindow>` Upgrade** | `weakref.ref(obj)()` returns `obj` or `None`, usable on any thread (causing GUI race bugs in Tkinter/Qt). | `Weak<AppWindow>` is `Send`, but `.upgrade()` only returns `Some(ui)` when executed on Thread 0! | **Topic 06:** `Weak<T>` Cycle Breaking & `upgrade()` |
| **Worker Channel (`mpsc`)** | `queue.Queue()` locks a Python mutex and pickles/boxes objects on the heap. | `std::sync::mpsc::channel<EngineCommand>()` moves unboxed Rust enums across threads in `<1µs`. | **Topic 02/08:** Algebraic `enum` + `⏳ Topic 08` `mpsc` |

## 🧠 5. Physical Metaphor Register

Memorize these four 1:1 physical metaphors to recall the exact invariants under interview or debugging pressure.

| Mechanism | Physical Metaphor | 1:1 Mapping to Runtime Behavior |
| :--- | :--- | :--- |
| **`Python<'py>` & `Bound<'py, T>`** | **The High-Voltage Keycard & Corded Power Tool** | `Python::with_gil` inserts the keycard into the wall socket (`'py`). `Bound<'py, T>` is a corded drill plugged into that socket—you cannot carry the plugged-in drill out of the room. |
| **`.unbind()` → `Py<T>`** | **Unplugging the Drill & Locking It in a Briefcase** | Calling `.unbind()` unplugs the cord from `'py` and puts the tool in a portable case (`Py<T>`). You can carry it across rooms (threads), but must plug it back in (`.bind(py)`) to pull the trigger. |
| **`#[pyclass]` `PyCell` Borrow** | **The Single-Key Restroom Lock (`&mut self`) vs Open Hallway (`&self`)** | If a method takes `&mut self`, Python locks the restroom door; if a nested callback tries to enter the same struct before the first call exits, it crashes into the locked door (`PyBorrowMutError`). |
| **`Weak<AppWindow>` + `invoke_from_event_loop`** | **Mailing a Postcard to a House That Might Be Demolished** | The worker thread cannot teleport into the house (`AppWindow` is `!Send`). It mails a postcard (`invoke_from_event_loop`) addressed to `Weak<AppWindow>`. If the user closed the window, the postman sees an empty lot (`upgrade() == None`) and drops the card safely. |

## 🛠️ 6. Syntax Bank

| Recipe # | Pattern Name | When to Copy-Paste | Subdomain Owner |
| :--- | :--- | :--- | :--- |
| **Recipe 1** | **GIL Acquisition & Detached Struct Storage** | Booting Python once and keeping the engine adapter alive across turns. | [`01_pyo3_core_mechanics`](./01_pyo3_core_mechanics/cheat_sheet.md) |
| **Recipe 2** | **Tuple Argument Call & Full Traceback Extraction** | Calling `execute_turn(prompt)` and capturing multi-line Python stack traces. | [`02_rust_driving_python`](./02_rust_driving_python/cheat_sheet.md) |
| **Recipe 3** | **Re-Entrancy-Safe `#[pyclass]` Event Sink** | Exposing a Rust callback receiver to `coldwind-core` `ContextRegistry`. | [`03_python_driving_rust`](./03_python_driving_rust/cheat_sheet.md) |
| **Recipe 4** | **Thread-Safe Slint UI Property Update** | Streaming tokens or status updates from Thread N onto Thread 0. | [`04_slint_concurrency_bridge`](./04_slint_concurrency_bridge/cheat_sheet.md) |

### Recipe 1: GIL Acquisition & Detached `Py<PyAny>` Storage
```rust
use pyo3::prelude::*;

pub struct PersistentPythonEngine {
    // Invariant: Store detached Py<PyAny> (no 'py lifetime, implements Send + Sync)
    adapter: Py<PyAny>,
}

impl PersistentPythonEngine {
    pub fn boot() -> PyResult<Self> {
        pyo3::prepare_freethreaded_python();
        let adapter = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            let module = py.import("coldwind.desktop.gui_bridge")?;
            let bound_adapter: Bound<'_, PyAny> = module.call_method0("create_adapter")?;
            Ok(bound_adapter.unbind()) // Detach from 'py before leaving closure!
        })?;
        Ok(Self { adapter })
    }
}
```

### Recipe 2: Calling Python with 1-Tuple Args & Formatting `PyErr`
```rust
use pyo3::prelude::*;

pub fn run_agent_turn(engine: &Py<PyAny>, prompt: &str) -> Result<String, String> {
    Python::with_gil(|py| {
        // Re-bind Py<PyAny> -> &Bound<'py, PyAny> and pass 1-tuple `(prompt,)`
        engine
            .bind(py)
            .call_method1("execute_turn", (prompt,))
            .and_then(|res| res.extract::<String>())
            .map_err(|err: PyErr| {
                // Extract full Python stack trace instead of bare exception name
                err.traceback(py)
                    .and_then(|tb| tb.format().ok())
                    .unwrap_or_else(|| err.to_string())
            })
    })
}
```

### Recipe 3: Re-Entrancy-Safe `#[pyclass]` Sink (`&self` + Channel)
```rust
use pyo3::prelude::*;
use std::sync::mpsc::Sender; // ⏳ Topic 08 boundary preview

#[pyclass]
pub struct RustTelemetrySink {
    tx: Sender<String>,
}

#[pymethods]
impl RustTelemetrySink {
    #[new]
    pub fn new(tx: Sender<String>) -> Self {
        Self { tx }
    }

    // Invariant: Shared `&self` allows concurrent/re-entrant Python logging calls!
    pub fn display_message(&self, role: &str, content: &str) -> PyResult<()> {
        let _ = self.tx.send(format!("[{}] {}", role, content));
        Ok(())
    }
}
```

### Recipe 4: Non-Blocking Slint UI Update via `Weak<AppWindow>`
```rust
use slint::ComponentHandle;

// Executed from inside the background PyO3 worker thread (Thread N):
pub fn push_token_to_slint(ui_weak: slint::Weak<crate::AppWindow>, token: String) {
    let _ = slint::invoke_from_event_loop(move || {
        // Runs on Thread 0! Safe to upgrade Weak<AppWindow> -> Option<AppWindow>
        if let Some(ui) = ui_weak.upgrade() {
            let mut text = ui.get_chat_log().to_string();
            text.push_str(&token);
            ui.set_chat_log(text.into());
        }
    });
}
```

## 🔬 7. Visual Memory Model

*How to read this:* Compare the three memory zones side by side—Thread 0's stack/heap (`!Send` UI objects), Thread N's stack (scoped `'py` GIL tokens), and the CPython Heap (`PyObject` headers managed by reference counts).

```text
Title: Cross-Runtime Memory Layout (Thread 0 Slint vs Thread N PyO3 vs CPython Heap)

THREAD 0 (Slint UI — !Send)          THREAD N (Rust Worker)            CPYTHON 3.13+ HEAP (GIL-Guarded)
┌──────────────────────────┐        ┌──────────────────────────┐      ┌──────────────────────────────┐
│ AppWindow (Strong Handle)│        │ ui_weak: Weak<AppWindow> │      │ PyObject (Adapter Instance)  │
│  • Rc<ComponentBox>      │◄ ─ ─ ─ │  • AtomicWeakRef (Send)  │      │  • ob_refcnt: usize (2)      │
│  • Wayland/GPU Surface   │upgrade │                          │      │  • ob_type: *mut PyTypeObject│
│  • CANNOT leave Thread 0 │on T0   │ adapter: Py<PyAny> ──────┼─────►│  • __dict__: {graph, state}  │
└──────────────────────────┘        ├──────────────────────────┤      └──────────────▲───────────────┘
                                    │ Inside Python::with_gil: │                     │
                                    │  • py: Python<'py> (0B)  │                     │
                                    │  • Bound<'py, PyAny> ────┼─────────────────────┘
                                    │    (8B ptr + 'py borrow) │      ┌──────────────────────────────┐
                                    └──────────────────────────┘      │ PyCell<SlintEventSink>       │
                                                 ▲                    │  • ob_refcnt: usize (1)      │
                                                 └────────────────────┤  • borrow_flag: isize (0)    │
                                                  Calls &self method  │  • payload: SlintEventSink   │
                                                                      └──────────────────────────────┘
```

| Memory Wrapper | Stack Size | Heap Allocation | Reference Count Mechanism | Thread Mobility |
| :--- | :--- | :--- | :--- | :--- |
| **`Python<'py>`** | `0 bytes` (ZST) | None | None (Lexical scope proof) | Locked to calling thread (`!Send`) |
| **`Bound<'py, T>`** | `8 bytes` (`NonNull`) | Points to `PyObject` | `Py_INCREF` / `Py_DECREF` under GIL | Locked to calling thread (`!Send`) |
| **`Py<T>`** | `8 bytes` (`NonNull`) | Points to `PyObject` | Drops safely by acquiring GIL if needed | Thread-safe (`Send + Sync`) |
| **`slint::Weak<T>`** | `8 bytes` (`Pin<Rc>`) | Control block on heap | Atomic weak counter | Thread-safe (`Send + Sync`) |

## 🛡️ 8. Compiler Diagnostics Table

When `rustc` or PyO3 halts your build or raises a runtime error, use this table to decode the exact invariant being protected.

| Exact Diagnostic / Error | Rule Violated | Runtime Bug Prevented | Python Equivalent of the Bug |
| :--- | :--- | :--- | :--- |
| **`error[E0597]: `py` does not live long enough`** | Returned or stored `Bound<'py, T>` outside `Python::with_gil` | Dangling pointer / calling CPython API without holding the GIL | Accessing freed C-extension memory (`Segmentation fault`) |
| **`error[E0277]: `Rc<...>` cannot be sent between threads safely`** | Captured strong `AppWindow` inside `std::thread::spawn` | Data race on non-atomic UI reference count and GPU surface | Mutating Tkinter/PyQt widgets from a background thread (random crash) |
| **`error[E0277]: `*mut PyObject` cannot be shared between threads`** | Placed a `!Send` field inside a `#[pyclass]` struct without `unsendable` | Cross-thread garbage collection freeing a thread-affine resource | Sharing a thread-local SQLite connection across threads |
| **`PyBorrowMutError: Already borrowed`** | Python re-entered a `#[pyclass]` method declared with `&mut self` | Simultaneous mutable aliasing (`&mut T` + `&mut T`) corrupting memory | Re-entrant callback mutating a list while iterating over it |
| **`PyErr { type: <class 'ModuleNotFoundError'> }`** | Embedded Python `sys.path` lacks workspace `core/src` directory | Unresolved module lookup in embedded interpreter | Running `python` outside `uv run` without `.pth` paths loaded |

## ⚠️ 9. Trap Archive (3-part form)

| # | Trap Name | Assumed | Reality | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **The Thread 0 GIL Freeze** | Calling a "fast" `Python::with_gil` inside a Slint button callback is harmless. | If the background worker holds the GIL during a 10s LLM call, Thread 0 blocks waiting for the GIL and freezes the UI. | **Zero GIL on Thread 0:** UI callbacks only call `prompt_tx.send(cmd)`. |
| **2** | **The 1-Tuple String Explosion** | `obj.call_method1("run", ("hello"))` passes `"hello"` as 1 argument. | In Rust (and Python), `("hello")` without a comma is a string, not a tuple; PyO3 unpacks it as 5 separate char arguments! | **Always add the trailing comma:** Write `("hello",)` for single-argument calls. |
| **3** | **The `&mut self` Callback Trap** | `#[pymethods]` sinks need `&mut self` to emit events or push logs. | If Python logs a debug message while inside another callback on the same `#[pyclass]`, `&mut self` panics with `Already borrowed`. | **Use `&self` + Channel:** `mpsc::Sender::send(&self)` and `Weak::clone(&self)` only need `&self`. |
| **4** | **The Unguarded `Weak::upgrade().unwrap()`** | `ui_weak.upgrade().unwrap()` is safe inside `invoke_from_event_loop`. | If the user closes the window while an agent turn is in flight, `upgrade()` returns `None` and `.unwrap()` panics on shutdown. | **Always guard with `if let Some(ui) = ui_weak.upgrade()`**. |

### Trap 1: The Thread 0 GIL Freeze
- **Assumed:** Calling `Python::with_gil` inside a Slint button callback for a quick status check won't hurt framerate.
- **Reality:** The GIL is a single global mutex. If the background worker thread is mid-turn holding the GIL, Thread 0 stalls at `Python::with_gil` until the turn finishes, freezing the entire window.
- **10-Second Recall Fix:** Never utter `Python::with_gil` on Thread 0; push a command over `mpsc::Sender` and let the worker reply via `invoke_from_event_loop`.

### Trap 2: The 1-Tuple String Explosion
- **Assumed:** Writing `adapter.call_method1("execute_turn", (prompt))` passes `prompt` as a 1-element tuple.
- **Reality:** Parentheses without a trailing comma `(prompt)` group the expression without creating a tuple. If a sequence is passed, Python unpacks its elements as multiple positional arguments (`TypeError: takes 2 positional arguments but N were given`).
- **10-Second Recall Fix:** Always write a trailing comma `(prompt,)` for single-argument `call1` and `call_method1` calls.

### Trap 3: The `&mut self` Re-Entrancy Panic
- **Assumed:** A `#[pyclass]` platform context should store logs in a `Vec<String>` mutated via `&mut self`.
- **Reality:** PyO3 wraps `#[pyclass]` structs in a runtime borrow checker (`PyCell`). If Python enters a `&mut self` method and triggers a nested log/error hook on the same context, PyO3 raises `RuntimeError: Already borrowed`.
- **10-Second Recall Fix:** Declare all `#[pymethods]` callback sinks with shared **`&self`** and forward data over an `mpsc::Sender` or `invoke_from_event_loop`.

### Trap 4: The Unguarded `Weak::upgrade().unwrap()` Crash
- **Assumed:** Inside `slint::invoke_from_event_loop`, the window always exists so `ui_weak.upgrade().unwrap()` is safe.
- **Reality:** Events queued just milliseconds before the user clicks the OS close button (`X`) still run during loop teardown when `AppWindow` has already dropped, causing `.unwrap()` to panic.
- **10-Second Recall Fix:** Always unwrap weakly via `if let Some(ui) = ui_weak.upgrade() { ... }`.

## ⏳ 10. Deferred Concepts (Manifest Boundary)

Per `learn_rust` `CONCEPT_MANIFEST.md` (Topics 00–06 completed, Topic 07 active), the following Rust concurrency and FFI internals are used here strictly as architectural boundary recipes and will be derived from scratch in their owning topics:

| Concept / Syntax | Manifest Status & Marker | What It Unlocks When Covered |
| :--- | :--- | :--- |
| **`std::thread::spawn` & `std::sync::mpsc`** | `⏳ Deferred until Topic 08 (Concurrency)` | OS thread spawning, `Send`/`Sync` auto-trait proofs, `Arc<Mutex<T>>`, and lock-free channels. |
| **`#[pyclass]` & `#[pymethods]` Proc Macros** | `⏳ Deferred until Topic 10 (FFI & PyO3) & Topic 12` | Procedural macro AST expansion, `extern "C"` ABI calling conventions, and `PyTypeObject` vtables. |
| **`pyo3-asyncio` / Tokio Event Loop Bridge** | `⏳ Deferred until Topic 11 (Networking & Async)` | Bridging Rust `Future` state machines (`tokio`) directly with Python `asyncio` coroutines. |
| **Raw Pointer C-API (`pyo3::ffi::*`, `unsafe`)** | `⏳ Deferred until Topic 12 (Advanced & Unsafe)` | Zero-copy NumPy/Arrow buffer protocol (`Py_buffer`) and manual `unsafe` pointer arithmetic. |

## 📈 11. Family Learning Progression

Master the four subdomains in this strict bottom-up sequence so no file uses an unexplained pointer or concurrency primitive.

```text
Title: 4-Stage Mastery Sequence for PyO3 + Slint Integration

[1. Subdomain 01: Bound<'py, T> vs Py<T>] ──► [2. Subdomain 02: call_method1 & PyErr]
                                                        │
[4. Subdomain 04: Weak<UI> & Event Loop]  ◄── [3. Subdomain 03: #[pyclass] &self Sinks]
```

| Order | Subdomain Milestone | Why You Must Learn It in This Position |
| :--- | :--- | :--- |
| **Step 1** | [`01_pyo3_core_mechanics`](./01_pyo3_core_mechanics/README.md) | Establishes the GIL token (`Python<'py>`) and `Bound<'py, T>` vs `Py<T>` lifetime rules used in every snippet. |
| **Step 2** | [`02_rust_driving_python`](./02_rust_driving_python/README.md) | Teaches how Rust imports `coldwind-core`, invokes `execute_turn`, and catches `PyErr` tracebacks. |
| **Step 3** | [`03_python_driving_rust`](./03_python_driving_rust/README.md) | Inverts control so Python's `ContextRegistry.get()` can call back into a Rust `#[pyclass]` struct safely. |
| **Step 4** | [`04_slint_concurrency_bridge`](./04_slint_concurrency_bridge/README.md) | Connects the Rust `#[pyclass]` sink to Thread 0's `AppWindow` using `Weak` handles and `invoke_from_event_loop`. |

## 📎 12. Concept Notes & Study Reports Directory

| Document | Relative Path | Scope & Invariants Covered | Status |
| :--- | :--- | :--- | :--- |
| **Architecture Report & Master Guide** | [`./00_pyo3_slint_architecture_report.md`](./00_pyo3_slint_architecture_report.md) | Full 4-hazard analysis, sequence traces, decoupled adapter blueprint, testing gates, and Q&A log. | `🟢 Complete` |
| **Subdomain 01 Concept Guide** | [`./01_pyo3_core_mechanics/README.md`](./01_pyo3_core_mechanics/README.md) | CPython embedding, `Python<'py>`, `Bound<'py, T>` vs `Py<T>`, `.bind()`/`.unbind()`, type extraction. | `🟢 Complete` |
| **Subdomain 01 War Chest** | [`./01_pyo3_core_mechanics/cheat_sheet.md`](./01_pyo3_core_mechanics/cheat_sheet.md) | 30s pointer router, GIL lifetime diagrams, `IntoPyObject`/`FromPyObject` matrix, E0597/E0277 fixes. | `🟢 Complete` |
| **Subdomain 02 Concept Guide** | [`./02_rust_driving_python/README.md`](./02_rust_driving_python/README.md) | `sys.path` workspace setup, `py.import`, `call_method1`, `PyDict` state, and `PyErr` traceback formatting. | `🟢 Complete` |
| **Subdomain 02 War Chest** | [`./02_rust_driving_python/cheat_sheet.md`](./02_rust_driving_python/cheat_sheet.md) | Call syntax matrix (`call0`/`call1`/`call_method1`), 1-tuple trap, kwargs, and exception translation. | `🟢 Complete` |
| **Subdomain 03 Concept Guide** | [`./03_python_driving_rust/README.md`](./03_python_driving_rust/README.md) | `#[pyclass]`, `#[pymethods]`, `PyCell` borrow flags, satisfying `PlatformRuntimeContextInterface`. | `🟢 Complete` |
| **Subdomain 03 War Chest** | [`./03_python_driving_rust/cheat_sheet.md`](./03_python_driving_rust/cheat_sheet.md) | Macro attribute matrix (`#[new]`, `#[pyo3(get)]`), `&self` vs `&mut self` rules, channel event sinks. | `🟢 Complete` |
| **Subdomain 04 Concept Guide** | [`./04_slint_concurrency_bridge/README.md`](./04_slint_concurrency_bridge/README.md) | Thread 0 `!Send` window loop, `Weak<AppWindow>`, `invoke_from_event_loop`, `allow_threads`, shutdown. | `🟢 Complete` |
| **Subdomain 04 War Chest** | [`./04_slint_concurrency_bridge/cheat_sheet.md`](./04_slint_concurrency_bridge/cheat_sheet.md) | Concurrency dispatch tree, `mpsc` + `invoke_from_event_loop` skeleton, token batching, teardown traps. | `🟢 Complete` |