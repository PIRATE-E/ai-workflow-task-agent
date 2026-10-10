# 🌬️ Cold Wind AI: Architecture Blueprint & Long-Term Vision

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Cold Wind AI** (`cold-wind-ai`) is an enterprise-grade, multi-platform autonomous AI platform. It transitions from a heavy, monolithic local CLI application into a modular, decoupled architecture featuring:
1. **Headless Agent Engine & Cloud API Backend**: A high-performance core orchestrating multi-agent graph workflows, context memory, and dynamic tool invocation.
2. **Pluggable Cross-Platform Presentation Layer**: A decoupled client architecture designed for low coupling and high coherence, enabling native GUIs (such as **Slint + Rust GUI** in `ai-workflow-gui`) or lightweight terminal interfaces to connect via structured streaming protocols.
3. **MCP Cloud Pod Infrastructure & Tool Marketplace**: An isolated containerized pod architecture where Model Context Protocol (MCP) servers run securely in sandboxed cloud pods with one-click installation, eliminating local dependency requirements (Node.js, Python runtimes) for end users.
4. **Modernized Single-Shot RAG**: An automated, non-blocking retrieval-augmented generation engine operating as a pure LangGraph node without terminal prompt interruptions or heavy PyTorch overhead.

---

## 🏛️ System Topology & Architectural Invariants

### 1. Invariant: Layering Direction & Client Decoupling
- **Direction**: Presentation layers import Core contracts; **Core NEVER imports Presentation layers**.
- Core exposes abstract contracts (`RuntimeContextInterface`, `MessageDisplayInterface`, `ExceptionHandlerInterface`).
- Clients (Desktop CLI, Slint+Rust Desktop App, Web UI) connect as interchangeable frontend drivers communicating via standard streaming APIs (JSONL / SSE / WebSockets).

### 2. Invariant: Config vs. Runtime Split
- **Static Configuration**: Strict schema validation via `pydantic-settings` (`CoreSettinngs`, `DesktopConfig`).
- **Dynamic Services**: Live runtime objects (Neo4j driver, ModelManager, MCP connection hubs) register dynamically through `ContextRegistry.get()`.

---

## 🔌 MCP Cloud Pod Architecture & Tool Marketplace

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Cold Wind Central Platform                      │
│                                                                        │
│   ┌────────────────────┐                   ┌────────────────────────┐  │
│   │  Tool Marketplace  │ ── 1-Click Install ─► │ Dynamic Pod Controller │  │
│   │  (Visual Catalog)  │                   └───────────┬────────────┘  │
│   └────────────────────┘                               │               │
└────────────────────────────────────────────────────────┼───────────────┘
                                                         │ (Spawns / Manages)
                     ┌───────────────────────────────────┴───────────────────────────────────┐
                     ▼                                   ▼                                   ▼
        ┌─────────────────────────┐         ┌─────────────────────────┐         ┌─────────────────────────┐
        │     MCP Cloud Pod 1     │         │     MCP Cloud Pod 2     │         │     MCP Cloud Pod N     │
        │  (Filesystem / Sandbox) │         │   (Web Search / Scrape) │         │   (Custom User Server)  │
        │  • Isolated MicroVM     │         │  • Ephemeral Container  │         │  • Zero Host Access     │
        │  • Remote SSE Transport │         │  • Remote SSE Transport │         │  • Remote SSE Transport │
        └─────────────────────────┘         └─────────────────────────┘         └─────────────────────────┘
```

### Key Principles of the Cloud Pod Model:
- **Zero Local Client Pollution**: Users never need to install `uvx`, `npx`, Node.js, or manage virtual environments locally to use tools.
- **Micro-Container Sandboxing**: Tools execute inside ephemeral, containerized pods with strict network isolation and permission sandboxes, neutralizing malicious tool code.
- **Standardized Remote SSE Transport**: Agent graphs communicate with tool pods over standard HTTP/SSE or secure WebSockets.
- **One-Click Marketplace**: Instead of editing `.mcp.json` by hand, users enable tools visually through an integrated marketplace catalog.

---

## 🔍 Modernized RAG Architecture (Single-Shot & Low Footprint)

### Current Outdated RAG Pain Points:
1. **Interactive Halts**: `rag.py` calls `_get_user_input()` 6+ times, halting agent workflows in the terminal.
2. **Heavy PyTorch Footprint**: Imports full PyTorch (~1GB heap footprint) simply to calculate basic cosine similarity vectors.
3. **Legacy SDK Deprecation**: Relies on legacy `google.generativeai` rather than the official `google-genai` SDK, with mismatched environment key checks (`GEMINI_API_KEY` vs `GOOGLE_API_KEY`).
4. **Outdated Text Splitters**: Imports `langchain.text_splitter` directly rather than modular `langchain_text_splitters`.

### Target Modern RAG Design:
- **Single-Shot LangGraph Node**: Operates end-to-end with a single structured request; streams async status updates without asking interactive CLI questions.
- **Lightweight Embeddings**: Use FastEmbed / ONNX Runtime (CPU-optimized, zero PyTorch dependency) or the modernized Google GenAI SDK.
- **Hybrid Search**: Combine vector search (Chroma / Qdrant) with knowledge graph relationships (Neo4j Cypher queries) seamlessly.

---

## 🗺️ Multi-Phase Strategic Roadmap

```text
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Monorepo Foundation & Layering Modernization   [COMPLETED]     │
│ • Partition core/ and desktop/ workspace packages via uv               │
│ • Purge dead code clusters (~6,800 lines eliminated)                   │
│ • Enforce strict Layering Invariant (Core never imports Desktop)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 2: RAG Modernization & Automated Test Harness     [ACTIVE TARGET]│
│ • Rebuild test harness (resolve Issue #6)                             │
│ • Strip PyTorch from RAG; implement single-shot LangGraph retrieval    │
│ • Modernize embedding providers (Google GenAI / FastEmbed ONNX)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 3: Headless API Engine & Pluggable GUI Framework  [PLANNED]      │
│ • Scaffold FastAPI headless server endpoints                           │
│ • Implement low-coupling streaming IPC / WebSocket adapter            │
│ • Wire pluggable presentation layer (Slint + Rust GUI in ai-workflow)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 4: MCP Cloud Pod System & Tool Marketplace        [FUTURE GOAL]  │
│ • Containerized micro-pod orchestrator for tool execution              │
│ • Visual One-Click Tool Marketplace catalog                            │
│ • Multi-tenant credential isolation and RBAC                           │
└────────────────────────────────────────────────────────────────────────┘
```
