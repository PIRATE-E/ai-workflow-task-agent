# Cold Wind AI Vision & Future Architecture

## Domain

- **shared** — Cross-platform strategic vision, MCP cloud pod infrastructure, headless server engine, and RAG modernization for the entire Cold Wind AI monorepo.

## Overview

Architectural blueprint and multi-phase roadmap for transitioning Cold Wind AI from a local monolithic CLI into a modular, decoupled AI platform.

| Document | Topic | Status |
|----------|-------|--------|
| `COLD_WIND_AI_VISION.md` | Strategic 4-Pillar Blueprint & Phase Roadmap | ✅ Published |

## Interdependence Map

```text
┌────────────────────────────────────────────────────────┐
│               Cold Wind AI Architecture                │
│                                                        │
│  ┌───────────────────────┐    ┌───────────────────────┐│
│  │ Headless Agent Engine │    │ Pluggable Client GUIs ││
│  │ (FastAPI + LangGraph) │ ◄─►│ (Slint+Rust / CLI)    ││
│  └───────────┬───────────┘    └───────────────────────┘│
│              │                                         │
│              ├───────────────────┐                     │
│              ▼                   ▼                     │
│  ┌───────────────────────┐ ┌─────────────────────────┐ │
│  │  Modern Single-Shot   │ │ MCP Cloud Pod System    │ │
│  │  Low-Footprint RAG    │ │ (Isolated Micro-Pods)   │ │
│  └───────────────────────┘ └─────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

## Ownership Table

| Domain | Folder | Document | Description |
|--------|--------|----------|-------------|
| shared | `reports/new_wind_ai/` | [`COLD_WIND_AI_VISION.md`](COLD_WIND_AI_VISION.md) | Multi-platform strategy, MCP cloud pod model, pluggable GUI presentation, and RAG modernization |

## Index

- [`COLD_WIND_AI_VISION.md`](COLD_WIND_AI_VISION.md) — Comprehensive architecture blueprint covering headless execution, Slint + Rust cross-platform presentation, containerized MCP cloud pods, and lightweight non-blocking RAG.
