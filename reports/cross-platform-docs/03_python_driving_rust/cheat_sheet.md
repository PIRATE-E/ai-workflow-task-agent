# 🧩 Python Driving Rust (`#[pyclass]` & Event Sinks) Cheat Sheet & 30-Second Invariants

| Field | Value |
| :--- | :--- |
| **Tier** | `1 — Subdomain War Chest (C1–C12)` · per `cheatsheet_for_cheatsheet.md` |
| **Domain** | `shared` / `desktop` (`cross-platform-docs/03_python_driving_rust`) |
| **Verified** | `2026-10-22` — verified against PyO3 0.22+ `#[pyclass]`, `#[pymethods]`, and `PyCell` borrow rules |
| **Confidence** | `VERIFIED ✅` |

> **TL;DR:** Expose Rust event sinks to Python with `#[pyclass]` and `#[pymethods]`, allocate them on the CPython heap via `Py::new(py, sink)?`, store only `Send + Sync` fields (`slint::Weak<AppWindow>` or `SyncSender<T>`), and always use `&self` receivers so re-entrant Python callbacks never trigger `PyBorrowMutError`.
> **Primary Objective:** Within 30 seconds, declare a `#[pyclass]` struct and `#[pymethods]` block, pass it into `coldwind-core` as an event sink, and avoid `PyBorrowMutError` and `!Send`/`!Sync` compiler errors.
> **Master Guide:** [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) · **Concept Guide:** [`./README.md`](./README.md) · **Prev War Chest:** [`../02_rust_driving_python/cheat_sheet.md`](../02_rust_driving_python/cheat_sheet.md) · **Next War Chest:** [`../04_slint_concurrency_bridge/cheat_sheet.md`](../04_slint_concurrency_bridge/cheat_sheet.md)

## 📺 1. Curated Learning Sources

| Source | Why This Source | Verification |
| :--- | :--- | :--- |
| [PyO3 Guide — Python Classes (`#[pyclass]`)](https://pyo3.rs/main/class.html) | Canonical syntax for `#[pyclass]`, `#[pymethods]`, `#[new]`, `#[pyo3(signature = ...)]`, and `Py::new`. | `VERIFIED ✅` |
| [PyO3 Guide — Class Interior Mutability & Borrows](https://pyo3.rs/main/class.html#bound-and-interior-mutability) | Explains `PyCell` runtime borrow checking (`PyBorrowError` vs `PyBorrowMutError`). | `VERIFIED ✅` |
| [`../../urgent_development/platform-integration-spec.md`](../../urgent_development/platform-integration-spec.md) | Cold Wind AI contract for `PlatformRuntimeContextInterface` and `GuiMessageDisplay`. | `VERIFIED ✅` |
| [`./README.md`](./README.md) | Subdomain 03 deep dive on the Diplomatic Embassy model and Thin-Wrapper split. | `VERIFIED ✅` |

## 🧭 2. 30-Second Decision Tree

Choose the exact PyO3 attribute macro and receiver mutability based on how Python interacts with your Rust code.

```text
Title: Exposing Rust Capabilities to Python (#[pyclass] vs #[pyfunction] & Receiver Rules)

What are you exposing from Rust to Python?
├─ 1. A stateful event sink or platform context object (`SlintEventSink`)?
│  ├─ Struct header ──────────► `#[pyclass] pub struct SlintEventSink { ... }`
│  ├─ Methods block ──────────► `#[pymethods] impl SlintEventSink { ... }`
│  ├─ Constructed in Rust? ───► `let py_obj: Py<SlintEventSink> = Py::new(py, instance)?;`
│  └─ Constructed in Python? ─► Add `#[new] pub fn new(...) -> Self` inside `#[pymethods]`
│
├─ 2. Which method receiver should I use inside `#[pymethods]`?
│  ├─ Forwarding events / logs / UI updates? ──► `pub fn emit(&self, ...)` (ALWAYS `&self`!)
│  └─ Mutating internal Rust state? ───────────► Prefer `&self` + `Mutex<T>` over `&mut self`
│
└─ 3. A standalone stateless Rust helper function (e.g. fast token counter)?
   └─ Annotate with `#[pyfunction]` + pass via `wrap_pyfunction!(my_fn, py)?`
```

| Macro / Function | Target Item | What It Generates | When to Use |
| :--- | :--- | :--- | :--- |
| **`#[pyclass]`** | `pub struct S` | CPython `PyTypeObject` + `PyCell` wrapper | Exposing a Rust struct as a Python object. |
| **`#[pymethods]`** | `impl S` | Python method descriptors on `S` | Exposing Rust methods to Python callers. |
| **`#[new]`** | `fn new() -> Self` | Python `__new__` / `__init__` constructor | Only when Python code calls `S()` directly. |
| **`#[pyo3(signature = (...))]`** | Method in `#[pymethods]` | Default argument & `*args`/`**kwargs` parser | Supporting optional args like `subtitle=""`. |
| **`Py::new(py, val)?`** | Rust expression | Heap-allocated `Py<S>` instance | Constructing `S` in Rust and passing it to Python. |

## ⚖️ 3. Invariant & Operations Matrix

Every `#[pyclass]` method invocation enforces Rust's Aliasing XOR Mutability law dynamically at the FFI boundary via `PyCell`:

$$\text{Method Receiver} = \texttt{\&self} \implies \text{Shared Aliasing Allowed (\texttt{borrow\_flag > 0})} \quad \big| \quad \text{Method Receiver} = \texttt{\&mut self} \implies \text{Exclusive Only (\texttt{borrow\_flag == -1})}$$

| Receiver / Access | `PyCell` Borrow Action | Concurrent / Re-Entrant `&self` Calls? | Concurrent `&mut self` Calls? | Recommended for GUI Sinks? |
| :--- | :--- | :--- | :--- | :--- |
| **`&self`** | Increments shared reader count (`+1`) | ✅ **YES** (Safe for nested callbacks) | ❌ Blocked while reading | ✅ **YES (Mandatory)** |
| **`&mut self`** | Locks exclusive writer flag (`-1`) | ❌ Raises `PyBorrowError` | ❌ Raises `PyBorrowMutError` | ❌ **NO** (Re-entry hazard) |
| **`Bound<'py, Self>`** | Borrows outer Python handle only | ✅ **YES** (Until `.borrow()` called) | ✅ Explicit scope control | Advanced manual borrows |

## 🐍 4. Python & `learn_rust` Bridge Delta

| Mechanism | CPython 3.13+ Runtime Reality | Rust + PyO3 Reality | Owning `learn_rust` Topic |
| :--- | :--- | :--- | :--- |
| **Object Mutability (`self`)** | Python methods always receive a mutable `self` reference with zero borrow tracking. | PyO3 wraps `#[pyclass]` in a `RefCell`-like `PyCell` that tracks shared (`&self`) vs exclusive (`&mut self`) borrows. | **Topic 06:** `RefCell<T>` & Runtime Borrow Guards |
| **Field Visibility** | All `self.attr` fields in Python are public by default unless hidden by convention (`_attr`). | All fields of a `#[pyclass]` struct are **100% invisible to Python** unless marked with `#[pyo3(get)]`. | **Topic 02 & 07:** Struct Encapsulation & Privacy |
| **Inheritance (`class Sub(Base)`)** | Python classes freely subclass any base class (`PlatformRuntimeContextInterface`). | `#[pyclass]` cannot subclass pure-Python ABCs directly; use composition (Python wrapper holding `#[pyclass]` sink). | **Topic 03:** Composition & Traits over Inheritance |
| **Default Arguments** | `def emit_banner(self, title, subtitle=""):` is built into Python function syntax. | Rust functions have no default args; `#[pyo3(signature = (title, subtitle=""))]` synthesizes them for Python. | **Topic 00 & 12:** Function Signatures & Attribute Macros |

## 🧠 5. Physical Metaphor Register

| Mechanism | Physical Metaphor | 1:1 Mapping to Code |
| :--- | :--- | :--- |
| **`#[pyclass]` + `Py::new(py, val)`** | **The Diplomatic Embassy on Foreign Soil** | Allocates a building on the CPython heap whose facade speaks Python (`PyObject` header) while its interior holds native Rust equipment. |
| **`PyCell` (`&self` vs `&mut self`)** | **Revolving Door (`&self`) vs Single-Occupancy Vault (`&mut self`)** | `&self` lets any number of nested Python callbacks walk through at once; `&mut self` bolts the door and panics (`PyBorrowMutError`) if a callback re-enters. |
| **Thin Python Wrapper + Rust Sink** | **Local Interpreter + Radio Transmitter** | A 20-line Python class handles local paperwork (`_services` dict) and hands every outgoing message to the Rust radio transmitter (`SlintEventSink`). |

## 🛠️ 6. Syntax Bank

| Snippet # | Pattern | Key Feature |
| :--- | :--- | :--- |
| **1** | **Re-Entrancy-Safe `#[pyclass]` Sink** | Uses `&self` + `SyncSender<String>` (`Send + Sync`). |
| **2** | **Default Args & Optional Params** | Uses `#[pyo3(signature = (role, content, metadata=None))]`. |
| **3** | **Injecting `Py<SlintEventSink>` into Python** | Allocates with `Py::new(py, ...)` and passes to Python bootloader. |

### 1. Declaring a Thread-Safe, Re-Entrancy-Safe `#[pyclass]` Sink
```rust
use pyo3::prelude::*;
use std::sync::mpsc::SyncSender;

#[pyclass]
pub struct SlintEventSink {
    // SyncSender<String> is Send + Sync; sending only requires `&self`!
    tx: SyncSender<String>,
}

#[pymethods]
impl SlintEventSink {
    pub fn emit_token(&self, token: &str) -> PyResult<()> {
        let _ = self.tx.send(token.to_string());
        Ok(())
    }
}
```

### 2. Supporting Optional & Default Python Arguments in `#[pymethods]`
```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyclass]
pub struct DisplayBridge;

#[pymethods]
impl DisplayBridge {
    // Matches Python: def display_message(self, role: str, content: str, metadata: dict | None = None)
    #[pyo3(signature = (role, content, metadata=None))]
    pub fn display_message(
        &self,
        role: &str,
        content: &str,
        metadata: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<()> {
        let meta_len = metadata.map_or(0, |m| m.len());
        println!("[{}] {} (meta keys: {})", role, content, meta_len);
        Ok(())
    }
}
```

### 3. Allocating `#[pyclass]` in Rust and Passing to Python
```rust
use pyo3::prelude::*;

pub fn pass_sink_to_python(py: Python<'_>, sink: SlintEventSink) -> PyResult<Py<PyAny>> {
    // Allocate SlintEventSink on CPython heap -> Py<SlintEventSink>
    let py_sink: Py<SlintEventSink> = Py::new(py, sink)?;
    let bridge = py.import("coldwind.desktop.gui_bridge")?;
    let ctx = bridge.call_method1("create_context", (py_sink.bind(py),))?;
    Ok(ctx.unbind())
}
```

## 🔬 7. Visual Memory Model

*How to read this:* Trace what happens when Python's `display_message` calls `SlintEventSink.emit_message(&self)` and triggers a nested `emit_log(&self)` call—both succeed because `borrow_flag` increments from `0 -> 1 -> 2` instead of locking `-1`.

```text
Title: Re-Entrant Callback Trace on #[pyclass] SlintEventSink (`&self` vs `&mut self`)

  [Python: display_message()]
               │
               ▼ Calls sink.emit_message(&self)
  ┌──────────────────────────────────────────────────────┐
  │ PyCell<SlintEventSink>                               │
  │  • borrow_flag: 0 ──► +1 (Shared borrow #1 acquired) │
  └──────────────────────────┬───────────────────────────┘
                             │ Suppose a hook inside logs status:
                             ▼ Calls sink.emit_log(&self)
  ┌──────────────────────────────────────────────────────┐
  │ PyCell<SlintEventSink>                               │
  │  • With `&self`:     borrow_flag: +1 ──► +2 (SAFE!)  │
  │  • With `&mut self`: PANICS! (PyBorrowMutError!)     │
  └──────────────────────────────────────────────────────┘
```

| Scenario | Receiver on `emit_message` | Receiver on `emit_log` | Runtime Outcome |
| :--- | :--- | :--- | :--- |
| **Design A (Correct)** | `&self` | `&self` | `borrow_flag` reaches `+2`, then unwinds to `0` (`VERIFIED ✅`). |
| **Design B (Broken)** | `&mut self` | `&mut self` | Second call raises `PyBorrowMutError: Already borrowed` (`❌ CRASH`). |

## 🛡️ 8. Compiler Diagnostics Table

| Exact Diagnostic / Error | Rule Violated | Runtime Bug Prevented | Python Equivalent of the Bug |
| :--- | :--- | :--- | :--- |
| **`PyBorrowMutError: Already borrowed`** | Re-entrant Python call hit `&mut self` on an active `#[pyclass]` | Aliasing two `&mut T` references to the same Rust struct (Undefined Behavior) | Mutating state mid-callback while outer frame holds inconsistent state |
| **`error[E0277]: `Sender<T>` cannot be shared between threads safely`** | Placed `!Sync` `mpsc::Sender<T>` in `#[pyclass]` without `SyncSender` or `Mutex` | Concurrent unsynchronized access to a `!Sync` channel endpoint from multiple Python threads | Sharing a non-thread-safe producer across OS threads |
| **`error[E0277]: `Rc<...>` cannot be sent between threads safely`** | Placed strong `AppWindow` (`!Send`) inside `#[pyclass]` | Moving thread-affine GUI resources to a background thread | Calling GUI toolkit methods from a non-main thread |
| **`TypeError: SlintEventSink.__new__() missing required positional argument`** | Python tried to call `SlintEventSink()` when no `#[new]` was defined | Unintended construction of unconfigured Rust sink from Python | Instantiating an internal adapter class without its required handle |

## ⚠️ 9. Trap Archive (3-part form)

| # | Trap Name | Assumed | Reality | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **The `&mut self` Event Sink Trap** | Event sink methods should take `&mut self` to push events. | Any nested/re-entrant call from Python into the same `#[pyclass]` while `&mut self` is active raises `PyBorrowMutError`. | Always use `&self` on `#[pymethods]` sinks; `SyncSender::send(&self)` and `Weak::clone(&self)` only need `&self`. |
| **2** | **The `!Sync` `mpsc::Sender` Trap** | `std::sync::mpsc::Sender<T>` is both `Send` and `Sync`. | `mpsc::Sender<T>` is `Send` but `!Sync`; newer PyO3 versions require `#[pyclass]` fields to be `Sync` as well. | Use `std::sync::mpsc::SyncSender<T>`, `slint::Weak<AppWindow>`, or `Mutex<Sender<T>>`. |
| **3** | **Trying to Subclass Python ABC in `#[pyclass]`** | `#[pyclass(extends=PlatformRuntimeContextInterface)]` works on Python ABCs. | PyO3 `extends=...` only subclasses C/Rust `#[pyclass]` base types, not pure-Python `abc.ABC` classes! | Use the Thin-Wrapper pattern: a 25-line Python class subclasses the ABC and delegates to your `#[pyclass]` sink. |

### Trap 1: The `&mut self` Event Sink Trap
- **Assumed:** Marking `#[pymethods]` with `&mut self` is harmless because only one thread holds the GIL.
- **Reality:** Even on a single thread, re-entrancy (Method A calls Python, which logs via Method B on the same object) violates Rust's exclusive `&mut self` rule and raises `RuntimeError: Already borrowed`.
- **10-Second Recall Fix:** Use shared `&self` receivers for every method in `SlintEventSink`.

### Trap 2: The `!Sync` `mpsc::Sender` Trap
- **Assumed:** `std::sync::mpsc::Sender<T>` implements `Sync` and can sit bare inside any `#[pyclass]`.
- **Reality:** In Rust's `std`, `Sender<T>` is `Send + !Sync`. PyO3 `0.22+`/`0.23+` checks `Sync` on `#[pyclass]` structs so `&self` methods are safe under free-threaded Python.
- **10-Second Recall Fix:** Store `slint::Weak<AppWindow>` (which is `Send + Sync`) or `std::sync::mpsc::SyncSender<T>` inside your `#[pyclass]`.

### Trap 3: Subclassing a Pure-Python `abc.ABC` from `#[pyclass]`
- **Assumed:** A Rust `#[pyclass]` can directly inherit from `coldwind.core.interfaces.runtime_interface.PlatformRuntimeContextInterface`.
- **Reality:** CPython's C-level `tp_base` inheritance across PyO3 requires the base class to be a statically sized C/PyO3 type, not a heap-defined Python `ABC`.
- **10-Second Recall Fix:** Implement `UniversalPlatformContext` in Python (`gui_bridge.py`) and pass the Rust `#[pyclass] SlintEventSink` into its `__init__`.

## ⏳ 10. Deferred Concepts (Manifest Boundary)

| Concept / Syntax | Manifest Status & Marker | What It Unlocks |
| :--- | :--- | :--- |
| **`#[pyclass(frozen)]` Immutable Classes** | `⏳ Deferred until Topic 10 (FFI & PyO3)` | Eliminates the 8-byte `PyCell` borrow flag overhead completely when a class only uses `&self`. |
| **Procedural Macro Token Expansion (`syn`/`quote`)** | `⏳ Deferred until Topic 12 (Advanced Patterns)` | How `#[pyclass]` and `#[pymethods]` rewrite Rust AST nodes into C-ABI trampolines at compile time. |

## 📈 11. Family Learning Progression

```text
Title: Subdomain 03 Internal Progression

[1. #[pyclass] Struct (Send + Sync)] ──► [2. #[pymethods] (&self Sinks)] ──► [3. Py::new(py, sink) Injection]
```

| Order | Milestone | Why Learn It Here |
| :--- | :--- | :--- |
| **1** | **`#[pyclass]` Memory & `Send + Sync` Rules** | Determines which fields (`Weak<AppWindow>`, `SyncSender`) can live inside the struct. |
| **2** | **`#[pymethods]` & `PyCell` Borrow Flag (`&self`)** | Prevents `PyBorrowMutError` during live agent streaming and logging. |
| **3** | **`Py::new(py, val)` & Thin-Wrapper Injection** | Connects the Rust sink to `coldwind-core`'s `ContextRegistry`. |

## 📎 12. Concept Notes & Study Reports Directory

| Document | Relative Path | Scope & Invariants Covered | Status |
| :--- | :--- | :--- | :--- |
| **Subdomain 03 Concept Guide** | [`./README.md`](./README.md) | Deep dive into `#[pyclass]`, `PyCell` memory layout, and Thin-Wrapper integration. | `🟢 Complete` |
| **Subdomain 02 War Chest** | [`../02_rust_driving_python/cheat_sheet.md`](../02_rust_driving_python/cheat_sheet.md) | Prerequisite: `py.import`, `call_method1`, and `PyErr` handling. | `🟢 Complete` |
| **Subdomain 04 Concept Guide** | [`../04_slint_concurrency_bridge/README.md`](../04_slint_concurrency_bridge/README.md) | Final step: wiring `SlintEventSink` to Thread 0's `AppWindow` via `invoke_from_event_loop`. | `🟢 Complete` |
| **Subdomain 04 War Chest** | [`../04_slint_concurrency_bridge/cheat_sheet.md`](../04_slint_concurrency_bridge/cheat_sheet.md) | `Weak<AppWindow>`, `invoke_from_event_loop`, `py.allow_threads`, and 60 FPS UI invariants. | `🟢 Complete` |