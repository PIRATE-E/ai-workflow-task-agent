# Domain 0 — Packaging Foundations

## Domain & Dependencies

- **Domain:** `shared` — applies equally to `core`, `desktop`, and the planned `server`.
- **Covers:** the four invisible primitives every uv command silently uses.
- **Does NOT cover:** uv commands themselves — that is Domain 1 onward.
- **Prerequisite of:** Domain 1 (uv Setup), Domain 3 (hatchling `src = ""` trick), Domain 5 (workspace).

> **TL;DR:** Before touching uv you need 4 pieces of vocabulary: **virtualenv** (a private room for libraries), **wheel** (the pre-built box a library ships in), **editable install + `.pth`** (a signpost that says "the code lives over there"), and **namespace package** (one family name spread across separate folders). uv never stops using these — learn them once.

---

## Executive Summary

You already know Python has libraries and something called a "virtual environment". But every uv command in this repo leans on four ideas nobody teaches explicitly:

1. **Where libraries physically live** — the `site-packages` folder inside a virtualenv.
2. **What you're actually downloading** — a *wheel*, a pre-built zip, not "the library".
3. **How "install my own code but keep editing it" works** — an *editable install* driven by a tiny `.pth` pointer file.
4. **How `coldwind.core` and `coldwind.desktop` stay one family from separate folders** — *namespace packages*.

That's the whole domain. Domains 1–5 assume these four words are solid.

---

## 1️⃣ Virtualenv & site-packages — the private room

**Metaphor-first:** a virtualenv is a **private room** for one project. Each project gets its own room with its own library shelf, so `project-A` needing `rich==13` and `this-repo` needing `rich==14` never fight.

**Plain English:** creating a virtualenv makes a folder (here: `.venv/`) containing its own Python interpreter copy and one very important shelf:

```text
.venv/
├── bin/            # python, pip, uv scripts
└── lib/python3.14/          ← this repo's venv runs Python 3.14
    └── site-packages/      ← ⭐ THE SHELF. Every installed package lives here, as a real folder of real files.
```

When you write `import langchain`, Python walks a search list, and `site-packages` is one of the first places it checks. "Installing a package" literally means **copying that package's folder into `site-packages`**.

> **⚠️ Key Takeaway:** There is no magic registry. A package = a folder of files that landed in `site-packages`. `uv sync` (Domain 2) is just a very fast, very correct "put folders on the shelf" machine for this repo's single shared `.venv/`.

**This repo:** one `.venv/` at the project root shared by `core/` and `desktop/` — because of the workspace, both members' code lives in the *same* room (Domain 5 explains why that's an advantage).

---

## 2️⃣ Wheel vs sdist — the delivery box

**Metaphor-first:** a **wheel** is a **pre-assembled piece of furniture** (IKEA already built it — you just place it). An **sdist** is the **flat-pack kit** (raw parts + instructions — you must build it yourself).

**Plain English:** when uv fetches a dependency like `pydantic`, the thing that actually downloads is one of two formats:

| Format | Extension | What it is | Install step |
|--------|-----------|------------|--------------|
| **Wheel** | `.whl` | Pre-built zip with files in their final layout | Just unzip into `site-packages` — fast |
| **sdist** (source dist) | `.tar.gz` | Raw source code | Must run the project's build step first — slow |

Filenames encode the platform: `pydantic_core-2.41.6-...-manylinux_2_17_x86_64.whl` means *"pre-built for Linux 64-bit"*. This is why installs are fast — no compilers, no build noise.

**Where it connects to this repo:** the `coldwind-core` and `coldwind-desktop` projects are **not wheels uv downloads** — they're local members (Domain 5). But their `pyproject.toml` files still describe *how to build a wheel* — that's the hatchling config you'll learn in Domain 3. Every one of their 30+ dependencies arrives as a wheel.

---

## 3️⃣ Editable installs & `.pth` — the signpost, not the move

This is the section newcomers get wrong, because it answers a question nobody has asked out loud yet: *"why does an 'install' exist at all — the code is already on my disk?"* So we do it in this order: the pain first (3.1), the two jobs an install actually performs (3.2), the four things you'd naturally try instead and where each dies (3.3), a decision table (3.4), and only then the mechanism (3.5) and this repo's real bug (3.6).

### 3.1 The pain first: Python never goes looking for your code

**Metaphor-first:** Python's import system is a **delivery company that only serves registered addresses**. Your files in `core/src/` are a house with no address on file. The driver isn't lazy — the house *isn't on the map*, so no amount of "but the files are right there!" helps.

**Plain English:** when you write `import coldwind.core`, Python walks one fixed list called **`sys.path`** — the *search list*, a short ordered list of folders. If your package isn't reachable through any entry on that list, the import dies. Python never scans your disk hunting for projects; it checks the registered list and nothing else.

You can watch this on this machine. Start Python **without** the startup machinery that reads signposts (`-S` skips the `site` module — the exact component that processes `.pth` files), then add the shelf back by hand so wheels still resolve:

```bash
.venv/bin/python -S -c "
import sys
sys.path.insert(0, '.venv/lib/python3.14/site-packages')
import langchain_core
print('wheel import OK   :', langchain_core.__name__)
import coldwind.core
"
```

```text
wheel import OK   : langchain_core
ModuleNotFoundError: No module named 'coldwind'
(a version-warning line from langchain trimmed for readability)
```

The wheel survived because its files were **copied onto the shelf**. Your project died because **nothing was ever copied** — the only thing that knew where your code lives was the signpost, and we just blindfolded the reader. That contrast is the whole lesson: dependencies are snapshots; your project is a registration.

And here is the state you actually want — this ran from `/tmp`, nowhere near the repo:

```bash
cd /tmp && /home/pirate/development/ai-workflow-task-agent/.venv/bin/python -c \
  "import coldwind.core; print(coldwind.core.__file__)"
```

```text
/home/pirate/development/ai-workflow-task-agent/core/src/coldwind/core/__init__.py
```

From any folder, for any tool — that is what `-e` buys. Now let's see what an install must deliver to make that true.

### 3.2 An install is two jobs, not one

"Installing" sounds like one action. It is two separate artifacts delivered onto the shelf:

| Job | Artifact (this repo, verified) | Who reads it |
|-----|-------------------------------|--------------|
| **Import visibility** — put the package on the search list | `_editable_impl_coldwind_core.pth` → one path line | Python, at import time |
| **Registration** — record that the package *exists* and what it offers | `coldwind_core-1.9.1.dist-info/` — the ID-card folder | uv/pip, `importlib.metadata`, generated command shims |

Inside the ID card you'll find `METADATA` (name, version, the full dependency list), `RECORD` (the receipt of everything installed), and — for desktop — `entry_points.txt`:

```text
[console_scripts]
coldwind = coldwind.desktop.main_orchestrator:boot
```

That one line is why a real **`coldwind` command** exists at `.venv/bin/coldwind` — a generated shim whose entire job is `from coldwind.desktop.main_orchestrator import boot; boot()`. No install → no ID card → no command. And uv even leaves a signed confession of the editable deal in `direct_url.json`:

```json
{"url":"file:///home/pirate/development/ai-workflow-task-agent/core","dir_info":{"editable":true}}
```

**Library vs project — the relation nobody spells out.** A *library* is someone else's finished product that you consume; a snapshot copy is perfect because it never changes under your feet. A *project* is your own product under construction; a copy goes stale the second you save a file. The editable install is the bridge between the two: it registers your project as a **first-class citizen of the venv** — importable from anywhere, versioned, owning a command — while the single source of truth stays in the working tree you edit.

### 3.3 The four things you'd try instead — and where each one dies

Every newcomer asks: "why `-e`? can't I just…?" Here are the four natural alternatives, each with the exact place it breaks. Fair warning: each one *seems* to work on day one — that is precisely what makes them traps.

1. **"Just run Python from the source folder."** When you run `python`, the folder you're standing in is silently added as the first slot of the search list. Verified on this machine (run from inside `core/src/`, signpost machinery off):

   ```text
   sys.path[0] = ''
   cwd luck OK — no install needed while standing here
   ```

   `''` means "wherever I'm standing." So the import works *while you stand in `core/src/`*. **Breaks:** the moment anything runs from anywhere else — `pytest` from the repo root, the app launcher, a script inside `desktop/`. Your code's importability now depends on where you happen to stand.

2. **Relative imports** (importing by dot position, `from ..config import settings`, instead of by name). They do **not** dodge the search-list problem — the search list is consulted *before* the dots mean anything. Worse: run the file directly (`python core/src/coldwind/core/state.py`) and Python no longer knows the file belongs to a package at all → `ImportError: attempted relative import with no known parent package`. And dots can never cross this repo's split: `core/` and `desktop/` are separate folder trees with no shared package parent to climb up from.

3. **`PYTHONPATH=...`** — an environment variable that injects extra folders into the search list. Works — but only in the shell where you exported it. Your editor, your CI runner, `pytest` in a fresh terminal, your teammate's laptop: none of them have it. It is invisible state that lives *outside* the project, so the project can neither carry it nor lock it. The classic "works on my machine" generator.

4. **`sys.path.append("/abs/path")` inside your code.** You've hard-coded your machine's layout into the product, made imports depend on execution order, and broken every tool that builds a fresh environment. Duct tape: holds until anyone else touches it.

See the pattern: alternatives 1, 3 and 4 all *do* put a path on the search list — but scoped to **a moment, a shell, or a file**, and none of them registers the ID card. An editable install writes the path **once, into the venv itself**, where every consumer (Python, `pytest`, the `coldwind` command, uv) reliably finds it — and pairs the signpost with registration, so tools know your package *exists*, not just *where it sits*.

### 3.4 When to actually use what — the decision table

| Situation | Right move | Why |
|-----------|-----------|-----|
| Throwaway script, one file, no tests | nothing — just run the file | no consumer needs registration |
| Developing this repo (edit + run + test) | **editable install** — in this repo `uv sync` wires it for both members automatically (receipt: `direct_url.json` above) | imports must work from every folder, for every tool, while you edit |
| Third-party dependencies | normal install (wheel) | finished products don't change under you — snapshot is ideal |
| Shipping your project to users | build a wheel (Domain 3) | users' machines have no access to your source tree |
| Hacking on a dependency *and* your project together | editable-install the dependency too (`uv pip install -e ../that-lib`) | same "live source" reasoning, one level down |

### 3.5 The mechanism, now that it has a reason to exist

**Metaphor-first:** a normal install is **moving your furniture into the house** (copy files into `site-packages`). An **editable install** is **leaving your furniture in your garage and putting a signpost in the house that says "go look in the garage"**. Edit a file in the garage → the house instantly sees the change.

**Plain English:** an *editable install* (historically `pip install -e .`; standardized for pyproject-only projects by **PEP 660**, which is how build backends like hatchling offer it to uv and pip today) does NOT copy your project into `site-packages`. Instead it drops a **`.pth` file** — a tiny text file whose only job is to add a path to the search list:

```text
site-packages/_editable_impl_coldwind_core.pth      ← the signpost (verified on this machine)
site-packages/_editable_impl_coldwind_desktop.pth

# Actual content of the first file — one path per line:
/home/pirate/development/ai-workflow-task-agent/core/src
```

At Python startup, the `site` module reads every `.pth` file sitting in `site-packages` and appends each listed path to the search list. `import coldwind.core` then resolves straight into your working source tree. Edit `core/src/...`, press run → no reinstall needed. That is the entire mechanism — the dist-info half of the deal was §3.2.

### 3.6 The real bug in this repo — now it fully decodes

Both member pyprojects carry this comment:

```python
[tool.hatch.build.targets.wheel.sources]
src = ""  # suggested by the ai because the hatching .pth file is not pointing
          # to the correct location. it must be pointed above the namespace
          # directory which is 'src'
```

Translation into Domain 0 language: hatchling generated a `.pth` pointing at `core/src/coldwind` — **one level too deep**. A path on the search list must be the folder *above* the top package name, so that `coldwind/` itself is visible as a package. Pointing at `coldwind/` means Python would look for `coldwind.coldwind.core` — import breaks. `src = ""` tells hatchling "the package root is `src/`, map it to the wheel root", and the `.pth` correctly lands one level up. Domain 3 explains *why* that TOML line fixes it; today you just need to recognize what was wrong.

> **💡 10-second recall:** installing = **registering**, not copying. Editable gives your project a `.pth` signpost (found from anywhere, forever) **plus** a dist-info ID card (so pytest, the `coldwind` command, and uv know it exists). Every DIY alternative — stand-in-the-folder, relative imports, `PYTHONPATH`, `sys.path` hacks — scopes the path to a moment, a shell, or a file, and registers nothing. `.pth` target = the folder *above* your top-level package.

---

## 4️⃣ Namespace packages — one family, several houses

**Metaphor-first:** think of `coldwind.` as a **family name**. `coldwind.core` and `coldwind.desktop` are two siblings with the same surname but **different houses** — the name joins them even though no single folder holds them.

**Plain English:** a *namespace package* lets multiple folders, in different locations, share one dotted prefix. In a normal package the top folder has an `__init__.py` and EVERYTHING under it ships from that one folder. A namespace package drops the `__init__.py` at the top level, so Python says: *"`coldwind` is just a namespace — I'll merge every `coldwind/` folder I find on the search path."*

```text
core/src/coldwind/core/         ← family folder #1   (no core/src/coldwind/__init__.py!)
desktop/src/coldwind/desktop/   ← family folder #2   (no desktop/src/coldwind/__init__.py!)

             Python merges them into:

coldwind                        ← one virtual namespace
├── core/      (from core/src/)
└── desktop/   (from desktop/src/)
```

**Why this repo needs it:** the long-term vision (memory graph: Cold Wind AI roadmap) is desktop now, server + mobile later. Each platform is its own installable wheel — `coldwind-core`, `coldwind-desktop`, eventually `coldwind-server` — yet they must all import as one coherent `coldwind.*` family without a fake shared parent package. Namespace packaging is the standard Python answer, and it's exactly what uv's `[tool.uv.workspace]` + hatchling `packages = ["src/coldwind/core"]` arrangement assumes.

> **⚠️ Pitfall to remember:** the moment anyone creates `core/src/coldwind/__init__.py`, the merge silently stops working — that sibling folder "wins" and `coldwind.desktop` becomes invisible. Namespace = **no** `__init__.py` at the shared prefix level, ever.

---

## 🧭 How the four pieces join into one picture

```text
                 WHAT RUNS THIS REPO TODAY (uv sync result)

  You edit ─────► core/src/  desktop/src/         (your real code, untouched, at home)
                       │
                 editable installs                  (garage + signpost)
                       │
                       ▼
  .venv/                                             ← the private room (ONE for the whole workspace)
   └── lib/python3.14/site-packages/
        ├── _editable_impl_coldwind_core.pth     → points at core/src     ◄┐ .pth signposts
        ├── _editable_impl_coldwind_desktop.pth  → points at desktop/src  ◄┘
        ├── langchain/  pydantic/  rich/ ...        ← ~30 wheels, unzipped on the shelf
        │
        └── import coldwind.core  ──►  namespace merge ──►  coldwind.{core, desktop}
```

Read that diagram top-down and you've re-derived all of Domain 0: wheels fill the shelf, `.pth` files point at your editable source, namespace packaging merges the two sibling trees into one import family — all inside the single shared virtualenv.

---

## ✅ Checkpoint (prove it to yourself — 5 minutes)

Run these before starting Domain 1. They are read-only.

```bash
# 1. Find the shelf
ls .venv/lib/python3.14/site-packages/ | head

# 2. Read the actual signposts in this repo
cat .venv/lib/python3.14/site-packages/_editable_impl_coldwind_core.pth
cat .venv/lib/python3.14/site-packages/_editable_impl_coldwind_desktop.pth
#    → confirm each points at .../src  (one level ABOVE coldwind/)

# 3. Prove the namespace merge works
.venv/bin/python -c "import coldwind.core, coldwind.desktop; print('namespace OK')"

# 4. See what a wheel's remains look like on the shelf (unzipped code folder + dist-info ID card)
ls .venv/lib/python3.14/site-packages/ | grep -i coldwind

# 5. Read the registration receipts — the editable confession and the command stub
cat .venv/lib/python3.14/site-packages/coldwind_core-1.9.1.dist-info/direct_url.json
cat .venv/lib/python3.14/site-packages/coldwind_desktop-1.9.1.dist-info/entry_points.txt
head -n 5 .venv/bin/coldwind
#    → editable:true + the console-script shim importing boot() = the dist-info half of §3.2
```

**Pass criteria:** you can say, in plain words, (a) what a `.pth` file contains, (b) why `src` is the right target and not `src/coldwind`, (c) why no `__init__.py` may exist at `core/src/coldwind/`, (d) the two jobs an install performs and which artifact answers each, (e) one concrete situation where each of the four alternatives (stand-in-folder, relative imports, `PYTHONPATH`, `sys.path` hacks) would break.

---

## 📎 Glossary

| Term | One-line meaning |
|------|-----------------|
| **virtualenv** | An isolated folder with its own Python + own library shelf (`.venv/`). |
| **site-packages** | The shelf folder inside a venv where installed packages physically live. |
| **wheel (`.whl`)** | Pre-built zip; install = unzip onto the shelf. Fast. |
| **sdist** | Raw source bundle; must be built before use. Slow fallback. |
| **editable install** | Install that leaves code in place and registers a signpost instead of copying. |
| **`sys.path`** | The ordered search list of folders Python checks on every `import`. |
| **`.pth` file** | Text file in `site-packages`; each line is a path added to Python's search list. |
| **dist-info** | The installed package's ID-card folder: name, version, dependencies, receipts (job 2 of an install). |
| **`direct_url.json`** | Receipt inside dist-info recording where the package was installed from; `editable:true` confesses the signpost deal. |
| **entry point / console script** | A declared `name = module:function` mapping that installs a real command (like `coldwind`) into `.venv/bin/`. |
| **PEP 660** | The 2021 standard that made editable installs a formal build-backend hook, used by hatchling/uv today. |
| **namespace package** | A package with no `__init__.py` at its prefix, allowing many folders to share one dotted name. |
| **hatchling** | The build backend this repo uses to construct wheels (details: Domain 3). |

---

## ❓ Domain 0 Q&A Log

*(questions from tutoring sessions get appended here, never overwritten)*

### 2026-09-20 — "Why does `-e` exist at all? Can't I just import directly, or use relative imports?"

**Asked during:** a tutoring review of this report. The reader's verdict on the old §3: "it explains *how* editable installs work, but never *why* they exist or when the obvious alternatives are enough — so even an experienced library-shipper reading it learns the mechanism, not the judgment." Correct.

**Answer:** §3 was rewritten problem-first to close exactly that gap — the pain (§3.1, with the real `-S` counter-demo), the two jobs an install performs and the library-vs-project relation (§3.2), the four natural alternatives and the exact place each dies (§3.3), the decision table (§3.4), and only then the mechanism (§3.5) and this repo's `.pth` bug (§3.6). Short version, if you keep only one sentence: **every alternative puts a path where only *some* consumers will see it (a moment, a shell, or a file) and none registers the dist-info ID card that pytest, the `coldwind` command, and uv rely on — editable does both, once, inside the venv.**

**Verified on this machine while writing:** the `.pth` contents, `direct_url.json` (`editable:true`), `entry_points.txt` + the `.venv/bin/coldwind` shim, the `/tmp` import, the `-S` counter-demo, and the `sys.path[0] == ''` cwd-luck demo.
