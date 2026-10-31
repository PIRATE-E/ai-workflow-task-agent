# 01 — How Rust Finds and Calls Your Python Code (`sys.path`, `call0`, `call1` & The 1-Tuple Trap)

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `core` (`cross-platform-docs`) |
| **Subdomain** | `02_rust_driving_python` |
| **Type** | Concept Note / Root-Cause Study Report |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ `PyAnyMethods`, `coldwind-core` `ChatInitializer`) |
| **Confidence** | `VERIFIED ✅` |
| **Prerequisites** | [`../01_pyo3_core_mechanics/02-bound-vs-py-pointers.md`](../01_pyo3_core_mechanics/02-bound-vs-py-pointers.md) |
| **Updated** | `2026-10-25` |

> **TL;DR:** When Rust boots embedded Python, Python starts blind—it does not know where `.venv` or `core/src` live on disk until you append them to `sys.path`. Once imported, zero-argument calls use `call0()` / `call_method0()`, and calls with arguments use `call1()` / `call_method1()` where the arguments **must** be wrapped in a Rust tuple—including the famous trailing comma `(arg,)` when passing just one argument!

## Domain & Dependencies

| Item | Detail | Status |
| :--- | :--- | :--- |
| **Covers** | Why embedded Python fails with `ModuleNotFoundError`; how `call0`, `call1`, and `call_method1` work; why `(arg,)` needs a comma; why we never call `run_chat()`. | `VERIFIED ✅` |
| **Prerequisite** | Subdomain 01 (`Python::with_gil`, `Bound<'py, T>`, `.unbind()`). | `VERIFIED ✅` |
| **Unlocks** | [`./02-python-exceptions-and-tracebacks.md`](./02-python-exceptions-and-tracebacks.md) and [`./cheat_sheet.md`](./cheat_sheet.md). | `VERIFIED ✅` |

## Executive Summary

Once you have the `py` permission slip from Subdomain 01, you want Rust to do three normal Python tasks:
1. **`import coldwind.desktop.gui_bridge`**
2. **`adapter = HeadlessEngineAdapter(sink)`**
3. **`reply = adapter.execute_turn("Hello")`**

If you try to write those three lines in Rust without knowing the root causes below, you will hit **three brick walls in a row**:
- **Brick Wall #1:** Python yells `ModuleNotFoundError: No module named 'coldwind'`—even though `uv sync` worked fine in your terminal!
- **Brick Wall #2:** You write `adapter.call_method1("execute_turn", ("Hello"))` and Rust refuses to compile (or Python yells `TypeError: takes 2 arguments but 6 were given`!).
- **Brick Wall #3:** You call `ChatInitializer.run_chat()` and your entire app hangs forever waiting for keyboard input that never comes.

| Brick Wall | Why It Happens (Root Cause) | The 1-Line Fix |
| :--- | :--- | :--- |
| **1. `ModuleNotFoundError`** | Embedded Python doesn't use `.venv/bin/python`, so it doesn't know where `.venv` or `core/src` sit. | Append `.venv/.../site-packages`, `core/src`, and `desktop/src` to `sys.path` once at boot. |
| **2. `"Hello"` unpacks into 5 letters** | In both Python and Rust, `("Hello")` without a comma is just a string, not a 1-item tuple! | Always write a trailing comma `("Hello",)` when passing 1 argument to `call1` / `call_method1`. |
| **3. `run_chat()` hangs forever** | `run_chat()` runs a `while` loop calling terminal `input()` (`prompt_toolkit`). | Never call `run_chat()` from a GUI; call `execute_turn(prompt)` once per button click. |

## 1️⃣ Brick Wall #1 — Why Embedded Python Can't Find `coldwind` or `langgraph`

**Metaphor-first:** When you order food using your regular phone app (`uv run python`), your home address is already saved in your profile. When Rust wakes up an embedded Python library inside a compiled binary (`cargo run`), it is like **hiring a brand-new delivery driver who just arrived in town with an empty address book (`sys.path`)**. If you say *"Go to `coldwind.core`"*, the driver says *"I have no idea what street that is!"*

**Plain English (The Root Cause):**  
Remember from [`../uv-package-manager/shared/01-packaging-foundations.md`](../uv-package-manager/shared/01-packaging-foundations.md) how `import coldwind.core` works:
- Python walks a list of folder paths called **`sys.path`**.
- When you run `.venv/bin/python`, that binary automatically adds `.venv/lib/python3.13/site-packages/` to `sys.path` and reads the `.pth` signposts pointing to `core/src` and `desktop/src`.
- When your **Rust binary** starts, it loads the raw system `libpython` shared library. It does **not** automatically load your `.venv`'s `site-packages` or your `core/src` folder!

```text
Title: Why `uv run python` Finds `coldwind` vs Why Embedded Rust Starts Blind

1. Terminal (`uv run python`):
   sys.path = [
     ".../.venv/lib/python3.13/site-packages",  ◄── Has langgraph, pydantic, mcp
     ".../ai-workflow-task-agent/core/src",     ◄── From _coldwind_core.pth
     ".../ai-workflow-task-agent/desktop/src"   ◄── From _coldwind_desktop.pth
   ] -> `import coldwind.core` SUCCEEDS!

2. Embedded Rust Binary (Before We Fix `sys.path`):
   sys.path = [
     "/usr/lib/python3.13"                      ◄── System stdlib ONLY (`os`, `sys`, `math`)
   ] -> `import coldwind.core` CRASHES with ModuleNotFoundError!
```

**The Fix — Handing the Map to `sys.path` at Startup:**  
Right after `pyo3::prepare_freethreaded_python()`, we import `sys` (which is built into Python, so it always works!) and append our three folders to `sys.path`:

| Folder We Append to `sys.path` | What It Unlocks |
| :--- | :--- |
| **`<root>/.venv/lib/python3.13/site-packages`** | All third-party wheels (`langgraph`, `langchain`, `pydantic`, `mcp`, `neo4j`). |
| **`<root>/core/src`** | Your `coldwind.core.*` engine code. |
| **`<root>/desktop/src`** | Your `coldwind.desktop.*` adapter code. |

## 2️⃣ Brick Wall #2 — How `call0`, `call1`, and `call_method1` Work (And Why `(arg,)` Needs a Comma!)

**The Question Every Root-Cause Learner Asks:**  
*"In Python I just write `obj.step(a)` or `obj.step(a, b)`. Why does Rust make me write `obj.call_method1("step", (a,))` with extra parentheses and a weird comma?"*

**The Root Cause (Two Reasons):**
1. **Rust functions cannot take a random number of arguments.** In Rust (`learn_rust` Topic 00), every function must declare a fixed number of arguments. You cannot have `call_method(name, arg1)` and `call_method(name, arg1, arg2)` with the same name!
2. **How does PyO3 solve that?** Instead of taking 1, 2, or 5 separate arguments, `call_method1` always takes **exactly TWO arguments**:
   - Argument 1: The method name as a string (`"execute_turn"`).
   - Argument 2: **ONE Rust tuple** holding all the arguments you want to pass to Python!
     - Passing 2 items? Pass a 2-tuple: `("user", "hello")`.
     - Passing 3 items? Pass a 3-tuple: `("user", "hello", 42)`.
     - Passing **1 item**? You still have to pass a **1-tuple**!

**Why `("hello")` Without a Comma Is a Trap:**  
In both Python and Rust, putting parentheses around a single item `("hello")` or `(5)` does **NOT** make a tuple—it is just math grouping (like `(2 + 3)`), so `("hello")` is still just a plain string!  
To tell Rust (and Python) *"Hey, this is a 1-item tuple, not just parentheses!"*, you **must put a trailing comma inside the parentheses: `("hello",)`**.

```text
Title: The Forklift Pallet Rule — `("hello")` vs `("hello",)`

What `call_method1` expects: A Tuple (A wooden forklift pallet holding boxes)

  ❌ You write: `("hello")` (No comma)
     Rust sees: Just a raw string `"hello"`, NOT a tuple!
     Result:    Compiler error (`&str` is not `PyCallArgs`) or Python unpacks 5 chars!

  ✅ You write: `("hello",)` (With trailing comma!)
     Rust sees: A 1-element Tuple `(&str,)` -> Packs 1 box onto the pallet!
     Result:    Python receives `execute_turn("hello")`!
```

| What You Want to Call in Python | Number of Args | Exact PyO3 Method to Use | Why It Is Named That |
| :--- | :--- | :--- | :--- |
| **`cls()`** | `0` args | **`cls.call0()?`** | `0` means "zero arguments" (fastest: doesn't even build a tuple!). |
| **`cls(a)`** | `1` arg | **`cls.call1((a,))?`** | `1` means "takes 1 tuple of positional arguments". Notice `(a,)`! |
| **`cls(a, b)`** | `2` args | **`cls.call1((a, b))?`** | Still uses `call1`! Why? Because `(a, b)` is **1 tuple** containing 2 items! |
| **`obj.run()`** | `0` args | **`obj.call_method0("run")?`** | Calls `obj.run()` with zero arguments. |
| **`obj.run(a)`** | `1` arg | **`obj.call_method1("run", (a,))?`** | Calls `obj.run(a)` using the 1-tuple `(a,)`. |
| **`obj.run(a, k=v)`** | Args + Kwargs | **`obj.call_method("run", (a,), Some(&dict))?`** | Full version when you also need a `PyDict` of keyword arguments (`k=v`). |

> **💡 Aha! Moment — Why is it called `call1` even when passing 3 arguments `(a, b, c)`?**  
> Because in CPython's C code, the function is named `PyObject_CallObject(callable, args_tuple)`—it takes **1 tuple object** (plus `0` keyword dicts), whereas `call` takes **2 objects** (the args tuple + the kwargs dict), and `call0` takes **0 argument objects**!

## 3️⃣ Brick Wall #3 — Why GUI Apps Must Never Call `ChatInitializer.run_chat()`

In `coldwind-core`, `ChatInitializer` has a method called `run_chat()`. In your terminal app (`coldwind-desktop`), `main_orchestrator.py` calls `run_chat()` and everything works. Why can't our Rust GUI call `run_chat()`?

Look at what `run_chat()` actually does inside [`../../core/src/coldwind/core/engine/chat_initializer.py`](../../core/src/coldwind/core/engine/chat_initializer.py):

```python
# Inside coldwind-core (Simplified):
def run_chat(self):
    while not context.is_exiting():
        # ❌ STOPS AND WAITS FOR KEYBOARD INPUT IN THE TERMINAL!
        user_text = context.get_command_parser().get_user_input()
        self._state = self.graph.invoke(self._state)
```

- In a **terminal CLI**, the program *wants* to stop at `get_user_input()` and wait for you to type in the terminal.
- In a **Slint GUI**, the user is not typing into a terminal—they type into a Slint text box and click a button! If Rust calls `run_chat()`, Python stops forever at `get_user_input()` waiting for terminal input that never arrives.
- **The Fix (`HeadlessEngineAdapter.execute_turn`):** Instead of calling `run_chat()` (which owns the `while` loop), Rust owns the loop! Rust initializes `ChatInitializer()` once at startup, and each time the user clicks "Send", Rust calls `adapter.call_method1("execute_turn", (prompt,))?` to run **just one turn** of `self.graph.invoke(self.state)`!

| Model | Who Owns the `while` Loop? | How User Input Arrives | Works in a GUI? |
| :--- | :--- | :--- | :--- |
| **CLI Pull Model (`run_chat()`)** | Python owns the `while` loop | Python blocks waiting on `get_user_input()` | ❌ **NO** (Hangs worker thread!) |
| **GUI Push Model (`execute_turn(prompt)`)** | Rust worker owns the `while` loop | Slint UI pushes `prompt` when user clicks Send | ✅ **YES** (Clean 1-turn step!) |

## 4️⃣ Step-by-Step Code Walkthrough (Every Line Decoded)

Here is the exact Rust code that fixes all three brick walls: it sets up `sys.path`, instantiates `HeadlessEngineAdapter`, and runs one turn with `(prompt,)`:

```rust
use pyo3::prelude::*;
use pyo3::types::PyList;

pub fn boot_and_step_once(project_root: &str, user_prompt: &str) -> PyResult<String> {
    pyo3::prepare_freethreaded_python();

    Python::with_gil(|py| {
        // STEP 1: Give Python the map (`sys.path`) so it finds `.venv` and `coldwind`
        let sys = py.import("sys")?;
        let path: Bound<'_, PyList> = sys.getattr("path")?.extract()?;
        path.append(format!("{}/.venv/lib/python3.13/site-packages", project_root))?;
        path.append(format!("{}/core/src", project_root))?;
        path.append(format!("{}/desktop/src", project_root))?;

        // STEP 2: `from coldwind.desktop.gui_bridge import HeadlessEngineAdapter`
        let bridge_mod = py.import("coldwind.desktop.gui_bridge")?;
        let adapter_class = bridge_mod.getattr("HeadlessEngineAdapter")?;

        // STEP 3: `adapter = HeadlessEngineAdapter()` (0 args -> use `call0()`)
        let adapter = adapter_class.call0()?;

        // STEP 4: `reply = adapter.execute_turn(user_prompt)` (1 arg -> `(user_prompt,)`!)
        let reply_obj = adapter.call_method1("execute_turn", (user_prompt,))?;

        // STEP 5: Copy Python string into Rust String
        reply_obj.extract::<String>()
    })
}
```

| Step | Python Equivalent | Rust + PyO3 Line | Why We Wrote It Like That |
| :--- | :--- | :--- | :--- |
| **Step 1** | `sys.path.append(...)` | `path.append(...)?` | So embedded Python can find `langgraph` in `.venv` and `coldwind` in `core/src`. |
| **Step 2** | `from mod import Cls` | `py.import(...)?.getattr("Cls")?` | In Python, a class inside a module is just an attribute on that module object! |
| **Step 3** | `adapter = Cls()` | `adapter_class.call0()?` | Calling a class object in Python runs `__init__` and returns the new instance. |
| **Step 4** | `adapter.execute_turn(p)` | `adapter.call_method1("execute_turn", (user_prompt,))?` | Uses the trailing comma `(user_prompt,)` to pack 1 argument into a 1-tuple. |

## 5️⃣ How This Decodes Your Subdomain 02 Cheat Sheet

| Cheat Sheet Term | Plain-English Meaning |
| :--- | :--- |
| **`call0()` / `call_method0("m")`** | Call a function or method with **zero arguments** (fastest—no tuple created). |
| **`call1((a, b))` / `call_method1("m", (a,))`** | Call a function or method with **positional arguments** packed inside **one Rust tuple**. |
| **`call((a,), Some(&kwargs_dict))`** | Call a function when you also need named **keyword arguments** (`stream=True`) inside a `PyDict`. |

## ✅ Checkpoint (Prove It to Yourself — 5 Minutes)

| # | Question | Concrete Answer |
| :--- | :--- | :--- |
| **1** | Why is `call1` named `call1` even when you pass 3 arguments `obj.call_method1("f", (1, 2, 3))`? | Because it takes **1 tuple argument** `(1, 2, 3)` (and `0` keyword argument dictionaries). |
| **2** | What is wrong with `adapter.call_method1("execute_turn", (prompt))`? | Missing the trailing comma! `(prompt)` is just a string, not a 1-tuple `(prompt,)`. |
| **3** | Why do we append `.venv/lib/python3.13/site-packages` and `core/src` to `sys.path` in Rust? | Because a compiled Rust binary does not run `.venv/bin/python`, so CPython doesn't load `.venv` or `.pth` files automatically. |

## 📎 Glossary (Plain-English Dictionary)

| Term | Simple Everyday Meaning |
| :--- | :--- |
| **`sys.path`** | Python's list of folders where it looks whenever you write `import something`. |
| **1-Tuple `(x,)`** | A tuple containing just one item; the comma before `)` tells Rust and Python it's a tuple and not just parentheses. |
| **`getattr("name")`** | Looking up `.name` on a Python object (works for variables, functions, and classes inside a module). |
| **Decoupled Turn (`execute_turn`)** | Running just ONE question-and-answer step in LangGraph instead of trapping the thread in an infinite `while` loop (`run_chat`). |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | Do I have to append `core/src` to `sys.path` on every single turn? | No! `sys` is global inside the embedded Python interpreter. Append to `sys.path` **once** when the worker thread boots, and every future turn remembers it. | `2026-10-25` |
| **Q2** | Does `py.import("coldwind.core.engine")` re-parse the Python files if I call it twice? | No. Just like `import` in Python, `py.import` checks Python's `sys.modules` cache first and returns the already-loaded module in $\mathcal{O}(1)$ time. | `2026-10-25` |
| **Q3** | What happens if `execute_turn` crashes inside Python (for example, an API key is missing or Neo4j is offline)? | `call_method1` returns `Err(PyErr)`—and how to get the exact file and line number from that `PyErr` is the subject of Report `02-python-exceptions-and-tracebacks.md`! | `2026-10-25` |