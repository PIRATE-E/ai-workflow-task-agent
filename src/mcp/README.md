# 🌐 MCP Package

**Model Context Protocol Integration**

> Integration with Model Context Protocol (MCP) servers for extended capabilities.

---

## 📋 **Table of Contents**

1. [What is MCP](#what-is-mcp)
2. [Available MCP Servers](#available-mcp-servers)
3. [How MCP Works](#how-mcp-works)
4. [Configuration](#configuration)
5. [Quick Start Guide](#quick-start-guide)

---

## 🎯 **What is MCP**

**Model Context Protocol** is a standard for extending LLM capabilities through external servers.

### **Why MCP?**

- ✅ **Extensibility** - Add new capabilities without changing code
- ✅ **Standardization** - Common protocol across tools
- ✅ **Isolation** - Servers run in separate processes
- ✅ **Reusability** - Share servers across projects

---

## 🔌 **Available MCP Servers**

### **1. GitHub Server**
- Create/update files
- Create issues and PRs
- Search repositories
- Manage branches

### **2. Filesystem Server**
- Read/write files
- List directories
- Search files
- File operations

### **3. Memory Server**
- Store knowledge graph
- Create entities and relations
- Query semantic memory

### **4. Git Server**
- Git operations
- Commit, push, pull
- Branch management

### **5. Sequential Thinking Server**
- Chain-of-thought reasoning
- Step-by-step problem solving

---

## ⚙️ **Configuration**

### **MCP Config File**

Location: `.mcp.json` (project root)

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github@latest"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem@latest",
        "C:\\path\\to\\workspace"
      ]
    }
  }
}
```

---

## 🚀 **Quick Start Guide**

### **Step 1: Configure MCP Servers**

Edit `.mcp.json` to add servers.

### **Step 2: Start MCP Manager**

```python
from src.mcp.mcp_manager import MCPManager

mcp = MCPManager()
mcp.start_all_servers()
```

### **Step 3: Use MCP Tools**

MCP tools are automatically available to agents.

---

## 🆘 **Support**

**Questions?** Check:
1. MCP official documentation
2. Server-specific docs

---

**Status:** ✅ **Production-Ready**

**Maintainer:** AI-Agent-Workflow Team

**Last Updated:** December 24, 2025

