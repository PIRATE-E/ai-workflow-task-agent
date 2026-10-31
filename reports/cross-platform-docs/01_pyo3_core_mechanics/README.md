# ⚡ Subdomain 01: PyO3 Core Mechanics & GIL Lifetime Model

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `core` (`cross-platform-docs`) |
| **Subdomain** | `01_pyo3_core_mechanics` |
| **Type** | Subdomain README + Tier 2 Concept Note Deep-Dive |
| **Prerequisites** | `learn_rust` Topics 00–01 (Lifetimes `'a`), Topic 06 (`Rc<T>`, `RefCell<T>`, `Drop`) |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ `Bound<'py, T>` API, CPython 3.13+ C-API) |
| **Confidence** | `VERIFIED ✅` |
| **Updated** | `2026-10-22` |

> **TL;DR:** When embedding Python inside a Rust binary (`ai-workflow-gui`), Rust must initialize the CPython runtime (`pyo3::prepare_freethreaded_python()`) and acquire a zero-sized lifetime token (`Python<'py>`) via `Python::with_gil(|py| ...)`. Inside that scope, use `Bound<'py, T>` for fast operations; to store a Python object inside a Rust struct or send it across threads, call `.unbind()` to obtain a detached `Py<T>` handle.
> **Scope:** Embedded CPython initialization, the Global Interpreter Lock (GIL) as a Rust lifetime `'py`, `Bound<'py, T>` vs `Py<T>` smart pointers, `.bind(py)` / `.unbind()` transitions, and `IntoPyObject` / `.extract::<T>()` data marshalling.
> **Python Bridge:** In CPython, every variable is a `PyObject*` heap pointer whose reference count (`ob_refcnt`) is mutated under the GIL. PyO3 maps that runtime discipline into Rust's type system: `Python<'py>` proves the thread holds the GIL, `Bound<'py, T>` ties pointer dereferencing to `'py`, and `Py<T>` provides a `'static` (`Send + Sync`) box that cannot be dereferenced until re-bound to a `Python<'py>` token.

## 📺 Recommended Learning & Reference Sources

| # | Source & Link | Architectural Focus | Verification |
| :--- | :--- | :--- | :--- |
| **1** | [PyO3 Guide — Memory Management (`Bound<'py, T>` & `Py<T>`)](https://pyo3.rs/main/memory.html) | Official specification of GIL-bound vs GIL-independent smart pointers and `ob_refcnt` lifecycle. | `VERIFIED ✅` |
| **2** | [PyO3 Guide — Type Conversions (`IntoPyObject` & `FromPyObject`)](https://pyo3.rs/main/conversions/tables.html) | Complete mapping table between Rust primitives/collections and CPython `PyObject` types. | `VERIFIED ✅` |
| **3** | [CPython 3.13+ C-API — Initialization & GIL (`PyGILState_Ensure`)](https://docs.python.org/3/c-api/init.html) | Under-the-hood C functions (`Py_InitializeEx`, `PyGILState_Ensure`) that PyO3 wraps safely. | `VERIFIED ✅` |
| **4** | [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) | Parent architecture report detailing how `Bound<'py, T>` and `Py<T>` power the worker thread. | `VERIFIED ✅` |

## At a Glance & Subdomain Navigation

| Artifact | Relative Path | Type | What It Answers | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Subdomain Concept Guide (This File)** | [`./README.md`](./README.md) | Concept Note + Subdomain Index | Why does `'py` exist, how do `Bound<'py, T>` and `Py<T>` differ in RAM, and how do types cross the FFI? | `🟢 Complete` |
| **Subdomain 01 War Chest** | [`./cheat_sheet.md`](./cheat_sheet.md) | Tier 1 Cheat Sheet (C1–C12) | 30-second pointer decision tree, `.bind()`/`.unbind()` syntax templates, and compiler error fixes. | `🟢 Complete` |
| **Next Subdomain (`02`)** | [`../02_rust_driving_python/README.md`](../02_rust_driving_python/README.md) | Subdomain 02 Concept Guide | How to use `Bound<'py, PyModule>` to import `coldwind-core` and execute LangGraph turns. | `🟢 Complete` |
| **Parent Shelf Index** | [`../README.md`](../README.md) | System Shelf README | Full domain topology and cross-subdomain ownership table. | `🟢 Complete` |

## 🐍 1. The Python vs Rust Architecture Comparison

In pure Python (`coldwind-core`), the CPython virtual machine (`ceval.c`) automatically holds the GIL on the executing thread and manages `ob_refcnt` behind every variable assignment. In an embedded Rust binary, **no Python interpreter exists when `fn main()` starts**, and Rust threads do not hold the GIL by default.

```python
# Python (coldwind-core): GIL and PyObject refcounts are 100% implicit
def process_items() -> list[int]:
    # CPython allocates PyListObject on heap (ob_refcnt = 1)
    items = [10, 20, 30]
    items.append(40)
    return items  # Caller receives PyObject*; GC decrements refcnt when out of scope
```

```rust
// Rust (ai-workflow-gui): Explicit runtime init, GIL token ('py), and Bound<'py, T>
use pyo3::prelude::*;
use pyo3::types::PyList;

pub fn process_items_from_rust() -> PyResult<Vec<i32>> {
    // 1. Initialize CPython interpreter once at process boot
    pyo3::prepare_freethreaded_python();

    // 2. Acquire the GIL -> yields zero-sized token `py: Python<'py>`
    Python::with_gil(|py| {
        // 3. Allocate PyList bound to lifetime `'py`
        let list: Bound<'_, PyList> = PyList::new(py, [10, 20, 30])?;
        list.append(40)?;

        // 4. Marshal CPython PyList into native Rust Vec<i32> before releasing GIL
        let rust_vec: Vec<i32> = list.extract()?;
        Ok(rust_vec)
    }) // <-- 'py ends here: `list` drops (Py_DECREF), then GIL is released!
}
```

| Architectural Aspect | Pure CPython 3.13+ | Rust + PyO3 (`Bound<'py, T>` API) | Why the Difference Exists |
| :--- | :--- | :--- | :--- |
| **Interpreter Boot** | Automatic before `main.py` runs | Explicit `pyo3::prepare_freethreaded_python()` | Rust owns `fn main()`; Python is a guest library inside the process. |
| **GIL Proof** | Hidden `PyThreadState*` in C TLS | Explicit `py: Python<'py>` token | Rust refuses to call CPython APIs unless you prove the GIL is held at compile time. |
| **Local Reference** | Implicit `PyObject*` variable | `Bound<'py, T>` (`8-byte` pointer + `'py`) | Guarantees `Py_DECREF` runs *before* the GIL is released at closure exit. |
| **Long-Lived Storage** | Global variable / `self.attr` | `Py<T>` (created via `.unbind()`) | Strips the `'py` lifetime so the pointer can live in a Rust struct across turns. |

## 🧠 2. Physical Metaphors for Core Mechanics

1. **The Cleanroom Airlock & Badge (`Python::with_gil` & `Python<'py>`):**  
   CPython's heap is a pressurized cleanroom where only one worker can operate machinery at a time. Calling `Python::with_gil(|py| ...)` steps through the airlock and clips a security badge (`py: Python<'py>`) to your coat. Every machine inside (`PyList::new(py, ...)`) checks for your badge. When you walk out the closing brace `}`, the airlock automatically strips your badge.
2. **The Tethered Inspection Wand (`Bound<'py, T>`):**  
   A `Bound<'py, T>` smart pointer is an inspection wand wired directly into the cleanroom wall socket (`'py`). While inside the room, it is fast and zero-cost to wave around (`.call_method0()`, `.getattr()`). However, if you try to carry the tethered wand out the airlock door (return `Bound<'py, T>` from `with_gil`), the cord yanks you back (`error[E0597]: 'py does not live long enough`).
3. **The Sealed Specimen Case (`Py<T>` via `.unbind()`):**  
   To take a Python object out of the cleanroom and store it in your Rust backpack (`struct EngineWorker`), you press `.unbind()`. This detaches the power cord and seals the object inside a protective glass case (`Py<T>`). Anyone can carry the sealed case between rooms (`Send + Sync`), but nobody can press its buttons until they bring it back inside the cleanroom and plug it in via `specimen.bind(py)`.

| PyO3 Concept | Physical Metaphor | What It Permits | What It Prevents |
| :--- | :--- | :--- | :--- |
| **`Python<'py>`** | Cleanroom Security Badge | Authorizes all Python heap allocations and calls. | Calling CPython C-API from an unattached thread (Segfault). |
| **`Bound<'py, T>`** | Tethered Inspection Wand | Direct method calls, indexing, iteration, type casts. | Escaping `Python::with_gil` or crossing OS threads (`!Send`). |
| **`Py<T>`** | Sealed Specimen Case | Storing inside `'static` structs and sending over `mpsc`. | Calling Python methods without first acquiring the GIL. |

## 🔑 3. Core Mechanics & Step-by-Step Derivation

### 3.1 Why `pyo3::prepare_freethreaded_python()` Is Mandatory in Binary Crates

When building a Python extension module (`maturin`), the `python` executable starts first and loads your Rust `.so`/`.pyd` library. In `ai-workflow-gui`, **Cargo builds a standalone native binary (`main.rs`)**. Without calling `pyo3::prepare_freethreaded_python()` once at startup, CPython's internal interpreter state is uninitialized, or its main thread holds the GIL forever and starves background Rust worker threads.

### 3.2 The Exact Lifecycle of `Bound<'py, T>` vs `Py<T>`

In PyO3 `0.22+` (the modern `Bound` API that replaced the legacy `&'py PyAny` GIL-refs), every Python pointer exists in one of two states:

| State | Rust Type | Lifetime Parameter? | Implements `Send + Sync`? | How to Transition to the Other State |
| :--- | :--- | :--- | :--- | :--- |
| **GIL-Attached** | `Bound<'py, T>` | **YES (`'py`)** | ❌ **NO** (`!Send + !Sync`) | Call `bound_obj.unbind()` → yields owned `Py<T>` (`0` refcnt change). |
| **GIL-Detached** | `Py<T>` | **NO (`'static`)** | ✅ **YES** (`Send + Sync`) | Call `py_obj.bind(py)` → yields `&Bound<'py, T>` (`0` refcnt change). |

Notice the performance gem: **both `.unbind()` and `.bind(py)` are zero-cost pointer reinterpretations ($\mathcal{O}(1)$, zero `ob_refcnt` traffic)!**
- `bound_obj.unbind()` consumes the `Bound<'py, T>` by value and transfers its existing `+1` strong reference count directly into `Py<T>`.
- `py_obj.bind(py)` borrows `&self` on `Py<T>` and borrows `py: Python<'py>`, returning a reference `&Bound<'py, T>` without incrementing `ob_refcnt`.

### 3.3 Crossing the Data Boundary: `IntoPyObject` vs `.extract::<T>()`

| Direction | Trait / Method | What Happens in Memory | When It Fails |
| :--- | :--- | :--- | :--- |
| **Rust → Python** | `val.into_pyobject(py)?` | Allocates a new CPython `PyObject` (e.g. `PyUnicode`, `PyLong`, `PyList`) and copies the Rust bytes into it. | Only on out-of-memory or invalid UTF-8/overflow. |
| **Python → Rust (Copy)** | `bound_any.extract::<T>()?` | Verifies the Python runtime type (`ob_type`) and copies the payload into a native Rust `String`, `Vec<T>`, or primitive. | Returns `Err(PyTypeError)` if Python holds the wrong type! |
| **Python → Rust (Downcast)** | `bound_any.downcast::<PyDict>()?` | Zero-copy pointer check (`PyDict_Check`) casting `&Bound<'py, PyAny>` to `&Bound<'py, PyDict>`. | Returns `Err(DowncastError)` if not a `dict`. |

## 🔬 4. Visual Invariant Models & Memory Layouts

*How to read this:* Trace the 8-byte pointer from the Rust stack (`Bound<'py, PyDict>` vs `Py<PyDict>`) across the FFI boundary to the 48-byte `PyDictObject` living on the CPython heap.

```text
Title: Memory Layout & Reference Count Lifecycle of Bound<'py, T> vs Py<T>

RUST WORKER THREAD STACK                        CPYTHON 3.13+ MANAGED HEAP
┌─────────────────────────────────────────┐     ┌────────────────────────────────────────┐
│ 1. Inside Python::with_gil(|py| { ... })│     │ PyDictObject (Address: 0x7f8a_1000)    │
│                                         │     ├────────────────────────────────────────┤
│   py: Python<'py> (Size: 0 bytes, ZST)  │     │ ob_refcnt : usize = 1                  │
│                                         │     │ ob_type   : *mut PyTypeObject (&PyDict)│
│   dict_bound: Bound<'py, PyDict>        │     │ ma_used   : isize = 2                  │
│   ┌───────────────────────┐             │     │ ma_keys   : *mut PyDictKeysObject      │
│   │ ptr: 0x7f8a_1000 ─────┼─────────────┼────►│   • "role"    -> "assistant"           │
│   │ _marker: PhantomData  │             │     │   • "content" -> "Hello Piyush"        │
│   └───────────┬───────────┘             │     └───────────────────▲────────────────────┘
│               │ .unbind()               │                         │
│               ▼ (Moves +1 refcnt, 0B)   │                         │
│ 2. Stored in Struct Outside with_gil:   │                         │
│   dict_detached: Py<PyDict>             │                         │
│   ┌───────────────────────┐             │                         │
│   │ ptr: 0x7f8a_1000 ─────┼─────────────┼─────────────────────────┘
│   └───────────────────────┘             │     (When Py<PyDict> finally drops, PyO3
│   • Implements Send + Sync ('static)    │      re-acquires GIL to run Py_DECREF -> 0)
└─────────────────────────────────────────┘
```

| Operation | Stack Bytes Copied | CPython `ob_refcnt` Delta | Requires `py: Python<'py>`? |
| :--- | :--- | :--- | :--- |
| **`let b2 = b1.clone();` (`Bound`)** | `8 bytes` | `+1` (`Py_INCREF` — fast, GIL already held) | Implicitly held by `'py` |
| **`let p: Py<T> = b1.unbind();`** | `8 bytes` (move) | `0` (ownership transferred without C-API call) | Implicitly held by `'py` |
| **`let b_ref: &Bound<'py, T> = p.bind(py);`** | `0 bytes` (borrow) | `0` (zero-cost reference transmutation) | **YES** (`py` passed explicitly) |
| **`let p2 = p.clone_ref(py);` (`Py<T>`)** | `8 bytes` | `+1` (`Py_INCREF` under `py`) | **YES** (`py` passed explicitly) |

## ⚖️ 5. Universal Invariant & Operations Matrix

The fundamental pointer selection law in PyO3 separates transient local execution from persistent cross-turn or cross-thread storage:

$$\text{Scope} = \text{Inside \texttt{Python::with\_gil}} \implies \text{Use \texttt{Bound<'py, T>}} \quad \big| \quad \text{Scope} = \text{Struct Field or Cross-Thread} \implies \text{Use \texttt{Py<T>} (\texttt{.unbind()})}$$

| Rust Type / Method | Lifetime Bound | `Send` + `Sync`? | Can Call Python Methods Directly? | Primary Use in Cold Wind GUI |
| :--- | :--- | :--- | :--- | :--- |
| **`Python<'py>`** | Scoped to closure `'py` | ❌ **NO** | N/A (`py.import()`, `py.eval()`) | Proves GIL ownership on the background worker thread. |
| **`Bound<'py, PyAny>`** | Scoped to `'py` | ❌ **NO** | ✅ **YES** (`.call_method1()`, `.getattr()`) | Inspecting turn outputs, manipulating `sys.path` and `PyDict`. |
| **`&Bound<'py, T>`** | Borrowed inside `'py` | ❌ **NO** | ✅ **YES** (via `Deref` / `PyAnyMethods`) | Zero-cost handle returned by `stored_py.bind(py)`. |
| **`Py<PyAny>` (`PyObject`)** | `'static` (Unbound) | ✅ **YES** | ❌ **NO** (must call `.bind(py)` first) | Storing `HeadlessEngineAdapter` across turns in `EngineWorker`. |

## 🛠️ 6. Production Blueprint & Code Patterns

| Blueprint Component | Purpose | Key Safety Guarantee |
| :--- | :--- | :--- |
| **`EngineHandle` Struct** | Holds the long-lived `coldwind-core` Python adapter inside Rust memory. | Uses `Py<PyAny>` so `EngineHandle` is `'static` and `Send`. |
| **`boot_and_inspect()`** | Initializes CPython and extracts typed configuration from `CoreSettinngs`. | Converts Python `str`/`int` to owned Rust `String`/`usize` before dropping GIL. |

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

/// Holds a persistent reference to a Python object across multiple turns
pub struct EngineHandle {
    // Py<PyAny> has no 'py lifetime and implements Send + Sync
    adapter_obj: Py<PyAny>,
}

impl EngineHandle {
    /// Boots CPython, creates a Python dict/object, and unbinds it for storage
    pub fn initialize() -> PyResult<Self> {
        pyo3::prepare_freethreaded_python();

        let adapter_obj = Python::with_gil(|py| -> PyResult<Py<PyAny>> {
            // Bound<'py, PyDict> is tied to this closure's 'py token
            let config_dict: Bound<'_, PyDict> = PyDict::new(py);
            config_dict.set_item("platform", "slint-desktop")?;
            config_dict.set_item("max_retries", 3)?;

            // Unbind strips 'py so the handle can be stored in EngineHandle
            Ok(config_dict.into_any().unbind())
        })?;

        Ok(Self { adapter_obj })
    }

    /// Re-acquires the GIL on a later turn, binds the stored handle, and reads a key
    pub fn read_platform_name(&self) -> PyResult<String> {
        Python::with_gil(|py| {
            // Zero-cost bind: &Py<PyAny> + Python<'py> -> &Bound<'py, PyAny>
            let bound_any: &Bound<'_, PyAny> = self.adapter_obj.bind(py);
            let bound_dict: &Bound<'_, PyDict> = bound_any.downcast::<PyDict>()?;

            // get_item returns PyResult<Option<Bound<'py, PyAny>>>
            let item = bound_dict
                .get_item("platform")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'platform'"))?;

            item.extract::<String>()
        })
    }
}
```

## ⚠️ 7. Learner Pitfall Archive

| # | Pitfall Name | What Was Written | Exact Compiler / Runtime Error | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **The Escaping `Bound<'py, T>` Trap** | `Python::with_gil(\|py\| py.import("sys"))` returning `Bound<'py, PyModule>` | `error[E0597]: py does not live long enough` | Call `.unbind()` inside `with_gil` to return `Py<PyModule>`, or `.extract::<T>()` to return a Rust value. |
| **2** | **The Unbound Method Call Trap** | Calling `self.adapter_obj.call_method0("step")` directly on `Py<PyAny>` | `error[E0599]: no method named call_method0 found for struct Py` | In PyO3 0.22+, methods live on `Bound<'py, T>`. Call `self.adapter_obj.bind(py).call_method0("step")`! |
| **3** | **The Missing `PyAnyMethods` Prelude Trap** | Importing only `use pyo3::Bound;` and calling `.getattr()` or `.extract()` | `error[E0599]: no method named getattr found for struct Bound` | Always import `use pyo3::prelude::*;` so `PyAnyMethods` trait is in lexical scope (`learn_rust` Topic 07 rule!). |

## ✅ 8. Checkpoint & Pass Criteria

Verify your mastery of Subdomain 01 by predicting the exact compiler outcome of each line below before moving to Subdomain 02:

| Test Case | Snippet Under Test | Compiles? | Reason & Invariant |
| :--- | :--- | :--- | :--- |
| **Case A** | `struct Worker { obj: Bound<'static, PyAny> }` | ❌ **NO** | `'py` can never be `'static` because the GIL is scoped to a temporary `with_gil` closure. Use `Py<PyAny>`. |
| **Case B** | `let p: Py<PyList> = Python::with_gil(\|py\| Ok(PyList::empty(py).unbind()))?;` | ✅ **YES** | `.unbind()` detaches the `Bound<'py, PyList>` into a `'static` `Py<PyList>` before the closure exits. |
| **Case C** | `let val: i32 = Python::with_gil(\|py\| py.eval("40 + 2", None, None)?.extract())?;` | ✅ **YES** | `.extract::<i32>()` copies the integer onto the Rust stack before `'py` ends. |

## 🎯 9. Core Systems Invariants & Reading Path

| Invariant # | Statement | Next Step in Reading Path |
| :--- | :--- | :--- |
| **1. The Token Law** | Zero CPython heap access occurs without an active `py: Python<'py>` token on the current OS thread. | Review [`./cheat_sheet.md`](./cheat_sheet.md) for 30-second recall. |
| **2. The `.unbind()` Boundary** | `Bound<'py, T>` is for active work; `Py<T>` is for storage and thread transport. | Proceed to [`../02_rust_driving_python/README.md`](../02_rust_driving_python/README.md). |
| **3. The Trait Prelude Law** | All `Bound<'py, T>` methods (`.call0()`, `.getattr()`, `.extract()`) live on traits in `pyo3::prelude::*`. | Apply in [`../02_rust_driving_python/cheat_sheet.md`](../02_rust_driving_python/cheat_sheet.md). |