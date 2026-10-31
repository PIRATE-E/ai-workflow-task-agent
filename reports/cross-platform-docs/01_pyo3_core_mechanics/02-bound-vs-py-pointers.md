# 02 — The Two Boxes for Python Objects: `Bound<'py, T>` vs `Py<T>` (`.bind` & `.unbind`)

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `core` (`cross-platform-docs`) |
| **Subdomain** | `01_pyo3_core_mechanics` |
| **Type** | Concept Note / Root-Cause Study Report |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ `Bound` API, `learn_rust` Topic 06 Smart Pointers) |
| **Confidence** | `VERIFIED ✅` |
| **Prerequisites** | [`./01-gil-and-interpreter-boot.md`](./01-gil-and-interpreter-boot.md), `learn_rust` Topic 06 (`Rc<T>`) |
| **Updated** | `2026-10-25` |

> **TL;DR:** PyO3 gives you two wrapper types for a Python object because of one root cause: you can only call Python methods *while* holding the GIL (`Bound<'py, T>`), but you need to store the Python engine in a Rust struct *between* turns when you do NOT hold the GIL (`Py<T>`). Use `.unbind()` to pack `Bound<'py, T>` into `Py<T>` for storage, and `.bind(py)` to unpack it when the next turn starts.

## Domain & Dependencies

| Item | Detail | Status |
| :--- | :--- | :--- |
| **Covers** | Why both `Bound<'py, T>` and `Py<T>` exist; how `.unbind()`, `.bind(py)`, `.extract()`, and `.downcast()` work. | `VERIFIED ✅` |
| **Prerequisite** | [`./01-gil-and-interpreter-boot.md`](./01-gil-and-interpreter-boot.md) (you know what `py: Python<'py>` is). | `VERIFIED ✅` |
| **Unlocks** | Full mastery of [`./cheat_sheet.md`](./cheat_sheet.md) and Subdomain 02 (`02_rust_driving_python`). | `VERIFIED ✅` |

## Executive Summary

The #1 thing that confuses everyone learning PyO3 is seeing two different Rust types that both point to a Python object:
- **`Bound<'py, PyAny>`** (has a `'py` lifetime)
- **`Py<PyAny>`** (has NO `'py` lifetime)

Why didn't the PyO3 authors just make one type? Because a Python object in a GUI app has **two completely different jobs**:
1. **Job 1 — Active Work Inside `Python::with_gil` (`Bound<'py, T>`):** While you are inside the Python room holding the `py` key, you want to call methods (`.getattr()`, `.call_method1()`) as fast as possible without re-checking the GIL lock on every line.
2. **Job 2 — Sitting on a Shelf Between Turns (`Py<T>`):** After the agent finishes answering Question #1, your worker thread releases the GIL and waits 2 minutes for the user to type Question #2. You **cannot** throw away `ChatInitializer` and reboot LangGraph on every question—you must store that Python object inside a Rust `struct` while the GIL is unlocked!

| Pointer Type | Simple Nickname | Has `'py` Tag? | Can Call Python Methods? | Can Sit Inside a Rust `struct` Between Turns? |
| :--- | :--- | :--- | :--- | :--- |
| **`Bound<'py, T>`** | **The Plugged-In Corded Drill** | **YES (`'py`)** | ✅ **YES** (`.call_method1()`, `.getattr()`) | ❌ **NO** (`rustc` stops you with `error[E0597]`) |
| **`Py<T>`** | **The Unplugged Drill in a Briefcase** | **NO** | ❌ **NO** (must plug in via `.bind(py)` first) | ✅ **YES** (lives as long as you want, `Send + Sync`) |

## 1️⃣ The Pain First — What Happens If You Try to Keep `Bound<'py, T>`?

Let's see the exact problem with your own eyes. Suppose we boot `coldwind-core` inside `Python::with_gil` and try to return the Python module so we can use it later when the user clicks "Send":

```rust
// ❌ BROKEN ATTEMPT: Trying to return Bound<'py, PyModule> out of with_gil
use pyo3::prelude::*;

pub fn broken_boot() -> PyResult<Bound<'static, PyModule>> {
    Python::with_gil(|py| {
        let engine_mod = py.import("coldwind.core.engine")?;
        Ok(engine_mod) // <-- ERROR E0597: `py` does not live long enough!
    })
}
```

**Why did the Rust compiler stop us here (`error[E0597]`)?**  
Trace what would happen at the closing brace `}` if Rust allowed this:
1. At `}`, `Python::with_gil` **unlocks the GIL**.
2. Now `engine_mod` (`Bound<'py, PyModule>`) is sitting outside in pure Rust with **no GIL lock held**.
3. If your next line of code called `engine_mod.getattr("ChatInitializer")`, Rust would read CPython's heap memory while another thread might be garbage-collecting it—**instant segfault!**

Because `Bound<'py, T>` carries the `'py` lifetime tag from `|py|`, Rust's borrow checker (`learn_rust` Topic 01) makes it **physically impossible** for `Bound<'py, T>` to step one inch past the closing `}` of `Python::with_gil`!

| What You Tried to Do | What `rustc` Says | What `rustc` Saved You From |
| :--- | :--- | :--- |
| Return `Bound<'py, T>` from `Python::with_gil` | `error[E0597]: py does not live long enough` | Calling Python methods after the GIL was already unlocked! |
| Put `Bound<'py, T>` inside `struct Worker` | `error[E0106]: missing lifetime specifier` | Keeping a GIL-tied pointer alive when the worker thread is sleeping without the GIL! |

## 2️⃣ The Solution: `.unbind()` and `.bind(py)` — The Briefcase Switch

**Metaphor-first:**
- Inside the Python room (`with_gil`), `py.import(...)` hands you a **corded power drill plugged into the wall socket** (`Bound<'py, T>`). You can drill holes immediately, but you cannot walk out the door while the cord is plugged into the wall.
- To carry the drill out the door and store it in your locker (`struct EngineWorker`), you press the **`.unbind()`** button. That unplugs the cord from the wall and snaps the drill inside a **locked carrying briefcase (`Py<T>`)**.
- Because the briefcase is locked, you can carry `Py<T>` anywhere—into a Rust struct, or even across threads (`Send + Sync`)—because nobody can pull the trigger while it is inside the briefcase!
- Later, when Turn #2 starts, you walk back into the Python room (`Python::with_gil(|py| ...)`), and call **`briefcase.bind(py)`**. That opens the briefcase and plugs the drill right back into the new wall socket (`&Bound<'py, T>`) so you can use it again!

```text
Title: How `.unbind()` and `.bind(py)` Let a Python Object Survive Across Turns

TURN 0 (App Startup — Inside `with_gil #1`):
  let bound_adapter: Bound<'py1, PyAny> = bridge.call_method0("create_adapter")?;
         │
         │  Call `.unbind()` (Unplugs from 'py1 -> Locks inside Briefcase)
         ▼
BETWEEN TURNS (User is reading UI — NO GIL HELD!):
  struct EngineWorker {
      adapter: Py<PyAny>,  ◄── Safe in struct! No 'py lifetime!
  }
         │
         │  User clicks "Send" -> Enter `with_gil #2` -> Call `self.adapter.bind(py)`
         ▼
TURN 1 (Running Prompt — Inside `with_gil #2`):
  let active_adapter: &Bound<'py2, PyAny> = self.adapter.bind(py);
  active_adapter.call_method1("execute_turn", (prompt,))?; ◄── Drill works again!
```

| Transition Method | What You Start With | What You Get Back | Does It Copy the Python Object in RAM? |
| :--- | :--- | :--- | :--- |
| **`bound_obj.unbind()`** | `Bound<'py, T>` (Plugged in) | `Py<T>` (Locked briefcase) | **NO!** Zero bytes copied, zero refcount change ($\mathcal{O}(1)$). |
| **`py_obj.bind(py)`** | `&Py<T>` + `py: Python<'py>` | `&Bound<'py, T>` (Plugged in) | **NO!** Zero bytes copied, zero refcount change ($\mathcal{O}(1)$). |

> **💡 Root-Cause Gem:** Notice the last column in the table above! Calling `.unbind()` and `.bind(py)` does **not** copy the Python object or even touch CPython's `ob_refcnt` counter. Both `Bound<'py, T>` and `Py<T>` are just an `8-byte` memory address pointing to the exact same `PyObject` on Python's heap—`.unbind()` simply erases the `'py` lifetime tag at compile time, and `.bind(py)` puts the `'py` tag back on when you show your `py` badge!

## 3️⃣ Wait — When Should I Use `.extract()` vs `.downcast()` vs `.unbind()`?

When a Python function returns a `Bound<'py, PyAny>` (which just means *"some Python object, could be anything"*), you have three ways to handle it before `Python::with_gil` ends. Here is how to choose in 5 seconds:

| What Is Inside the Python Object? | What Do You Want in Rust? | Which Method to Call | What Actually Happens in RAM |
| :--- | :--- | :--- | :--- |
| **Simple data (`str`, `int`, `bool`, `list[str]`)** | A normal Rust `String`, `i64`, `bool`, or `Vec<String>` | **`.extract::<String>()?`** | **Copies** the bytes out of Python into a brand-new Rust value. |
| **A Python `dict` or `list` you want to edit in-place** | A typed `&Bound<'py, PyDict>` or `&Bound<'py, PyList>` | **`.downcast::<PyDict>()?`** | **Zero-copy check!** Just verifies it's a `dict` so you can call `.get_item()`. |
| **A big Python class (`ChatInitializer` / `Adapter`)** | To keep the Python object alive for the next turn | **`.unbind()`** (gives `Py<PyAny>`) | **Zero-copy!** Keeps the object on Python's heap and stores its address in Rust. |

## 4️⃣ Step-by-Step Code Walkthrough (Every Line Decoded)

Look at how clean and natural this is once you know the **Briefcase Rule** (`Py<T>` in the struct, `.unbind()` when saving, `.bind(py)` when using):

```rust
use pyo3::prelude::*;
use pyo3::types::PyDict;

// 1. In our struct, we store the UNPLUGGED briefcase (`Py<PyDict>`), NOT `Bound`!
pub struct SessionStore {
    saved_dict: Py<PyDict>,
}

impl SessionStore {
    // 2. At startup: create the Python dict, then `.unbind()` it so we can save it
    pub fn new() -> PyResult<Self> {
        pyo3::prepare_freethreaded_python();

        let saved_dict: Py<PyDict> = Python::with_gil(|py| {
            // `d` is a plugged-in `Bound<'py, PyDict>`
            let d: Bound<'_, PyDict> = PyDict::new(py);
            d.set_item("turn_count", 1)?;

            // Unplug `d` from `'py` so it can live inside `SessionStore`!
            Ok(d.unbind())
        })?;

        Ok(Self { saved_dict })
    }

    // 3. On a later turn: grab the GIL, plug `saved_dict` back in with `.bind(py)`, and read it!
    pub fn get_turn_count(&self) -> PyResult<i64> {
        Python::with_gil(|py| {
            // Plug the briefcase back into `py` -> gives `&Bound<'py, PyDict>`
            let d: &Bound<'_, PyDict> = self.saved_dict.bind(py);

            // Look up "turn_count" and copy the integer to Rust with `.extract()`
            let val: Bound<'_, PyAny> = d.get_item("turn_count")?.expect("key exists");
            val.extract::<i64>()
        })
    }
}
```

| Code Step | What Type We Have | Why We Did It That Way |
| :--- | :--- | :--- |
| **`saved_dict: Py<PyDict>`** | `Py<PyDict>` | Structs live outside `Python::with_gil`, so they must hold unplugged `Py<T>` handles. |
| **`let d = PyDict::new(py);`** | `Bound<'py, PyDict>` | Inside `with_gil`, `new(py)` gives us a plugged-in handle so we can immediately call `d.set_item(...)`. |
| **`Ok(d.unbind())`** | Converts `Bound` → `Py` | Unplugs `d` right before the `with_gil` closure closes at `}`. |
| **`self.saved_dict.bind(py)`** | Converts `&Py` → `&Bound` | Plugs `saved_dict` into the new `py` token on Turn 2 so we can call `.get_item(...)`. |

## 5️⃣ How This Decodes Your Subdomain 01 Cheat Sheet

Every single symbol in [`./cheat_sheet.md`](./cheat_sheet.md) now maps to the Corded Drill (`Bound`) vs Briefcase (`Py`) rule:

| Cheat Sheet Row | Plain-English Meaning |
| :--- | :--- |
| **`Bound<'py, T>` (`!Send`)** | Plugged into the current thread's GIL token `'py`; cannot leave `with_gil` or move to another thread. |
| **`Py<T>` (`Send + Sync`)** | Unplugged briefcase (`bound.unbind()`); safe to store in structs and send to worker threads. |
| **`py_obj.clone_ref(py)`** | How you duplicate a `Py<T>` briefcase (similar to `Rc::clone` in `learn_rust` Topic 06, using `py` to bump `ob_refcnt` by `+1`). |

## ✅ Checkpoint (Prove It to Yourself — 5 Minutes)

| # | Scenario | Which Method Do You Call? | Why? |
| :--- | :--- | :--- | :--- |
| **1** | You created `adapter: Bound<'py, PyAny>` in `with_gil` and want to save it in `struct Worker`. | `adapter.unbind()` | Strips `'py` and gives you `Py<PyAny>` for struct storage. |
| **2** | Inside the next turn's `with_gil`, you want to call a method on `self.adapter: Py<PyAny>`. | `self.adapter.bind(py)` | Re-attaches the `'py` token so you get `&Bound<'py, PyAny>` with all methods unlocked. |
| **3** | Python returned a `Bound<'py, PyAny>` containing `"Hello"` and you want a Rust `String`. | `.extract::<String>()?` | Copies the UTF-8 text out of Python into an owned Rust `String`. |

## 📎 Glossary (Plain-English Dictionary)

| Technical Term | Simple Everyday Meaning |
| :--- | :--- |
| **`Bound<'py, T>`** | A Python object handle that is currently "plugged into" the GIL (`'py`); you can call methods on it right now, but it cannot leave `with_gil`. |
| **`Py<T>`** | A Python object handle "unplugged" from the GIL; you can store it in a Rust struct forever, but must call `.bind(py)` before calling methods on it. |
| **`.unbind()`** | Unplugs a `Bound<'py, T>` into a `Py<T>` so it can survive after `Python::with_gil` ends. |
| **`.bind(py)`** | Plugs a stored `Py<T>` back into an active `py: Python<'py>` token so you can call Python methods on it again. |
| **`.extract::<T>()?`** | Copies a Python value (like a string, number, or list) into a native Rust type (`String`, `i64`, `Vec<T>`). |
| **`.downcast::<PyDict>()?`** | Checks if a generic `Bound<'py, PyAny>` is actually a Python `dict` without copying any data. |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | What happens when a `Py<T>` struct field is finally dropped in Rust while the GIL is NOT held? | PyO3's `Drop` implementation for `Py<T>` automatically acquires the GIL briefly behind the scenes (or queues the drop) so `Py_DECREF` is always executed safely! | `2026-10-25` |
| **Q2** | Why do older blog posts show `&'py PyAny` instead of `Bound<'py, PyAny>`? | PyO3 0.21 and older used `&'py PyAny` (which had hidden memory pool overhead). PyO3 0.22+ replaced it with `Bound<'py, PyAny>`, which is faster and acts like a true Rust smart pointer (`Rc`). | `2026-10-25` |
| **Q3** | What does `PyAny` mean in `Bound<'py, PyAny>`? | `PyAny` is PyO3's name for Python's base `object` (`typing.Any`)—it represents any Python value before you narrow it down with `.extract()` or `.downcast()`. | `2026-10-25` |