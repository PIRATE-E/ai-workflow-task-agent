# 02 — Why `&mut self` Crashes Callbacks (`PyCell` Borrow Flags & Re-Entrant Sinks)

| Field | Value |
| :--- | :--- |
| **Domain** | `shared` / `desktop` (`cross-platform-docs`) |
| **Subdomain** | `03_python_driving_rust` |
| **Type** | Concept Note / Root-Cause Study Report |
| **Verification Mode** | `Codebase + Research` (PyO3 0.22+ `PyClass` Interior Mutability, `learn_rust` Topic 06 `RefCell<T>`) |
| **Confidence** | `VERIFIED ✅` |
| **Prerequisites** | [`./01-exposing-rust-to-python-pyclass.md`](./01-exposing-rust-to-python-pyclass.md), `learn_rust` Topic 06 (`RefCell<T>`) |
| **Updated** | `2026-10-25` |

> **TL;DR:** Because Python has no compile-time borrow checker, PyO3 wraps every `#[pyclass]` struct inside a runtime borrow checker (`PyCell`, identical to `RefCell<T>` from `learn_rust` Topic 06). If you write `&mut self` on a callback method and Python calls back into the same object while the first call is still on the stack, PyO3 crashes with `RuntimeError: Already borrowed` (`PyBorrowMutError`). Always use `&self` + a channel (`SyncSender`) or `Weak<AppWindow>` on callback sinks!

## Domain & Dependencies

| Item | Detail | Status |
| :--- | :--- | :--- |
| **Covers** | How `#[pyclass]` enforces Rust's borrowing rules at runtime (`PyCell`); why `&mut self` fails on nested callbacks; why `SyncSender` / `Weak<AppWindow>` are required inside `#[pyclass]`. | `VERIFIED ✅` |
| **Prerequisite** | [`./01-exposing-rust-to-python-pyclass.md`](./01-exposing-rust-to-python-pyclass.md) and `learn_rust` Topic 06 (`RefCell<T>`). | `VERIFIED ✅` |
| **Unlocks** | Full mastery of [`./cheat_sheet.md`](./cheat_sheet.md) and Subdomain 04 (`04_slint_concurrency_bridge`). | `VERIFIED ✅` |

## Executive Summary

You already mastered **`RefCell<T>`** in `learn_rust` Topic 06. That knowledge is about to pay off big time!

Remember the core rule of Rust (`learn_rust` Topic 01):
- You can have **many shared readers (`&self`)** at the same time, **OR**
- You can have **exactly ONE exclusive writer (`&mut self`)**—never both!

In pure Rust, the compiler checks that rule at **compile time**.  
**But wait:** once you hand a `#[pyclass]` object (`SlintEventSink`) over to Python, `rustc` cannot see what your Python code is going to do at runtime! In Python, 10 variables can point to `sink` at the same time. How does PyO3 stop Python from breaking Rust's memory safety rules?

**The Root Cause:** PyO3 puts a **`RefCell<T>`-style counter (`PyCell`)** inside every `#[pyclass]` object on the Python heap!

| Method Receiver You Write in `#[pymethods]` | What PyO3's Hidden `RefCell` Counter Does | What Happens If Python Calls Another Method on the Same Object Before the First Finishes |
| :--- | :--- | :--- |
| **`&self` (Shared Read)** | Adds `+1` to the reader counter (`borrow_flag > 0`). | ✅ **Works every time!** (Reader count goes `1 -> 2 -> 1 -> 0`). |
| **`&mut self` (Exclusive Write)** | Locks the writer flag (`borrow_flag = -1`). | 💥 **CRASH!** Raises `PyBorrowMutError` (`RuntimeError: Already borrowed`)! |

## 1️⃣ The Pain First — How `&mut self` Blows Up in Real Life (Re-Entrancy)

You might think: *"Wait—only one thread holds the GIL at a time! How could Python possibly call two methods on `SlintEventSink` at the same time?"*

**Answer: Nested calls on the same thread (called Re-Entrancy)!**  
Watch how easily this happens if someone writes `&mut self` on `SlintEventSink`:
1. Python calls `sink.emit_message(&mut self, ...)`. PyO3 sets `borrow_flag = -1` (Locked!).
2. Suppose `emit_message` calls a Python helper (or triggers a logging hook) before returning.
3. That hook calls `sink.emit_log(&mut self, ...)`.
4. PyO3 checks `sink`'s `borrow_flag`, sees it is **already `-1`** from step 1, and immediately aborts the call with **`RuntimeError: Already borrowed` (`PyBorrowMutError`)**!

```text
Title: How a Nested Call Triggers `PyBorrowMutError` When Using `&mut self`

Call Stack Frame 1: Python calls `sink.emit_message(&mut self)`
  │  • PyO3 sets `sink.borrow_flag = -1` (EXCLUSIVE LOCK HELD!)
  │
  └─► Call Stack Frame 2 (Before Frame 1 finishes!): Hook calls `sink.emit_log(&mut self)`
        • PyO3 checks `sink.borrow_flag` -> Sees `-1`!
        • Two `&mut self` references to the same Rust struct = Undefined Behavior!
        • PyO3 raises `PyBorrowMutError: Already borrowed`! 💥
```

| What You Assumed | What Actually Happened | How to Fix It Forever |
| :--- | :--- | :--- |
| "Only 1 thread has the GIL, so `&mut self` can never conflict." | A nested call on the *same* thread tried to borrow `sink` mutably while the outer call was still running! | Use **`&self`** on all callback methods! Sending on a channel (`tx.send()`) only needs `&self`, never `&mut self`! |

## 2️⃣ The Second Root-Cause Puzzle: Why `#[pyclass]` Demands `Send + Sync` Fields

Suppose you follow the `&self` rule and write:
```rust
// ❌ Why does rustc complain if we put a plain std::sync::mpsc::Sender<String> here in newer PyO3?
#[pyclass]
pub struct BrokenSink {
    tx: std::sync::mpsc::Sender<String>, // <-- Sender is `Send`, but NOT `Sync`!
}
```

**Why does PyO3 care about `Send` and `Sync` on a `#[pyclass]` struct?**  
Let's translate `Send` and `Sync` (`learn_rust` Topic 06/08 preview) into 10-year-old plain English:
- **`Send` ("Safe to mail to another thread"):** One thread can hand ownership of the object to another thread. (For example, `Rc<T>` and Slint's `AppWindow` are **`!Send`**—they are bolted to Thread 0's floor).
- **`Sync` ("Safe for two threads to read `&self` at the same time"):** Two threads can hold a shared `&self` reference to the object at the same time without corrupting anything.

Because our `#[pymethods]` use **`&self`**, and Python 3.13+ supports free-threaded execution (and multi-threaded Python scripts), PyO3 checks that the fields inside your `#[pyclass]` are safe to access through `&self` (`Sync`) and safe to move between threads (`Send`)!

Look at which channel/handle types pass both checks automatically:

| Field Type You Want to Put Inside `#[pyclass]` | Is It `Send`? | Is It `Sync` (`&self` safe)? | Works Inside `#[pyclass]` Out of the Box? |
| :--- | :--- | :--- | :--- |
| **`slint::Weak<AppWindow>`** | ✅ **YES** | ✅ **YES** | ✅ **YES! (Best choice for direct Slint updates)** |
| **`std::sync::mpsc::SyncSender<T>`** | ✅ **YES** | ✅ **YES** | ✅ **YES! (Best choice for bounded channels)** |
| **`std::sync::Mutex<mpsc::Sender<T>>`** | ✅ **YES** | ✅ **YES** | ✅ **YES! (Wraps regular `Sender` in a lock)** |
| **Plain `std::sync::mpsc::Sender<T>`** | ✅ **YES** | ❌ **NO (`!Sync`)** | ⚠️ Fails `Sync` check in PyO3 0.23+ unless wrapped in `Mutex` or replaced by `SyncSender`. |
| **Strong `slint::AppWindow` or `Rc<T>`** | ❌ **NO (`!Send`)** | ❌ **NO (`!Sync`)** | ❌ **NEVER** (`error[E0277]`). |

> **💡 10-Second Rule of Thumb:** Inside a `#[pyclass]` struct, either store **`slint::Weak<AppWindow>`** directly (which we'll use in Subdomain 04!) or store **`std::sync::mpsc::SyncSender<T>`**—both are `Send + Sync` AND let you send messages using only **`&self`**!

## 3️⃣ Step-by-Step Code Walkthrough (Comparing Broken vs Bulletproof)

Look at the side-by-side difference between a fragile `&mut self` struct and a bulletproof `&self` event sink:

```rust
use pyo3::prelude::*;
use std::sync::mpsc::{sync_channel, Receiver, SyncSender};

#[pyclass]
pub struct BulletproofSink {
    // SyncSender is both Send AND Sync, and `.send()` only requires `&self`!
    tx: SyncSender<String>,
}

#[pymethods]
impl BulletproofSink {
    // Shared `&self`: 10 nested Python functions can call this at once with ZERO panics!
    pub fn emit_message(&self, role: &str, text: &str) -> PyResult<()> {
        let _ = self.tx.send(format!("[{}] {}", role, text));
        Ok(())
    }

    pub fn emit_log(&self, info: &str) -> PyResult<()> {
        let _ = self.tx.send(format!("[LOG] {}", info));
        Ok(())
    }
}

pub fn create_sink_pair(py: Python<'_>) -> PyResult<(Py<BulletproofSink>, Receiver<String>)> {
    // Buffer capacity 1024 messages
    let (tx, rx) = sync_channel::<String>(1024);
    let py_sink = Py::new(py, BulletproofSink { tx })?;
    Ok((py_sink, rx))
}
```

| Detail in Code | What It Protects You From |
| :--- | :--- |
| **`tx: SyncSender<String>`** | Satisfies `Send + Sync` so `rustc` compiles `#[pyclass]` cleanly on all PyO3 versions. |
| **`pub fn emit_message(&self, ...)`** | Uses shared `&self` (`borrow_flag > 0`) so `emit_message` and `emit_log` never lock each other out. |
| **`let _ = self.tx.send(...)`** | Pushes the message into the Rust channel in `<1 microsecond` and returns `Ok(())` to Python immediately. |

## 4️⃣ How This Decodes Your Subdomain 03 Cheat Sheet

| Cheat Sheet Term | Plain-English Translation |
| :--- | :--- |
| **`PyCell` runtime borrow check** | The hidden `RefCell<T>` counter inside every `#[pyclass]` object on Python's heap. |
| **`PyBorrowMutError: Already borrowed`** | The error Python gets when you used `&mut self` and called a second method on the same object before the first finished. |
| **`Operation = Read/Send ⇒ Shared Aliasing (&self)`** | Because sending a message down a channel doesn't mutate the struct's fields directly, you only need `&self`. |

## ✅ Checkpoint (Prove It to Yourself — 5 Minutes)

| # | Check Question | Expected Root-Cause Answer |
| :--- | :--- | :--- |
| **1** | Why can't `rustc` check borrowing rules on a `#[pyclass]` struct at compile time? | Because once the object is passed into Python, dynamic Python code decides when to call its methods at runtime. |
| **2** | How does `&mut self` fail even when only 1 thread is running Python? | If Method A (`&mut self`) triggers a Python hook that calls Method B (`&mut self`) on the same object before Method A returns, the `PyCell` counter is still `-1` and panics! |
| **3** | Why is `SyncSender<T>` or `slint::Weak<AppWindow>` better than plain `mpsc::Sender<T>` inside `#[pyclass]`? | Because both `SyncSender<T>` and `Weak<AppWindow>` implement `Send + Sync`, satisfying PyO3's thread-safety check on `&self` methods without needing a `Mutex`. |

## 📎 Glossary (Plain-English Dictionary)

| Technical Term | Simple Everyday Meaning |
| :--- | :--- |
| **`PyCell`** | PyO3's built-in `RefCell` wrapper around every `#[pyclass]` that counts active `&self` and `&mut self` borrows at runtime. |
| **Re-Entrancy** | When Function A calls out to Python, and Python calls Function B on the *same* Rust object before Function A has finished. |
| **`Send` / `Sync`** | Rust marker traits: `Send` means "safe to move to another thread"; `Sync` means "safe for multiple threads to read via `&self`". |
| **`SyncSender<T>`** | The `Send + Sync` brother of `mpsc::Sender<T>` created via `std::sync::mpsc::sync_channel(capacity)`. |

## Q&A Log

| # | Question | Answer (concrete) | Date |
| :--- | :--- | :--- | :--- |
| **Q1** | What if my `#[pyclass]` struct genuinely needs to mutate a Rust counter or `Vec` inside a `&self` method? | Wrap just that field in `std::sync::Mutex<T>` (or `Cell`/`RefCell` if single-threaded) and keep the `#[pymethods]` signature as `&self`! | `2026-10-25` |
| **Q2** | Can I skip the `SyncSender` channel completely and have `SlintEventSink` send updates straight to the Slint window? | **YES!** By storing `slint::Weak<AppWindow>` directly inside `SlintEventSink`—which brings us to our final folder, Subdomain 04 (`04_slint_concurrency_bridge`)! | `2026-10-25` |