# Domain 2 — Dependency Lifecycle: `uv add` vs `uv pip install`

## Domain & Dependencies

- **Domain:** `shared`
- **Covers:** the four verbs you'll use daily — `uv add`, `uv remove`, `uv sync`, `uv run` — and the escape hatch `uv pip install`.
- **Prerequisite:** Domain 1 (uv installed; pyproject exists).
- **Prerequisite of:** Domain 4 (lockfile), Domain 5 (workspace adds).

> **TL;DR:** `uv add` is a **triple write** — it updates `pyproject.toml`, re-resolves `uv.lock`, AND installs. `uv pip install` is a **cash sale** — it touches the shelf (`.venv`) only, and the next `uv sync` **evicts** whatever it added. Use `add` to declare, `pip install` only to experiment.

---

## Executive Summary

Every dependency question reduces to **"which of the three artifacts should change?"**

```text
pyproject.toml  (the CONTRACT — what you declare you need)
uv.lock         (the RECEIPT — the exact resolved graph)     ← introduced fully in Domain 4
.venv/          (the SHELF  — what is physically installed)
```

`uv add` changes all three, atomically. `uv pip install` changes only the shelf. That single difference drives every rule below.

---

## 1️⃣ `uv add` — declare it, file it, deliver it

**Metaphor-first:** `uv add` is **ordering furniture for the office with full paperwork**: the purchase goes in the company's contract book (pyproject), accounting re-issues the notarized receipt (lock), and the truck delivers it to the room (venv) — all in one step.

**Plain English:** `uv add rich` does three things, in order:

```text
uv add rich
  ├── 1. writes "rich>=<latest>" into pyproject.toml [project] dependencies
  ├── 2. re-solves the graph and rewrites uv.lock (rich + anything it pulls in, pinned exactly)
  └── 3. installs into .venv/ immediately
```

Useful variants (essentials only):

```bash
uv add rich                          # runtime dependency
uv add pytest --dev                  # dev-only group (not shipped to users)
uv add "langchain>=0.3.27"           # pin a minimum yourself
uv remove rich                       # the exact opposite: unfile + unresolve + uninstall
```

**In a workspace (this repo):** run `uv add` **inside the member whose pyproject should change** — `cd desktop && uv add rich` edits `desktop/pyproject.toml`, never core's. The lock and venv are shared, but the *declaration* is per-member.

---

## 2️⃣ `uv pip install` — the escape hatch (and its trap)

**Metaphor-first:** `uv pip install` is **paying cash, no receipt**: the item lands on the shelf instantly, no contract is signed, no ledger updated. It's perfect for a one-day experiment — and every ledger audit (`uv sync`) will **confiscate unrecorded items**.

**Plain English:** `uv pip install X` puts X into `.venv` **only**. No pyproject change. No lock change. This is deliberate — it's the pip-compatibility interface for throwaway work.

**The eviction trap (memorize this):**

```text
uv pip install cowsay            # shelf only — works
uv sync                          # "make the shelf match the lock EXACTLY"
                                 # → cowsay is REMOVED, because it's in no receipt
```

`uv sync`'s default behavior is **prune**: it removes anything in the venv that the lock doesn't vouch for. That's a feature — the venv can never drift into a state nobody can reproduce.

> **💡 When to legitimately use `uv pip install`:** quick experiments you *want* to disappear, reproducing a bug with one specific version, or CI debug sessions. If the package survives the day, it deserves `uv add`.

---

## 3️⃣ The decision table

| Command | `pyproject.toml` | `uv.lock` | `.venv/` | Survives next `uv sync`? |
|---|---|---|---|---|
| `uv add X` | ✅ writes dep | ✅ re-resolves | ✅ installs | ✅ yes |
| `uv add X --dev` | ✅ dev group | ✅ re-resolves | ✅ installs | ✅ yes (with `--group dev` syncs) |
| `uv remove X` | ✅ removes dep | ✅ re-resolves | ✅ uninstalls | — |
| `uv pip install X` | ❌ untouched | ❌ untouched | ✅ installs | ❌ **evicted** |
| `uv sync` | ❌ untouched | ❌ untouched (unless stale) | ✅ makes exact | — |

---

## 4️⃣ `uv sync` and `uv run` — the two daily verbs

**`uv sync`** — *"make the shelf equal the receipt."* Installs exactly what `uv.lock` says, nothing more, and prunes strays. This is the repo's "reproduce my environment" command. Variants you'll meet: `uv sync --frozen` (install from lock; refuse to re-resolve — CI safety) and `uv sync --inexact` (install but *don't* prune).

**`uv run`** — *"sync if needed, then run."* It guarantees the venv is up to date, then executes your command inside it — **no `source .venv/bin/activate` needed, ever**. This repo's documented run command is exactly that:

```bash
uv run python -m coldwind.desktop.main_orchestrator
```

---

## ✅ Checkpoint (safe sandbox, 5 minutes)

Do the experiment in a throwaway folder — NOT this repo:

```bash
cd "$(mktemp -d)" && uv init demo && cd demo

uv add rich                     # then: cat pyproject.toml  → rich is DECLARED
uv pip install cowsay           # then: cat pyproject.toml  → UNCHANGED
uv run python -c "import cowsay; print('cash sale on shelf')"
uv sync                         # cowsay is evicted — prove it:
uv run python -c "import cowsay" 2>&1 | tail -1   # → ModuleNotFoundError
```

**Pass criteria:** you can predict, before running any command, which of the three artifacts it will touch.

---

## 📎 Glossary additions

| Term | One-line meaning |
|------|-----------------|
| **`uv add`** | Declare + resolve + install, one atomic step. |
| **`uv remove`** | Retract the declaration, re-resolve, uninstall. |
| **`uv sync`** | Make `.venv` exactly match `uv.lock` (installs missing, prunes strays). |
| **`uv run`** | Auto-sync then execute — the "no activate needed" verb. |
| **prune / eviction** | `uv sync` deleting shelf items the lock doesn't vouch for. |
| **dev group** | `--dev` dependencies for development only, not shipped. |

---

## ❓ Domain 2 Q&A Log

*(empty — questions from tutoring sessions get appended here, never overwritten)*
