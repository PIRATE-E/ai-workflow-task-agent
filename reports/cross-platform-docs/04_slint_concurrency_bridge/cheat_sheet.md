# 🧩 Slint Concurrency Bridge & Event Loop Cheat Sheet & 30-Second Invariants

| Field | Value |
| :--- | :--- |
| **Tier** | `1 — Subdomain War Chest (C1–C12)` · per `cheatsheet_for_cheatsheet.md` |
| **Domain** | `desktop` (`cross-platform-docs/04_slint_concurrency_bridge`) |
| **Verified** | `2026-10-22` — verified against Slint 1.8+ `ComponentHandle`, `Weak`, `invoke_from_event_loop` & PyO3 |
| **Confidence** | `VERIFIED ✅` |

> **TL;DR:** Keep `AppWindow` (`!Send`) on Thread 0, pass `main_window.as_weak()` (`slint::Weak<AppWindow>`, which is `Send + Sync`) to the PyO3 worker thread, send user prompts from UI to worker via `mpsc::Sender`, and mutate UI properties from the worker via `ui_weak.upgrade_in_event_loop(move |ui| ...)` or `slint::invoke_from_event_loop`.
> **Primary Objective:** Within 30 seconds, scaffold a lock-free 60 FPS message bridge between Slint's main UI thread and a background PyO3 worker thread without `!Send` compiler errors, silent `upgrade() == None` bugs, or shutdown panics.
> **Master Guide:** [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) · **Concept Guide:** [`./README.md`](./README.md) · **Prev War Chest:** [`../03_python_driving_rust/cheat_sheet.md`](../03_python_driving_rust/cheat_sheet.md) · **Root War Chest:** [`../cheat_sheet.md`](../cheat_sheet.md)

## 📺 1. Curated Learning Sources

| Source | Why This Source | Verification |
| :--- | :--- | :--- |
| [Slint Rust Docs — `slint::invoke_from_event_loop`](https://releases.slint.dev/1.8.0/docs/rust/slint/fn.invoke_from_event_loop.html) | Authoritative API for queuing cross-thread closures onto Thread 0's event loop. | `VERIFIED ✅` |
| [Slint Rust Docs — `slint::Weak::upgrade_in_event_loop`](https://releases.slint.dev/1.8.0/docs/rust/slint/struct.Weak.html#method.upgrade_in_event_loop) | Combines event-loop dispatch and safe `Weak` upgrading on Thread 0 in one method call. | `VERIFIED ✅` |
| [PyO3 Guide — `Python::allow_threads` / `detach`](https://pyo3.rs/main/parallelism.html) | Releasing the CPython GIL during pure-Rust CPU compute or blocking I/O. | `VERIFIED ✅` |
| [`./README.md`](./README.md) | Subdomain 04 full derivation, Control Tower metaphors, and teardown protocol. | `VERIFIED ✅` |

## 🧭 2. 30-Second Decision Tree

Select the exact channel or Slint event-loop primitive based on the direction of communication between Thread 0 and Thread N.

```text
Title: Thread Dispatch Router in Slint + PyO3 Applications (Thread 0 <-> Thread N)

Where does the event start, and what needs to happen?
├─ 1. User clicks a button / presses Enter in Slint UI (Starts on Thread 0):
│  └─ Send command over `std::sync::mpsc::Sender<EngineCommand>`
│     • `let _ = cmd_tx.send(EngineCommand::RunTurn(text.to_string()));`
│     • NEVER call `Python::with_gil` on Thread 0!
│
├─ 2. Python worker emits a token or status update (Starts on Thread N):
│  ├─ Shorthand (Recommended) ──► `ui_weak.upgrade_in_event_loop(move |ui| { ui.set_prop(...); })`
│  └─ Explicit Event Loop ──────► `slint::invoke_from_event_loop(move || { if let Some(ui) = ui_weak.upgrade() { ... } })`
│     • NEVER call `ui_weak.upgrade()` outside the event-loop closure on Thread N (always returns `None`!)
│
├─ 3. Rust worker runs heavy native CPU work (e.g., RAG chunking) inside a Python call:
│  └─ Wrap pure-Rust block in `py.allow_threads(|| heavy_rust_compute())`
│
└─ 4. User closes the Slint window (`main_window.run()` returns on Thread 0):
   └─ Send `cmd_tx.send(EngineCommand::Shutdown)` + `worker_handle.join()`
```

| Action | Executing Thread | Allowed Handle | Method to Call | Latency |
| :--- | :--- | :--- | :--- | :--- |
| **Downgrade Window** | Thread 0 (Main) | `AppWindow` | `let w = main_window.as_weak();` | `< 0.1 µs` |
| **Push User Prompt** | Thread 0 (Main) | `mpsc::Sender<Cmd>` | `cmd_tx.send(EngineCommand::RunTurn(s))` | `~0.5 µs` |
| **Schedule UI Write** | Thread N (Worker) | `slint::Weak<AppWindow>` | `ui_weak.upgrade_in_event_loop(move \|ui\| ...)` | `~2–5 µs` |
| **Temporarily Drop GIL** | Thread N (Worker) | `py: Python<'py>` | `py.allow_threads(\|\| ...)` | `~0.2 µs` |

## ⚖️ 3. Invariant & Operations Matrix

Every interaction with Slint components obeys the Thread-0 Affinity & Weak-Upgrade Law:

$$\text{Thread} = \text{Thread 0} \implies \text{\texttt{AppWindow} + \texttt{Weak::upgrade()} Valid} \quad \big| \quad \text{Thread} = \text{Thread N} \implies \text{\texttt{Weak<AppWindow>} Only (\texttt{upgrade()} Returns \texttt{None}!)}$$

| Entity / Function | Lives on Thread 0? | Can Move to Thread N (`Send`)? | Can Share Ref Across Threads (`Sync`)? | Critical Safety Invariant |
| :--- | :--- | :--- | :--- | :--- |
| **`AppWindow`** | ✅ **YES** | ❌ **NO** (`!Send`) | ❌ **NO** (`!Sync`) | Backed by `Rc` and GPU surface; never leaves Thread 0. |
| **`slint::Weak<AppWindow>`** | ✅ **YES** | ✅ **YES** (`Send`) | ✅ **YES** (`Sync`) | Created via `.as_weak()`; safe inside `#[pyclass]`. |
| **`ui_weak.upgrade()`** | ✅ Returns `Some(ui)` | ⚠️ Returns **`None`** on Thread N! | N/A | Must ONLY be called inside a closure running on Thread 0! |
| **`upgrade_in_event_loop`** | ✅ **YES** | ✅ **YES** | ✅ **YES** | Queues closure to Thread 0 and runs it only if window is alive. |
| **`py.allow_threads`** | ❌ Never on T0 | ✅ **YES** (On Worker) | N/A | Closure inside cannot touch `Bound<'py, T>` pointers. |

## 🐍 4. Python & `learn_rust` Bridge Delta

| Mechanism | Python GUI (`Tkinter` / `PyQt`) Reality | Rust + Slint Reality | Owning `learn_rust` Topic |
| :--- | :--- | :--- | :--- |
| **Thread-Affine Widgets** | Mutating a widget from `threading.Thread` compiles/runs until it randomly segfaults C++. | `AppWindow` is `!Send`; `rustc` refuses to compile `thread::spawn` if it captures `AppWindow`. | **Topic 06 & 08:** `Rc<T>` (`!Send`) vs Thread Bounds |
| **Weak UI Reference** | `weakref.ref(window)()` can be dereferenced on any thread, racing with window destruction. | `slint::Weak<AppWindow>` is `Send + Sync`, and `.upgrade()` returns `None` unless called on Thread 0. | **Topic 06:** `Weak<T>` & `upgrade() -> Option<T>` |
| **UI Thread Dispatch** | `root.after(0, fn)` or `QMetaObject.invokeMethod` (untyped string/callback). | `ui_weak.upgrade_in_event_loop(move \|ui\| ...)` is statically typed and requires `FnOnce(AppWindow) + Send + 'static`. | **Topic 05 & 08:** `move` Closures (`FnOnce + Send`) |
| **GIL Release for CPU Work** | Python code cannot voluntarily release the GIL; only C/Rust extensions can call `Py_BEGIN_ALLOW_THREADS`. | `py.allow_threads(\|\| ...)` releases the GIL with compile-time proof that no `Bound<'py, T>` enters the closure. | **Topic 01 & 10:** Lifetime Bounds & FFI |

## 🧠 5. Physical Metaphor Register

| Mechanism | Physical Metaphor | 1:1 Mapping to Code |
| :--- | :--- | :--- |
| **`AppWindow` (`!Send`)** | **The Bolted Control-Tower Radar Console** | Hardwired to Thread 0's GPU display; cannot be carried down to the worker runway. |
| **`slint::Weak<AppWindow>`** | **The Pocket Walkie-Talkie Call-Sign** | Cloned via `main_window.as_weak()` and carried by worker threads (`Send + Sync`). |
| **`upgrade_in_event_loop`** | **Pneumatic Capsule Delivered to the Tower Operator** | Sends a closure up to Thread 0; the operator checks if the tower is still open and runs it on the console. |
| **`EngineCommand::Shutdown`** | **The End-of-Shift Whistle (Poison Pill)** | Sent after `main_window.run()` exits so the worker thread breaks its `while let Ok(cmd) = rx.recv()` loop cleanly. |

## 🛠️ 6. Syntax Bank

| Snippet # | Pattern | Use Case |
| :--- | :--- | :--- |
| **1** | **`upgrade_in_event_loop` Shorthand** | Cleanest 1-step way to update Slint properties from Thread N or `#[pymethods]`. |
| **2** | **`invoke_from_event_loop` Explicit Form** | Updating multiple components or running Thread-0 logic before upgrading `Weak`. |
| **3** | **Releasing the GIL with `py.allow_threads`** | Running pure-Rust RAG chunking or SHA-256 hashing without holding the CPython GIL. |

### 1. Updating Slint Properties via `upgrade_in_event_loop` (Recommended)
```rust
use slint::ComponentHandle;

pub fn append_streaming_token(ui_weak: &slint::Weak<crate::AppWindow>, token: String) {
    // Clones Weak handle, posts closure to Thread 0, and upgrades to `ui: AppWindow` automatically!
    let _ = ui_weak.upgrade_in_event_loop(move |ui| {
        let mut current = ui.get_chat_history().to_string();
        current.push_str(&token);
        ui.set_chat_history(current.into());
    });
}
```

### 2. Explicit `slint::invoke_from_event_loop` + `Weak::upgrade()`
```rust
use slint::ComponentHandle;

pub fn set_busy_indicator(ui_weak: slint::Weak<crate::AppWindow>, busy: bool) {
    let _ = slint::invoke_from_event_loop(move || {
        // Runs on Thread 0: upgrade() returns Some(ui) if window is still open
        if let Some(ui) = ui_weak.upgrade() {
            ui.set_is_busy(busy);
        }
    });
}
```

### 3. Releasing the GIL During Pure-Rust Compute (`py.allow_threads`)
```rust
use pyo3::prelude::*;

pub fn hash_document_without_gil(py: Python<'_>, raw_text: &Bound<'_, pyo3::types::PyString>) -> PyResult<usize> {
    // 1. Extract owned Rust String while holding the GIL ('py)
    let owned_text: String = raw_text.extract()?;

    // 2. Release GIL during pure-Rust CPU work (Bound<'py, T> cannot enter this closure!)
    let word_count = py.allow_threads(move || {
        owned_text.split_whitespace().count()
    }); // <-- GIL automatically re-acquired here!

    Ok(word_count)
}
```

## 🔬 7. Visual Memory Model

*How to read this:* Compare the failing attempt (calling `ui_weak.upgrade()` on Thread N before queuing) with the working pattern (moving `ui_weak` into `invoke_from_event_loop` and upgrading on Thread 0).

```text
Title: Why `ui_weak.upgrade()` Must Run INSIDE the Event Loop Closure (Thread N vs Thread 0)

❌ WRONG (Upgrading on Thread N):
  Thread N (Worker):
    let ui = ui_weak.upgrade(); // Checks current_thread == Thread 0 -> FALSE! Returns None!
    // UI never updates, and no compiler error is emitted!

✅ RIGHT (Moving Weak to Thread 0, Upgrading on Thread 0):
  Thread N (Worker)                           Thread 0 (Slint Event Loop)
  ┌──────────────────────────────┐            ┌──────────────────────────────────────┐
  │ let w = ui_weak.clone();     │            │ Closure popped on next 16.6ms tick:  │
  │ invoke_from_event_loop(      ├───────────►│   if let Some(ui) = w.upgrade() {    │
  │   move || { ... }            │  Slint     │       // current_thread == Thread 0! │
  │ );                           │  Queue     │       ui.set_chat_history(...);      │
  └──────────────────────────────┘            │   }                                  │
                                              └──────────────────────────────────────┘
```

| Call Location of `ui_weak.upgrade()` | Calling Thread | Thread Check Passes? | Return Value (While Window Open) |
| :--- | :--- | :--- | :--- |
| **Directly inside `#[pymethods]` or `thread::spawn`** | Thread N | ❌ **NO** | **`None`** (Silent failure!) |
| **Inside `slint::invoke_from_event_loop(move \|\| ...)`** | Thread 0 | ✅ **YES** | **`Some(AppWindow)`** |
| **Inside `ui_weak.upgrade_in_event_loop(move \|ui\| ...)`** | Thread 0 | ✅ **YES** | Passes `ui: AppWindow` directly |

## 🛡️ 8. Compiler Diagnostics Table

| Exact Diagnostic / Error | Rule Violated | Runtime Bug Prevented | Python Equivalent of the Bug |
| :--- | :--- | :--- | :--- |
| **`error[E0277]: `Rc<...>` cannot be sent between threads safely`** | Captured `AppWindow` inside `thread::spawn` or `invoke_from_event_loop` | Concurrent non-atomic refcount corruption and off-thread GPU calls | Calling Qt/Tkinter widget methods from a `threading.Thread` |
| **`error[E0599]: no method named `as_weak` found for struct `AppWindow`** | Missing `use slint::ComponentHandle;` in current module | Unresolved extension trait method (`learn_rust` Topic 07 prelude rule) | Calling an unimported protocol extension |
| **`error[E0277]: `Bound<'_, PyAny>` cannot be shared between threads safely`** | Tried to capture a `Bound<'py, T>` inside `py.allow_threads(\|\| ...)` | Reading/mutating a `PyObject*` after releasing the GIL | Dereferencing a `PyObject*` inside `Py_BEGIN_ALLOW_THREADS` |
| **`error[E0373]: closure may outlive the current function`** | Forgot `move` keyword on `invoke_from_event_loop(\|\| ...)` closure | Dangling stack reference after worker function returns | Late-binding closure variable capture bug |

## ⚠️ 9. Trap Archive (3-part form)

| # | Trap Name | Assumed | Reality | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **The Silent Off-Thread `upgrade()` Bug** | Calling `ui_weak.upgrade()` on the worker thread returns `Some(ui)` if the window is open. | `slint::Weak::upgrade()` checks that the current thread is Thread 0; calling it on Thread N always returns `None`! | Only call `.upgrade()` inside `invoke_from_event_loop`, or use `ui_weak.upgrade_in_event_loop(move \|ui\| ...)`. |
| **2** | **The Missing `use slint::ComponentHandle;`** | `.as_weak()`, `.run()`, and `.show()` are inherent methods on `AppWindow`. | They are trait methods on `slint::ComponentHandle`; without importing the trait, `rustc` raises `error[E0599]`. | Always add `use slint::ComponentHandle;` at the top of any file touching `AppWindow`. |
| **3** | **Micro-Token Event Loop Flooding** | Calling `invoke_from_event_loop` 50,000 times per second for byte-by-byte output is free. | Flooding the UI queue + copying a huge `SharedString` on every character causes $\mathcal{O}(N^2)$ string reallocation lag. | Coalesce/batch high-frequency tokens into `16ms–33ms` frames or append to a `VecModel` per message. |

### Trap 1: The Silent Off-Thread `ui_weak.upgrade()` Bug
- **Assumed:** You can call `let Some(ui) = self.ui_weak.upgrade() else { return; };` at the top of a worker thread function to check if the window is still open.
- **Reality:** Because `AppWindow` is `!Send`, `slint::Weak::upgrade()` is programmed to return `None` whenever called from any thread other than the main UI thread! Your code will silently early-return every time.
- **10-Second Recall Fix:** Move `ui_weak` into `slint::invoke_from_event_loop` first, and call `.upgrade()` *inside* the closure on Thread 0 (or call `ui_weak.upgrade_in_event_loop`).

### Trap 2: Missing `use slint::ComponentHandle;`
- **Assumed:** `main_window.as_weak()` works out of the box as soon as `AppWindow` is generated by `slint!`.
- **Reality:** Per `learn_rust` Topic 03 & Topic 07, trait methods are invisible unless their trait (`slint::ComponentHandle`) is in lexical scope.
- **10-Second Recall Fix:** Put `use slint::ComponentHandle;` at the top of every Slint module.

### Trap 3: $\mathcal{O}(N^2)$ `SharedString` Concatenation on Huge Chat Logs
- **Assumed:** Concatenating `ui.get_chat_history().to_string() + &token` on every single token scales indefinitely.
- **Reality:** Copying a 100KB chat log string 2,000 times during a long response copies 200MB of UTF-8 text on Thread 0 (`learn_rust` Topic 01/05 string reallocation trap).
- **10-Second Recall Fix:** Use a Slint `ModelRc<ChatMessage>` (`VecModel`) so only the active message row is updated, and batch token flushes to every `16ms–33ms` (30–60 Hz).

## ⏳ 10. Deferred Concepts (Manifest Boundary)

| Concept / Syntax | Manifest Status & Marker | What It Unlocks |
| :--- | :--- | :--- |
| **`std::thread::spawn` & `mpsc::channel`** | `⏳ Deferred until Topic 08 (Concurrency)` | Full formal derivation of OS threads, `JoinHandle`, `Send`/`Sync` auto-traits, and channel lifecycles. |
| **`slint::spawn_local` (Async UI Futures)** | `⏳ Deferred until Topic 11 (Async & Event Loops)` | Running local `!Send` async futures directly on Slint's Thread 0 event loop. |

## 📈 11. Family Learning Progression

```text
Title: Subdomain 04 Internal Progression

[1. ComponentHandle + .as_weak()] ──► [2. mpsc UI->Worker Channel] ──► [3. upgrade_in_event_loop] ──► [4. Poison-Pill Shutdown]
```

| Order | Milestone | Why Learn It Here |
| :--- | :--- | :--- |
| **1** | **`AppWindow` (`!Send`) vs `Weak<AppWindow>` (`Send`)** | Explains why `as_weak()` is the only legal handle to pass to `thread::spawn` or `#[pyclass]`. |
| **2** | **`mpsc` Prompt Channel (Thread 0 → Thread N)** | Keeps Slint button callbacks under `1µs` so the UI never drops below 60 FPS. |
| **3** | **`upgrade_in_event_loop` (Thread N → Thread 0)** | Safely mutates Slint properties from inside `#[pyclass] SlintEventSink`. |
| **4** | **Graceful Shutdown & `py.allow_threads`** | Ensures clean process exit and maximum multi-core throughput. |

## 📎 12. Concept Notes & Study Reports Directory

| Document | Relative Path | Scope & Invariants Covered | Status |
| :--- | :--- | :--- | :--- |
| **Subdomain 04 Concept Guide** | [`./README.md`](./README.md) | Full derivation of Thread 0 affinity, `Weak<AppWindow>`, `invoke_from_event_loop`, and shutdown. | `🟢 Complete` |
| **Subdomain 03 War Chest** | [`../03_python_driving_rust/cheat_sheet.md`](../03_python_driving_rust/cheat_sheet.md) | Prerequisite: `#[pyclass] SlintEventSink` and `&self` borrow safety. | `🟢 Complete` |
| **Root Master War Chest** | [`../cheat_sheet.md`](../cheat_sheet.md) | Master 1-page reference combining all 4 subdomains (`01`–`04`). | `🟢 Complete` |
| **Root Architecture Report** | [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) | Complete 14-section report, sequence diagrams, testing gates, glossary, and Q&A log. | `🟢 Complete` |