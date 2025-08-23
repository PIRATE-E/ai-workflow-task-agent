# 🤖 AI-Agent-Workflow Project

> Enterprise-grade desktop AI assistant with LangGraph multi-agent architecture, dynamic MCP integration via .mcp.json, universal MCP routing, hybrid OpenAI/NVIDIA (with circuit breaker), local Ollama support, Rich Traceback, and professional workflows.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Latest-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-v1.8.0-brightgreen.svg)]()

---

## 🚀 What’s New (v1.8.0 – August 2025)
- ✅ Dynamic MCP server registration from .mcp.json (no code edits required)
- ✅ UniversalMCPWrapper + universal tool routing with static+dynamic tool→server map
- ✅ Robust MCP manager: ServerConfig/Command enum, safer subprocess I/O, encoding fallbacks, tool discovery mapping
- ✅ OpenAIIntegration hardened: circuit breaker, retry/backoff, streaming/JSON extraction safety
- ✅ Dockerfile + docker-compose for simple container runs
- ✅ Python target updated to 3.13 via pyproject.toml
- ✅ Expanded diagnostic logging and tests (MCP routing, circuit breaker)

## ✨ Current Status
- Production Readiness: 95% → Stability improved via circuit breaker + MCP hardening
- MCP: Fully dynamic via .mcp.json at project root (path set in settings.MCP_CONFIG.MCP_CONFIG_PATH)
- Agent Mode: More reliable parameter generation and MCP tool execution (auto-injects tool_name)
- DevOps: Container-first workflow supported (build and run via docker-compose)
- Compatibility: Python 3.13 baseline; legacy 3.11 works with requirements.txt

## 🔧 MCP Configuration
Place .mcp.json at repo root. Example:
```
{
  "servers": {
    "filesystem": { "command": "npx", "args": ["-y","@modelcontextprotocol/server-filesystem@latest","<ABS_PATH>"] },
    "memory": { "command": "npx", "args": ["-y","@modelcontextprotocol/server-memory@latest"] },
    "github": { "command": "npx", "args": ["-y","@modelcontextprotocol/server-github@latest"] }
  }
}
```
ChatInitializer loads and starts servers asynchronously; discovered tools are auto-registered.

## 🐳 Docker Quick Start
```
docker compose up --build
# or
docker build -t ai-agent .
docker run --rm -it -p 8000:8000 -v ./src:/app/src ai-agent
```

## 🧠 Hybrid AI (unchanged, stabilized)
- NVIDIA/OpenAI with rate limiting and circuit breaker
- Local Ollama optional
- Streaming and reasoning-friendly output

(Other sections remain as in prior README; see full document for architecture, usage, and development workflow.)
