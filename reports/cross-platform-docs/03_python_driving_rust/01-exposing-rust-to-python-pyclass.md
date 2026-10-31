# 01 — Disguising a Rust Struct as a Python Object (`#[pyclass]`, `#[pymethods]` & The Thin-Wrapper Split)

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `desktop` (`cross-platform-docs`) |
| **Subdomain** | `03_python_driving_rust` |
| **Type** | Concept Note / Root-Cause Study Report |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ `#[pyclass]`, `PlatformRuntimeContextInterface`) |
| **Confidence** | `VERIFIED ✅` |
| **Prerequisites** | Subdomains 01 & 02, `learn_rust` Topic 02 (`struct` & `impl`) |
| **Updated** | `2026-10-25` |

> **TL;DR:** While `coldwind-core` is running a 15-second turn in Python, it needs to send live chat messages, banners, and logs to our Rust GUI—without importing anything from the GUI. We solve this by putting a Python costume (`#[pyclass]` and `#[pymethods]`) on a Rust struct (`SlintEventSink`), placing it on Python's heap via `Py::new(py, sink)?`, and handing it to a tiny 25-line Python wrapper (`UniversalPlatformContext`).

## Domain & Dependencies

| Item | Detail | Status |
| :--- | :--- | :--- |
| **Covers** | Why Python needs to call Rust *during* a turn; how `#[pyclass]`, `#[pymethods]`, and `Py::new` work; why we split `UniversalPlatformContext` (Python) and `SlintEventSink` (Rust). | `VERIFIED ✅` |
| **Prerequisite** | Subdomains 01 & 02 (`Python::with_gil`, `Bound<'py, T>`, `call1`). | `VERIFIED ✅` |
| **Unlocks** | [`./02-pycell-borrows-and-reentrancy.md`](./02-pycell-borrows-and-reentrancy.md) and [`./cheat_sheet.md`](./cheat_sheet.md). | `VERIFIED ✅` |

## Executive Summary

In Subdomain 02, you learned how Rust calls `adapter.execute_turn(prompt)` and gets a return value at the end.

**Wait—if `execute_turn` returns the answer at the end, why does Python ever need to call Rust?**  
Because an agent turn in `coldwind-core` is **not** a 1-millisecond math calculation! During a single turn:
1. The router classifies the prompt (`[Log] Classifying intent...`).
2. A sub-agent spawns and calls an MCP browser tool (`[Status] Opening browser...`).
3. The LLM streams tokens word-by-word (`"Here"`, `" is"`, `" your"`, `" answer..."`).

If Rust just waited for `execute_turn()` to return at the very end, your GUI window would stay completely blank for 20 seconds and then dump everything on screen at once! Instead, while Python is still inside `execute_turn()`, Python calls `ContextRegistry.get().get_message_display().display_message(role, text)`. We need that Python call to **trigger our Rust code in real time**!

| Macro / Function in the Cheat Sheet | Plain-English Meaning (Like You're 10) |
| :--- | :--- |
| **`#[pyclass]` above `pub struct SlintEventSink`** | "Put a Python costume on this Rust struct so Python thinks it's a normal Python class." |
| **`#[pymethods]` above `impl SlintEventSink`** | "Let Python call these Rust methods just like normal Python methods (`sink.emit_message(...)`)." |
| **`Py::new(py, SlintEventSink { ... })?`** | "Move this Rust struct onto Python's heap so we can pass it as an argument to a Python function." |

## 1️⃣ The Pain First — Why Can't We Just Subclass `PlatformRuntimeContextInterface` in Rust?

When you look at [`../../core/src/coldwind/core/interfaces/runtime_interface.py`](../../core/src/coldwind/core/interfaces/runtime_interface.py), you see that `coldwind-core` expects a class that inherits from `PlatformRuntimeContextInterface` (which is a Python `abc.ABC` abstract base class with ~20 methods, including a `self._services` dictionary where Python stores `(HumanMessage, AIMessage, BaseMessage)`).

Your first instinct is: *"Let's just write one big Rust `#[pyclass]` that inherits from `PlatformRuntimeContextInterface`!"*

Here are the **two root causes** why that dies immediately:

| Why "One Giant Rust Class" Dies | The Technical Root Cause |
| :--- | :--- |
| **1. PyO3 `#[pyclass(extends=...)]` CANNOT inherit from a pure-Python class!** | In CPython's C-API, a compiled C/Rust struct has a fixed byte size calculated at compile time, while a pure-Python `class` (`abc.ABC`) is a dynamic heap dictionary created at runtime. PyO3 cannot glue a static Rust struct underneath a dynamic Python `ABC`. |
| **2. Core stores pure-Python objects inside `register_service()`** | During boot, `ChatInitializer` stores Python classes (`HumanMessage`, `neo4j_driver`) in `context.register_service(key, val)` and reads them back inside Python. Bouncing those pure-Python objects into Rust and back on every turn is pointless work. |

## 2️⃣ The Solution: The "Local Interpreter + Radio Transmitter" Split

**Metaphor-first:** Suppose your Rust headquarters needs to open an office in Python-land. Python law requires the office to fill out 20 pages of local Python paperwork (`PlatformRuntimeContextInterface` and the `_services` dictionary), and whenever a customer speaks, radio the message back to Rust headquarters.
- You don't teach a Rust radio tower how to fill out 20 pages of Python paperwork!
- Instead, you hire a **25-line Python receptionist (`UniversalPlatformContext`)** to hold the local Python dictionaries, and you hand that receptionist a **Rust Walkie-Talkie (`#[pyclass] SlintEventSink`)**.
- Whenever `coldwind-core` tells the receptionist *"Display this message!"*, the receptionist presses the button on the Rust Walkie-Talkie (`self._rust_sink.emit_message(role, content)`)!

```text
Title: The Thin-Wrapper + Rust Sink Split (How Core Talks to Rust)

COLD WIND CORE (Python)            THIN PYTHON WRAPPER (`gui_bridge.py`)        RUST `#[pyclass]` (`SlintEventSink`)
┌─────────────────────────┐        ┌───────────────────────────────────┐        ┌──────────────────────────────────┐
│ ContextRegistry.get()   │        │ class UniversalPlatformContext:   │        │ #[pyclass]                       │
│  ├─ register_service() ─┼───────►│  • self._services = {} (In Python)│        │ pub struct SlintEventSink {      │
│  ├─ get_service()      ─┼───────►│  • Fast local dict lookup!        │        │   tx: SyncSender<GuiBridgeEvent> │
│  │                      │        │                                   │        │ }                                │
│  └─ display_message()  ─┼───────►│  • Calls `self._sink.emit_msg()` ─┼───────►│ #[pymethods]                     │
│     log_info()         ─┼───────►│  • Calls `self._sink.emit_log()` ─┼───────►│ pub fn emit_msg(&self, ...)      │
└─────────────────────────┘        └───────────────────────────────────┘        └──────────────────────────────────┘
```

| Piece | Written In | Lines of Code | What It Owns |
| :--- | :--- | :--- | :--- |
| **`UniversalPlatformContext`** | Python (`gui_bridge.py`) | ~25 lines | Subclasses `PlatformRuntimeContextInterface`; holds `_services` dict in Python. |
| **`SlintEventSink`** | Rust (`#[pyclass]`) | ~30 lines | Receives `emit_message`, `emit_banner`, `emit_log`, and `emit_error` in Rust! |

## 3️⃣ How `#[pyclass]`, `#[pymethods]`, and `Py::new` Work Together

Let's trace how a Rust struct puts on its Python costume in three small steps:

### Step 1: Put `#[pyclass]` on the `struct`
```rust
#[pyclass]
pub struct SlintEventSink {
    tx: std::sync::mpsc::SyncSender<String>,
}
```
- **What it does:** Tells PyO3 to generate a Python class header (`PyTypeObject`) for `SlintEventSink`.
- **Important Privacy Rule:** Just like `learn_rust` Topic 07 (where struct fields are private by default), **every field inside a `#[pyclass]` struct is 100% invisible to Python** unless you explicitly write `#[pyo3(get)]` above it! That's great for us: Python doesn't need to touch `tx` directly; Python only calls our methods.

### Step 2: Put `#[pymethods]` on the `impl` block
```rust
#[pymethods]
impl SlintEventSink {
    pub fn emit_message(&self, role: String, content: String) -> PyResult<()> {
        let _ = self.tx.send(format!("[{}] {}", role, content));
        Ok(())
    }
}
```
- **What it does:** For every `pub fn` inside this `impl` block, PyO3 generates a C wrapper function that unpacks Python's `str` arguments into Rust `String`s and calls your Rust method!

### Step 3: Move It to Python's Heap with `Py::new(py, sink)?`
When you create a normal Rust struct (`let sink = SlintEventSink { tx };`), it sits on the Rust stack. To hand it to Python, it needs to live on the **CPython heap** with an `ob_refcnt` header:
```rust
let py_sink: Py<SlintEventSink> = Py::new(py, SlintEventSink { tx })?;
```
- `Py::new(py, ...)` allocates a Python object box on CPython's heap, moves your Rust `SlintEventSink` inside it, and returns a `Py<SlintEventSink>` briefcase!

| Step | What You Write in Rust | What Python Sees |
| :--- | :--- | :--- |
| **1. Struct** | `#[pyclass] pub struct SlintEventSink` | A Python type `<class 'builtins.SlintEventSink'>`. |
| **2. Methods** | `#[pymethods] impl SlintEventSink { pub fn emit_message(&self, ...) }` | A callable method `sink.emit_message(role, content)`. |
| **3. Heap Box** | `let py_sink = Py::new(py, sink)?;` | A live Python object instance you can pass into `call1((py_sink.bind(py),))`! |

## 4️⃣ Step-by-Step Code Walkthrough (Every Line Decoded)

Here is how Rust creates `SlintEventSink`, wraps it on the Python heap with `Py::new`, and hands it to Python's `boot_headless_engine(sink)`:

```rust
use pyo3::prelude::*;
use std::sync::mpsc::SyncSender;

#[pyclass]
pub struct SlintEventSink {
    // Private to Rust: Python cannot see or mess with this channel!
    tx: SyncSender<String>,
}

#[pymethods]
impl SlintEventSink {
    // Python calls: `rust_sink.emit_message("assistant", "Hello!")`
    pub fn emit_message(&self, role: &str, content: &str) -> PyResult<()> {
        let _ = self.tx.send(format!("[{}]: {}", role, content));
        Ok(())
    }

    // Optional default argument in Python: `rust_sink.emit_banner("Cold Wind")`
    #[pyo3(signature = (title, subtitle=""))]
    pub fn emit_banner(&self, title: &str, subtitle: &str) -> PyResult<()> {
        let _ = self.tx.send(format!("=== {} ({}) ===", title, subtitle));
        Ok(())
    }
}

pub fn inject_sink_into_python(py: Python<'_>, tx: SyncSender<String>) -> PyResult<Py<PyAny>> {
    // 1. Construct the Rust struct and move it onto Python's heap (`Py::new`)
    let py_sink: Py<SlintEventSink> = Py::new(py, SlintEventSink { tx })?;

    // 2. Import our 25-line Python wrapper module and pass `py_sink` to it!
    let bridge = py.import("coldwind.desktop.gui_bridge")?;
    let adapter = bridge.call_method1("boot_headless_engine", (py_sink.bind(py),))?;

    // 3. Unbind the returned adapter so our worker thread can store it across turns
    Ok(adapter.unbind())
}
```

| Code Feature | Why It Is Written That Way |
| :--- | :--- |
| **No `#[new]` inside `#[pymethods]`** | We only need `#[new]` if *Python* code writes `SlintEventSink()`. Here, *Rust* builds `SlintEventSink` with `Py::new(py, ...)` and hands the finished object to Python! |
| **`#[pyo3(signature = (title, subtitle=""))]`** | Rust functions don't support default parameter values (`subtitle=""`), so this macro tells PyO3 to fill in `""` if Python only passes 1 argument! |
| **`(py_sink.bind(py),)`** | Plugs `py_sink` into `py` and wraps it in a 1-tuple `(...,)` to pass it to `boot_headless_engine`. |

## ✅ Checkpoint (Prove It to Yourself — 5 Minutes)

| # | Check Question | Expected Root-Cause Answer |
| :--- | :--- | :--- |
| **1** | Why don't we inherit directly from Python's `PlatformRuntimeContextInterface` (`abc.ABC`) on our Rust `#[pyclass]`? | Because PyO3 `#[pyclass(extends=...)]` cannot inherit from a dynamic pure-Python `ABC` class—so a tiny Python wrapper class implements the `ABC` and holds our Rust `#[pyclass]` sink. |
| **2** | Can Python code read or overwrite `self.tx` on `SlintEventSink`? | No! All fields on a `#[pyclass]` struct are completely hidden from Python unless marked with `#[pyo3(get, set)]`. |
| **3** | How do you move a `#[pyclass]` struct instance from Rust onto the CPython heap? | Call `Py::new(py, my_struct)?`, which returns `PyResult<Py<MyStruct>>`. |

## 📎 Glossary (Plain-English Dictionary)

| Technical Term | Simple Everyday Meaning |
| :--- | :--- |
| **`#[pyclass]`** | Rust macro that wraps a Rust `struct` so Python can hold it as a normal Python object. |
| **`#[pymethods]`** | Rust macro placed above `impl MyStruct` that exposes its `pub fn` methods to Python. |
| **`Py::new(py, val)`** | Allocates a `#[pyclass]` struct on Python's heap and returns a `Py<T>` handle to it. |
| **`#[pyo3(signature = ...)]`** | Macro that adds Python default argument values (like `subtitle=""`) to a Rust method. |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | What if I want to expose just ONE standalone Rust function to Python without creating a whole `struct`? | Put `#[pyfunction]` above `fn my_helper(...)` and pass it to Python via `pyo3::wrap_pyfunction!(my_helper, py)?`. | `2026-10-25` |
| **Q2** | Why did we use `&self` instead of `&mut self` on `emit_message` and `emit_banner`? | Because using `&mut self` on a callback sink causes a nasty runtime crash (`PyBorrowMutError: Already borrowed`)—which we prove step-by-step in Report `02-pycell-borrows-and-reentrancy.md`! | `2026-10-25` |