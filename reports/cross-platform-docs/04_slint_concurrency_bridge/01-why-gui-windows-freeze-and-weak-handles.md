# 01 — Why GUI Windows Freeze and Why `AppWindow` Refuses to Cross Threads (`60 FPS`, `!Send` & `Weak`)

| Field | Value |
| :--- | :--- |
| **Domain** | `desktop` (`ai-workflow-gui` / `cross-platform-docs`) |
| **Subdomain** | `04_slint_concurrency_bridge` |
| **Type** | Concept Note / Root-Cause Study Report |
| **Verification Mode** | `Codebase + Research` (Slint 1.8+ `ComponentHandle`, `Weak`, `learn_rust` Topic 06 `Rc`/`Weak`) |
| **Confidence** | `VERIFIED ✅` |
| **Prerequisites** | Subdomains 01–03, `learn_rust` Topic 06 (`Rc<T>` & `Weak<T>`) |
| **Updated** | `2026-10-25` |

> **TL;DR:** A 60 FPS GUI window must redraw the screen every `16.6 milliseconds` on Thread 0. If Thread 0 waits 10 seconds for Python (`Python::with_gil`), the window freezes ("Not Responding"). To fix this, we run Python on a background worker thread (Thread N)—and because Slint's `AppWindow` uses `Rc` pointers (`!Send`) bolted to Thread 0, we call `main_window.as_weak()` to hand the worker thread a thread-safe `slint::Weak<AppWindow>` radio handle.

## Domain & Dependencies

| Item | Detail | Status |
| :--- | :--- | :--- |
| **Covers** | Why running Python on Thread 0 freezes the window; why `AppWindow` cannot move to a background thread (`error[E0277]`); how `main_window.as_weak()` solves it. | `VERIFIED ✅` |
| **Prerequisite** | Subdomains 01–03 and `learn_rust` Topic 06 (`Rc<T>` vs `Weak<T>`). | `VERIFIED ✅` |
| **Unlocks** | [`./02-event-loop-dispatch-and-shutdown.md`](./02-event-loop-dispatch-and-shutdown.md) and [`./cheat_sheet.md`](./cheat_sheet.md). | `VERIFIED ✅` |

## Executive Summary

When you build your first Slint desktop app, you write a button callback `main_window.on_send_prompt(...)`. Your natural instinct is to put `Python::with_gil(|py| ...)` right inside that button callback.

When you do that, **your app works—until the user clicks the button.** The moment you click "Send":
1. The button stays stuck in its "pressed" animation.
2. You cannot type, scroll, or move the window for 10 seconds while the LLM thinks.
3. Linux (Wayland/Hyprland) pops up a dark box saying **"Application is not responding. Force Quit?"**

Then, when you try to fix the freeze by spawning a background thread (`std::thread::spawn`) and moving `main_window` into it, Rust refuses to compile with **`error[E0277]: Rc<...> cannot be sent between threads safely`**.

This report explains the exact root cause of both problems and how one method—**`main_window.as_weak()`**—solves them.

| The Problem You Hit | The Root Cause | The Exact Fix |
| :--- | :--- | :--- |
| **Window freezes when button is clicked** | Thread 0 draws 60 frames per second (`16.6ms` per frame). Waiting 10s for Python on Thread 0 skips 600 frames! | Spawn a background worker thread (`std::thread::spawn`) to run Python, and send prompts over an `mpsc` channel. |
| **`AppWindow` refuses to enter `thread::spawn` (`E0277`)** | `AppWindow` holds internal `Rc` pointers (`learn_rust` Topic 06) and GPU textures that have no thread locks (`!Send`). | Call `let ui_weak = main_window.as_weak();` on Thread 0 and move `ui_weak` (`slint::Weak<AppWindow>`) into the worker thread! |

## 1️⃣ Root Cause #1 — The 16.6-Millisecond Clock Inside Every GUI Window

**Metaphor-first:** Think of Thread 0 (your main GUI thread) as a movie projector operator who **must flip a new film frame onto the screen every 16.6 milliseconds** (60 times every second), while also checking if you moved your mouse or clicked a button.
- If you hand the projector operator a 500-page Python book (`execute_turn`) and say *"Read this whole book before you flip the next frame!"*, the movie screen freezes solid for 15 seconds!
- After 5 seconds of no frames flipping, your operating system assumes the program crashed and pops up the **"Wait or Force Close?"** popup!

```text
Title: What Happens to the 60 FPS Movie Projector When Python Runs on Thread 0

NORMAL 60 FPS LOOP ON THREAD 0:
  [Frame 1: 16ms] ──► [Frame 2: 16ms] ──► [Frame 3: 16ms] ──► [Frame 4: 16ms] (Smooth!)

❌ BROKEN (Calling `Python::with_gil` Inside Button Click on Thread 0):
  [Frame 1: 16ms] ──► [Click! Python LLM runs for 10,000ms... WINDOW FROZEN!] ──► [Frame 2]

✅ FIXED (Button Click Drops Note in Mailbox -> Worker Thread Runs Python):
  Thread 0 (UI):     [Frame 1] ──► [Click! Send to channel (0.001ms)] ──► [Frame 2] ──► [Frame 3]
                                           │
  Thread N (Worker):                       └──► [Python LLM runs 10,000ms on Thread N!]
```

| Thread | Its ONE Job | What It Is Forbidden to Do |
| :--- | :--- | :--- |
| **Thread 0 (Main UI Thread)** | Draw frames every `16.6ms`, animate spinners, and drop user clicks into a channel (`< 0.001ms`). | **NEVER call `Python::with_gil` or wait on network/LLM calls!** |
| **Thread N (Background Worker)** | Wait for messages from the channel, lock `Python::with_gil`, and run `coldwind-core`. | **NEVER hold the strong `AppWindow` handle directly!** |

## 2️⃣ Root Cause #2 — Why `AppWindow` Refuses to Move to Thread N (`!Send`)

Okay, so we know we must spawn a background worker thread (`std::thread::spawn`) for Python!  
Naturally, you write this:

```rust
// ❌ BROKEN ATTEMPT: Trying to move `main_window` into the background thread
let main_window = AppWindow::new()?;
std::thread::spawn(move || {
    // ERROR E0277: `Rc<...>` cannot be sent between threads safely!
    main_window.set_status_text("Thinking...".into());
});
```

**Why does Rust stop you with `error[E0277]: Rc<...> cannot be sent between threads safely`?**  
Remember **`Rc<T>`** from `learn_rust` Topic 06!
1. Inside Slint, `AppWindow` is a tree of hundreds of buttons, rectangles, and text boxes connected by **`Rc<T>`** smart pointers, plus direct pointers to your graphics card (Wayland/OpenGL/Vulkan).
2. Why did Slint's creators use `Rc<T>` instead of a thread-safe lock on every single rectangle? **Speed!** If your GPU had to lock and unlock a thread mutex 10,000 times per frame just to draw text and rectangles, your UI would lag and drain laptop battery.
3. Because `Rc<T>` uses a plain, unlocked reference counter (just like Python's `ob_refcnt`!), if Thread 0 and Thread N both held `AppWindow` at the same time, they would corrupt the `Rc` counter and crash the GPU driver!

*(Bonus Bridge: In Python's Tkinter or PyQt, if you modify a window widget from a background `threading.Thread`, Python doesn't stop you—and your app randomly segfaults in C++ 10 minutes later! Rust's `!Send` rule catches that exact bug at compile time before your program even runs!)*

| Handle Type | What Is Inside It | Can It Cross Threads (`Send`)? | Why? |
| :--- | :--- | :--- | :--- |
| **`AppWindow` (Strong Handle)** | `Rc<ComponentBox>` + GPU surface | ❌ **NO (`!Send`)** | Non-atomic `Rc` counter would corrupt if touched by 2 threads. |
| **`slint::Weak<AppWindow>`** | Atomic weak counter + Thread 0 ID | ✅ **YES (`Send + Sync`)** | Does not touch the UI widgets directly; acts as a safe remote address! |

## 3️⃣ The Solution: `main_window.as_weak()` — The Walkie-Talkie Call-Sign

How do we let the background worker thread talk back to the window without moving `AppWindow`?

**Metaphor-first:**
- `main_window` (`AppWindow`) is a **500-pound radar console bolted to the floor of the Control Tower (Thread 0)**. You cannot carry it out of the tower.
- Before the worker crew leaves the tower to go to the runway (Thread N), you call **`let ui_weak = main_window.as_weak();`**.
- That hands the worker crew a **pocket walkie-talkie (`slint::Weak<AppWindow>`)** tuned to the control tower's frequency!
- Because `slint::Weak<AppWindow>` uses an **atomic thread-safe counter**, you can clone it (`ui_weak.clone()`), send it into `std::thread::spawn`, and even store it directly inside your `#[pyclass] SlintEventSink` struct!

```text
Title: Bolted Console (`AppWindow`) vs Pocket Walkie-Talkie (`Weak<AppWindow>`)

THREAD 0 (Control Tower — Main UI)              THREAD N (Runway Crew — Python Worker)
┌───────────────────────────────────┐           ┌──────────────────────────────────────┐
│ let main_window = AppWindow::new()│           │ Moves into `thread::spawn(move ||)`: │
│  • Bolted to Thread 0 (!Send)     │           │  • Holds `ui_weak: Weak<AppWindow>`  │
│  • Calls `.as_weak()` ────────────┼──────────►│  • Implements `Send + Sync + Clone`! │
│  • Runs `main_window.run()`       │  Hands    │  • Can sit inside `#[pyclass]`!      │
└───────────────────────────────────┘  Walkie   └──────────────────────────────────────┘
```

| Action on `Weak<AppWindow>` | Allowed on Thread 0? | Allowed on Thread N (Worker)? | Why |
| :--- | :--- | :--- | :--- |
| **Create via `main_window.as_weak()`** | ✅ **YES** | ❌ **NO** | Must be downgraded from `main_window` on Thread 0 before spawning. |
| **Clone via `ui_weak.clone()`** | ✅ **YES** | ✅ **YES** | Increments atomic weak counter safely on any thread. |
| **Store inside `#[pyclass]`** | ✅ **YES** | ✅ **YES** | Implements `Send + Sync` so PyO3 accepts it as a struct field. |

## 4️⃣ Step-by-Step Code Walkthrough (How Thread 0 Spawns the Worker)

Look at the exact 4 steps on Thread 0 that set up the channel (`mpsc`) for outgoing prompts and the `Weak<AppWindow>` walkie-talkie for incoming replies:

```rust
use slint::ComponentHandle; // <-- Unlocks `.as_weak()` and `.run()`!
use std::sync::mpsc::channel;
use std::thread;

pub fn setup_window_and_worker(main_window: &crate::AppWindow) {
    // Step 1: Create a one-way mailbox (channel) from Thread 0 -> Worker Thread
    // `prompt_tx` = Sender (stays on Thread 0)
    // `prompt_rx` = Receiver (moves to Worker Thread)
    let (prompt_tx, prompt_rx) = channel::<String>();

    // Step 2: Create the thread-safe Walkie-Talkie (`Weak<AppWindow>`) on Thread 0
    let ui_weak: slint::Weak<crate::AppWindow> = main_window.as_weak();

    // Step 3: Spawn the background worker thread, moving `prompt_rx` and `ui_weak` inside!
    thread::spawn(move || {
        // The worker waits here at 0% CPU until the user clicks "Send":
        while let Ok(user_prompt) = prompt_rx.recv() {
            println!("Worker received prompt on background thread: {}", user_prompt);
            // (In Report 02, we will send the reply back using `ui_weak`!)
            let _ = &ui_weak;
        }
    });

    // Step 4: When user clicks "Send" on Thread 0, drop the text into `prompt_tx` (< 1 microsecond!)
    main_window.on_submit_prompt(move |text| {
        let _ = prompt_tx.send(text.to_string());
    });
}
```

| Line of Code | Why It Is Required |
| :--- | :--- |
| **`use slint::ComponentHandle;`** | Just like `use pyo3::prelude::*;`, `.as_weak()` lives on the `ComponentHandle` trait (`learn_rust` Topic 07 rule). Without this line, `rustc` says `no method named as_weak found`! |
| **`let (prompt_tx, prompt_rx) = channel();`** | Creates a thread-safe pipe: Thread 0 drops `String` prompts into `prompt_tx`, and Thread N pulls them out of `prompt_rx`. |
| **`let ui_weak = main_window.as_weak();`** | Creates the `Send + Sync` weak handle *before* `thread::spawn`, so `main_window` itself stays safely on Thread 0. |
| **`prompt_tx.send(text.to_string())`** | Takes less than `0.001 milliseconds`—so the Slint button callback finishes instantly and the UI stays at 60 FPS! |

## ✅ Checkpoint (Prove It to Yourself — 5 Minutes)

| # | Check Question | Expected Root-Cause Answer |
| :--- | :--- | :--- |
| **1** | Why does a 60 FPS window freeze if you run `Python::with_gil` inside a button callback on Thread 0? | Because Thread 0 has only `16.6ms` between frames; blocking Thread 0 for 10 seconds while Python runs stops the window from drawing or handling OS events. |
| **2** | Why did Slint make `AppWindow` `!Send` (using `Rc` instead of locks)? | Because locking mutexes on thousands of UI widgets every `16.6ms` would make rendering slow; keeping `AppWindow` on 1 thread allows fast, lock-free `Rc` pointers. |
| **3** | Which trait must you import at the top of your Rust file to unlock `.as_weak()` on `AppWindow`? | `use slint::ComponentHandle;` |

## 📎 Glossary (Plain-English Dictionary)

| Technical Term | Simple Everyday Meaning |
| :--- | :--- |
| **Thread 0 (Main Thread)** | The initial OS thread where `fn main()` and the Slint window (`main_window.run()`) live. |
| **60 FPS (`16.6ms` Frame Budget)** | Drawing 60 pictures per second ($1000\text{ ms} / 60 = 16.67\text{ ms}$); if any callback on Thread 0 takes longer than `16.6ms`, the UI stutters or freezes. |
| **`!Send` (Not Send)** | Rust compiler rule meaning *"This value is bolted to the current thread and may NEVER be moved to another thread."* |
| **`slint::Weak<AppWindow>`** | A lightweight, thread-safe (`Send + Sync`) remote handle to `AppWindow` created via `main_window.as_weak()`. |
| **`mpsc::channel()`** | "Multi-Producer, Single-Consumer" one-way pipe used to send messages from Thread 0 to the worker thread. |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | Does `while let Ok(prompt) = prompt_rx.recv()` burn 100% CPU while waiting for the user to type? | No! `recv()` puts the background worker thread to sleep in the OS kernel at **0% CPU** until `prompt_tx.send(...)` wakes it up. | `2026-10-25` |
| **Q2** | Once the worker thread has `ui_weak: Weak<AppWindow>`, can it just call `ui_weak.upgrade()` on the worker thread to update the text? | **NO!** Calling `ui_weak.upgrade()` directly on the worker thread is a famous silent bug (it always returns `None`!)—and why that happens is the exact subject of our final report, `02-event-loop-dispatch-and-shutdown.md`! | `2026-10-25` |