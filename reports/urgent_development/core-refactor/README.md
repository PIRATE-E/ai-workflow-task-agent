# Urgent Development — Core Refactor & Headless Engine

## Domain

- **urgent_development** (Parent Domain) — High-priority infrastructural refactors, architectural decoupling, and system modernizations.
- **core-refactor** (System Shelf) — Decoupling `coldwind-core` from interactive terminal assumptions into a headless, stateless turnkey agent engine supporting Desktop CLI, native Slint + Rust GUI (`ai-workflow-gui`), and FastAPI headless servers.

## Overview

Historically, `coldwind-core` grew alongside the Desktop CLI harness. As a result, Core inherited interactive terminal biases: blocking user input loops (`run_chat()`), hardcoded disk dumping of conversation history (`conversation_history.json`), and process signal hijacking (`ChatDestructor`).

This system shelf documents the architectural audit and the concrete implementation blueprint to transform Core into a pure, headless engine:
1. **The Audit (`01-platform-integration-spec.md`):** Identifies all touchpoints between Core and presentation platforms, cataloging Core exports, expectations, and architectural friction points (GIL locks, blocking I/O, service injections).
2. **The Refactor Blueprint (`02-headless-engine-refactoring-guide.md`):** Specifies the turnkey `ColdWindEngine` facade and the Ticket-driven execution model (`Ticket` in, `TurnResult` out), eliminating terminal bias while preserving turnkey setup inside Core.

## Interdependence Map

```text
┌────────────────────────────────────────────────────────────────────────┐
│                     Platform Presentation Layers                       │
│                                                                        │
│   ┌────────────────────┐   ┌─────────────────────┐  ┌───────────────┐  │
│   │ Desktop CLI        │   │ Slint + Rust GUI    │  │ FastAPI Pod   │  │
│   │ (prompt_toolkit)   │   │ (Maturin / PyO3)    │  │ (HTTP / WS)   │  │
│   └─────────┬──────────┘   └──────────┬──────────┘  └───────┬───────┘  │
│             │                         │                     │          │
│             └───────────────────┬─────┴─────────────────────┘          │
│                                 │ 1. Boot Handshake (activate_context) │
│                                 │ 2. Turn Handshake (process_ticket)   │
│                                 ▼                                      │
│             ┌──────────────────────────────────────────────┐           │
│             │      ColdWindEngine (Turnkey Facade)         │           │
│             │  • LangGraph compilation (GraphBuilder)      │           │
│             │  • Tool discovery (ToolAssigner & MCP)       │           │
│             │  • Stateless turn execution (Ticket -> Result│           │
│             └───────────────────┬──────────────────────────┘           │
│                                 │                                      │
│                                 ▼                                      │
│             ┌──────────────────────────────────────────────┐           │
│             │   Core Engine Brain & Knowledge Subsystems   │           │
│             │  • LangGraph Node Assign • Agentic Core      │           │
│             │  • ModelManager • Neo4j Driver • MCP Clients │           │
│             └──────────────────────────────────────────────┘           │
└────────────────────────────────────────────────────────────────────────┘
```

## Ownership Table

| Domain | Folder | Document | Description |
|---|---|---|---|
| shared, core | `reports/urgent_development/core-refactor/` | [`01-platform-integration-spec.md`](01-platform-integration-spec.md) | Universal contract specification: Core exports, mandatory platform expectations, and audit of legacy CLI hazards (GIL, blocking loops). |
| core, shared | `reports/urgent_development/core-refactor/` | [`02-headless-engine-refactoring-guide.md`](02-headless-engine-refactoring-guide.md) | Step-by-step refactoring architecture guide: `ColdWindEngine` turnkey facade, `Ticket` / `TurnResult` data models, and platform ambassador designs. |

## Index

- [`01-platform-integration-spec.md`](01-platform-integration-spec.md) — Comprehensive technical audit of current Core interface contracts, undocumented gaps, and architectural friction points for external GUI and server integrations.
- [`02-headless-engine-refactoring-guide.md`](02-headless-engine-refactoring-guide.md) — Architectural blueprint solving the legacy terminal biases: formalizing the turnkey engine model, dual-handshake lifecycle, Ticket contract, and Slint/FastAPI/Desktop ambassador bindings.
