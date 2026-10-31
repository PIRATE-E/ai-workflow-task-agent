# 🧩 Rust Driving Python (Execution Engine) Cheat Sheet & 30-Second Invariants

| Field | Value |
| :--- | :--- |
| **Tier** | `1 — Subdomain War Chest (C1–C12)` · per `cheatsheet_for_cheatsheet.md` |
| **Domain** | `shared` / `core` (`cross-platform-docs/02_rust_driving_python`) |
| **Verified** | `2026-10-22` — verified against PyO3 0.22+ `PyAnyMethods`, `PyDictMethods`, and `coldwind-core` |
| **Confidence** | `VERIFIED ✅` |

> **TL;DR:** Configure `sys.path` once at worker startup, use `call0` / `call_method0` for zero-argument calls, use `call1` / `call_method1` with a Rust tuple (`(arg,)` for 1 arg!) for positional calls, and always format `PyErr` with `err.traceback(py)` instead of calling `.unwrap()`.
> **Primary Objective:** Within 30 seconds, write the exact PyO3 call syntax to import `coldwind-core` modules, instantiate Python classes, pass positional or keyword arguments, and extract formatted Python tracebacks.
> **Master Guide:** [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) · **Concept Guide:** [`./README.md`](./README.md) · **Prev War Chest:** [`../01_pyo3_core_mechanics/cheat_sheet.md`](../01_pyo3_core_mechanics/cheat_sheet.md) · **Next War Chest:** [`../03_python_driving_rust/cheat_sheet.md`](../03_python_driving_rust/cheat_sheet.md)

## 📺 1. Curated Learning Sources

| Source | Why This Source | Verification |
| :--- | :--- | :--- |
| [PyO3 Guide — Calling Python Functions](https://pyo3.rs/main/function.html#calling-python-functions-in-rust) | Complete matrix of `call0`, `call1`, `call`, `call_method0`, `call_method1`, and `call_method`. | `VERIFIED ✅` |
| [PyO3 Guide — Python Exceptions (`PyErr` & `PyTraceback`)](https://pyo3.rs/main/exception.html) | Official patterns for catching, inspecting, and formatting Python exceptions in Rust. | `VERIFIED ✅` |
| [`../../urgent_development/platform-integration-spec.md`](../../urgent_development/platform-integration-spec.md) | Cold Wind AI `HeadlessEngineAdapter` contract replacing blocking `ChatInitializer.run_chat()`. | `VERIFIED ✅` |
| [`./README.md`](./README.md) | Subdomain 02 deep dive on `uv` workspace `sys.path` bootstrapping and call mechanics. | `VERIFIED ✅` |

## 🧭 2. 30-Second Decision Tree

Route any Rust-to-Python invocation to its exact zero-overhead `PyAnyMethods` call signature.

```text
Title: Invoking Python Callables & Methods from Rust (PyO3 0.22+ Bound API)

How are you invoking the Python callable or object method?
├─ 1. Zero arguments (e.g., `ChatInitializer()` or `ctx.is_exiting()`)
│  ├─ Standalone class/function ──► `cls.call0()?` (Fastest: vectorcall, 0 tuple alloc)
│  └─ Method on an object ────────► `obj.call_method0("is_exiting")?`
│
├─ 2. Positional arguments only (e.g., `adapter.execute_turn(prompt)`)
│  ├─ 1 positional argument ──────► `obj.call_method1("execute_turn", (prompt,))?` (TRAILING COMMA!)
│  └─ N positional arguments ─────► `obj.call_method1("step", (arg1, arg2, arg3))?`
│
├─ 3. Keyword arguments (`**kwargs`) or mixed positional + keyword args
│  ├─ Build kwargs dict first ────► `let kw = PyDict::new(py); kw.set_item("stream", true)?;`
│  └─ Invoke with `Some(&kw)` ────► `obj.call_method("step", (prompt,), Some(&kw))?`
│
└─ 4. Handling the returned `PyResult<Bound<'py, PyAny>>`:
   ├─ Convert to Rust value ──────► `.and_then(|res| res.extract::<String>())`
   └─ Format Python traceback ────► `.map_err(|e| format_py_err(py, e))`
```

| Python Call Shape | Exact PyO3 Method on `Bound<'py, PyAny>` | Argument Type Required | Allocates `PyTuple`? |
| :--- | :--- | :--- | :--- |
| **`func()`** | `func.call0()?` | None | ❌ **NO** |
| **`func(a)`** | `func.call1((a,))?` | 1-Tuple `(A,)` | ✅ **YES** |
| **`func(a, b)`** | `func.call1((a, b))?` | 2-Tuple `(A, B)` | ✅ **YES** |
| **`obj.m()`** | `obj.call_method0("m")?` | `&str` method name | ❌ **NO** |
| **`obj.m(a)`** | `obj.call_method1("m", (a,))?` | `&str` + 1-Tuple `(A,)` | ✅ **YES** |
| **`obj.m(a, k=v)`** | `obj.call_method("m", (a,), Some(&kw_dict))?` | `&str` + Tuple + `Option<&Bound<'py, PyDict>>` | ✅ **YES** |

## ⚖️ 3. Invariant & Operations Matrix

Every dynamic Python call from Rust obeys the Tuple Packing & Exception Value Invariant:

$$\text{Positional Args} \implies \text{Must Implement \texttt{IntoPyObject} as Rust Tuple \texttt{(T1, ...)}} \quad \big| \quad \text{Python \texttt{raise}} \implies \text{Returns \texttt{Err(PyErr)} (Never Panics)}$$

| Operation | Method Signature | Borrows or Consumes Receiver? | Mutates Python State? | Failure Mode (`Err(PyErr)`) |
| :--- | :--- | :--- | :--- | :--- |
| **Module Import** | `py.import("pkg.mod")?` | Borrows `py: Python<'py>` | Loads into `sys.modules` | `ModuleNotFoundError` / `SyntaxError` |
| **Attribute Read** | `obj.getattr("field")?` | Borrows `&Bound<'py, PyAny>` | May run `@property` getter | `AttributeError` |
| **Attribute Write** | `obj.setattr("field", val)?` | Borrows `&Bound<'py, PyAny>` | Mutates `obj.__dict__` | `AttributeError` / `TypeError` |
| **Dict Lookup** | `dict.get_item("key")?` | Borrows `&Bound<'py, PyDict>` | Read-only (`Option<Bound>`) | Only if key hash fails (`TypeError`) |
| **Method Call** | `obj.call_method1("m", (a,))?` | Borrows `&Bound<'py, PyAny>` | Arbitrary Python execution | Any exception raised inside `m()` |

## 🐍 4. Python & `learn_rust` Bridge Delta

| Mechanism | CPython 3.13+ Runtime Reality | Rust + PyO3 Reality | Owning `learn_rust` Topic |
| :--- | :--- | :--- | :--- |
| **Variadic Args (`*args`)** | Python functions accept arbitrary positional args packed into a `PyTupleObject`. | Rust has no variadic functions; PyO3 implements `PyCallArgs` for Rust tuples up to 12 elements `(T1, ..., T12)`. | **Topic 02 & 03:** Tuples + Trait Implementations |
| **Keyword Args (`**kwargs`)** | Python packs named arguments into a `PyDictObject` at the call site. | Rust has no named function arguments; you explicitly construct `PyDict::new(py)` and pass `Some(&kwargs)`. | **Topic 05:** `HashMap` / Key-Value Builders |
| **Exception Propagation** | Uncaught exceptions unwind bytecode frames up to the top-level interpreter loop. | PyO3 catches C `NULL` returns at the FFI edge and converts them into `Result<Bound<'py, PyAny>, PyErr>` for `?`. | **Topic 04:** `Result<T, E>` & `?` Operator |
| **Package Discovery** | `uv run` injects `.venv` and `.pth` workspace roots automatically. | Embedded CPython starts bare; Rust must append `.venv/.../site-packages` and `core/src` to `sys.path`. | **Topic 07:** Workspaces & Path Resolution |

## 🧠 5. Physical Metaphor Register

| Mechanism | Physical Metaphor | 1:1 Mapping to Code |
| :--- | :--- | :--- |
| **`(arg,)` 1-Tuple Syntax** | **The Single-Box Forklift Pallet** | The loading dock (`call1`) only accepts forklift pallets (tuples). Putting parentheses `(arg)` without a comma is just wrapping tape around the box; adding the comma `(arg,)` places it on a pallet. |
| **`sys.path.append(...)`** | **Handing the GPS Address Book to a New Driver** | The embedded Python interpreter just woke up inside a Rust binary and doesn't know where `coldwind-core` lives on disk until you add `core/src` to `sys.path`. |
| **`PyErr` & `err.traceback(py)`** | **The Black-Box Flight Recorder** | `err.to_string()` only reads the cockpit warning light (`ValueError: bad key`); `err.traceback(py)` extracts the full flight recorder transcript showing every Python file and line number. |

## 🛠️ 6. Syntax Bank

| Snippet # | Pattern | Use Case |
| :--- | :--- | :--- |
| **1** | **Workspace `sys.path` Bootstrap** | Making `coldwind.core` and `.venv` packages importable in embedded Python. |
| **2** | **Class Instantiation & `call_method1`** | Booting `HeadlessEngineAdapter` and running `execute_turn(prompt)`. |
| **3** | **Full Traceback Formatter** | Extracting multi-line Python stack traces from `PyErr`. |

### 1. Bootstrapping `uv` Workspace Paths in Embedded Python
```rust
use pyo3::prelude::*;
use pyo3::types::PyList;

pub fn configure_coldwind_paths(py: Python<'_>, root: &str, site_pkgs: &str) -> PyResult<()> {
    let sys = py.import("sys")?;
    let path: Bound<'_, PyList> = sys.getattr("path")?.extract()?;
    path.append(site_pkgs)?; // .venv/lib/python3.13/site-packages
    path.append(format!("{}/core/src", root))?;
    path.append(format!("{}/desktop/src", root))?;
    Ok(())
}
```

### 2. Instantiating a Class & Calling Methods with Positional + Keyword Args
```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

pub fn invoke_graph_turn<'py>(
    py: Python<'py>,
    adapter: &Bound<'py, PyAny>,
    prompt: &str,
) -> PyResult<String> {
    let kwargs = PyDict::new(py);
    kwargs.set_item("stream_tokens", true)?;

    // Positional 1-tuple `(prompt,)` + optional `Some(&kwargs)`
    let out = adapter.call_method("execute_turn", (prompt,), Some(&kwargs))?;
    out.extract::<String>()
}
```

### 3. Extracting Full Python Stack Traces from `PyErr`
```rust
use pyo3::prelude::*;

pub fn format_python_exception(py: Python<'_>, err: &PyErr) -> String {
    let tb_str = err
        .traceback(py)
        .and_then(|tb| tb.format().ok())
        .unwrap_or_default();
    format!("{}{}", tb_str, err)
}
```

## 🔬 7. Visual Memory Model

*How to read this:* Compare how Rust packs arguments on the stack before PyO3 allocates the `PyTuple` and `PyDict` on the CPython heap for `tp_call`.

```text
Title: Argument Marshalling Layout for `obj.call_method("step", (prompt,), Some(&kwargs))`

RUST STACK (Caller)                          CPYTHON HEAP (Callee Frame)
┌─────────────────────────────────┐          ┌──────────────────────────────────────┐
│ Method Name: "step" (&str)      ├─────────►│ Interned PyUnicode ("step")          │
├─────────────────────────────────┤          ├──────────────────────────────────────┤
│ Positional 1-Tuple: (prompt,)   ├─────────►│ PyTupleObject (ob_size = 1)          │
│  • item 0: &str ("Hello")       │          │  └── [0]: PyUnicode ("Hello")        │
├─────────────────────────────────┤          ├──────────────────────────────────────┤
│ Keyword Dict: Some(&kwargs)     ├─────────►│ PyDictObject (ma_used = 1)           │
│  • Bound<'py, PyDict>           │          │  └── "stream_tokens": Py_True        │
└─────────────────────────────────┘          └──────────────────────────────────────┘
```

| Call Variant | Heap Allocations Created in CPython | Fastest Choice When... |
| :--- | :--- | :--- |
| **`call_method0("m")`** | `0` (uses CPython 3.9+ `vectorcall` stack array) | Method takes `self` only. |
| **`call_method1("m", (a,))`** | `1` (`PyTuple` of length 1 + converted `a`) | Method takes positional args only. |
| **`call_method("m", (a,), Some(&kw))`** | `2` (`PyTuple` + `PyDict`) | Method requires named keyword arguments. |

## 🛡️ 8. Compiler Diagnostics Table

| Exact Diagnostic / Error | Rule Violated | Runtime Bug Prevented | Python Equivalent of the Bug |
| :--- | :--- | :--- | :--- |
| **`error[E0277]: the trait bound `&str: PyCallArgs` is not satisfied`** | Passed `("hello")` without a trailing comma to `call1` / `call_method1` | Unpacking a string into 5 character arguments | `TypeError: step() takes 2 positional arguments but 6 were given` |
| **`PyErr { type: <class 'ModuleNotFoundError'> }`** | `sys.path` missing `.venv` site-packages or `core/src` | Importing unlocated workspace packages | Running `python` outside `uv run` |
| **`PyErr { type: <class 'AttributeError'> }`** | Misspelled method or class name in `getattr` / `call_method1` | Calling non-existent attribute | `AttributeError: 'ChatInitializer' object has no attribute ...` |
| **`PyErr { type: <class 'TypeError'>: 'NoneType' object is not callable }`** | Called `.call0()` on an attribute that is `None` or a property | Invoking non-callable attribute | `TypeError: 'NoneType' object is not callable` |

## ⚠️ 9. Trap Archive (3-part form)

| # | Trap Name | Assumed | Reality | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **The 1-Tuple Comma Trap** | `call1(("prompt"))` passes a 1-element tuple. | `("prompt")` is just a parenthesized `&str`, failing `PyCallArgs` or unpacking chars. | Always write `("prompt",)` with a trailing comma. |
| **2** | **The Bare `.to_string()` on `PyErr`** | `err.to_string()` prints the full Python traceback with line numbers. | `err.to_string()` only prints `ExceptionType: message` and discards the stack trace! | Call `err.traceback(py)` and `tb.format()` while holding `py`. |
| **3** | **The `PyDict::get_item` Unwrap Trap** | `dict.get_item("key")?` raises `KeyError` if `"key"` is missing. | `PyDict::get_item("key")?` returns `Ok(None)` when the key is absent, whereas `any.get_item("key")?` raises `KeyError`! | Pattern-match the `Option<Bound<'py, PyAny>>` returned by `PyDict::get_item`. |

### Trap 1: The 1-Tuple Comma Trap
- **Assumed:** Wrapping a single argument in parentheses `obj.call_method1("run", (prompt))` creates a tuple.
- **Reality:** In both Rust and Python, `(x)` is just `x`. A 1-element tuple requires a trailing comma `(x,)`.
- **10-Second Recall Fix:** Memorize the visual pair `("method", (arg,))`—never write `call_method1` without seeing a comma inside the second argument.

### Trap 2: Losing the Python Stack Trace with `err.to_string()`
- **Assumed:** Converting `PyErr` via `err.to_string()` includes the file names and line numbers where Python crashed.
- **Reality:** `Display` on `PyErr` only prints the exception type and value (e.g., `KeyError: 'messages'`), leaving you blind to which LangGraph node failed.
- **10-Second Recall Fix:** Extract `err.traceback(py).and_then(|tb| tb.format().ok())` inside `Python::with_gil`.

### Trap 3: `PyDict::get_item` vs `PyAny::get_item` Semantics
- **Assumed:** `bound_dict.get_item("k")?` returns `Bound<'py, PyAny>` directly.
- **Reality:** On a typed `Bound<'py, PyDict>`, `.get_item("k")?` mirrors Python's `dict.get("k")` and returns `Option<Bound<'py, PyAny>>` (`Ok(None)` if missing).
- **10-Second Recall Fix:** Chain `.get_item("k")?.ok_or_else(|| PyKeyError::new_err("k"))?` when the key is mandatory.

## ⏳ 10. Deferred Concepts (Manifest Boundary)

| Concept / Syntax | Manifest Status & Marker | What It Unlocks |
| :--- | :--- | :--- |
| **Async Coroutine Driving (`pyo3_async_runtimes`)** | `⏳ Deferred until Topic 11 (Async & Networking)` | Awaiting Python `async def ainvoke()` coroutines directly from a Rust `tokio` runtime. |
| **Custom Rust Error `From<PyErr>` Conversion** | `⏳ Deferred until Topic 10 (FFI & PyO3)` | Automatic `?` conversion from `PyErr` into domain-specific `GuiEngineError` enums. |

## 📈 11. Family Learning Progression

```text
Title: Subdomain 02 Internal Progression

[1. sys.path Bootstrap] ──► [2. py.import & getattr] ──► [3. call0 / call_method1 (arg,)] ──► [4. PyErr Traceback Formatting]
```

| Order | Milestone | Why Learn It Here |
| :--- | :--- | :--- |
| **1** | **`sys.path` Configuration** | Without valid module search paths, `py.import("coldwind...")` fails immediately. |
| **2** | **`getattr` & `call0` / `call_method1`** | Core mechanics for instantiating `HeadlessEngineAdapter` and driving turns. |
| **3** | **`PyErr` Traceback Extraction** | Essential for diagnosing Python-side configuration or MCP errors from Rust. |

## 📎 12. Concept Notes & Study Reports Directory

| Document | Relative Path | Scope & Invariants Covered | Status |
| :--- | :--- | :--- | :--- |
| **Subdomain 02 Concept Guide** | [`./README.md`](./README.md) | Deep dive into `uv` workspace imports, tuple packing, and `ColdWindPyDriver`. | `🟢 Complete` |
| **Subdomain 01 War Chest** | [`../01_pyo3_core_mechanics/cheat_sheet.md`](../01_pyo3_core_mechanics/cheat_sheet.md) | Prerequisite pointer rules (`Bound<'py, T>` vs `Py<T>`). | `🟢 Complete` |
| **Subdomain 03 Concept Guide** | [`../03_python_driving_rust/README.md`](../03_python_driving_rust/README.md) | Next step: exposing Rust structs (`#[pyclass]`) so Python can call back into Rust. | `🟢 Complete` |
| **Subdomain 03 War Chest** | [`../03_python_driving_rust/cheat_sheet.md`](../03_python_driving_rust/cheat_sheet.md) | `#[pyclass]`, `#[pymethods]`, `PyCell` borrow safety, and channel sinks. | `🟢 Complete` |