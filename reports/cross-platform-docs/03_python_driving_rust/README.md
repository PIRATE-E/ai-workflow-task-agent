# ⚡ Subdomain 03: Python Driving Rust (Platform Context & Event Sinks)

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `desktop` (`cross-platform-docs`) |
| **Subdomain** | `03_python_driving_rust` |
| **Type** | Subdomain README + Tier 2 Concept Note Deep-Dive |
| **Prerequisites** | [`../01_pyo3_core_mechanics/README.md`](../01_pyo3_core_mechanics/README.md), [`../02_rust_driving_python/README.md`](../02_rust_driving_python/README.md), `learn_rust` Topics 02, 06 (`RefCell`) |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ `#[pyclass]`, `PyCell` borrow rules, `PlatformRuntimeContextInterface`) |
| **Confidence** | `VERIFIED ✅` |
| **Updated** | `2026-10-22` |

> **TL;DR:** To let `coldwind-core` stream tokens, status updates, and errors into a native Rust GUI without violating the core layering invariant, annotate a Rust struct with `#[pyclass]` and its methods with `#[pymethods]`, allocate it on the CPython heap via `Py::new(py, sink)?`, and always use shared `&self` receivers backed by an `mpsc::Sender` or `Weak<AppWindow>` so re-entrant Python callbacks never trigger `PyBorrowMutError`.
> **Scope:** Exposing Rust structs to Python via `#[pyclass]` and `#[pymethods]`, `Py::new(py, val)` heap construction, `PyCell` interior mutability borrow flags (`&self` vs `&mut self`), and satisfying Cold Wind's `PlatformRuntimeContextInterface`.
> **Python Bridge:** In Python, any class can implement `MessageDisplayInterface` by defining `def display_message(self, role, content):`—and Python allows arbitrary re-entrant calls to `self` without checking if another stack frame is already mutating `self`. When a Rust struct is wrapped in `#[pyclass]`, PyO3 embeds it inside a `PyCell` (the FFI equivalent of `RefCell<T>` from `learn_rust` Topic 06) that tracks shared (`&self`) vs exclusive (`&mut self`) borrows at runtime.

## 📺 Recommended Learning & Reference Sources

| # | Source & Link | Architectural Focus | Verification |
| :--- | :--- | :--- | :--- |
| **1** | [PyO3 Guide — Python Classes defined in Rust (`#[pyclass]`)](https://pyo3.rs/main/class.html) | Complete reference for `#[pyclass]`, `#[pymethods]`, `#[new]`, `#[pyo3(get, set)]`, and `Py::new`. | `VERIFIED ✅` |
| **2** | [PyO3 Guide — Interior Mutability & `PyClass` Borrows](https://pyo3.rs/main/class.html#bound-and-interior-mutability) | Explains how PyO3 enforces Rust's Aliasing XOR Mutability rule at runtime via borrow flags. | `VERIFIED ✅` |
| **3** | [`../../core/src/coldwind/core/interfaces/runtime_interface.py`](../../core/src/coldwind/core/interfaces/runtime_interface.py) | Defines `PlatformRuntimeContextInterface` (`get_message_display`, `get_logger`, `get_error_handler`). | `VERIFIED ✅` |
| **4** | [`../../urgent_development/platform-integration-spec.md`](../../urgent_development/platform-integration-spec.md) | Defines `UniversalPlatformContext` and why dynamic services (`_services`) live in a thin Python wrapper. | `VERIFIED ✅` |

## At a Glance & Subdomain Navigation

| Artifact | Relative Path | Type | What It Answers | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Subdomain Concept Guide (This File)** | [`./README.md`](./README.md) | Concept Note + Subdomain Index | How does `#[pyclass]` work in memory, why does `&mut self` panic on re-entrant callbacks, and how do we wire `ContextRegistry`? | `🟢 Complete` |
| **Subdomain 03 War Chest** | [`./cheat_sheet.md`](./cheat_sheet.md) | Tier 1 Cheat Sheet (C1–C12) | 30-second macro router (`#[pyclass]`, `#[pymethods]`, `#[pyfunction]`), borrow matrix, and `PyBorrowMutError` fixes. | `🟢 Complete` |
| **Previous Subdomain (`02`)** | [`../02_rust_driving_python/README.md`](../02_rust_driving_python/README.md) | Subdomain 02 Concept Guide | Importing `coldwind-core`, `call_method1`, and formatting `PyErr` tracebacks. | `🟢 Complete` |
| **Next Subdomain (`04`)** | [`../04_slint_concurrency_bridge/README.md`](../04_slint_concurrency_bridge/README.md) | Subdomain 04 Concept Guide | Connecting the Rust `#[pyclass]` sink to Slint's Thread 0 event loop via `Weak<AppWindow>`. | `🟢 Complete` |

## 🐍 1. The Python vs Rust Architecture Comparison

In `coldwind-desktop`, the terminal UI implements `MessageDisplayInterface` in Python (`DesktopMessageDisplay`) and prints directly to a Rich `Console`. When moving to a native Rust GUI, we use the **Hybrid Thin-Wrapper + Rust Sink Pattern**:
1. A tiny Python class (`UniversalPlatformContext`) holds the dynamic Python dictionaries (`self._services`, `self._listeners`) that Core mutates during `ChatInitializer.__init__()`.
2. A compiled Rust `#[pyclass]` struct (`SlintEventSink`) is injected into `UniversalPlatformContext` to receive every user message, banner, log entry, and exception at native C speed.

```python
# Python Side (coldwind/desktop/gui_bridge.py):
# Thin wrapper satisfies Core's dictionary storage while delegating I/O to Rust's #[pyclass] sink!
class GuiMessageDisplay(MessageDisplayInterface):
    def __init__(self, rust_sink) -> None:
        self._rust_sink = rust_sink  # Instance of Rust #[pyclass] SlintEventSink

    def display_message(self, role: str, content: str, metadata: dict | None = None) -> None:
        # Calls compiled Rust #[pymethods] function directly across FFI!
        self._rust_sink.emit_message(role, content)
```

```rust
// Rust Side (ai-workflow-gui):
use pyo3::prelude::*;
use std::sync::mpsc::Sender;

pub enum UiEvent {
    ChatMessage { role: String, content: String },
    StatusUpdate { stage: String, detail: String },
}

#[pyclass]
pub struct SlintEventSink {
    // Channel sender is Send + Clone and only requires `&self` to send!
    event_tx: Sender<UiEvent>,
}

#[pymethods]
impl SlintEventSink {
    /// Called by Python's GuiMessageDisplay.display_message()
    /// Invariant: Shared `&self` receiver prevents PyBorrowMutError on nested calls!
    pub fn emit_message(&self, role: String, content: String) -> PyResult<()> {
        let _ = self.event_tx.send(UiEvent::ChatMessage { role, content });
        Ok(())
    }

    pub fn emit_status(&self, stage: String, detail: String) -> PyResult<()> {
        let _ = self.event_tx.send(UiEvent::StatusUpdate { stage, detail });
        Ok(())
    }
}
```

| Responsibility | Where It Lives | Why It Lives There |
| :--- | :--- | :--- |
| **`_services` Dict (`CoreRunTimeObjects`)** | Python (`UniversalPlatformContext`) | Core stores arbitrary Python tuples `(HumanMessage, AIMessage, BaseMessage)` that never need to cross into Rust. |
| **`emit_message` / `emit_status` / `emit_error`** | Rust (`#[pyclass] SlintEventSink`) | Crosses the FFI boundary immediately so Rust can forward owned `String` payloads to the Slint UI thread. |

## 🧠 2. Physical Metaphors for Core Mechanics

1. **The Diplomatic Embassy Building (`#[pyclass]` & `Py::new`):**  
   A normal Rust struct lives on the Rust stack or Rust heap—CPython's garbage collector has no idea it exists. Adding `#[pyclass]` and calling `Py::new(py, SlintEventSink { ... })?` builds a **Diplomatic Embassy** directly on CPython's heap: the outside of the building has a standard CPython `PyObject` header (`ob_refcnt`, `ob_type`) so Python code can hold references to it, while the interior room houses your native Rust struct fields.
2. **The Turnstile Borrow Counter vs Revolving Door (`&mut self` vs `&self` in `#[pymethods]`):**  
   Inside the embassy doorway sits a `RefCell`-style security guard (`PyCell`).
   - If you declare a `#[pymethods]` function with **`&mut self`**, the guard locks the turnstile whenever Python enters. If that method triggers a Python logger hook that calls *another* method on the same `SlintEventSink` before the first call finishes, the guard panics (`PyBorrowMutError: Already borrowed`).
   - If you declare all sink methods with **`&self`** and push events into an `mpsc::Sender` (or `slint::invoke_from_event_loop`), the doorway becomes a frictionless revolving door: any number of nested Python callbacks can enter simultaneously without ever locking each other out!

| `#[pymethods]` Receiver | Physical Metaphor | Concurrent / Re-Entrant Calls Allowed? |
| :--- | :--- | :--- |
| **`&self` (Shared Borrow)** | Open Revolving Door (`borrow_count += 1`) | ✅ **YES** (Unlimited nested readers/senders) |
| **`&mut self` (Exclusive Borrow)** | Single-Occupancy Locked Vault (`borrow_flag = -1`) | ❌ **NO** (Raises `PyBorrowMutError` on re-entry!) |

## 🔑 3. Core Mechanics & Step-by-Step Derivation

### 3.1 What `#[pyclass]` Actually Generates in Memory

When you annotate `pub struct SlintEventSink` with `#[pyclass]`, PyO3 generates:
1. A static C `PyTypeObject` descriptor table registering the class name and size with CPython.
2. A wrapper allocation (`PyCell` / `PyClassObject`) on the CPython heap containing three contiguous sections:
   - The standard `PyObject` header (`ob_refcnt` + `ob_type`).
   - An atomic/thread-checked borrow flag (`isize`, identical in spirit to `RefCell<T>` in `learn_rust` Topic 06).
   - Your actual Rust struct fields (`event_tx: Sender<UiEvent>`).

### 3.2 Thread Safety Requirement on `#[pyclass]` (`Send` Bound)

Because Python objects can potentially be referenced from multiple Python threads, **PyO3 requires every `#[pyclass]` struct to implement `Send` by default!**

| Field Type Inside `#[pyclass]` | Implements `Send`? | Allowed Inside `#[pyclass]`? |
| :--- | :--- | :--- |
| **`std::sync::mpsc::SyncSender<T>`** | ✅ **YES** (`Send + Sync`) | ✅ **YES** (Recommended for channel event sinks) |
| **`slint::Weak<AppWindow>`** | ✅ **YES** (`Send + Sync`) | ✅ **YES** (Can be stored directly inside `#[pyclass]`!) |
| **`slint::AppWindow` (Strong Handle) or `Rc<T>`** | ❌ **NO** (`!Send`) | ❌ **FORBIDDEN** (`error[E0277]: Rc<...> cannot be sent between threads`) |

*(Note: In Rust's standard library, `mpsc::Sender<T>` is `Send` but `!Sync`; if a `#[pyclass]` requires `Sync` in newer PyO3 versions, either store `slint::Weak<AppWindow>` directly inside `#[pyclass]`, use `std::sync::mpsc::SyncSender<T>`, or wrap `Mutex<Sender<T>>`.)*

## 🔬 4. Visual Invariant Models & Memory Layouts

*How to read this:* Inspect the exact byte layout of `Py::new(py, SlintEventSink { ... })` on the CPython heap, showing how `PyCell`'s borrow counter sits between the `PyObject` header and your Rust fields.

```text
Title: CPython Heap Layout of a #[pyclass] Struct (PyClassObject<SlintEventSink>)

CPYTHON HEAP ALLOCATION (Created via `Py::new(py, SlintEventSink { ... })?`)
┌─────────────────────────────────────────────────────────────────────────┐
│ 1. CPython PyObject Header (16 bytes on 64-bit)                         │
│    • ob_refcnt : usize = 2 (Held by Python Context + Rust Bound handle) │
│    • ob_type   : *mut PyTypeObject -> SlintEventSink vtable             │
├─────────────────────────────────────────────────────────────────────────┤
│ 2. PyO3 Runtime Borrow Checker (8 bytes — RefCell-style guard)          │
│    • borrow_flag : isize                                                │
│      - `0`   = Unborrowed                                               │
│      - `> 0` = Shared `&self` borrows active (Multiple allowed!)        │
│      - `-1`  = Exclusive `&mut self` borrow active (Blocks all others!) │
├─────────────────────────────────────────────────────────────────────────┤
│ 3. Embedded Rust Struct Payload (`SlintEventSink`)                      │
│    • ui_weak : slint::Weak<AppWindow> (Send + Sync, 8 bytes)            │
└─────────────────────────────────────────────────────────────────────────┘
```

| `borrow_flag` State | Triggered By | If Python Calls Another `&self` Method | If Python Calls a `&mut self` Method |
| :--- | :--- | :--- | :--- |
| **`0` (Idle)** | No active Rust method call | Transitions to `+1` (`Ok`) | Transitions to `-1` (`Ok`) |
| **`+1..+N` (Shared `&self`)** | Active `&self` method on stack | Increments to `N + 1` (`Ok`) | Raises `PyBorrowMutError` (`RuntimeError`) |
| **`-1` (Exclusive `&mut self`)** | Active `&mut self` method on stack | Raises `PyBorrowError` (`RuntimeError`) | Raises `PyBorrowMutError` (`RuntimeError`) |

## ⚖️ 5. Universal Invariant & Operations Matrix

The cardinal design law for `#[pyclass]` callbacks in event-driven architectures is the Shared-Receiver Sink Law:

$$\text{Role} = \text{Python-to-Rust Callback Sink} \implies \text{Receiver MUST Be \texttt{\&self} (Shared Read)} \quad \big| \quad \text{Receiver} = \texttt{\&mut self} \implies \text{Re-Entrant Call Panics (\texttt{PyBorrowMutError})}$$

| Macro / Method | Where Applied | Rust Signature | Python Sees | Borrow / Thread Invariant |
| :--- | :--- | :--- | :--- | :--- |
| **`#[pyclass]`** | Above `pub struct S` | `pub struct S { ... }` | `<class 'builtins.S'>` | All fields must implement `Send` (and `Sync` where required). |
| **`#[pymethods]`** | Above `impl S` | `impl S { ... }` | Methods on `S` | Generates C wrapper functions checking `borrow_flag`. |
| **`#[new]`** | Inside `#[pymethods]` | `fn new(...) -> Self` | `S(...)` (`__init__`) | Optional if struct is only constructed from Rust via `Py::new`. |
| **`Py::new(py, val)?`** | Inside `with_gil` | `Py::new(py, S { .. })` | Instance of `S` | Moves Rust struct onto CPython heap; returns `PyResult<Py<S>>`. |
| **`#[pyo3(get, set)]`** | Above struct field | `pub count: usize` | `obj.count` property | Generates getter (`&self`) and setter (`&mut self`) descriptors. |

## 🛠️ 6. Production Blueprint & Code Patterns

| Component | Language | Purpose |
| :--- | :--- | :--- |
| **`SlintEventSink` (`#[pyclass]`)** | Rust | Exposes `emit_message`, `emit_banner`, `emit_log`, and `emit_error` via shared `&self` methods. |
| **`attach_sink_to_python()`** | Rust | Allocates `SlintEventSink` via `Py::new(py, ...)` and injects it into `coldwind.desktop.gui_bridge`. |

```rust
use pyo3::prelude::*;
use std::sync::mpsc::SyncSender;

#[derive(Debug, Clone)]
pub enum GuiBridgeEvent {
    Message { role: String, content: String },
    Banner { title: String, subtitle: String },
    Log { level: String, heading: String, body: String },
    Error { summary: String },
}

#[pyclass]
pub struct SlintEventSink {
    // SyncSender<T> implements both Send and Sync!
    tx: SyncSender<GuiBridgeEvent>,
}

impl SlintEventSink {
    // Rust-only constructor (not exposed to Python so Python cannot forge sinks)
    pub fn create_in_rust(tx: SyncSender<GuiBridgeEvent>) -> Self {
        Self { tx }
    }
}

#[pymethods]
impl SlintEventSink {
    /// Satisfies MessageDisplayInterface.display_message(role, content)
    pub fn emit_message(&self, role: String, content: String) -> PyResult<()> {
        let _ = self.tx.send(GuiBridgeEvent::Message { role, content });
        Ok(())
    }

    /// Satisfies MessageDisplayInterface.display_banner(title, subtitle)
    #[pyo3(signature = (title, subtitle=""))]
    pub fn emit_banner(&self, title: String, subtitle: &str) -> PyResult<()> {
        let _ = self.tx.send(GuiBridgeEvent::Banner {
            title,
            subtitle: subtitle.to_string(),
        });
        Ok(())
    }

    /// Satisfies DebugLoggerInterface.log_info / log_warning / log_error
    pub fn emit_log(&self, level: String, heading: String, body: String) -> PyResult<()> {
        let _ = self.tx.send(GuiBridgeEvent::Log { level, heading, body });
        Ok(())
    }

    /// Satisfies ExceptionHandlerInterface.handle_exception
    pub fn emit_error(&self, summary: String) -> PyResult<()> {
        let _ = self.tx.send(GuiBridgeEvent::Error { summary });
        Ok(())
    }
}

pub fn attach_sink_to_python(
    py: Python<'_>,
    tx: SyncSender<GuiBridgeEvent>,
) -> PyResult<Py<PyAny>> {
    // Move Rust struct onto CPython heap and pass it to Python's HeadlessEngineAdapter
    let py_sink: Py<SlintEventSink> = Py::new(py, SlintEventSink::create_in_rust(tx))?;
    let bridge_mod = py.import("coldwind.desktop.gui_bridge")?;
    let adapter = bridge_mod.call_method1("boot_headless_engine", (py_sink.bind(py),))?;
    Ok(adapter.unbind())
}
```

## ⚠️ 7. Learner Pitfall Archive

| # | Pitfall Name | What Was Written | Exact Compiler / Runtime Error | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **The Re-Entrant `&mut self` Crash** | `pub fn emit_message(&mut self, ...)` on `SlintEventSink` | `RuntimeError: Already borrowed` (`PyBorrowMutError`) | Change receiver to `&self` and send events over `SyncSender` or `Weak<AppWindow>`. |
| **2** | **The Non-`Sync` `mpsc::Sender` Error** | Storing `std::sync::mpsc::Sender<T>` directly in `#[pyclass]` on PyO3 0.23+ | `error[E0277]: Sender<T> cannot be shared between threads safely` | Use `std::sync::mpsc::SyncSender<T>`, `slint::Weak<AppWindow>`, or `Mutex<Sender<T>>`. |
| **3** | **Invisible Struct Fields in Python** | Accessing `sink.tx` or `sink.count` from Python on a `#[pyclass]` | `AttributeError: 'SlintEventSink' object has no attribute 'count'` | Rust struct fields are private to Python by default; add `#[pyo3(get)]` only on fields Python must read. |

## ✅ 8. Checkpoint & Pass Criteria

Confirm your mastery of Subdomain 03 by verifying the three design questions below:

| Scenario | Correct Design Choice | Why |
| :--- | :--- | :--- |
| **Python calls `sink.emit_message()` only** | Construct in Rust via `Py::new(py, SlintEventSink { ... })?` without `#[new]`. | Python never needs to instantiate `SlintEventSink` itself; Rust injects the pre-wired instance. |
| **Python passes optional `subtitle=""` arg** | Add `#[pyo3(signature = (title, subtitle=""))]` above the method. | Rust has no default function arguments; `#[pyo3(signature = ...)]` generates Python's default parameter table. |
| **During `emit_message`, Python logs an info trace** | Both `emit_message(&self)` and `emit_log(&self)` take `&self`. | Multiple concurrent shared borrows (`borrow_flag = 2`) succeed with zero contention. |

## 🎯 9. Core Systems Invariants & Reading Path

| Invariant # | Statement | Next Step in Reading Path |
| :--- | :--- | :--- |
| **1. The Thin-Wrapper Split** | Keep Core's `_services` dictionary in a 30-line Python `UniversalPlatformContext` and delegate I/O to a Rust `#[pyclass]` sink. | Review [`./cheat_sheet.md`](./cheat_sheet.md) for 30-second recall. |
| **2. The `&self` Sink Law** | Every `#[pymethods]` callback invoked by Python must take `&self`, never `&mut self`. | Proceed to [`../04_slint_concurrency_bridge/README.md`](../04_slint_concurrency_bridge/README.md). |
| **3. The `Send + Sync` Field Law** | Every field inside a `#[pyclass]` struct must be thread-safe (`Weak<AppWindow>`, `SyncSender<T>`, or `Mutex<T>`). | Wire directly to Slint in [`../04_slint_concurrency_bridge/cheat_sheet.md`](../04_slint_concurrency_bridge/cheat_sheet.md). |