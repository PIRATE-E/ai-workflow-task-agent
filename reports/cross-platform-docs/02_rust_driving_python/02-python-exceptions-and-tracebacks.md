# 02 — How Python Crashes Travel Safely Into Rust (`PyResult`, `PyErr` & Full Tracebacks)

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `core` (`cross-platform-docs`) |
| **Subdomain** | `02_rust_driving_python` |
| **Type** | Concept Note / Root-Cause Study Report |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ `PyErr`, `PyTracebackMethods`, `learn_rust` Topic 04) |
| **Confidence** | `VERIFIED ✅` |
| **Prerequisites** | [`./01-importing-and-calling-python.md`](./01-importing-and-calling-python.md), `learn_rust` Topic 04 (`Result<T, E>` & `?`) |
| **Updated** | `2026-10-25` |

> **TL;DR:** Python uses `raise Exception` (which unwinds stack frames), while Rust uses `Result<T, E>` values. Because unwinding a Python exception across a C/Rust boundary would corrupt memory, PyO3 catches every Python exception at the border and turns it into `Err(PyErr)`. Never call `.unwrap()` on a `PyResult`, and always use `err.traceback(py)` because `err.to_string()` throws away the Python file names and line numbers!

## Domain & Dependencies

| Item | Detail | Status |
| :--- | :--- | :--- |
| **Covers** | How Python `raise` becomes Rust `Err(PyErr)`; why `.unwrap()` crashes the GUI; why `err.to_string()` hides line numbers and how `err.traceback(py)` restores them. | `VERIFIED ✅` |
| **Prerequisite** | [`./01-importing-and-calling-python.md`](./01-importing-and-calling-python.md) and `learn_rust` Topic 04 (`Result` & `?`). | `VERIFIED ✅` |
| **Unlocks** | Complete mastery of Subdomain 02 and [`./cheat_sheet.md`](./cheat_sheet.md). | `VERIFIED ✅` |

## Executive Summary

In `coldwind-core`, things go wrong at runtime all the time: an Ollama model is offline, an MCP server times out, or a tool raises `ValueError("Invalid JSON")`.

When you call Python from Rust, two big questions come up:
1. **Why doesn't a Python `raise ValueError` crash the Rust program?** (How does it turn into a Rust `Result`?)
2. **Why does printing a `PyErr` with `println!("{}", err)` only show `ValueError: Invalid JSON` without telling you which Python file and line number failed?**

| What Happens in Python | What PyO3 Hands You in Rust | What You Should Do With It |
| :--- | :--- | :--- |
| **Function returns `val` normally** | `Ok(Bound<'py, PyAny>)` | Extract or use the value with `?`. |
| **Function raises `KeyError("messages")`** | `Err(PyErr)` | **Never `.unwrap()`!** Format the full traceback via `err.traceback(py)` and send it to the GUI error banner. |

## 1️⃣ The Pain First — Why `err.to_string()` Leaves You Blind When Debugging

Suppose your LangGraph agent crashes deep inside `core/src/coldwind/core/agents/classify_agent.py` at line 84 with `KeyError: 'message_type'`.

If your Rust code catches the `PyErr` and converts it to a string using the normal Rust `.to_string()` (or `format!("{}", err)`):

```text
Title: What `err.to_string()` Prints vs What You Actually Need to Debug

❌ What `err.to_string()` gives you:
   "KeyError: 'message_type'"
   (Zero files! Zero line numbers! Good luck guessing which of your 90 Python files failed!)

✅ What `err.traceback(py)` + `.format()` gives you:
   "Traceback (most recent call last):
      File \".../core/src/coldwind/core/engine/chat_initializer.py\", line 112, in step
      File \".../core/src/coldwind/core/agents/classify_agent.py\", line 84, in classify
        msg_type = state['message_type']
    KeyError: 'message_type'"
```

**Why does `err.to_string()` hide the traceback?**  
**The Root Cause:** In CPython, an exception is stored in **three separate C pointers**:
1. `ptype` (the class, e.g., `KeyError`)
2. `pvalue` (the message, e.g., `'message_type'`)
3. `ptraceback` (a linked list of Python stack frames with file names and line numbers)

In Rust, the standard `Display` trait (`err.to_string()`) is **not allowed to take a `py: Python<'py>` parameter**. And to walk the `ptraceback` linked list on Python's heap, you **must** hold the GIL (`py`)! So `err.to_string()` can only print the short message, and you must call `err.traceback(py)` while holding `py` to read the line numbers!

| Method on `PyErr` | Needs `py: Python<'py>`? | Prints Exception Name & Message? | Prints Python File Names & Line Numbers? |
| :--- | :--- | :--- | :--- |
| **`err.to_string()`** | ❌ **NO** | ✅ **YES** (`KeyError: 'x'`) | ❌ **NO** (Cannot walk heap frames without `py`!) |
| **`err.traceback(py)` + `.format()`** | ✅ **YES** | ✅ **YES** (when combined with `err`) | ✅ **YES** (Full multi-line Python stack trace!) |

## 2️⃣ How a Python Exception Crosses the Border Without Crashing Rust

**Metaphor-first:** Think of Python and Rust as two countries with different traffic laws. Inside Python, when an error happens (`raise`), a siren goes off and the car drives backward up the highway (`stack unwinding`) until it hits a `try / except` roadblock.  
If that car drove backward across the border bridge (`FFI boundary`) into Rust, the bridge would collapse (**Undefined Behavior / Immediate Process Abort**), because Rust stack frames don't speak Python's unwinding language!

So what does CPython do at the border bridge?
1. When Python code called from C/Rust raises an exception, CPython stops the backward car **right before the border bridge**.
2. CPython parks the exception in a special border office (`tstate->curexc_type`, the thread-local error slot) and sends a **`NULL` (`0x0`) pointer** across the bridge to Rust.
3. PyO3 sees the `NULL` pointer, walks into the border office, picks up the parked exception, clears the alarm, and hands your Rust code a normal, peaceful `Result::Err(PyErr)`!

```text
Title: How CPython + PyO3 Turn a `raise` Into a Safe Rust `Result::Err(PyErr)`

INSIDE PYTHON (`execute_turn`)               THE FFI BORDER                  INSIDE RUST (`call_method1`)
┌──────────────────────────────┐             ┌───────────────┐               ┌──────────────────────────────┐
│ `raise ValueError("Bad MCP")`│             │ C Return Slot │               │ PyO3 checks return pointer:  │
│  • Unwinds Python frames     ├────────────►│ Returns `NULL`├──────────────►│  • Sees `NULL`!              │
│  • Stops at top Python frame!│             │ + Sets C Error│               │  • Fetches `PyErr` from C    │
│  • NEVER unwinds into Rust!  │             │   Slot        │               │  • Returns `Err(PyErr)`!     │
└──────────────────────────────┘             └───────────────┘               └──────────────────────────────┘
```

| Rule | Why It Matters to You |
| :--- | :--- |
| **1. `PyResult<T>` is just an alias for `Result<T, PyErr>`** | Every tool you learned in `learn_rust` Topic 04 (`?`, `match`, `if let Err(e)`, `.map_err()`) works identically on `PyResult<T>`! |
| **2. Never call `.unwrap()` on `PyResult` in a GUI** | If an MCP tool fails in Python and you wrote `.unwrap()` in Rust, your entire Slint window crashes and closes! Catch `Err(e)` and show it in the UI instead. |

## 3️⃣ Step-by-Step Code Walkthrough (The Full Traceback Extractor)

Here is the exact helper function you can drop into any Rust + PyO3 project. Whenever Python fails, it extracts the complete multi-line Python stack trace (files + line numbers + error message) as a normal Rust `String`:

```rust
use pyo3::prelude::*;

/// Converts a PyErr into a full Python traceback string (with file names & line numbers!)
pub fn format_full_python_error(py: Python<'_>, err: &PyErr) -> String {
    // Line A: Ask PyO3 for the optional traceback object (`Option<Bound<'py, PyTraceback>>`)
    match err.traceback(py) {
        Some(tb) => {
            // Line B: Ask Python to format the stack frames into a multi-line String
            match tb.format() {
                Ok(frames_text) => format!("{}{}", frames_text, err),
                Err(_) => err.to_string(),
            }
        }
        // Line C: If the error was created in C without stack frames, fall back to short string
        None => err.to_string(),
    }
}

pub fn run_turn_safely(adapter: &Py<PyAny>, prompt: &str) -> Result<String, String> {
    Python::with_gil(|py| {
        // Call `adapter.execute_turn(prompt)` and convert any PyErr into a full traceback String!
        adapter
            .bind(py)
            .call_method1("execute_turn", (prompt,))
            .and_then(|res| res.extract::<String>())
            .map_err(|err| format_full_python_error(py, &err))
    })
}
```

| Line | Exact Code | Plain-English Explanation |
| :--- | :--- | :--- |
| **Line A** | `err.traceback(py)` | Uses our `py` GIL key to open the exception's flight recorder (`Option<Bound<'py, PyTraceback>>`). |
| **Line B** | `tb.format()` | Runs Python's `traceback.format_tb()` on the frames, returning `"Traceback (most recent call last):\n File ..."` as a Rust `String`. |
| **`format!("{}{}", frames_text, err)`** | Joins the stack frames (`frames_text`, which ends with `\n`) with the exception name and message (`err`). | Produces the exact same error output you would see in a Python terminal! |
| **`.map_err(\|err\| ...)`** | Standard `learn_rust` Topic 05 combinator | Converts `Result<String, PyErr>` into a pure Rust `Result<String, String>` while we still hold `py`! |

## 4️⃣ Bonus Trap: Why `PyDict::get_item("key")?` Does NOT Raise `KeyError`!

Here is one sneaky trap from the Subdomain 02 Cheat Sheet that catches every Python developer:
- In Python, `my_dict["missing"]` raises `KeyError`, while `my_dict.get("missing")` returns `None`.
- In PyO3, when you have a typed `Bound<'py, PyDict>`, calling **`dict.get_item("missing")?` works like `dict.get()`**: it returns **`Ok(None)`**, NOT `Err(PyKeyError)`!

```text
Title: `PyDict::get_item` vs `PyAny::get_item` Return Types

On a typed `Bound<'py, PyDict>`:
  dict.get_item("role")?  ──► Returns `Option<Bound<'py, PyAny>>`
                              • Key exists  -> `Some(value)`
                              • Key missing -> `None` (No KeyError raised!)

On an untyped `Bound<'py, PyAny>`:
  any.get_item("role")?   ──► Returns `Bound<'py, PyAny>` directly
                              • Key missing -> Returns `Err(PyKeyError)`!
```

| What You Have | What `.get_item("k")?` Returns | How to Unpack a Mandatory Key |
| :--- | :--- | :--- |
| **`dict: &Bound<'py, PyDict>`** | `Option<Bound<'py, PyAny>>` | `dict.get_item("k")?.ok_or_else(\|\| PyKeyError::new_err("k"))?` |
| **`any: &Bound<'py, PyAny>`** | `Bound<'py, PyAny>` | `any.get_item("k")?` (raises `KeyError` automatically if missing) |

## ✅ Checkpoint (Prove It to Yourself — 5 Minutes)

| # | Check Question | Expected Root-Cause Answer |
| :--- | :--- | :--- |
| **1** | Why can't `err.to_string()` print the Python file names and line numbers? | Because reading the traceback frames on Python's heap requires holding the GIL (`py: Python<'py>`), and Rust's `to_string()` doesn't have `py`. |
| **2** | Why should you convert `PyErr` into a `String` *inside* `Python::with_gil` using `.map_err(...)`? | Because `err.traceback(py)` needs `py`, which only exists inside `Python::with_gil(|py| ...)`. |
| **3** | What does `bound_dict.get_item("missing_key")?` return when `bound_dict` is a `Bound<'py, PyDict>`? | It returns `Ok(None)` (like Python's `dict.get()`), not `Err(KeyError)`. |

## 📎 Glossary (Plain-English Dictionary)

| Technical Term | Simple Everyday Meaning |
| :--- | :--- |
| **`PyErr`** | Rust struct holding a caught Python exception (`type`, `value`, and `traceback`). |
| **`PyTraceback`** | The chain of Python stack frames showing which files and line numbers were running when the error happened. |
| **Stack Unwinding** | Walking backward up the function call chain when an exception is thrown; forbidden across the C/Rust border. |
| **`tb.format()`** | Method on `Bound<'py, PyTraceback>` that turns the stack frames into a readable multi-line Rust `String`. |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | Can Rust also *create* a new Python exception and raise it back to Python? | Yes! Every standard Python exception lives in `pyo3::exceptions::*`—for example, `return Err(pyo3::exceptions::PyValueError::new_err("Bad input"));`. | `2026-10-25` |
| **Q2** | What if I just want to print the full Python traceback to the terminal console during debugging? | Call `err.print(py);` inside `Python::with_gil`—it prints the full traceback directly to Python's `sys.stderr`. | `2026-10-25` |
| **Q3** | Now Rust can call Python and catch errors—how does Python call Rust back while an agent turn is still running? | By wrapping a Rust struct with `#[pyclass]` and passing it to Python—which is Subdomain 03 (`03_python_driving_rust`)! | `2026-10-25` |