# 02 — Sending Updates Back to Thread 0 & Clean Shutdown (`invoke_from_event_loop` & Poison Pills)

| Field | Value |
| :--- | :--- |
| **Domain** | `desktop` (`ai-workflow-gui` / `cross-platform-docs`) |
| **Subdomain** | `04_slint_concurrency_bridge` |
| **Type** | Concept Note / Root-Cause Study Report |
| **Verification Mode** | `Codebase + Research` (Slint 1.8+ `invoke_from_event_loop`, `upgrade_in_event_loop`, PyO3 `allow_threads`) |
| **Confidence** | `VERIFIED ✅` |
| **Prerequisites** | [`./01-why-gui-windows-freeze-and-weak-handles.md`](./01-why-gui-windows-freeze-and-weak-handles.md) |
| **Updated** | `2026-10-25` |

> **TL;DR:** You can never call `ui_weak.upgrade()` directly on the background worker thread—Slint checks which thread is calling, sees you are not on Thread 0, and silently returns `None`! Instead, use `ui_weak.upgrade_in_event_loop(move |ui| ...)` (or `slint::invoke_from_event_loop`), which mails your closure back to Thread 0 so it runs safely on the next frame tick.

## Domain & Dependencies

| Item | Detail | Status |
| :--- | :--- | :--- |
| **Covers** | Why `ui_weak.upgrade()` returns `None` on Thread N; how `invoke_from_event_loop` and `upgrade_in_event_loop` work; why `upgrade()` protects against window-close crashes; `py.allow_threads` and Poison-Pill shutdown. | `VERIFIED ✅` |
| **Prerequisite** | [`./01-why-gui-windows-freeze-and-weak-handles.md`](./01-why-gui-windows-freeze-and-weak-handles.md). | `VERIFIED ✅` |
| **Closes** | The 4-subdomain `cross-platform-docs` curriculum and unlocks [`./cheat_sheet.md`](./cheat_sheet.md) + [`../cheat_sheet.md`](../cheat_sheet.md). | `VERIFIED ✅` |

## Executive Summary

In Report 01, we handed a `ui_weak: slint::Weak<AppWindow>` walkie-talkie to our background Python worker thread.

Now the Python worker finishes generating a reply (or streams a token into `SlintEventSink`) and wants to put that text onto the Slint screen. This report answers the final three root-cause questions of the architecture:
1. **Why does calling `ui_weak.upgrade()` on the worker thread silently return `None` every time?**
2. **How do `slint::invoke_from_event_loop` and `ui_weak.upgrade_in_event_loop` get our text onto the screen safely—even if the user slams the window `X` button mid-turn?**
3. **How do we shut down the background Python worker cleanly when the window closes (`EngineCommand::Shutdown`), and how do we let pure-Rust code run without holding the GIL (`py.allow_threads`)?**

| Task on the Worker Thread | The Wrong Way (And Why It Fails) | The Right Way (And Why It Works) |
| :--- | :--- | :--- |
| **Update Slint UI text from Thread N** | Call `ui_weak.upgrade()` directly on Thread N → **Always returns `None`!** | Call `ui_weak.upgrade_in_event_loop(move \|ui\| ...)` → Mails closure to Thread 0 and upgrades safely! |
| **Check if user closed the window** | Call `ui_weak.upgrade().unwrap()` → **Panics if window just closed!** | Use `if let Some(ui) = ui_weak.upgrade()` (or `upgrade_in_event_loop`, which skips automatically if closed!). |
| **Stop worker when window closes** | Let `main()` exit abruptly → **Leaves MCP subprocesses orphaned!** | Send `EngineCommand::Shutdown` ("Poison Pill") after `main_window.run()` returns. |

## 1️⃣ The Pain First — The Silent `ui_weak.upgrade() == None` Trap

Because you know `Weak::upgrade()` from `learn_rust` Topic 06, the very first thing you will try inside your background worker thread is this:

```rust
// ❌ SILENT BUG: Calling `.upgrade()` directly inside the worker thread!
thread::spawn(move || {
    // We are currently on Thread N (the background worker):
    if let Some(ui) = ui_weak.upgrade() {
        // THIS LINE NEVER RUNS! `upgrade()` returned `None`!
        ui.set_status_text("Done!".into());
    }
});
```

**Wait—the window is wide open on your monitor! Why did `ui_weak.upgrade()` return `None`?!**  
**The Root Cause:**  
Remember from Report 01 that `AppWindow` is **`!Send`**—it is only allowed to exist on **Thread 0**.
- If `ui_weak.upgrade()` returned `Some(AppWindow)` while you were standing on **Thread N**, then **Thread N would now be holding a strong `AppWindow`**—violating the `!Send` law and crashing your GPU!
- So inside Slint's source code, `Weak::upgrade()` has a built-in security check:
  $$\text{If } \texttt{current\_thread\_id} \neq \texttt{Thread 0} \implies \text{Return } \texttt{None} \text{ immediately!}$$

```text
Title: Why `ui_weak.upgrade()` Fails on Thread N vs Succeeds Inside `invoke_from_event_loop`

CASE 1: Called directly on Thread N (Worker Thread)
  ui_weak.upgrade() ──► Checks: "Am I on Thread 0?" ──► NO! (On Thread N) ──► Returns `None`!

CASE 2: Mailed to Thread 0 via `slint::invoke_from_event_loop`
  Thread N calls `invoke_from_event_loop(move || { ... })`
       │
       └──► Places closure in Slint's Mailbox ──► Thread 0 wakes up and runs closure:
            ui_weak.upgrade() ──► Checks: "Am I on Thread 0?" ──► YES! ──► Returns `Some(ui)`!
```

| Where You Call `ui_weak.upgrade()` | Which Thread Runs It? | What `.upgrade()` Returns (When Window Is Open) |
| :--- | :--- | :--- |
| **Directly inside `thread::spawn` or `#[pymethods]`** | Thread N (Worker) | **`None`** ❌ (Your UI silently stays blank!) |
| **Inside `slint::invoke_from_event_loop(move \|\| ...)`** | Thread 0 (Main UI) | **`Some(AppWindow)`** ✅ (Updates screen!) |

## 2️⃣ The Solution: Mailing a Letter to Thread 0 (`invoke_from_event_loop` & `upgrade_in_event_loop`)

**Metaphor-first:** Since the runway worker (Thread N) is not allowed to touch the radar console in the Control Tower (Thread 0), how does the worker update the screen?
- The worker writes instructions on a sticky note (`move || { ... }`), puts the walkie-talkie (`ui_weak`) in an envelope, and drops it into the **Control Tower Pneumatic Tube (`slint::invoke_from_event_loop`)**.
- Between movie frames on Thread 0, the Control Tower operator opens the envelope, upgrades `ui_weak` (which succeeds because the operator is standing on Thread 0!), and updates the screen!

Wait—what if the user clicked the **`X` button** to close the window 2 milliseconds *after* the worker put the envelope in the tube, right before Thread 0 opened it?
- Because `AppWindow` was destroyed when the window closed, `ui_weak.upgrade()` on Thread 0 sees that the strong count is `0`, returns **`None`**, and your `if let Some(ui) = ui_weak.upgrade()` block simply does nothing instead of crashing!

Even better, Slint gives you a **one-line shortcut** called **`ui_weak.upgrade_in_event_loop(move |ui| ...)`** that does BOTH steps (`invoke_from_event_loop` + `if let Some(ui) = ui_weak.upgrade()`) automatically!

| Pattern | Code You Write on Thread N | What It Does Behind the Scenes |
| :--- | :--- | :--- |
| **The 2-Step Explicit Way** | `slint::invoke_from_event_loop(move \|\| { if let Some(ui) = ui_weak.upgrade() { ui.set_busy(false); } });` | Sends closure to Thread 0; manually checks `if let Some(ui) = ui_weak.upgrade()`. |
| **The 1-Step Shorthand (Best!)** | `ui_weak.upgrade_in_event_loop(move \|ui\| { ui.set_busy(false); });` | Sends closure to Thread 0, calls `upgrade()` for you, and only runs your code if the window is still open! |

## 3️⃣ Two Final Production Polish Rules: `py.allow_threads` & Poison-Pill Shutdown

### Rule A: Taking a Break From the GIL (`py.allow_threads`)
Suppose inside a Python turn, your code calls a fast Rust function to split or hash 50 megabytes of text (`Rank #2` on your roadmap). While Rust is crunching pure Rust `String`s and `Vec`s, it doesn't touch any Python objects.
- If you wrap that pure-Rust work in **`py.allow_threads(|| { ... })`** (also called `py.detach` in PyO3 0.26+), Rust temporarily hangs the `py` GIL key back on the hook while crunching the data, and grabs it back when finished!

### Rule B: The "Poison Pill" Shutdown (`EngineCommand::Shutdown`)
When the user clicks the OS window `X` button:
1. `main_window.run()` on Thread 0 finishes and returns.
2. If `fn main()` just exits right there while `coldwind-core` has live MCP server subprocesses open, those subprocesses might be left behind!
3. Instead, right after `main_window.run()` finishes, Thread 0 sends **`EngineCommand::Shutdown`** (called a "Poison Pill" message) into the worker channel and waits (`worker.join()`) for the worker to call `ChatDestructor` and exit cleanly!

```text
Title: Clean Application Shutdown Sequence (The Poison Pill Pattern)

1. User clicks Window [X] ──► `main_window.run()` finishes on Thread 0
2. Thread 0 sends `cmd_tx.send(EngineCommand::Shutdown)` into channel
3. Worker Thread receives `Shutdown` ──► Calls Python `adapter.shutdown()` ──► Breaks `while` loop
4. Thread 0 completes `worker_handle.join()` ──► Process exits with 0 leaked subprocesses!
```

| Shutdown Step | Where It Runs | Why It Matters |
| :--- | :--- | :--- |
| **`main_window.run()` returns** | Thread 0 | Happens automatically the instant the user closes the Slint window. |
| **`cmd_tx.send(EngineCommand::Shutdown)`** | Thread 0 → Thread N | Wakes the sleeping worker thread so it knows the GUI is gone. |
| **`worker_handle.join()`** | Thread 0 | Waits ~50ms for Python's `ChatDestructor` to close MCP servers and flush logs before exiting. |

## 4️⃣ Step-by-Step Code Walkthrough (The Complete All-In-One Bridge)

Look at how all 4 subdomains (`01` → `04`) click together into one clean, readable Rust file—and notice that you now understand the root cause of **every single line**:

```rust
use pyo3::prelude::*;
use slint::ComponentHandle;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::thread;

slint::slint! {
    export component AppWindow inherits Window {
        in-out property <string> chat_log: "";
        in-out property <bool> is_busy: false;
        callback submit_prompt(string);
    }
}

pub enum EngineCommand {
    RunTurn(String),
    Shutdown, // <-- The Poison Pill for clean exit!
}

#[pyclass]
pub struct SlintEventSink {
    // Subdomain 03 + 04: `Weak<AppWindow>` is `Send + Sync`, so it sits directly inside `#[pyclass]`!
    ui_weak: slint::Weak<AppWindow>,
}

#[pymethods]
impl SlintEventSink {
    // Subdomain 03: Shared `&self` so nested Python callbacks never trigger `PyBorrowMutError`!
    pub fn emit_message(&self, role: String, content: String) -> PyResult<()> {
        let line = format!("[{}]: {}\n", role, content);

        // Subdomain 04: Mail update to Thread 0 and auto-upgrade `Weak -> AppWindow`!
        let _ = self.ui_weak.upgrade_in_event_loop(move |ui: AppWindow| {
            let mut current = ui.get_chat_log().to_string();
            current.push_str(&line);
            ui.set_chat_log(current.into());
        });
        Ok(())
    }
}

pub fn run_app() -> Result<(), slint::PlatformError> {
    let main_window = AppWindow::new()?;
    let (cmd_tx, cmd_rx): (Sender<EngineCommand>, Receiver<EngineCommand>) = channel();
    let worker_ui_weak = main_window.as_weak();

    // Spawn Thread N (The Background Python Worker)
    let worker_handle = thread::spawn(move || {
        // Subdomain 01: Flip CPython's master power switch once
        pyo3::prepare_freethreaded_python();

        while let Ok(cmd) = cmd_rx.recv() {
            match cmd {
                EngineCommand::RunTurn(prompt) => {
                    let _ = worker_ui_weak.upgrade_in_event_loop(|ui| ui.set_is_busy(true));

                    // Subdomain 01 & 02: Lock GIL on Thread N and call Python
                    Python::with_gil(|py| {
                        let _ = (py, &prompt); // Call `adapter.bind(py).call_method1("execute_turn", (prompt,))`
                    });

                    let _ = worker_ui_weak.upgrade_in_event_loop(|ui| ui.set_is_busy(false));
                }
                EngineCommand::Shutdown => break, // Clean exit!
            }
        }
    });

    // Wire Thread 0 Button Click -> Channel (`< 1 microsecond`, never touches GIL!)
    let ui_tx = cmd_tx.clone();
    main_window.on_submit_prompt(move |text| {
        let _ = ui_tx.send(EngineCommand::RunTurn(text.to_string()));
    });

    // Run 60 FPS Event Loop on Thread 0 until window closes, then shut down worker
    let res = main_window.run();
    let _ = cmd_tx.send(EngineCommand::Shutdown);
    let _ = worker_handle.join();
    res
}
```

| Subdomain | Which Lines in the Code Above It Owns |
| :--- | :--- |
| **Subdomain 01 (`01_pyo3_core_mechanics`)** | `pyo3::prepare_freethreaded_python()`, `Python::with_gil(\|py\| ...)`, `.unbind()` / `.bind(py)`. |
| **Subdomain 02 (`02_rust_driving_python`)** | Importing `coldwind`, calling `call_method1("execute_turn", (prompt,))`, and formatting `PyErr`. |
| **Subdomain 03 (`03_python_driving_rust`)** | `#[pyclass] pub struct SlintEventSink` and `#[pymethods] pub fn emit_message(&self, ...)`. |
| **Subdomain 04 (`04_slint_concurrency_bridge`)** | `main_window.as_weak()`, `mpsc::channel`, `upgrade_in_event_loop`, and `EngineCommand::Shutdown`. |

## ✅ Checkpoint (Prove It to Yourself — 5 Minutes)

Go back and open any of the 5 `cheat_sheet.md` files now—and verify how easily you can answer these three final questions:

| # | Check Question | Expected Root-Cause Answer |
| :--- | :--- | :--- |
| **1** | Why does `ui_weak.upgrade()` return `None` if you call it directly on the Python worker thread? | Because `AppWindow` is `!Send` and can only exist on Thread 0; Slint checks the current thread ID and returns `None` if you aren't on Thread 0. |
| **2** | What does `ui_weak.upgrade_in_event_loop(move \|ui\| ...)` do in one step? | It mails the closure to Thread 0's event loop, calls `ui_weak.upgrade()` on Thread 0, and runs your closure with `ui: AppWindow` only if the window is still open. |
| **3** | Why do we send `EngineCommand::Shutdown` after `main_window.run()` finishes? | So the sleeping background worker thread wakes up, runs Python's cleanup (`ChatDestructor`), and exits cleanly before the process terminates. |

## 📎 Glossary (Plain-English Dictionary)

| Technical Term | Simple Everyday Meaning |
| :--- | :--- |
| **`slint::invoke_from_event_loop`** | Mails a closure from any background thread to Thread 0 so it runs safely on the next UI frame tick. |
| **`ui_weak.upgrade_in_event_loop`** | Shortcut that mails a closure to Thread 0 and automatically upgrades `Weak<AppWindow>` to `AppWindow` if the window is still open. |
| **`py.allow_threads(\|\| ...)`** | Temporarily unlocks the Python GIL while Rust runs heavy pure-Rust CPU work, then re-locks it when done. |
| **Poison Pill (`EngineCommand::Shutdown`)** | A special "stop working" message sent into a channel so a background worker loop breaks and exits cleanly. |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | What happens if Python streams 10,000 tiny 1-character tokens per second into `upgrade_in_event_loop`? | If you copy a huge `chat_log` string 10,000 times a second, string copying slows down Thread 0. Either batch tokens in `16ms–33ms` chunks or push messages into a Slint `VecModel` row-by-row. | `2026-10-25` |
| **Q2** | Why do we need `move` in `upgrade_in_event_loop(move \|ui\| ...)`? | Because the closure travels across threads from Thread N to Thread 0 and runs *after* `emit_message()` has already returned—so the closure must take ownership (`move`) of `line: String`! | `2026-10-25` |