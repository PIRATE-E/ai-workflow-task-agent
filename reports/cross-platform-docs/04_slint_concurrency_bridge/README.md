# ⚡ Subdomain 04: Slint Concurrency Bridge & Event Loop Mechanics

| Field | Value |
| :--- | :--- |
| **Domain** | `desktop` (`ai-workflow-gui` / `cross-platform-docs`) |
| **Subdomain** | `04_slint_concurrency_bridge` |
| **Type** | Subdomain README + Tier 2 Concept Note Deep-Dive |
| **Prerequisites** | [`../01_pyo3_core_mechanics/README.md`](../01_pyo3_core_mechanics/README.md) → [`../03_python_driving_rust/README.md`](../03_python_driving_rust/README.md), `learn_rust` Topic 06 (`Weak<T>`) + `⏳ Topic 08` |
| **Verification Mode** | `Codebase + Research` (Slint 1.8+ `ComponentHandle`, `Weak`, `invoke_from_event_loop`, PyO3 `allow_threads`) |
| **Confidence** | `VERIFIED ✅` |
| **Updated** | `2026-10-22` |

> **TL;DR:** Slint component handles (`AppWindow`) use internal `Rc` pointers and GPU surfaces tied to Thread 0 (`!Send`). To keep the GUI responsive at 60 FPS while `coldwind-core` runs on a background thread, Thread 0 sends user prompts over an `mpsc::Sender<EngineCommand>`, passes `main_window.as_weak()` (`slint::Weak<AppWindow>`, which is `Send + Sync`) to the worker thread, and the worker dispatches UI mutations back to Thread 0 via `slint::invoke_from_event_loop`.
> **Scope:** Thread 0 UI event loop (`main_window.run()`), `!Send` window handles vs `Send + Sync` `slint::Weak<AppWindow>`, `slint::invoke_from_event_loop`, releasing the GIL during pure-Rust work (`py.allow_threads` / `py.detach`), and graceful Poison-Pill shutdown.
> **Python Bridge:** In Python GUI toolkits (Tkinter, PyQt), calling `label.setText("...")` from a background `threading.Thread` silently corrupts internal C++ widget trees or crashes with a segfault because Python has no compile-time `Send` trait. Rust + Slint makes cross-thread widget mutation a **compile-time error** (`error[E0277]: Rc<...> cannot be sent between threads safely`) and forces you to use `Weak<AppWindow>` + `invoke_from_event_loop`.

## 📺 Recommended Learning & Reference Sources

| # | Source & Link | Architectural Focus | Verification |
| :--- | :--- | :--- | :--- |
| **1** | [Slint Rust Docs — `slint::invoke_from_event_loop`](https://releases.slint.dev/1.8.0/docs/rust/slint/fn.invoke_from_event_loop.html) | Official specification for waking Thread 0's event loop and executing a closure on the UI thread. | `VERIFIED ✅` |
| **2** | [Slint Rust Docs — `slint::Weak` & `ComponentHandle`](https://releases.slint.dev/1.8.0/docs/rust/slint/struct.Weak.html) | Explains why `as_weak()` produces a `Send + Sync` handle and why `.upgrade()` only succeeds on Thread 0. | `VERIFIED ✅` |
| **3** | [PyO3 Parallelism Guide — `allow_threads` / `detach`](https://pyo3.rs/main/parallelism.html) | How a Rust worker temporarily releases the CPython GIL during heavy native Rust I/O or hashing. | `VERIFIED ✅` |
| **4** | [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md) | Parent architecture report tying all four subdomains into the unified Cold Wind desktop blueprint. | `VERIFIED ✅` |

## At a Glance & Subdomain Navigation

| Artifact | Relative Path | Type | What It Answers | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Subdomain Concept Guide (This File)** | [`./README.md`](./README.md) | Concept Note + Subdomain Index | Why is `AppWindow` `!Send`, how does `Weak<AppWindow>` cross threads, and how does `invoke_from_event_loop` work? | `🟢 Complete` |
| **Subdomain 04 War Chest** | [`./cheat_sheet.md`](./cheat_sheet.md) | Tier 1 Cheat Sheet (C1–C12) | 30-second thread dispatch router, full bidirectional wiring skeleton, and teardown race fixes. | `🟢 Complete` |
| **Previous Subdomain (`03`)** | [`../03_python_driving_rust/README.md`](../03_python_driving_rust/README.md) | Subdomain 03 Concept Guide | Exposing `#[pyclass] SlintEventSink` with `&self` methods to Python. | `🟢 Complete` |
| **Root Master War Chest** | [`../cheat_sheet.md`](../cheat_sheet.md) | Tier 1 Master War Chest | Single-page reference across all four subdomains (`01`–`04`). | `🟢 Complete` |

## 🐍 1. The Python vs Rust Architecture Comparison

In Python's `coldwind-desktop` CLI, the main thread runs a blocking loop (`prompt_toolkit`), and the terminal freezes until the turn finishes. In a native Slint GUI, Thread 0 must never block for more than `16.6ms` (60 FPS). Compare how a naive blocking callback fails versus how the dual-channel Rust + Slint bridge operates:

```python
# Naive Python GUI Anti-Pattern (Freezes Window & Risks Thread Crash!):
def on_send_clicked(user_text: str) -> None:
    # BAD 1: If run on main thread, UI freezes for 15 seconds!
    # BAD 2: If run on background threading.Thread, mutating `window.chat_box` directly
    #        from a worker thread causes random C++ segfaults in Qt/Tkinter!
    response = engine.execute_turn(user_text)
    window.chat_box.append(response)
```

```rust
// Rust + Slint + PyO3 (Compile-Time Enforced Thread Isolation):
use slint::ComponentHandle;
use std::sync::mpsc::channel;
use std::thread;

pub fn wire_non_blocking_gui(main_window: &crate::AppWindow) {
    let (prompt_tx, prompt_rx) = channel::<String>();

    // 1. Downgrade !Send AppWindow -> Send + Sync Weak<AppWindow> on Thread 0:
    let ui_weak: slint::Weak<crate::AppWindow> = main_window.as_weak();

    // 2. Spawn persistent background worker thread (Thread N):
    thread::spawn(move || {
        while let Ok(prompt) = prompt_rx.recv() {
            // Worker runs Python turn here (off Thread 0!), then posts result to UI queue:
            let ui_copy = ui_weak.clone();
            let _ = slint::invoke_from_event_loop(move || {
                // Executes on Thread 0! Safe to upgrade Weak -> Option<AppWindow>
                if let Some(ui) = ui_copy.upgrade() {
                    ui.set_status_text(format!("Finished: {}", prompt).into());
                }
            });
        }
    });

    // 3. UI button callback on Thread 0 returns in <1 microsecond:
    main_window.on_submit_prompt(move |text| {
        let _ = prompt_tx.send(text.to_string());
    });
}
```

| Architectural Property | Python Tkinter / PyQt Threading | Rust + Slint (`Weak<T>` + `invoke_from_event_loop`) |
| :--- | :--- | :--- |
| **Passing Widget to Worker Thread** | Allowed at runtime → crashes or corrupts GUI randomly | **Compile-time error (`error[E0277]: Rc<...> is !Send`)** |
| **Sending Weak Handle to Worker** | `weakref.ref` has no thread check | `main_window.as_weak()` returns `slint::Weak<T>` (`Send + Sync`) |
| **Upgrading `Weak` on Wrong Thread** | Not checked | `ui_weak.upgrade()` returns `None` if called outside Thread 0! |
| **Window Closed While Worker Runs** | Raises `RuntimeError: wrapped C/C++ object deleted` | `ui_weak.upgrade()` cleanly returns `None` (zero panic!) |

## 🧠 2. Physical Metaphors for Core Mechanics

1. **The Control Tower Glass Room (`Thread 0` & `!Send` `AppWindow`):**  
   The Slint `AppWindow` is a 500-pound radar console bolted to the floor of the Airport Control Tower (`Thread 0`). Because its wires are soldered directly into the tower's GPU display (`Rc`-backed, `!Send`), you cannot unbolt the radar console and carry it down to the runway crew (`Thread N`).
2. **The Walkie-Talkie Call-Sign (`slint::Weak<AppWindow>`):**  
   Calling `main_window.as_weak()` writes the control tower's radio frequency onto a pocket walkie-talkie (`Weak<AppWindow>`). You can hand copies of that walkie-talkie to any number of background worker threads (`Send + Sync + Clone`).
3. **The Pneumatic Mail Capsule (`slint::invoke_from_event_loop`):**  
   When the runway crew (`Thread N`) wants to change a number on the radar screen, they place instructions inside a capsule and shoot it up the pneumatic tube (`slint::invoke_from_event_loop(move || ...)`). When the tower operator (`Thread 0`) opens the capsule between frames, they check if the radar console is still powered on (`if let Some(ui) = ui_weak.upgrade()`) and flip the switch.

| Slint / PyO3 Primitive | Physical Metaphor | Thread Constraint |
| :--- | :--- | :--- |
| **`AppWindow` (Strong Handle)** | Bolted Radar Console | Must stay on Thread 0 (`!Send + !Sync`). |
| **`slint::Weak<AppWindow>`** | Pocket Walkie-Talkie Call-Sign | Can travel to any thread (`Send + Sync`), but `.upgrade()` only works on Thread 0. |
| **`slint::invoke_from_event_loop`** | Pneumatic Mail Tube to Tower | Callable from any thread; runs the closure on Thread 0 during the next frame tick. |
| **`py.allow_threads(\|\| ...)`** | Stepping Out of the Cleanroom | Temporarily releases the Python GIL while Rust performs heavy pure-Rust work. |

## 🔑 3. Core Mechanics & Step-by-Step Derivation

### 3.1 Connecting `learn_rust` Topic 06 (`Rc`/`Weak`) to `slint::Weak<AppWindow>`

In `learn_rust` Topic 06, you mastered `Rc<T>` (single-threaded reference counting, `!Send`) and `Weak<T>` (`Rc::downgrade`, `Weak::upgrade() -> Option<Rc<T>>`). Slint's component handle architecture is a direct industrial extension of Topic 06:
- `AppWindow` internally holds a pinned `Rc` to the component tree. Because `Rc` uses non-atomic reference counts for maximum 60 FPS rendering speed, `AppWindow` is `!Send`.
- `main_window.as_weak()` creates a `slint::Weak<AppWindow>` that uses an **atomic weak counter** and stores the ID of Thread 0.
- If you call `ui_weak.upgrade()` on Thread N (the Python worker), Slint checks `std::thread::current().id() == thread_0_id`, sees a mismatch, and returns **`None`**!
- Inside `slint::invoke_from_event_loop(move || { ... })`, the closure executes on **Thread 0**, so `ui_weak.upgrade()` returns **`Some(AppWindow)`** (unless the user already closed the window, in which case it returns `None`).

| Where `ui_weak.upgrade()` Is Called | Window Still Open | Window Already Closed by User |
| :--- | :--- | :--- |
| **Inside `slint::invoke_from_event_loop` (Runs on Thread 0)** | Returns **`Some(AppWindow)`** ✅ | Returns **`None`** ✅ (Safe no-op!) |
| **Directly inside `thread::spawn` (Runs on Thread N)** | Returns **`None`** ❌ (Silent bug!) | Returns **`None`** |
| **Via `ui_weak.upgrade_in_event_loop(move \|ui\| ...)`** | Runs closure with `ui: AppWindow` ✅ | Safely drops closure without running ✅ |

*(Pro Tip: Slint also provides the shorthand `ui_weak.upgrade_in_event_loop(move |ui| { ui.set_prop(...); })`, which combines `invoke_from_event_loop` and `if let Some(ui) = ui_weak.upgrade()` into a single call!)*

### 3.2 Releasing the GIL During Pure-Rust Work (`py.allow_threads` / `py.detach`)

When `coldwind-core` invokes a Rust-accelerated RAG chunker or SHA-256 file hasher (`Rank #2` on Piyush's roadmap), the Rust code does not touch any `PyObject` pointers while hashing bytes. Holding the GIL during 200ms of pure-Rust file hashing blocks any other Python thread from running. Wrapping the pure-Rust computation in `py.allow_threads(|| { ... })` (or `py.detach(|| { ... })` in PyO3 0.26+) temporarily releases the GIL and re-acquires it when the closure finishes.

## 🔬 4. Visual Invariant Models & Memory Layouts

*How to read this:* Trace the two-way non-blocking loop between Thread 0 (left) and Thread N (right). Notice that no lock is ever shared between Thread 0 and Thread N.

```text
Title: Lock-Free Dual-Loop Architecture (Thread 0 Slint Event Loop <-> Thread N PyO3 Worker)

THREAD 0 (Main OS Thread — 60 FPS UI)          THREAD N (Background Worker Thread)
┌────────────────────────────────────────┐     ┌────────────────────────────────────────┐
│ 1. User clicks "Send" button           │     │ 2. Worker wakes from `prompt_rx.recv()`│
│    • Callback runs `prompt_tx.send(p)` ├────►│    • Acquires `Python::with_gil(|py|)` │
│    • Finishes in 0.5 µs (No GIL!)      │mpsc │    • Calls `adapter.execute_turn(p)`   │
│                                        │     │                                        │
│ 5. Next 16.6ms Frame Tick on Thread 0: │     │ 3. Python streams token to Rust sink:  │
│    • Pops closure from Slint Queue     │     │    • `SlintEventSink::emit_token(&self)`│
│    • `ui_weak.upgrade()` -> `Some(ui)` │◄────┤ 4. Calls `invoke_from_event_loop`:     │
│    • Mutates `ui.set_chat_log(...)`    │Event│    • Moves `Weak<AppWindow>` + `String`│
│    • GPU renders updated frame         │Queue│    • Returns immediately to Python!    │
└────────────────────────────────────────┘     └────────────────────────────────────────┘
```

| Channel / Queue | Direction | Payload Type | Blocking Behavior |
| :--- | :--- | :--- | :--- |
| **`mpsc::channel::<EngineCommand>()`** | Thread 0 → Thread N | `EngineCommand::RunTurn(String)` | Sender never blocks; Receiver sleeps at 0% CPU when idle. |
| **Slint Internal Event Queue** | Thread N → Thread 0 | `Box<dyn FnOnce() + Send>` | `invoke_from_event_loop` never blocks caller; wakes Thread 0. |

## ⚖️ 5. Universal Invariant & Operations Matrix

The fundamental concurrency law of the Slint + PyO3 bridge separates thread-local UI ownership from cross-thread weak message passing:

$$\text{Handle} = \texttt{AppWindow} \implies \text{Thread 0 Exclusive (\texttt{!Send})} \quad \big| \quad \text{Handle} = \texttt{Weak<AppWindow>} \implies \text{Cross-Thread Safe (\texttt{Send + Sync}) + Upgrade on Thread 0}$$

| Operation / Type | Allowed on Thread 0? | Allowed on Thread N? | Implements `Send`? | What Happens If Misused |
| :--- | :--- | :--- | :--- | :--- |
| **`AppWindow::new()?` / `.run()`** | ✅ **YES** | ❌ **NO** | ❌ **NO** (`!Send`) | Compiler rejects moving `AppWindow` across threads (`E0277`). |
| **`main_window.as_weak()`** | ✅ **YES** | ✅ **YES** (via `.clone()`) | ✅ **YES** (`Send + Sync`) | Produces a thread-safe weak handle. |
| **`ui_weak.upgrade()`** | ✅ **YES** (`Some(ui)`) | ❌ **NO** (Returns `None`!) | N/A | Calling `.upgrade()` on Thread N silently returns `None`! |
| **`slint::invoke_from_event_loop`** | ✅ **YES** | ✅ **YES** | Closure requires `Send + 'static` | Queues closure onto Thread 0's event loop safely. |
| **`ui_weak.upgrade_in_event_loop`** | ✅ **YES** | ✅ **YES** | Closure requires `Send + 'static` | Queues closure and auto-upgrades `ui` on Thread 0 if alive. |

## 🛠️ 6. Production Blueprint & Code Patterns

| Component | Role in Blueprint | Key Safety Mechanism |
| :--- | :--- | :--- |
| **`EngineCommand` Enum** | Carries `RunTurn(String)` and `Shutdown` commands from UI to Worker. | Cleanly terminates the worker loop when `main_window.run()` exits. |
| **`DirectSlintSink` (`#[pyclass]`)** | Dispatches UI updates directly from `#[pymethods]` via `upgrade_in_event_loop`. | Eliminates an extra intermediate thread by queuing directly to Slint's event loop! |

```rust
use pyo3::prelude::*;
use slint::ComponentHandle;
use std::sync::mpsc::{channel, Receiver, Sender};
use std::thread;

slint::slint! {
    export component AppWindow inherits Window {
        in-out property <string> chat_history: "";
        in-out property <bool> is_busy: false;
        callback request_turn(string);
    }
}

pub enum EngineCommand {
    RunTurn(String),
    Shutdown,
}

#[pyclass]
pub struct DirectSlintSink {
    // slint::Weak<AppWindow> is Send + Sync — can live directly inside #[pyclass]!
    ui_weak: slint::Weak<AppWindow>,
}

#[pymethods]
impl DirectSlintSink {
    /// Invoked by Python's MessageDisplayInterface on Thread N
    pub fn emit_message(&self, role: String, content: String) -> PyResult<()> {
        let formatted = format!("[{}]: {}\n", role, content);
        // Queues closure onto Thread 0 and only runs if AppWindow is still alive!
        let _ = self.ui_weak.upgrade_in_event_loop(move |ui: AppWindow| {
            let mut history = ui.get_chat_history().to_string();
            history.push_str(&formatted);
            ui.set_chat_history(history.into());
        });
        Ok(())
    }
}

pub fn launch_gui_application() -> Result<(), slint::PlatformError> {
    let main_window = AppWindow::new()?;
    let (cmd_tx, cmd_rx): (Sender<EngineCommand>, Receiver<EngineCommand>) = channel();

    // 1. Create Send + Sync Weak handle on Thread 0
    let worker_ui_weak = main_window.as_weak();

    // 2. Spawn persistent PyO3 worker thread
    let worker_join = thread::spawn(move || {
        pyo3::prepare_freethreaded_python();
        while let Ok(cmd) = cmd_rx.recv() {
            match cmd {
                EngineCommand::RunTurn(prompt) => {
                    let _ = worker_ui_weak.upgrade_in_event_loop(|ui| ui.set_is_busy(true));
                    // Execute Python turn here via Python::with_gil(...)
                    let _ = prompt;
                    let _ = worker_ui_weak.upgrade_in_event_loop(|ui| ui.set_is_busy(false));
                }
                EngineCommand::Shutdown => break,
            }
        }
    });

    // 3. Wire UI callback (non-blocking channel send)
    let ui_cmd_tx = cmd_tx.clone();
    main_window.on_request_turn(move |prompt| {
        let _ = ui_cmd_tx.send(EngineCommand::RunTurn(prompt.to_string()));
    });

    // 4. Run Thread 0 event loop until user closes window, then send Poison Pill
    let run_result = main_window.run();
    let _ = cmd_tx.send(EngineCommand::Shutdown);
    let _ = worker_join.join();
    run_result
}
```

## ⚠️ 7. Learner Pitfall Archive

| # | Pitfall Name | What Was Written | Exact Compiler / Runtime Symptom | 10-Second Recall Fix |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Upgrading `Weak` Outside `invoke_from_event_loop`** | Calling `if let Some(ui) = ui_weak.upgrade()` directly inside `thread::spawn` | `upgrade()` always returns `None` on Thread N; UI never updates and no error is printed! | Always call `.upgrade()` *inside* `slint::invoke_from_event_loop` (or use `upgrade_in_event_loop`). |
| **2** | **Moving `AppWindow` into `thread::spawn`** | `thread::spawn(move \|\| { main_window.set_is_busy(true); })` | `error[E0277]: Rc<...> cannot be sent between threads safely` | Call `let ui_weak = main_window.as_weak();` before `thread::spawn` and move `ui_weak`. |
| **3** | **Orphaned Worker Thread on Exit** | Exiting `main()` after `main_window.run()` without signaling the worker | Background Python MCP subprocesses remain orphaned if worker is blocked | Send `EngineCommand::Shutdown` after `main_window.run()` returns and `.join()` the worker. |

## ✅ 8. Checkpoint & Pass Criteria

Verify your mastery of Subdomain 04 by tracing what happens in each scenario below:

| Scenario | What Happens at Runtime | Why |
| :--- | :--- | :--- |
| **Calling `ui_weak.upgrade()` on Thread N (before `invoke_from_event_loop`)** | Always returns **`None`** (UI silently fails to update!). | Slint verifies the calling thread ID; `AppWindow` can only be instantiated or upgraded on Thread 0. |
| **User closes window `1ms` before `upgrade_in_event_loop` runs** | Closure is safely ignored; zero panics or segfaults. | The strong `Rc` count on Thread 0 dropped to `0`, so the weak upgrade cleanly yields `None`. |
| **Rust worker hashes a 50MB file inside a Python tool** | Wrap hashing in `py.allow_threads(\|\| hash_bytes(&buf))` | Releases the CPython GIL during pure-Rust CPU work so other Python tasks aren't blocked. |

## 🎯 9. Core Systems Invariants & Reading Path

| Invariant # | Statement | Next Step in Reading Path |
| :--- | :--- | :--- |
| **1. The Thread 0 Affinity Law** | `AppWindow` is strictly `!Send`; only `slint::Weak<AppWindow>` may cross into `thread::spawn` or `#[pyclass]`. | Review [`./cheat_sheet.md`](./cheat_sheet.md) for 30-second recall. |
| **2. The Upgrade-On-Thread-0 Law** | Never call `ui_weak.upgrade()` on the worker thread; always upgrade inside `invoke_from_event_loop` or via `upgrade_in_event_loop`. | Review the master war chest at [`../cheat_sheet.md`](../cheat_sheet.md). |
| **3. The Poison-Pill Shutdown Law** | When `main_window.run()` returns on Thread 0, send `EngineCommand::Shutdown` so `ChatDestructor` cleans up MCP servers cleanly. | Cross-check with [`../00_pyo3_slint_architecture_report.md`](../00_pyo3_slint_architecture_report.md). |