# ⚙️ CoreSettinngs — The Complete Settings Schema

> Every configuration key Core owns, how each one maps to an environment variable, and what a platform must add.

**Source:** [`coreSettings.py`](coreSettings.py) · **Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## Domain & Dependencies

**Domain:** `core` / `shared`.
`CoreSettinngs` is the root of the config hierarchy and the base class every
platform subclasses (desktop's `DesktopConfig` being the reference). It is
returned to Core through the master context
([`../interfaces/runtime_interface.md`](../interfaces/runtime_interface.md),
Pillar 1) and consumed via `ContextRegistry.get().get_settings()`.

---

## 📌 Executive Summary

```python
class CoreSettinngs(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
```

- **37 typed fields** — every knob Core needs: models, APIs, timeouts, Neo4j,
  MCP, concurrency, feature flags.
- **Every field has a default**, so `CoreSettinngs()` always constructs — a
  bare boot works out of the box (see the [placeholder-poison](#-placeholder-poison-keys) caveat).
- **Every field is overridable from the environment** — env var or `.env`
  file, case-insensitive.
- **Platforms extend, Core never imports back**: `DesktopConfig(CoreSettinngs)`
  adds desktop-only fields; Core only ever reads the base contract.

---

## 🔑 How Environment Variables Map

| Rule | Detail |
|------|--------|
| Field → env var | Same name, case-insensitive: `default_model` ⇄ `DEFAULT_MODEL` |
| Sources | Real env vars **and** the `.env` file (`env_file=".env"`, UTF-8) |
| Precedence | init kwargs > real env vars > `.env` values > field defaults |
| Unknown keys | **Rejected** — pydantic-settings defaults to `extra="forbid"`, so a key present in `.env` but not declared as a field raises a validation error. *This is why the Aura placeholders are declared fields — the real Aura `.env` must not explode validation.* |
| Paths | `png_file_path` is a `Path` — accepts a string, pydantic coerces it |

> ⚠️ Practical consequence of `extra="forbid"`: when you add a new key to
> your `.env`, you must also declare it (on `CoreSettinngs` if core-wide, on
> your platform subclass if platform-only) — or boot dies in settings
> validation with a clear "extra field" error.

---

## 🗂️ The Full Key Catalog (37 keys)

### Server (2)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `socket_host` | `str` | `localhost` | Local socket server bind host |
| `socket_port` | `int` | `5390` | Local socket server port |

### Models (6)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `default_model` | `str` | `nvidia/nemotron-3-ultra-550b-a55b` | Primary chat model id |
| `cypher_model` | `str` | `deepseek-r1:8b` | Model used for Cypher generation |
| `classifier_model` | `str` | `llama3.1:8b` | Input-classification model |
| `gpt_model` | `str` | `openai/gpt-oss-120b` | GPT-family model id |
| `kimi_model` | `str` | `moonshotai/kimi-k2.6` | Kimi model id |
| `api_default_api_model` | `str` | `moonshotai/kimi-k3` | Default model for API calls |

### API (2)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `openai_api_key` | `str` | `your_openai_api_key_here` ⚠️ placeholder | Cloud API credential |
| `translation_api_url` | `str` | `http://localhost:5560/translate` | Translation service endpoint |

### Task management (1)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `skip_threshold` | `int` | `70` | Score threshold for skip/accept decisions |

### Logging (3)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `log_level` | `str` | `INFO` | Root log verbosity |
| `enable_socket_logging` | `bool` | `True` | Ship logs over the socket channel |
| `enable_sound_notifications` | `bool` | `True` | Play notification sounds |

### Feature flags (2)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `debug` | `bool` | `False` | Debug mode master switch |
| `browser_use_enabled` | `bool` | `True` | Browser automation feature flag |

### Timeouts (2 core-owned; more under MCP/Browser)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `openai_timeout` | `int` | `60` | Request timeout (seconds) |
| `openai_connect_timeout` | `int` | `10` | Connect timeout (seconds) |

### Neo4j (4)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `neo4j_uri` | `str` | `bolt://localhost:7687` | Graph database bolt URI |
| `neo4j_username` | `str` | `neo4j` | Auth user |
| `neo4j_password` | `str` | `your_password_here` ⚠️ placeholder | Auth password |
| `neo4j_database` | `str` | `neo4j` | Database name |

### Aura — Neo4j cloud (2)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `aura_instanceid` | `str` | `""` | Aura instance id (declared so real Aura `.env` files pass validation; core does not require it) |
| `aura_instancename` | `str` | `""` | Aura instance name (same rationale) |

### Release (1)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `release` | `str` | `1.0.0` | Project release tag — surfaced via `.env` as `release=...`; stored for diagnostics/banners, not core logic |

### Concurrency (3)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `semaphore_limit_cli` | `int` | `15` | Max concurrent CLI-side operations |
| `semaphore_limit_api` | `int` | `5` | Max concurrent API calls |
| `semaphore_limit_openai` | `int` | `15` | Max concurrent OpenAI requests |

### Recursion (1)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `recursion_limit` | `int` | `500` | LangGraph recursion ceiling (guard against spin loops) |

### MCP (6)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `mcp_enabled` | `bool` | `True` | MCP subsystem master switch |
| `mcp_host` | `str` | `localhost` | MCP server host |
| `mcp_port` | `int` | `5000` | MCP server port |
| `mcp_api_key` | `str` | `your_api_key_here` ⚠️ placeholder | MCP credential |
| `mcp_timeout` | `int` | `30` | Per-call timeout (seconds) |
| `mcp_start_timeout` | `int` | `30` | Server startup timeout (seconds) |

### Browser (1)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `browser_use_timeout` | `int` | `1300` | Browser automation timeout (seconds) |

### Paths (1)

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `png_file_path` | `Path` | `basic_logs/graph.png` | LangGraph PNG export target; platforms override with absolute paths |

---

## ☠️ Placeholder-Poison Keys

Three keys ship with **placeholder defaults that must be overridden** in any
real deployment — the app will boot, but the relevant subsystem will fail at
first use with an auth error:

| Key | Placeholder default | Override with |
|-----|--------------------|---------------|
| `openai_api_key` | `your_openai_api_key_here` | Your real API key |
| `neo4j_password` | `your_password_here` | Your real Neo4j password |
| `mcp_api_key` | `your_api_key_here` | Your real MCP credential |

> ⚠️ Secrets belong in `.env` (git-ignored) or real environment variables —
> never in code, never committed. `neo4j_uri` should also be overridden the
> moment your database is not localhost.

---

## 🏗️ The Subclass Contract (how platforms extend)

Core reads settings **through the interface typed as `CoreSettinngs`** — it
never learns your subclass exists. Desktop's `DesktopConfig` is the canonical
extension:

```python
# desktop/src/coldwind/desktop/config/DesktopConfig.py — excerpt
class DesktopConfig(CoreSettinngs):
    # inherited: ALL 37 core keys
    log_display_mode: str = "separate_window"          # desktop-only, defaulted
    dashboard_terminal_bin: str = "auto"               # desktop-only, defaulted

    project_root: Path                                 # desktop-only, REQUIRED
    mcp_config_path: Path                              # computed in __init__
    rag_example_file_path: Path                        # computed in __init__
    # … more desktop paths …

    def __init__(self, project_root: Path, **kwargs):
        kwargs["project_root"] = project_root           # satisfies required fields
        kwargs["mcp_config_path"] = project_root / ".mcp.json"
        kwargs["png_file_path"] = project_root / "basic_logs" / "graph.png"
        kwargs["_env_file"] = project_root / ".env"     # re-aims the .env source
        super().__init__(**kwargs)
```

**The rules for a platform subclass:**

1. **Inherit everything.** All 37 core keys arrive for free.
2. **Add platform-only keys** with defaults when optional, without defaults
   when they must be supplied (then populate them in `__init__` like desktop
   computes its paths from `project_root`).
3. **Re-aim `_env_file`** if your platform's `.env` is not in the default
   working directory.
4. **Never write core keys back** to different names — override a *default*
   at most.

---

## 🔧 The `CoreSettings` Alias

```python
CoreSettings = CoreSettinngs
```

The class carries a historical triple-"n" typo (`CoreSettinngs`). The alias
exists so import sites can use the correct spelling; **both names refer to
the same class** — pick one and be consistent. New code prefers
`CoreSettinngs` (matching the real definition) or the alias — both are
first-class.

---

## 🚀 Quick Start

```python
# 1) Direct construction (tests, scripts) — auto-loads ./env or .env from cwd
from coldwind.core.config.coreSettings import CoreSettinngs
settings = CoreSettinngs()
print(settings.default_model)     # nvidia/nemotron-3-ultra-550b-a55b

# 2) The runtime way — what Core code actually does
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry
settings = ContextRegistry.get().get_settings()
```

```env
# .env — example overrides
DEFAULT_MODEL=moonshotai/kimi-k2.6
NEO4J_PASSWORD=real-secret-here
DEBUG=true
```

---

## ✅ Testing Checklist

1. **Bare boot:** `CoreSettinngs()` constructs with zero arguments and 37
   populated fields.
2. **Env override:** setting `LOG_LEVEL=DEBUG` in the environment (or
   `.env`) changes `settings.log_level`.
3. **Unknown-key rejection:** adding `BOGUS_KEY=1` to `.env` raises a
   pydantic validation error (`extra="forbid"`).
4. **Subclass fidelity:** `DesktopConfig(project_root)` exposes all 37 core
   keys **and** the desktop-only ones.

---

## 📖 Glossary

- **Settings schema** — the declared field set of `CoreSettinngs`; the
  contract for what may legally appear in `.env`.
- **Placeholder-poison key** — a field whose default is a fake credential;
  valid to construct with, fatal to use.
- **Platform subclass** — a `BaseSettings` child (e.g. `DesktopConfig`) that
  adds platform keys while satisfying the core base type.

---

## ❓ Q&A Log

> **Q: Required vs optional env vars — the audit asked for the list.**
> **Nothing is formally required** (every field has a default), but three
> keys are *practically required* in real deployments — see
> [Placeholder-Poison Keys](#-placeholder-poison-keys). Everything else
> works on defaults for local development.

> **Q: Why are the Aura fields here if Core doesn't use them?**
> `extra="forbid"` would reject the real Aura-hosted `.env` otherwise.
> Declaring them lets that file validate; the driver-build site may consume
> them when needed.

> **Q: How do I add a new CORE-wide key?**
> Declare the field on `CoreSettinngs` with a sensible default, add it to
> this catalog, and it becomes overridable from `.env` automatically.
> Anything platform-specific goes on the subclass instead.

> **Q: Can Core read `project_root`-style desktop fields?**
> No — Core sees only the 37 base fields. If a core module needs a path, it
> becomes a core key (like `png_file_path`) that the platform overrides.

---

**Cold Wind AI · `coldwind-core` · Created in the platform-docs pass (2026-10-10).**
