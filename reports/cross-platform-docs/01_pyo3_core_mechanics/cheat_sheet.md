# 🧩 PyO3 Core Mechanics & GIL Lifetime Cheat Sheet & 30-Second Invariants

| Field | Value |
| :--- | :--- |
| **Tier** | `1 — Subdomain War Chest (C1–C12)` · per `cheatsheet_for_cheatsheet.md` |
| **Domain** | `shared` / `core` (`cross-platform-docs/01_pyo3_core_mechanics`) |
| **Verified** | `2026-10-22` — verified against PyO3 0.22+ `Bound<'py, T>` API & `PyAnyMethods` trait |
| **Confidence** | `VERIFIED ✅` |

> **TL;DR:** Use `Bound<'py, T>` inside `Python::with_gil(|py| ...)` for all active method calls and type extractions; call `.unbind()` to convert it into `Py<T>` whenever a handle must live in a Rust struct or cross threads, and `.bind(py)` to reactivate it later.
> **Primary Objective:** Within 30 seconds, choose between `Bound<'py, T>` and `Py<T>`, acquire the GIL safely, and convert between Rust and Python types without lifetime (`E0597`) or thread-safety (`E0277`) errors.
> **Master Guide:** [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) · **Concept Guide:** [`./README.md`](./README.md) · **Next War Chest:** [`../02_rust_driving_python/cheat_sheet.md`](../02_rust_driving_python/cheat_sheet.md)

## 📺 1. Curated Learning Sources

| Source | Why This Source | Verification |
| :--- | :--- | :--- |
| [PyO3 Memory Management — `Bound<'py, T>` vs `Py<T>`](https://pyo3.rs/main/memory.html) | Authoritative breakdown of GIL-bound lifetimes, `.bind(py)`, `.unbind()`, and reference counts. | `VERIFIED ✅` |
| [PyO3 Type Conversion Tables](https://pyo3.rs/main/conversions/tables.html) | Exact Rust ↔ Python type mappings (`String`, `Vec<T>`, `HashMap<K,V>`, `Option<T>`). | `VERIFIED ✅` |
| [PyO3 `0.21 -> 0.22` Migration Guide (`Bound` API)](https://pyo3.rs/main/migration.html) | Explains why legacy `&'py PyAny` was replaced by smart pointer `Bound<'py, PyAny>`. | `VERIFIED ✅` |
| [`./README.md`](./README.md) | Subdomain 01 full derivation, cleanroom metaphors, and memory diagrams. | `VERIFIED ✅` |

## 🧭 2. 30-Second Decision Tree

Select the exact smart pointer and conversion method based on where the Python object lives and what you need from it.

```text
Title: PyO3 Pointer & Conversion Router (Bound<'py, T> vs Py<T> vs Rust Native)

What do you need to do with the Python value right now?
├─ 1. Call methods, read attributes, or index items inside Python::with_gil(|py| ...)?
│  └─ Use Bound<'py, T> (or &Bound<'py, T>)
│     • Import `use pyo3::prelude::*;` to unlock `PyAnyMethods`
│     • Zero extra refcount traffic when borrowed via `.bind(py)`
│
├─ 2. Store the Python object in a Rust struct or send it over an mpsc::channel?
│  └─ Call `bound_obj.unbind()` ──► produces `Py<T>` ('static, Send + Sync)
│     • To use later: `Python::with_gil(|py| { let b = stored.bind(py); ... })`
│
├─ 3. Convert a Python object into an owned Rust value (`String`, `i64`, `Vec<T>`)?
│  └─ Call `bound_obj.extract::<RustType>()?`
│     • Validates Python runtime type; returns `Err(PyTypeError)` on mismatch
│
└─ 4. Narrow `Bound<'py, PyAny>` to a concrete Python type (`PyDict`, `PyList`) without copying?
   └─ Call `bound_any.downcast::<PyDict>()?` (zero-copy pointer check)
```

| Goal | Starting Type | Method to Call | Resulting Type | Cost |
| :--- | :--- | :--- | :--- | :--- |
| **Detach from GIL scope** | `Bound<'py, T>` | `.unbind()` | `Py<T>` (`Send + Sync`) | $\mathcal{O}(1)$ (`0` refcnt ops) |
| **Re-attach to GIL scope** | `Py<T>` | `.bind(py)` | `&Bound<'py, T>` | $\mathcal{O}(1)$ (`0` refcnt ops) |
| **Clone inside GIL** | `Bound<'py, T>` | `.clone()` | `Bound<'py, T>` | $\mathcal{O}(1)$ (`Py_INCREF`) |
| **Clone detached handle** | `Py<T>` | `.clone_ref(py)` | `Py<T>` | $\mathcal{O}(1)$ (`Py_INCREF`) |
| **Copy to Rust native** | `Bound<'py, PyAny>` | `.extract::<T>()?` | `T` (e.g. `String`, `Vec<i32>`) | $\mathcal{O}(N)$ byte copy |

## ⚖️ 3. Invariant & Operations Matrix

Every PyO3 pointer obeys the GIL Attachment Bifurcation Law:

$$\text{Pointer} = \texttt{Bound<'py, T>} \implies \text{Callable + \texttt{!Send} (Locked to \texttt{'py})} \quad \big| \quad \text{Pointer} = \texttt{Py<T>} \implies \text{Storable + \texttt{Send + Sync} (Inert Until \texttt{.bind(py)})}$$

| Type / Operation | Holds GIL (`'py`)? | `Send + Sync`? | Aliasing Allowed? | Mutation Allowed? | Drop Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`Python<'py>`** | **YES** | ❌ **NO** | `Copy` on same thread | N/A (Token) | Releases GIL when `with_gil` exits |
| **`Bound<'py, T>`** | **YES** | ❌ **NO** | Shared (`Clone` bumps refcnt) | Mutates Python heap | Immediate `Py_DECREF` under `'py` |
| **`&Bound<'py, T>`** | **YES** | ❌ **NO** | Shared Rust borrow (`&`) | Mutates Python heap | Zero-cost (no `Py_DECREF` on drop) |
| **`Py<T>`** | **NO** | ✅ **YES** | Shared via `.clone_ref(py)` | Only after `.bind(py)` | Acquires GIL if needed to `Py_DECREF` |

## 🐍 4. Python & `learn_rust` Bridge Delta

| PyO3 Mechanism | CPython 3.13+ Runtime Reality | Rust Compile-Time Reality | Owning `learn_rust` Topic |
| :--- | :--- | :--- | :--- |
| **`Python<'py>` Lifetime** | `PyGILState_Ensure()` locks a global C mutex; forgetting to release it deadlocks all threads. | `Python::with_gil` scopes the lock to closure lifetime `'py` and releases it via RAII on unwind or return. | **Topic 01:** Lifetimes (`'a`) & RAII Scope Drop |
| **`Bound<'py, T>` Cloning** | Every Python assignment (`y = x`) increments `ob_refcnt` by 1 under the GIL. | `bound.clone()` calls `Py_INCREF` without locking overhead because `'py` proves the GIL is already held. | **Topic 06:** `Rc::clone` Pointer Copying |
| **`PyAnyMethods` Trait** | Every `PyObject` has a C `ob_type` vtable scanned at runtime (`PyObject_GetAttrString`). | Methods on `Bound<'py, T>` are exposed via the `PyAnyMethods` extension trait imported by `pyo3::prelude::*`. | **Topic 03 & 07:** Extension Traits & Preludes |
| **`Option<T>` ↔ `None`** | Any Python variable can silently be `None` (`NoneType`), causing runtime `AttributeError`. | `.extract::<Option<String>>()?` maps Python `None` to `Ok(None)` and `str` to `Ok(Some(String))`. | **Topic 02 & 04:** `Option<T>` & `Result<T, E>` |

## 🧠 5. Physical Metaphor Register

| Mechanism | Physical Metaphor | 1:1 Mapping to Code |
| :--- | :--- | :--- |
| **`pyo3::prepare_freethreaded_python()`** | **Turning on the Building Main Breaker** | Flipping the master power switch in `main()` so worker threads can plug into wall outlets later. |
| **`Python::with_gil(\|py\| ...)`** | **Badging into the Pressurized Cleanroom** | Only one worker can enter the cleanroom at a time; `py` is the badge proving you are inside. |
| **`Bound<'py, T>` vs `Py<T>`** | **Corded Wall Drill vs Unplugged Briefcase Drill** | `Bound<'py, T>` is plugged into `'py` and ready to drill; `.unbind()` unplugs it into `Py<T>` so you can store or carry it. |
| **`.downcast::<PyDict>()?`** | **Checking the Label on a Closed Box** | Inspects the `ob_type` pointer in $\mathcal{O}(1)$ time without unpacking or copying the dictionary contents. |

## 🛠️ 6. Syntax Bank

| Snippet # | Pattern | Key Methods Demonstrated |
| :--- | :--- | :--- |
| **1** | **Boot & GIL Scope** | `prepare_freethreaded_python()`, `Python::with_gil`, `py.import()` |
| **2** | **Struct Storage (`Py<T>`)** | `.unbind()`, `.bind(py)`, `.clone_ref(py)` |
| **3** | **Type Marshalling** | `PyDict::new(py)`, `.set_item()`, `.get_item()`, `.extract::<Option<T>>()` |

### 1. Booting Embedded Python & Acquiring `Python<'py>`
```rust
use pyo3::prelude::*;

pub fn verify_python_runtime() -> PyResult<String> {
    // Call once at binary startup before spawning worker threads:
    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py: Python<'_>| {
        let sys: Bound<'_, PyModule> = py.import("sys")?;
        let version: String = sys.getattr("version")?.extract()?;
        Ok(version) // Owned Rust String safely escapes 'py!
    })
}
```

### 2. Storing `Py<T>` in a Struct & Re-binding via `.bind(py)`
```rust
use pyo3::prelude::*;
use pyo3::types::PyList;

pub struct TokenHistory {
    // Detached handle: no 'py lifetime, safe to store in structs!
    py_list: Py<PyList>,
}

impl TokenHistory {
    pub fn new() -> PyResult<Self> {
        Python::with_gil(|py| {
            let bound = PyList::empty(py);
            Ok(Self { py_list: bound.unbind() })
        })
    }

    pub fn push_token(&self, token: &str) -> PyResult<usize> {
        Python::with_gil(|py| {
            let bound: &Bound<'_, PyList> = self.py_list.bind(py);
            bound.append(token)?;
            Ok(bound.len())
        })
    }
}
```

### 3. Safe `Option<T>` & Collection Extraction
```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

pub fn parse_agent_metadata(raw_dict: &Bound<'_, PyDict>) -> PyResult<(Option<String>, HashMap<String, i64>)> {
    // Python None -> Ok(None); Python str -> Ok(Some(String))
    let model_name: Option<String> = match raw_dict.get_item("model")? {
        Some(val) => val.extract::<Option<String>>()?,
        None => None,
    };
    let counts: HashMap<String, i64> = raw_dict.get_item("counts")?
        .map(|v| v.extract())
        .transpose()?
        .unwrap_or_default();
    Ok((model_name, counts))
}
```

## 🔬 7. Visual Memory Model

*How to read this:* Follow the transition from left to right as a `PyObject` pointer moves from an active `Bound<'py, T>` inside `with_gil` to a detached `Py<T>` inside a Rust struct, and back via `.bind(py)`.

```text
Title: Pointer State Machine Across GIL Scopes (with_gil #1 -> Struct Storage -> with_gil #2)

  [Python::with_gil #1]                  [Between Turns (No GIL)]             [Python::with_gil #2]
┌────────────────────────┐              ┌────────────────────────┐          ┌────────────────────────┐
│ Bound<'py1, PyDict>    │  .unbind()   │ struct EngineWorker {  │ .bind(py)│ &Bound<'py2, PyDict>   │
│  • 8B NonNull<PyObject>├─────────────►│   state: Py<PyDict>    ├─────────►│  • Tied to new 'py2    │
│  • !Send (Tied to 'py1)│  (0 refcnt)  │ }                      │(0 refcnt)│  • Full PyDictMethods  │
└────────────────────────┘              │  • Send + Sync         │          └────────────────────────┘
                                        │  • Cannot call methods │
                                        └────────────────────────┘
```

| Rust Type | Python Equivalent | `size_of::<T>()` | Can Outlive `with_gil`? |
| :--- | :--- | :--- | :--- |
| **`Bound<'py, PyAny>`** | Local variable inside active thread | `8 bytes` | ❌ **NO** |
| **`Py<PyAny>`** | Heap reference stored on an object | `8 bytes` | ✅ **YES** |
| **`Option<Bound<'py, PyAny>>`** | Nullable `PyObject*` (Null-pointer optimized!) | `8 bytes` | ❌ **NO** |
| **`Option<Py<PyAny>>`** | Nullable stored `PyObject*` (NPO optimized!) | `8 bytes` | ✅ **YES** |

## 🛡️ 8. Compiler Diagnostics Table

| Exact Diagnostic / Error | Rule Violated | Runtime Bug Prevented | Python Equivalent of the Bug |
| :--- | :--- | :--- | :--- |
| **`error[E0597]: `py` does not live long enough`** | Tried to return `Bound<'py, T>` from `Python::with_gil` | Dereferencing a Python pointer after releasing the GIL | Segfault in C extension after `Py_END_ALLOW_THREADS` |
| **`error[E0277]: `Bound<'_, PyAny>` cannot be sent between threads safely`** | Captured `Bound<'py, T>` in `std::thread::spawn` closure | Concurrent unsynchronized refcount mutation across OS threads | Race condition corrupting `ob_refcnt` without GIL |
| **`error[E0599]: no method named `getattr` found for struct `Py<T>`** | Called a `PyAnyMethods` method on detached `Py<T>` | Inspecting Python object attributes without holding the GIL | Calling `PyObject_GetAttr` from an unattached C thread |
| **`error[E0599]: no method named `extract` found for struct `Bound`** | Missing `use pyo3::prelude::*;` (`PyAnyMethods` not in scope) | Unresolved trait method dispatch | Calling a method from an unimported mixin |

## ⚠️ 9. Trap Archive (3-part form)

| # | Trap Name | Assumed | Reality | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Returning `Bound<'py, T>` from `with_gil`** | `Python::with_gil(\|py\| py.import("os"))` can return the module directly. | `Bound<'py, PyModule>` is tied to the closure's `'py` token and cannot escape it (`E0597`). | Call `.unbind()` inside `with_gil` to return `Py<PyModule>`. |
| **2** | **Cloning `Py<T>` with `.clone()`** | `my_py_handle.clone()` works outside `Python::with_gil` without a GIL token. | `Py<T>` does not implement `Clone` without GIL context (or requires `clone_ref(py)`) so refcounts stay safe. | Call `my_py_handle.clone_ref(py)` inside `Python::with_gil`. |
| **3** | **Using `.extract::<PyDict>()` Instead of `.downcast()`** | `.extract::<Bound<'py, PyDict>>()` is the fastest way to cast `&Bound<'py, PyAny>`. | `.downcast::<PyDict>()?` returns a direct `&Bound<'py, PyDict>` reference with zero refcount increment. | Use `.downcast::<PyDict>()?` for PyO3 types and `.extract::<T>()?` for Rust types. |

### Trap 1: Returning `Bound<'py, T>` from `Python::with_gil`
- **Assumed:** You can return `Bound<'py, PyAny>` from `Python::with_gil(|py| ...)` and use it in the next line of Rust code.
- **Reality:** The lifetime `'py` ends at the closing brace of `Python::with_gil`, releasing the GIL; `rustc` rejects the return with `error[E0597]`.
- **10-Second Recall Fix:** Either `.extract::<RustType>()?` inside the closure or call `.unbind()` to return `Py<PyAny>`.

### Trap 2: Calling Methods Directly on `Py<T>`
- **Assumed:** Once you have `adapter: Py<PyAny>`, you can call `adapter.call_method0("run")` directly.
- **Reality:** `Py<T>` is an inert storage handle with no active GIL token; all object operations live on `Bound<'py, T>`.
- **10-Second Recall Fix:** Enter `Python::with_gil(|py| adapter.bind(py).call_method0("run"))`.

### Trap 3: Missing `use pyo3::prelude::*;`
- **Assumed:** Importing `use pyo3::{Python, Bound};` is enough to call `.import()`, `.getattr()`, and `.extract()`.
- **Reality:** PyO3 `0.22+` places methods on extension traits (`PyAnyMethods`, `PyListMethods`, `PyDictMethods`) re-exported in `pyo3::prelude::*`.
- **10-Second Recall Fix:** Always start every PyO3 file with `use pyo3::prelude::*;`.

## ⏳ 10. Deferred Concepts (Manifest Boundary)

| Concept / Syntax | Manifest Status & Marker | What It Unlocks |
| :--- | :--- | :--- |
| **Raw FFI Pointers (`*mut pyo3::ffi::PyObject`)** | `⏳ Deferred until Topic 10 & Topic 12 (unsafe)` | Direct CPython C-API calls (`PyList_GET_ITEM`) bypassing bounds checks. |
| **Zero-Copy Buffer Protocol (`PyBuffer<f32>`)** | `⏳ Deferred until Topic 10 (FFI & PyO3)` | Reading NumPy arrays or image tensors in Rust as `&[f32]` slices without copying. |

## 📈 11. Family Learning Progression

```text
Title: Subdomain 01 Internal Progression

[1. prepare_freethreaded_python + with_gil] ──► [2. Bound<'py, T> vs Py<T> (.unbind/.bind)] ──► [3. .extract() vs .downcast()]
```

| Order | Concept Milestone | Why Learn It Here |
| :--- | :--- | :--- |
| **1** | **GIL Token (`Python<'py>`)** | Every single PyO3 call requires acquiring `py` first. |
| **2** | **`Bound<'py, T>` ↔ `Py<T>`** | Needed immediately in Subdomain 02 to store `ChatInitializer` / `HeadlessEngineAdapter` across turns. |
| **3** | **`.extract::<T>()` & `.downcast::<T>()`** | Needed to convert Python state dicts and strings back into Rust types. |

## 📎 12. Concept Notes & Study Reports Directory

| Document | Relative Path | Scope & Invariants Covered | Status |
| :--- | :--- | :--- | :--- |
| **Subdomain 01 Concept Guide** | [`./README.md`](./README.md) | Full derivation of `Python<'py>`, `Bound<'py, T>`, `Py<T>`, and memory layout traces. | `🟢 Complete` |
| **Parent Architecture Report** | [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) | System-wide 4 hazards, sequence diagrams, and decoupled adapter specification. | `🟢 Complete` |
| **Root Master War Chest** | [`../cheat_sheet.md`](../cheat_sheet.md) | Cross-cutting quick reference across all 4 subdomains. | `🟢 Complete` |
| **Subdomain 02 War Chest** | [`../02_rust_driving_python/cheat_sheet.md`](../02_rust_driving_python/cheat_sheet.md) | Next step: importing `coldwind-core`, `call_method1`, and `PyErr` handling. | `🟢 Complete` |