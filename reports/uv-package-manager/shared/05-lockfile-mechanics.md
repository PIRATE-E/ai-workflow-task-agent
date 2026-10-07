# Domain 4 — Lockfile Mechanics: reading `uv.lock`, updating it, and untangling conflicts

## Domain & Dependencies

- **Domain:** `shared`
- **Covers:** what `uv.lock` actually contains (real excerpts from this repo), the three lock verbs, updating a single package, and how to read resolver conflicts.
- **Prerequisites:** Domain 2 (the contract / receipt / shelf model), Domain 3 (pyproject = contract).
- **Prerequisite of:** Domain 5 (ONE lock for the whole workspace).

> **TL;DR:** `pyproject.toml` is the **shopping list** (your wishes, `>=` ranges); `uv.lock` is the **notarized receipt** (every package, exact version, where it came from, cryptographic hashes). You never hand-edit the receipt — you regenerate it (`uv lock`), bump one line on it (`uv lock --upgrade-package X`), or install from it verbatim (`uv sync`). One lock covers the entire workspace.

---

## Executive Summary

The lock answers the question the contract can't: *"after uv solved everything, **what exact versions** are we committed to?"* Anyone — a teammate, CI, your future laptop — runs `uv sync` and gets a byte-identical environment, because the receipt says exactly which wheel (with which hash) to fetch.

---

## 1️⃣ Anatomy — the real file, top to bottom

**Header** — the lock's own ID card (from this repo):

```toml
version = 1
revision = 3                       # uv's lock format revision
requires-python = ">=3.13"         # the contract, restated
resolution-markers = [             # Python-version forks:
    "python_full_version >= '3.14'",   # 3.14+ may resolve DIFFERENT versions than <3.14
    "python_full_version < '3.14'",
]
```

**`[manifest]`** — the roster: every workspace member this lock vouches for.

```toml
[manifest]
members = [ "cold-wind-ai", "coldwind-core", "coldwind-desktop" ]
```

**A normal (registry) package entry** — note the exact pin + hashes:

```toml
[[package]]
name = "aiofiles"
version = "25.1.0"                                   # EXACT — no >= anywhere
source = { registry = "https://pypi.org/simple" }    # where it comes from
sdist = { url = "https://files.pythonhosted.org/...", hash = "sha256:a8d7...", ... }
wheels = [ { url = "https://files.pythonhosted.org/...", hash = "sha256:abe3...", ... } ]
```

The `hash` lines are the tamper seal: uv verifies the downloaded file *is* the filed receipt's file.

**A workspace member entry** — no PyPI, no hashes, editable:

```toml
[[package]]
name = "coldwind-core"
version = "1.9.1"
source = { editable = "core" }     # ← "not from the store — from the garage, signposted"
dependencies = [ { name = "langchain" }, { name = "mcp" }, ... ]
```

**`[package.metadata]`** — each entry also stores *why* (which member demanded which range), e.g. desktop's `{ name = "browser-use", extras = ["video"], specifier = ">=0.7.7" }` and `{ name = "coldwind-core", editable = "core" }`. When a conflict appears, this is the evidence trail.

---

## 2️⃣ The three lock verbs

| Command | What it does | When |
|---|---|---|
| `uv lock` | Re-solve from pyproject, rewrite the receipt | after editing dependencies |
| `uv lock --check` | Verify the receipt is fresh; exit non-zero if stale | before committing / in CI |
| `uv lock --upgrade` | Re-solve allowing newest allowed versions | periodic refresh |
| `uv lock --upgrade-package langchain` | Re-solve allowing a new version for ONE name | targeted bump |

**The single-entry update you asked about**, end to end:

```bash
uv lock --upgrade-package rich      # receipt now pins a newer rich (only if compatible)
uv sync                             # shelf updated to match the new receipt
git add uv.lock && git commit ...   # the bump IS the lockfile diff
```

> **⚠️ Never hand-edit `uv.lock`.** It's generated, hash-sealed, and cross-checked. `uv lock --check` will fail (or syncs will misbehave) on a hand-crafted file. Change the *contract* (`uv add "rich>=14.2"`) or use the upgrade flags — never the receipt itself.

---

## 3️⃣ Reading resolver conflicts — the tangle protocol

**Metaphor-first:** a conflict is **two family members demanding incompatible furniture**: "the shelf needs `thing>=2`" (from `langchain`) vs "this corner only fits `thing<2`" (from `browser-use`). uv refuses to guess — it prints both demands and stops.

**What the error looks like (shape, not exact text):**

```text
No solution found when resolving dependencies:
- package A depends on X>=2.0
- package B depends on X<2.0
```

**The untangling sequence (in order):**

1. **Read, don't panic** — the error names the two packages and the two ranges. That's the whole tangle.
2. **Find the culprit pair** — `uv.lock`'s `[package.metadata]` (or the error text) tells you which *member* pulled each side in.
3. **Pick a fix, cheapest first:**
   - **Loosen your own pin** — if *your* pyproject over-constrained something (e.g. you wrote `pydantic>=2.11.7` and the ecosystem moved), relax it.
   - **Upgrade both fighters together** — `uv lock --upgrade-package A --upgrade-package B` lets the pair re-negotiate at newer versions where they often agree again.
   - **Full re-solve** — `uv lock --upgrade` when the tangle is wide (old receipt vs new world).
   - **Last resort** — pin one side explicitly to the version the other needs: `uv add "X==1.9"`.

**Real tangle territory in THIS repo:**

```text
core/pyproject.toml:
  langchain>=0.3.27 · langchain-core>=0.3.74 · langchain-community>=0.3.27
  langchain-ollama>=0.3.6 · langchain-mcp-adapters>=0.1.9 ...
```

The `langchain*` family releases in **lockstep** (their versions move together and depend on each other tightly) — so a conflict here usually means the family got half-upgraded. The fix is upgrading the family together, not fighting one member. `browser-use[video]` is the other heavyweight: it drags a wide transitive tree (playwright etc.), so when it conflicts, it's usually with something old pinned elsewhere.

---

## ✅ Checkpoint (read-only, 5 minutes)

```bash
# 1. Is the receipt fresh?
uv lock --check

# 2. Read real entries — member (editable) vs store (registry+hashes)
grep -A3 'name = "coldwind-core"' uv.lock | head -4
grep -A3 'name = "aiofiles"' uv.lock | head -4

# 3. What EXACT version is langchain pinned to right now?
grep -B1 -A1 'name = "langchain"$' uv.lock | head -3

# 4. See the evidence trail: who demanded what
grep -A3 'name = "coldwind-desktop"' uv.lock | head -12
```

**Pass criteria:** (a) you can find the pinned version of any package in under 10 seconds; (b) you can explain why `--upgrade-package X` exists instead of hand-editing.

---

## 📎 Glossary additions

| Term | One-line meaning |
|------|-----------------|
| **lockfile (`uv.lock`)** | The notarized receipt: exact versions + sources + hashes for the entire graph. |
| **resolve / re-solve** | uv computing the one consistent version-set that satisfies every range. |
| **`uv lock --check`** | Freshness audit — fails if the receipt no longer matches the contract. |
| **`--upgrade-package X`** | Targeted bump: re-solve allowing only X (and its consequences) to move. |
| **resolution-markers** | Lock sections forked by Python version (3.14 vs older may pin differently). |
| **hash (sha256)** | Tamper seal proving the downloaded wheel is the exact filed one. |

---

## ❓ Domain 4 Q&A Log

*(empty — questions from tutoring sessions get appended here, never overwritten)*
