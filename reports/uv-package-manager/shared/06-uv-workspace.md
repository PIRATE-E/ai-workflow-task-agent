# Domain 5 — The uv Workspace: one repo, one lock, one room

## Domain & Dependencies

- **Domain:** `shared`
- **Covers:** what a workspace is and why this repo uses one; `[tool.uv.workspace]` and `[tool.uv.sources]` fully decoded; the shared venv + shared lock model; how the future `server/` member will be born; an end-to-end boot walkthrough.
- **Prerequisites:** Domains 0–4. This is the capstone — it assumes all previous vocabulary.
- **Closes:** the 6-domain curriculum.

> **TL;DR:** A workspace is **several installable packages that develop together inside one repo, sharing ONE lock and ONE `.venv`**. `[tool.uv.workspace]` names the family; `[tool.uv.sources] coldwind-core = { workspace = true }` says *"don't fetch `coldwind-core` from PyPI — use the sibling folder, editable."* Everything from Domains 0–4 was building toward this single picture.

---

## Executive Summary

Before the workspace, this repo was one giant flat package. The Phase 1 restructure split it into `coldwind-core` (the shared brain) and `coldwind-desktop` (the CLI), with `coldwind-server` planned. The problem a workspace solves: **how do separate packages import each other, stay version-locked to each other, and avoid N duplicate venvs — while living in one repo?**

---

## 1️⃣ The family estate metaphor

**Metaphor-first:** think of a **family estate**: each member keeps a private room with their own ID card (`core/pyproject.toml`), but everyone eats in **one shared kitchen** (`.venv/`) from **one shared pantry ledger** (`uv.lock`). No member shops for themselves; the estate shops once, for everyone.

**Plain English, three structural decisions:**

```text
pyproject.toml (root)
├── [tool.uv.workspace] members = ["core", "desktop", "server"]   ← THE FAMILY ROSTER
├── [tool.uv.sources]   coldwind-core = { workspace = true }      ← "use the sibling, not PyPI"
└── (no dependencies of its own — root ships nothing)
```

Verified live on this machine (`uv 0.11.32`):

```text
$ uv workspace list
cold-wind-ai          ← the root itself is a member (its pyproject has an ID card)
coldwind-core
coldwind-desktop
```

Note: `server` sits in the roster already, but since `server/` has no pyproject yet, uv simply finds nothing there — the declaration is **forward-looking**, ready for the day the folder exists.

---

## 2️⃣ `[tool.uv.sources]` — the routing override

```toml
[tool.uv.sources]
coldwind-core = { workspace = true }
```

**Plain English:** without this line, `uv add coldwind-core` in desktop's pyproject would send uv to **PyPI** looking for a package named `coldwind-core` (which doesn't exist publicly — failure). With it, uv routes that dependency to **the local workspace member**: installed **editable** (Domain 0's signpost), version taken from the sibling's pyproject, resolved into the shared lock as:

```toml
[[package]]
name = "coldwind-core"
source = { editable = "core" }    # from the estate, not the store
```

That's why `desktop` can declare plain `"coldwind-core"` with no version constraint — the estate member is always exactly "the version in the repo next to you."

---

## 3️⃣ Why ONE lock and ONE venv — the payoff

| Without workspace (N packages, N projects) | With workspace (this repo) |
|---|---|
| N separate `.venv/`, each resolving alone | **1 shared `.venv/`** at the root |
| N locks drifting apart; core updated in one, stale in another | **1 `uv.lock`** — members move atomically together |
| core installed as a *copy* into desktop's venv; edits invisible | core installed **editable** — edit `core/src/`, desktop sees it instantly |
| Cross-package version conflicts discovered at runtime | One resolution step catches conflicts across ALL members at `uv sync` time |

And the import layer (Domain 0) is what makes the merge seamless: the shared venv holds both `.pth` signposts (`core/src`, `desktop/src`), and the `coldwind` namespace package stitches the siblings into one importable family — `import coldwind.core` and `import coldwind.desktop` resolve side by side.

> **⚠️ One boundary uv does NOT enforce:** the architectural invariant *desktop imports core, core never imports desktop* is a **Python-level rule**, not a packaging one. uv wires the packages; the code's own import discipline keeps the layering. (Workspace members CAN see each other — that's the point — so the invariant lives in code review, enforced by convention and tests.)

---

## 4️⃣ How `server/` will be born (the recipe)

When the API-server roadmap item lands, a new member needs exactly four moves — no workspace surgery:

```bash
# 1. Scaffold the member folder + its own ID card
#    server/pyproject.toml: name = "coldwind-server", requires-python, deps incl. "coldwind-core"
#    + hatchling tables (copy desktop's: packages = ["src/coldwind/server"], sources src = "")
#    + [tool.uv.sources] coldwind-core = { workspace = true }

# 2. Root roster already lists "server" — nothing to edit there
# 3. Resolve + install into the shared kitchen
uv lock          # coldwind-server joins [manifest] members, editable entry appears
uv sync          # .pth signpost for server/src lands in the shared .venv
# 4. Code: mkdir server/src/coldwind/server/  (NO __init__.py in coldwind/ — Domain 0 pitfall!)
```

---

## 5️⃣ End-to-end: what happens when you run the app

```text
$ uv run python -m coldwind.desktop.main_orchestrator

 uv run
   └─ finds ROOT pyproject (workspace) ──► checks ONE uv.lock
        └─ uv sync (if anything drifted) ──► fills/repairs ONE shared .venv
             ├─ wheels from PyPI  (registry entries: exact pins + hashes)
             ├─ editable: core   (signpost → core/src)
             ├─ editable: desktop(signpost → desktop/src)
             └─ namespace merge: coldwind.core + coldwind.desktop = one family
                  └─ python -m coldwind.desktop.main_orchestrator boots
```

Every domain's knowledge appears in that trace: the **shelf** (Domain 0–1), the **signposts** (Domain 0), the **sync** (Domain 2), the **hatchling wheels** (Domain 3), the **receipt** (Domain 4), and the **estate** (Domain 5).

---

## ✅ Capstone Checkpoint (read-only, 5 minutes)

```bash
uv workspace list                     # the family roster, live
uv lock --check                       # the shared receipt is fresh
.venv/bin/python -c "import coldwind.core, coldwind.desktop; print('estate OK')"
ls .venv/lib/python3.14/site-packages/_editable_impl_*.pth   # both signposts in one kitchen
```

**Pass criteria:** you can explain (a) why desktop's `"coldwind-core"` dependency doesn't come from PyPI, (b) why there's only one `.venv` and one `uv.lock` for the whole repo, and (c) what four moves create `server/`.

---

## 📎 Glossary additions

| Term | One-line meaning |
|------|-----------------|
| **workspace** | A repo of several installable packages sharing one lock and one venv. |
| **member** | One package of the workspace (root, core, desktop — server pending). |
| **`[tool.uv.workspace]`** | The family roster: `members = [...]` folders uv treats as one estate. |
| **`[tool.uv.sources]`** | Routing override: `{ workspace = true }` = use the local sibling, editable. |
| **shared venv** | One `.venv/` at the root serving every member (all signposts, one kitchen). |

---

## ❓ Domain 5 Q&A Log

*(empty — questions from tutoring sessions get appended here, never overwritten)*
