# ⚡ Subdomain 02: Rust Driving Python (Execution Engine)

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `core` (`cross-platform-docs`) |
| **Subdomain** | `02_rust_driving_python` |
| **Type** | Subdomain README + Tier 2 Concept Note Deep-Dive |
| **Prerequisites** | [`../01_pyo3_core_mechanics/README.md`](../01_pyo3_core_mechanics/README.md), `learn_rust` Topics 02 (Tuples), 04 (`Result`/`?`) |
| **Verification Mode** | `Codebase + Research` (`coldwind-core` `ChatInitializer`, PyO3 `PyAnyMethods`) |
| **Confidence** | `VERIFIED ✅` |
| **Updated** | `2026-10-22` |

> **TL;DR:** To drive `coldwind-core` from Rust, append the workspace `core/src` and `desktop/src` paths to Python's `sys.path` at boot, import the decoupled adapter module via `py.import()`, invoke discrete turns using `call_method1("execute_turn", (prompt,))?` (always with a trailing comma for 1-tuples!), and translate `PyErr` into formatted tracebacks via `err.traceback(py)`.
> **Scope:** Embedded `sys.path` configuration for `uv` workspaces, `py.import()`, attribute lookup (`getattr`), method dispatch (`call0`, `call1`, `call_method0`, `call_method1`, `call_method` with `PyDict` kwargs), and `PyErr` traceback formatting.
> **Python Bridge:** In Python, calling `engine.execute_turn(prompt, stream=True)` packs positional args into a `PyTuple` and keyword args into a `PyDict`, then invokes the `tp_call` slot on the method descriptor. PyO3 exposes this exact C-level protocol to Rust via `call_method0` (zero tuple allocation), `call_method1` (Rust tuple packed into `PyTuple`), and `call_method` (tuple + `Option<&Bound<'py, PyDict>>`).

## 📺 Recommended Learning & Reference Sources

| # | Source & Link | Architectural Focus | Verification |
| :--- | :--- | :--- | :--- |
| **1** | [PyO3 Guide — Calling Python Functions & Methods](https://pyo3.rs/main/function.html#calling-python-functions-in-rust) | Official reference for `call0`, `call1`, `call`, `call_method0`, `call_method1`, and `IntoPyObject` tuple packing. | `VERIFIED ✅` |
| **2** | [PyO3 Guide — Error Handling & `PyErr`](https://pyo3.rs/main/exception.html) | How Python exceptions become `Err(PyErr)` in Rust and how to inspect `PyTraceback`. | `VERIFIED ✅` |
| **3** | [`../../urgent_development/platform-integration-spec.md`](../../urgent_development/platform-integration-spec.md) | Defines `HeadlessEngineAdapter.execute_turn(user_message)` that bypasses `ChatInitializer.run_chat()`. | `VERIFIED ✅` |
| **4** | [`../uv-package-manager/shared/06-uv-workspace.md`](../uv-package-manager/shared/06-uv-workspace.md) | Explains how `coldwind-core` and `coldwind-desktop` live in `core/src` and `desktop/src` under `.venv`. | `VERIFIED ✅` |

## At a Glance & Subdomain Navigation

| Artifact | Relative Path | Type | What It Answers | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Subdomain Concept Guide (This File)** | [`./README.md`](./README.md) | Concept Note + Subdomain Index | How does Rust locate `coldwind.*` packages, invoke `execute_turn`, pass kwargs, and format `PyErr`? | `🟢 Complete` |
| **Subdomain 02 War Chest** | [`./cheat_sheet.md`](./cheat_sheet.md) | Tier 1 Cheat Sheet (C1–C12) | 30-second call router (`call0`/`call1`/`call_method1`), 1-tuple syntax law, and `PyErr` diagnostics. | `🟢 Complete` |
| **Previous Subdomain (`01`)** | [`../01_pyo3_core_mechanics/README.md`](../01_pyo3_core_mechanics/README.md) | Subdomain 01 Concept Guide | `Python<'py>`, `Bound<'py, T>` vs `Py<T>`, and `.bind(py)` / `.unbind()`. | `🟢 Complete` |
| **Next Subdomain (`03`)** | [`../03_python_driving_rust/README.md`](../03_python_driving_rust/README.md) | Subdomain 03 Concept Guide | Exposing Rust structs (`#[pyclass]`) to Python so Core can emit UI events back to Rust. | `🟢 Complete` |

## 🐍 1. The Python vs Rust Architecture Comparison

In Python, importing a class, instantiating it, calling a method, and catching an exception is dynamic syntax handled by bytecode instructions (`IMPORT_NAME`, `LOAD_ATTR`, `CALL`, `PUSH_EXC_INFO`). In Rust via PyO3, every step returns a `PyResult<Bound<'py, PyAny>>` so failures propagate cleanly via Rust's `?` operator (`learn_rust` Topic 04).

```python
# Python: Dynamic import, instantiation, method call, and traceback capture
import sys
import traceback

sys.path.append("./core/src")
from coldwind.desktop.gui_bridge import HeadlessEngineAdapter

try:
    adapter = HeadlessEngineAdapter(platform_context)
    state = adapter.execute_turn("Summarize MCP server status")
except Exception as err:
    formatted_tb = "".join(traceback.format_exception(err))
```

```rust
// Rust + PyO3: Explicit Result propagation (?) at every dynamic lookup step
use pyo3::prelude::*;
use pyo3::types::PyList;

pub fn boot_and_run_turn(project_root: &str, sink: Py<PyAny>, prompt: &str) -> Result<String, String> {
    Python::with_gil(|py| -> PyResult<String> {
        // 1. Append uv workspace source paths to sys.path
        let sys = py.import("sys")?;
        let path: Bound<'_, PyList> = sys.getattr("path")?.extract()?;
        path.append(format!("{}/core/src", project_root))?;
        path.append(format!("{}/desktop/src", project_root))?;

        // 2. Import module and instantiate HeadlessEngineAdapter(sink)
        let bridge_mod = py.import("coldwind.desktop.gui_bridge")?;
        let adapter_cls = bridge_mod.getattr("HeadlessEngineAdapter")?;
        let adapter = adapter_cls.call1((sink.bind(py),))?; // Note trailing comma `(...,)`!

        // 3. Invoke discrete turn: adapter.execute_turn(prompt)
        let result = adapter.call_method1("execute_turn", (prompt,))?;
        result.extract::<String>()
    })
    .map_err(|py_err| {
        Python::with_gil(|py| {
            py_err.traceback(py)
                .and_then(|tb| tb.format().ok())
                .unwrap_or_else(|| py_err.to_string())
        })
    })
}
```

| Python Operation | PyO3 Equivalent on `Bound<'py, PyAny>` | CPython C-API Function Invoked | Error Returned on Failure |
| :--- | :--- | :--- | :--- |
| **`import pkg.mod`** | `py.import("pkg.mod")?` | `PyImport_ImportModule` | `Err(PyErr)` (`ModuleNotFoundError`) |
| **`obj.attr`** | `obj.getattr("attr")?` | `PyObject_GetAttrString` | `Err(PyErr)` (`AttributeError`) |
| **`cls()`** | `cls.call0()?` | `PyObject_CallNoArgs` (Fast path!) | `Err(PyErr)` (`TypeError` / `__init__` err) |
| **`cls(a, b)`** | `cls.call1((a, b))?` | `PyObject_CallObject` | `Err(PyErr)` (`TypeError`) |
| **`obj.method(a)`** | `obj.call_method1("method", (a,))?` | `PyObject_CallMethodObjArgs` | `Err(PyErr)` (Any raised exception) |

## 🧠 2. Physical Metaphors for Core Mechanics

1. **The Custom Shipping Crate (`call1` & `call_method1` Tuple Packing):**  
   CPython's function-call doorway (`tp_call`) refuses loose items—it demands every delivery arrive packed inside a standard wooden pallet (`PyTuple`). When you pass a 2-element Rust tuple `("user", "hello")`, PyO3 automatically nails together a 2-slot `PyTuple`. If you write `("hello")` without a comma, Rust treats the parentheses as mathematical grouping and hands Python a raw string—which Python tries to unpack character-by-character as 5 separate arguments (`'h', 'e', 'l', 'l', 'o'`)! The trailing comma `("hello",)` is the pallet base.
2. **The Pneumatic Exception Return Tube (`PyResult<T>` & `?`):**  
   When a Python function raises `ValueError`, CPython does **not** unwind the C/Rust stack (unwinding across FFI boundaries is Undefined Behavior!). Instead, CPython sets a thread-local error pointer (`PyErr_Occurred()`) and returns `NULL`. PyO3 immediately checks for `NULL`, clears the C error flag, and hands your Rust code a normal `Result::Err(PyErr)` value on the stack so you can use `?`.

| Mechanism | Physical Metaphor | Key Takeaway |
| :--- | :--- | :--- |
| **Embedded `sys.path` Injection** | **Giving the Courier the Warehouse Map** | Embedded Python does not auto-load `.venv` `.pth` files unless pointed to the venv site-packages and `core/src`. |
| **1-Tuple Trailing Comma `(arg,)`** | **The Single-Box Shipping Pallet** | `(arg)` is an unpacked expression; `(arg,)` is a 1-element tuple that satisfies `call1` / `call_method1`. |
| **`PyErr` vs Rust `panic!`** | **Red Warning Ticket vs Building Explosion** | Never `.unwrap()` a `PyResult` in production; convert `PyErr` into a UI status event so bad tool inputs never crash the GUI. |

## 🔑 3. Core Mechanics & Step-by-Step Derivation

### 3.1 Why Embedded Python Needs Explicit `sys.path` + `.venv` Site-Packages

When you run `uv run python ...` in a terminal, `uv` activates `.venv/bin/python`, which automatically reads `.venv/lib/python3.13/site-packages/_coldwind.pth` (`learn_adv_python` / `uv-package-manager` Domain 0). When a native Rust binary embeds `libpython3.13.so`, CPython boots with default system paths and **does not know about your workspace's `.venv` or `core/src` directory** unless you append them to `sys.path` (or set `VIRTUAL_ENV` / `PYTHONPATH` before boot):

| Path to Append to `sys.path` at Worker Startup | Why It Is Required |
| :--- | :--- |
| **`<project_root>/.venv/lib/python3.13/site-packages`** | Makes third-party dependencies (`langgraph`, `langchain`, `pydantic`, `mcp`, `neo4j`) importable. |
| **`<project_root>/core/src`** | Makes `coldwind.core.*` namespace package importable without requiring wheel re-installation. |
| **`<project_root>/desktop/src`** | Makes `coldwind.desktop.*` (and `gui_bridge.py`) importable. |

### 3.2 Selecting the Exact Call Method (`call0` vs `call1` vs `call`)

PyO3 provides six call methods on `Bound<'py, PyAny>` (via `PyAnyMethods`), corresponding to whether you are calling a direct callable (`fn`/`class`) or a method on an instance, and how many arguments you pass:

| Target | 0 Arguments (Fastest — Zero Tuple Alloc) | Positional Args Only (Rust Tuple) | Positional + Keyword Args (`PyDict`) |
| :--- | :--- | :--- | :--- |
| **Callable (`func` / `Class`)** | `callable.call0()?` | `callable.call1((arg1, arg2))?` | `callable.call((arg1,), Some(&kwargs))?` |
| **Object Method (`obj.m`)** | `obj.call_method0("m")?` | `obj.call_method1("m", (arg1,))?` | `obj.call_method("m", (), Some(&kwargs))?` |

## 🔬 4. Visual Invariant Models & Memory Layouts

*How to read this:* Follow how a Rust `call_method1("execute_turn", (prompt,))` call crosses the PyO3 FFI boundary, executes `coldwind-core`'s LangGraph state machine, and returns either an `Ok(Bound<'py, PyAny>)` or an `Err(PyErr)` without ever unwinding across C frames.

```text
Title: FFI Call & Exception Translation Pipeline (Rust Worker -> CPython ceval -> Rust PyResult)

RUST WORKER (Thread N)                         CPYTHON 3.13+ INTERPRETER
┌──────────────────────────────────────┐       ┌───────────────────────────────────────────┐
│ adapter.call_method1(                │       │ 1. PyUnicode_FromString("Summarize...")   │
│   "execute_turn",                    ├──────►│ 2. PyTuple_Pack(1, py_str)                │
│   ("Summarize...",) // 1-Tuple!      │       │ 3. PyObject_CallMethodObjArgs(adapter,..) │
│ )                                    │       │    │                                      │
└──────────────────────────────────────┘       │    ├─► CASE A (Success):                  │
                                               │    │   Returns *mut PyObject (Non-NULL)   │
┌──────────────────────────────────────┐       │    │                                      │
│ Ok(Bound<'py, PyAny>)                │◄──────┼────┘                                      │
├──────────────────────────────────────┤       │                                           │
│ Err(PyErr)                           │◄──────┼────┐   CASE B (Python Exception Raised):  │
│  • Caught via `?` or `match`         │       │    └─► Sets tstate->curexc_type           │
│  • Formatted via `err.traceback(py)` │       │        Returns NULL pointer (No C unwind!)│
└──────────────────────────────────────┘       └───────────────────────────────────────────┘
```

| Outcome in Python | C-API Return Pointer | CPython Thread Error Slot | Rust `PyResult` Variant | Stack Unwinding Across FFI? |
| :--- | :--- | :--- | :--- | :--- |
| **Normal `return val`** | `NonNull<PyObject>` | Empty (`NULL`) | `Ok(Bound<'py, PyAny>)` | **NO** |
| **`raise RuntimeError(...)`** | `NULL` (`0x0`) | Populated (`PyErr_Fetch`) | `Err(PyErr)` | **NO** (Safe value return!) |

## ⚖️ 5. Universal Invariant & Operations Matrix

The golden rule of Rust-to-Python invocation separates zero-allocation 0-arg calls from tuple-packed positional calls and prevents raw panics on Python exceptions:

$$\text{Args} = 0 \implies \text{Use \texttt{call\_method0} (0 Alloc)} \quad \big| \quad \text{Args} \ge 1 \implies \text{Use \texttt{call\_method1} with Tuple \texttt{(a,)} + Handle \texttt{PyResult}}$$

| Operation | PyO3 Syntax | Allocates `PyTuple`? | Allocates `PyDict`? | Exception Safety Invariant |
| :--- | :--- | :--- | :--- | :--- |
| **Import Module** | `py.import("coldwind.core.engine")?` | ❌ **NO** | ❌ **NO** | Cached in `sys.modules` after first call. |
| **0-Arg Method** | `obj.call_method0("is_exiting")?` | ❌ **NO** (`vectorcall`) | ❌ **NO** | Never pass `()` to `call_method1`; use `call_method0`. |
| **1-Arg Method** | `obj.call_method1("execute_turn", (msg,))?` | ✅ **YES** (1-slot) | ❌ **NO** | Trailing comma `(msg,)` is mandatory! |
| **Kwargs Method** | `obj.call_method("f", (a,), Some(&dict))?` | ✅ **YES** | ✅ **YES** | Construct `dict` via `PyDict::new(py)`. |
| **Format Traceback** | `err.traceback(py)` + `tb.format()` | ❌ **NO** | ❌ **NO** | Must be called while holding `py: Python<'py>`. |

## 🛠️ 6. Production Blueprint & Code Patterns

| Pattern Name | Target Problem Solved | Cold Wind Touchpoint |
| :--- | :--- | :--- |
| **`ColdWindPyDriver`** | Bootstraps `.venv` + `core/src`, instantiates `HeadlessEngineAdapter`, and runs turns without `run_chat()`. | [`../../core/src/coldwind/core/engine/chat_initializer.py`](../../core/src/coldwind/core/engine/chat_initializer.py) |
| **`format_py_err()`** | Converts any `PyErr` into a rich multi-line traceback string for the Slint error panel. | [`../../core/src/coldwind/core/interfaces/exception_interface.py`](../../core/src/coldwind/core/interfaces/exception_interface.py) |

```rust
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

pub struct ColdWindPyDriver {
    adapter: Py<PyAny>,
}

impl ColdWindPyDriver {
    /// Boots Cold Wind Core inside embedded Python and stores the HeadlessEngineAdapter
    pub fn boot(project_root: &str, venv_site_packages: &str, event_sink: Py<PyAny>) -> Result<Self, String> {
        pyo3::prepare_freethreaded_python();

        Python::with_gil(|py| -> PyResult<Self> {
            // 1. Wire uv workspace paths into sys.path
            let sys = py.import("sys")?;
            let path: Bound<'_, PyList> = sys.getattr("path")?.extract()?;
            path.append(venv_site_packages)?;
            path.append(format!("{}/core/src", project_root))?;
            path.append(format!("{}/desktop/src", project_root))?;

            // 2. Import adapter and instantiate with event_sink (1-tuple!)
            let bridge = py.import("coldwind.desktop.gui_bridge")?;
            let adapter = bridge
                .getattr("HeadlessEngineAdapter")?
                .call1((event_sink.bind(py),))?;

            Ok(Self { adapter: adapter.unbind() })
        })
        .map_err(Self::format_py_err)
    }

    /// Drives a single non-blocking turn on the compiled LangGraph workflow
    pub fn execute_turn(&self, user_prompt: &str, temperature: f64) -> Result<String, String> {
        Python::with_gil(|py| -> PyResult<String> {
            let kwargs = PyDict::new(py);
            kwargs.set_item("temperature", temperature)?;

            let response = self.adapter.bind(py).call_method(
                "execute_turn",
                (user_prompt,), // 1-tuple positional argument
                Some(&kwargs),  // optional keyword arguments
            )?;
            response.extract::<String>()
        })
        .map_err(Self::format_py_err)
    }

    /// Formats full Python file/line stack trace instead of just the exception message
    fn format_py_err(err: PyErr) -> String {
        Python::with_gil(|py| {
            match err.traceback(py).and_then(|tb| tb.format().ok()) {
                Some(trace) => format!("{}\n{}", trace.trim_end(), err),
                None => err.to_string(),
            }
        })
    }
}
```

## ⚠️ 7. Learner Pitfall Archive

| # | Pitfall Name | What Was Written | What Failed at Compile / Runtime | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **The Missing 1-Tuple Comma** | `adapter.call_method1("execute_turn", (prompt))` | `error[E0277]: &str is not a valid PyCallArgs` (or `TypeError` in Python) | Add a trailing comma: `(prompt,)` so Rust constructs a 1-element tuple. |
| **2** | **The Unconfigured `sys.path` Crash** | `py.import("coldwind.core.engine")?` immediately after `with_gil` | `ModuleNotFoundError: No module named 'coldwind'` | Append `<root>/.venv/lib/python3.13/site-packages` and `<root>/core/src` to `sys.path` at boot. |
| **3** | **Calling `ChatInitializer.run_chat()`** | `chat_init.call_method0("run_chat")?` on the worker thread | Worker thread hangs forever inside `get_user_input()` waiting for stdin | Never call `run_chat()` in a GUI; call `HeadlessEngineAdapter.execute_turn(prompt)` per message. |

## ✅ 8. Checkpoint & Pass Criteria

Test your understanding of Subdomain 02 by verifying each call signature below:

| Call Goal in Python | Correct PyO3 Call Syntax | Why Alternative Fails |
| :--- | :--- | :--- |
| **`context.is_exiting()`** | `ctx.call_method0("is_exiting")?.extract::<bool>()?` | `call_method1` allocates an unnecessary empty tuple. |
| **`adapter.execute_turn("hi")`** | `adapter.call_method1("execute_turn", ("hi",))?` | `("hi")` without comma is `&str`, not `(&str,)`. |
| **`graph.invoke(state, config=cfg)`** | `graph.call_method("invoke", (&state,), Some(&kwargs))?` | Keyword arguments require `PyDict` passed to `call_method`. |

## 🎯 9. Core Systems Invariants & Reading Path

| Invariant # | Statement | Next Step in Reading Path |
| :--- | :--- | :--- |
| **1. The Workspace Path Law** | Embedded CPython must have `.venv/.../site-packages`, `core/src`, and `desktop/src` appended to `sys.path` once at boot. | Review [`./cheat_sheet.md`](./cheat_sheet.md) for 30-second recall. |
| **2. The 1-Tuple Comma Law** | Every 1-argument `call1` or `call_method1` call must use `(arg,)` with a trailing comma. | Proceed to [`../03_python_driving_rust/README.md`](../03_python_driving_rust/README.md). |
| **3. The Zero-Unwind FFI Law** | Never `.unwrap()` a `PyResult`; convert `PyErr` via `err.traceback(py)` so Python exceptions surface cleanly in the UI. | Connect to Rust sinks in [`../03_python_driving_rust/cheat_sheet.md`](../03_python_driving_rust/cheat_sheet.md). |