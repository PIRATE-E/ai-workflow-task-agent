# Domain 1 — uv Setup & Project Bootstrap

## Domain & Dependencies

- **Domain:** `shared`
- **Covers:** what uv *is*, installing it, `uv init` (new projects), and converting an existing pip project.
- **Prerequisite:** Domain 0 (you know what a virtualenv, wheel, and `site-packages` are).
- **Prerequisite of:** Domain 2 (Dependency Lifecycle), Domain 5 (Workspace).

> **TL;DR:** uv is **one fast binary that replaces pip + venv + pip-tools** (and can even download Python itself). A new project starts with `uv init`; an **existing** pip project converts with `uv add -r requirements.txt`. This repo already made that journey — branch `phase1/uv-workspace-restrucure`.

---

## Executive Summary

Three things matter in this domain:

1. **What uv replaces** — so you stop reaching for pip muscle-memory.
2. **`uv init`** — the "new project from zero" path (not what this repo needed, but you must recognize it).
3. **The pip → uv conversion** — the path this repo actually took.

---

## 1️⃣ What uv is — the one-truck moving company

**Metaphor-first:** pip, venv, and pip-tools are **three separate companies** you used to coordinate: one installs, one builds rooms, one pins versions. uv is **one moving company with one truck** that does all three jobs, 10–100× faster (it's written in Rust and installs in parallel).

**Plain English:** one binary, four old jobs:

| Old tool | Old job | uv replacement |
|---|---|---|
| `pip install` | put packages on the shelf | `uv add` / `uv pip install` (Domain 2) |
| `python -m venv` | create the private room | `uv venv` (or automatic) |
| `pip-tools` / `pip freeze` | pin exact versions | `uv lock` (Domain 4) |
| `pyenv` | install Python versions | `uv python install` |

**Install (one of these):**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # official installer → ~/.local/bin/uv
# or: pip install uv    # works, but slower to upgrade
```

**This repo:** `uv 0.11.32` is installed; every command in this curriculum is run from the repo root so uv finds the workspace automatically.

---

## 2️⃣ `uv init` — starting from zero

**Metaphor-first:** `uv init` is the **construction crew that pours the foundation**: it scaffolds the files a uv project always needs, before any walls (code) go up.

**Plain English:** running `uv init` in an empty folder creates:

```text
my-project/
├── pyproject.toml     ← the ID card: name, version, requires-python, empty dependencies
├── .python-version    ← which Python uv should use here
├── main.py            ← a hello-world entry (applications only)
└── README.md
```

The three flavors worth recognizing:

| Command | Layout | Use when |
|---|---|---|
| `uv init` | flat, `main.py` | tiny script/app |
| `uv init --lib` | `src/<name>/` folder | a library others install |
| `uv init --package` | src layout **+ `[build-system]`** | an *installable* app — the closest single-project analog of this repo's members |

> **⚠️ This repo did NOT need `uv init`** — it already had code and a `requirements.txt`. Running `uv init` in an existing project is legal (it only adds missing files) but the meaningful step is the conversion below.

---

## 3️⃣ Converting an existing pip project — the path this repo took

**Metaphor-first:** you don't demolish a lived-in house to join a new utility company; you **switch the meters**: point uv at your existing room (`.venv`), move your shopping list into the modern format, then throw the old paperwork away.

**Plain English — the essential sequence:**

```bash
# 1. uv adopts (or creates) the private room — it automatically finds/creates .venv/
uv venv                                  # optional: uv creates .venv on first use anyway

# 2. MIGRATE the shopping list: requirements.txt → [project] dependencies
uv add -r requirements.txt               # writes deps into pyproject.toml AND resolves uv.lock

# 3. Verify, then retire the old paperwork
uv sync                                  # shelf now matches pyproject + lock
rm requirements.txt                      # pyproject.toml is now the single source of truth
```

Why `uv add -r` and **not** `uv pip install -r requirements.txt`: the second only fills the shelf — `pyproject.toml` stays empty and nothing is declared. `uv add` **files the paperwork too** (full difference in Domain 2).

**Proof it happened here:**

```text
git branch:  phase1/uv-workspace-restrucure        ← the migration has its own branch
pyproject:   requires-python = ">=3.13"           ← the contract uv enforces
.venv:       lib/python3.14/                       ← uv picked a satisfying Python (3.14)
```

---

## ✅ Checkpoint (read-only, 2 minutes)

```bash
uv --version                       # confirm uv ≥ 0.11 is on PATH
uv python list | head -3            # see Pythons uv knows about
ls .python-version 2>/dev/null      # does this repo pin one? (observe, don't change)
grep requires-python pyproject.toml
```

**Pass criteria:** you can say why `uv add -r requirements.txt` beats `uv pip install -r requirements.txt` during a migration.

---

## 📎 Glossary additions

| Term | One-line meaning |
|------|-----------------|
| **uv** | Single Rust binary by Astral replacing pip, venv, pip-tools, pyenv. |
| **`uv init`** | Scaffold a new uv project (pyproject, .python-version, entry file). |
| **`.python-version`** | Small file telling uv which interpreter this project wants. |
| **`uv venv`** | Create `.venv/` (usually unnecessary — uv auto-creates it). |
| **`uv python install`** | uv downloads a Python build for you. |

---

## ❓ Domain 1 Q&A Log

*(empty — questions from tutoring sessions get appended here, never overwritten)*
