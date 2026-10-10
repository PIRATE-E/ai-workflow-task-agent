# ⚙️ Config Package (`coldwind.core.config`)

> Every knob and dial of Cold Wind AI lives here — **typed settings** loaded from a `.env` file.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
.env file ──► CoreSettinngs (core settings)
                  │
                  ▼
             DesktopConfig  (desktop adds its own knobs)
                  │
                  ▼
   ContextRegistry.get().get_settings()   ◄── ALL code reads settings here
```

---

## 🎯 Why This Exists

- **One typed place** for every setting — no magic global variables.
- Core and Desktop **share the same base**; Desktop only adds its own extras.
- Any value can be overridden from a **`.env` file** without touching code.

---

## 🏗️ The Most Important Picture: Config vs Runtime

```text
      PURE CONFIG                        LIVE RUNTIME OBJECTS
 (decided BEFORE boot)                 (created AFTER boot)
┌────────────────────────────┐      ┌────────────────────────────┐
│  CoreSettinngs            │      │  ContextRegistry           │
│   └─ DesktopConfig        │      │   └─ active runtime context │
│      (pydantic-settings)  │      │      • neo4j driver        │
│                           │      │      • message classes     │
│  = values from .env       │      │      • listeners, UI hooks │
└────────────────────────────┘      └────────────────────────────┘
        Settings NEVER hold live objects. Ever.
```

**Rule of thumb:** if it can be written in a `.env` file → it belongs here. If it's a real object created at boot → it belongs on the runtime context.

---

## 📦 Module Map

| File | What it does (plain English) |
|------|------------------------------|
| `coreSettings.py` | Defines `CoreSettinngs` — every setting Core needs |
| `__init__.py` | Package exports |

> 💡 There is **no `settings.py` anymore** — the old flat-global settings module was removed in the v2.0.0 purge. If you see `from src.config import settings` in old notes, it's dead history.

---

## 🔑 Settings Groups (all on `CoreSettinngs`)

| Group | Fields | What they control |
|-------|--------|-------------------|
| **Models** | `default_model`, `gpt_model`, `classifier_model`, `cypher_model`, `kimi_model`, `api_default_api_model` | Which AI models to use for each job |
| **API** | `openai_api_key`, `translation_api_url` | Cloud keys + translation endpoint |
| **Server** | `socket_host`, `socket_port` | Local server binding |
| **Logging** | `log_level`, `enable_socket_logging`, `enable_sound_notifications` | How loud the logs are |
| **Features** | `debug`, `browser_use_enabled` | On/off switches |
| **Timeouts** | `openai_timeout`, `openai_connect_timeout`, `mcp_timeout`, `mcp_start_timeout`, `browser_use_timeout` | How long to wait before giving up |
| **Neo4j** | `neo4j_uri`, `neo4j_username`, `neo4j_password`, `neo4j_database`, `aura_instanceid`, `aura_instancename` | Graph database connection |
| **MCP** | `mcp_enabled`, `mcp_host`, `mcp_port`, `mcp_api_key` | MCP server integration |
| **Limits** | `semaphore_limit_cli`, `semaphore_limit_api`, `semaphore_limit_openai`, `recursion_limit`, `skip_threshold` | Concurrency + safety caps |
| **Paths** | `png_file_path` | Where the graph PNG export goes |

**`DesktopConfig` adds (desktop only):** `log_display_mode`, log-rotation knobs, `project_root`, `mcp_config_path`, browser profile path, and the three RAG file paths.

---

## 🚀 Quick Start

```python
# 1) Direct (mostly for tests)
from coldwind.core.config.coreSettings import CoreSettinngs

settings = CoreSettinngs()          # auto-loads .env from the project root
print(settings.default_model)      # nvidia/nemotron-3-ultra-550b-a55b

# 2) The normal way — inside a running app
from coldwind.core.runtime.CoreContextRegistry import ContextRegistry

settings = ContextRegistry.get().get_settings()
```

### Override anything from `.env`

```env
DEFAULT_MODEL=nvidia/nemotron-3-ultra-550b-a55b
OPENAI_TIMEOUT=60
NEO4J_URI=bolt://localhost:7687
```

Field names map to env vars case-insensitively: `default_model` ⇄ `DEFAULT_MODEL`.

---

## 🐛 Gotchas

- **The class is spelled `CoreSettinngs`** (triple "n" — kept for compatibility). A `CoreSettings` alias exists, so both names work.
- **Import errors?** The old `from src.config import settings` pattern is gone forever. Use `ContextRegistry.get().get_settings()`.
- **Desktop-only fields** (like `log_display_mode`) don't exist on plain `CoreSettinngs` — they appear on `DesktopConfig`.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (was documenting the deleted `src.config.settings` module).**
