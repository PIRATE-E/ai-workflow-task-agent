# Domain 3 — `pyproject.toml` Deep Dive: metadata, hatchling, and the `[tool.*]` tables

## Domain & Dependencies

- **Domain:** `shared`
- **Covers:** reading every section of this repo's pyprojects; what a build backend is; the full decode of the `src = ""` fix teased in Domain 0; the `[tool.*]` config parking lot (including what "lint" means).
- **Prerequisites:** Domain 0 (wheel, `.pth`, namespace), Domain 2 (add writes pyproject).
- **Prerequisite of:** Domain 5 (workspace tables are also `[tool.*]`).

> **TL;DR:** `pyproject.toml` is one file with three jobs: **ID card** (`[project]` — who the package is, what it needs), **builder's blueprint** (`[build-system]` + `[tool.hatch...]` — how a wheel gets made), and **config parking lot** (`[tool.*]` — settings for uv, ruff, pytest). The cryptic `src = ""` line is a path-rewrite rule that fixed this repo's broken editable `.pth`.

---

## Executive Summary

You will read `pyproject.toml` files far more often than you write them. The essential skill is knowing, for any line, **which of the three jobs it belongs to** — and that skill unlocks both member pyprojects and the root workspace file.

---

## 1️⃣ TOML in 30 seconds

**Metaphor-first:** TOML is a **filing cabinet**: `[section]` headers are drawer labels, `key = value` lines are files inside, and nested tables like `[tool.uv.workspace]` are folders inside folders.

```toml
title = "string"                   # a value
dependencies = ["a", "b"]          # a list
coldwind-core = { workspace = true }   # an inline table: one key with sub-keys
[project]                          # a table (drawer)
[tool.hatch.build.targets.wheel]   # a nested table (folder in folder)
```

That's all the TOML you need for this file.

---

## 2️⃣ `[project]` — the ID card

From the real `core/pyproject.toml`:

```toml
[project]
name = "coldwind-core"              # the PyPI-style package name (dash-form)
version = "1.9.1"                   # your version, bumped by you
description = "Cold Wind AI — shared agent core, MCP protocol, tools, RAG"
requires-python = ">=3.13"          # the contract uv enforces (venv runs 3.14)
dependencies = [                    # your declared shopping list (Domain 2)
    "langchain>=0.3.27",
    "pydantic>=2.11.7",
    ...
]
```

Note the two name spellings — **dash-form vs dot-form** — this bites everyone once:

```text
pyproject name:      coldwind-core          ← the DISTRIBUTION name (PyPI-style)
import in Python:    import coldwind.core   ← the PACKAGE name (folder-based)
```

**Extras — the "options menu":** `desktop` depends on `browser-use[video]`. The `[video]` suffix means *"install browser-use PLUS its optional video-recording extras."* Same package, bigger delivery.

---

## 3️⃣ `[project.scripts]` — the launcher button

```toml
[project.scripts]
coldwind = "coldwind.desktop.main_orchestrator:boot"
```

**Plain English:** this one line makes `uv sync` drop a `coldwind` command into `.venv/bin/`. Typing `coldwind` calls the `boot()` function inside `coldwind/desktop/main_orchestrator.py` — a **console entry point** (a labeled button wired straight to your function). The desktop pyproject marks it as a placeholder (run via `python -m` until finalized), but the mechanism is standard and worth recognizing.

---

## 4️⃣ `[build-system]` + hatchling — the contractor

```toml
[build-system]
requires = ["hatchling"]        # the tool needed to BUILD this package
build-backend = "hatchling.build"   # the program uv calls to do the building
```

**Metaphor-first:** from Domain 0 — `[project]` is the **blueprint**, and the build backend is the **contractor** who turns the blueprint into a deliverable wheel. uv knows how to *download and install* wheels; it doesn't know how to *make* one from raw source — so each package declares its own contractor. **Hatchling** is a modern, fast, minimalist contractor, and it's the one both members chose.

The two lines mean: *"to build me, you first need hatchling; then call its `build` program."*

---

## 5️⃣ The hatchling wheel tables — where Domain 0's bug gets fully decoded

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/coldwind/core"]      # what goes INSIDE the wheel

[tool.hatch.build.targets.wheel.sources]
src = ""    # rewrite rule: the folder src/ maps to the wheel ROOT
```

**Plain English, in two moves:**

1. `packages = ["src/coldwind/core"]` — *"the payload lives here."* Without the next line, hatchling preserves the folder structure and your code lands inside the wheel at `src/coldwind/core/...`
2. `src = ""` — *"rewrite `src/` to mean the root."* Now the same code lands at `coldwind/core/...` inside the wheel — exactly where Python's import rules (Domain 0: search path is the folder *above* the package) need it.

**Why that matters for editable installs:** when uv installs the member editable, hatchling computes the `.pth` signpost from these tables. Before the fix, the signpost pointed at `.../src/coldwind` (one level too deep → `coldwind.coldwind.core` → broken imports). After `src = ""`, it points at `.../src` — verified on this machine:

```text
_editable_impl_coldwind_core.pth → /home/pirate/development/ai-workflow-task-agent/core/src   ✓
```

> **💡 The 10-second version:** `packages` says *what* ships; `sources` says *where it sits* in the delivery box. Get "where" wrong and every import breaks — which is exactly the bug this repo hit and fixed.

---

## 6️⃣ `[tool.*]` — the config parking lot

**Metaphor-first:** `[tool.*]` is a **public parking lot**: any program (uv, ruff, pytest, hatch) may claim a numbered space named after itself. Seeing `[tool.ruff]` does NOT mean uv is doing something — it's just ruff parking its config here so you don't need a second file.

What's parked in this repo:

| Table | Owner | Purpose |
|---|---|---|
| `[tool.uv.workspace]` / `[tool.uv.sources]` | uv | workspace wiring (Domain 5) |
| `[tool.ruff]` | **ruff (the linter)** | code style + common-error checks; `lint.select = ["PTH", ...]` turns on rule groups (PTH = prefer `pathlib`, ASYNC = async correctness, UP028 = modernize) |
| `[tool.pytest.ini_options]` | pytest | test runner settings (`asyncio_mode = "auto"`) |
| `[tool.hatch.build...]` | hatchling | wheel building (section 5 above) |

**What "lint" means** (the word you asked about): a **linter** scans code without running it and flags style problems and suspicious patterns. `ruff` is this repo's linter; run it with `ruff check core/src/ desktop/src/ tests/`.

---

## 7️⃣ Root vs member — one file, different jobs

| Line | Root | `core/` | `desktop/` |
|---|---|---|---|
| `[project] dependencies` | **deliberately empty** — root ships nothing | the 27 real deps | 7 deps + `coldwind-core` |
| `[tool.uv.workspace]` | ✅ defines members | — | — |
| `[tool.uv.sources]` | ✅ | — | ✅ `coldwind-core = { workspace = true }` |
| hatch tables | — | ✅ | ✅ |

The root pyproject is a **coordinator, not a package** — its `[project]` block is just an ID card; all real work is declared by members.

---

## ✅ Checkpoint (read-only, 5 minutes)

```bash
# 1. Name spellings — prove dash vs dot to yourself
grep '^name' pyproject.toml core/pyproject.toml desktop/pyproject.toml
# 2. Find the entry point and say what command it creates
grep -A1 'project.scripts' desktop/pyproject.toml
# 3. Which pyproject declares YOUR dependency rules? (PTH rule lives where?)
grep -n 'lint.select' pyproject.toml
```

**Pass criteria:** for any random line in `desktop/pyproject.toml`, you can name its job — ID card, builder, or parked config — in under 5 seconds.

---

## 📎 Glossary additions

| Term | One-line meaning |
|------|-----------------|
| **TOML** | The filing-cabinet config format pyproject.toml is written in. |
| **distribution name** | Dash-form PyPI name (`coldwind-core`); differs from the import name. |
| **build backend** | The contractor program that turns source into a wheel (here: hatchling). |
| **hatchling** | The fast minimalist build backend both members use. |
| **entry point** | `[project.scripts]` line that installs a CLI command wired to a function. |
| **lint / linter** | A checker that flags style and suspicious code without running it (here: ruff). |

---

## ❓ Domain 3 Q&A Log

*(empty — questions from tutoring sessions get appended here, never overwritten)*
