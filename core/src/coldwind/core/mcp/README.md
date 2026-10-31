# 🔌 MCP Package (`coldwind.core.mcp`)

> Lets Cold Wind AI use external tool servers — any tool that speaks the Model Context Protocol, plugged in through a config file.

**Part of:** `coldwind-core` · **Last Updated:** October 2026

---

## 🗺️ Where This Fits

```text
.mcp.json (config file)
        │  McpConfigFile.retrieve_config()
        ▼
   MCP_Manager ──► starts server subprocess ──► tool_discovery
        │                                            │
        ▼                                            ▼
  call_mcp_server()                        DynamicToolRegister ──► ToolAssign
  (run a tool call)                        (MCP tools join the normal menu)
```

---

## 🎯 Why This Exists

- Writing every integration by hand doesn't scale — **MCP is a shared language** for tools.
- One config file lists your servers; the app **discovers their tools automatically**.
- MCP tools appear next to built-in tools — **agents don't know or care where a tool came from**.

---

## 📦 Module Map

| File | Plain-English job |
|------|-------------------|
| `load_config.py` | `McpConfigFile` — reads the config file from disk |
| `mcp_manager.py` | `MCP_Manager` — singleton lifecycle manager (start, call, stop) |
| `DynamicToolRegister.py` | `DynamicToolRegister` — holds discovered MCP tools |
| `mcp_register_structure.py` | `Command` enum + `ServerConfig` types (see below) |
| `mcp_manager_util.py` | `Utils(MCP_Manager)` — extra helpers on top of the manager |
| (adaptation lives in tools/) | `UniversalMCPWrapper` in `tools/lggraph_tools/mcp_wrapper/` |

---

## 📝 The Config File (`.mcp.json`)

The path comes from settings: `ContextRegistry.get().get_settings().mcp_config_path` (a `DesktopConfig` field — not hardcoded).

```json
{
  "servers": {
    "github": {
      "command": "NPX",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "…" }
    },
    "filesystem": {
      "command": "UVX",
      "args": ["mcp-server-filesystem", "/safe/dir"]
    }
  }
}
```

> ⚠️ The key is **`"servers"`** — the loader reads `config.get("servers", {})`. Older docs showed `"mcpServers"` (the Claude Desktop format); that key is silently ignored here.

`command` is a `Command` enum: `NPX` | `UVX` | `PIPX` | `PIP` | `PYTHON` — how the server process gets launched.

---

## 🏗️ Lifecycle of an MCP Server

```text
 1. McpConfigFile.retrieve_config()      read .mcp.json → server definitions
 2. MCP_Manager.add_server(name, cfg)    register the definition
 3. MCP_Manager.start_server(name)       launch subprocess, speak MCP over stdio
 4. MCP_Manager.tool_discovery(name)     "what tools do you offer?"
 5. DynamicToolRegister.register_tool()   each tool joins the menu
 6. MCP_Manager.call_mcp_server(...)     agents call tools (JSON-RPC 2.0)
 7. MCP_Manager.stop_server / stop_all_servers / cleanup()   shutdown
```

**Boot happens in** `ChatInitializer._initialize_mcp_servers_sync()`; **shutdown is registered** with `ChatDestructor` — MCP servers never outlive the app.

---

## 🚀 Quick Start

```python
from coldwind.core.mcp.mcp_manager import MCP_Manager

manager = MCP_Manager()
manager.add_server("github", server_config)
manager.start_server("github")          # subprocess up + tools discovered

tools = manager.tool_discovery("github")
result = manager.call_mcp_server("github", tool_name, arguments)
```

Usually you won't do this by hand — the engine boots MCP, and agents call tools through the normal tool menu.

Also available: `read_uri_resource(...)` to fetch MCP resources (like files) directly.

---

## 🛡️ Runtime Rules

- **Singleton** — one `MCP_Manager` for the whole process; never instantiate a second one.
- **Not thread-safe by design** — call it from one place (the engine does exactly that).
- **Config is declarative** — add a server by editing `.mcp.json`, not code. The absence of the file simply means "no external servers right now"; the runtime flow stays the same.

---

## ❓ FAQ

- **`MCPManager`?** Doesn't exist — the class is `MCP_Manager` (with underscore), plus a `Utils` subclass in `mcp_manager_util.py`.
- **How do MCP tools reach the agents?** `DynamicToolRegister` → `UniversalMCPWrapper` → `ToolAssign` — see the tools README.

---

**Cold Wind AI · `coldwind-core` · Updated in the v2.0.0 docs pass (fixed the broken `mcpServers` config example to the real `servers` key; corrected class names).**
