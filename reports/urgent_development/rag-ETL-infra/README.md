# Urgent Development — RAG & ETL Infrastructure

## Domain

- **urgent_development** (Parent Domain) — High-priority infrastructural refactors, blockers, and system modernizations.
- **rag-ETL-infra** (System Shelf) — Comprehensive audit, architectural bottleneck diagnosis, and clean-slate pipeline architecture for Cold Wind AI's Retrieval-Augmented Generation (RAG) and document ETL infrastructure.

## Overview

The legacy RAG subsystem (`core/src/coldwind/core/RAG/`) suffers from severe architectural decay: interactive terminal lockups, fatal process aborts, unindexed on-the-fly embedding re-calculation, PyTorch/Playwright memory bloat, and monolithic coupling. 

This system shelf provides the architectural autopsy of the existing legacy implementation and establishes the tech-agnostic architectural models required to build a modular, high-cohesion, low-coupling RAG pipeline supporting multi-platform clients (CLI, Slint + Rust GUI, Headless API server).

## Interdependence Map

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   RAG & ETL Infrastructure Context                     │
│                                                                        │
│   ┌────────────────────┐                   ┌────────────────────────┐  │
│   │ Client Frontends   │ ◄── Streaming ──► │ Headless Core Engine   │  │
│   │ (CLI, Slint+Rust)  │     Events / IPC  │ (LangGraph Nodes)      │  │
│   └────────────────────┘                   └───────────┬────────────┘  │
│                                                        │               │
│                                                        ▼               │
│                                            ┌────────────────────────┐  │
│                                            │ rag-ETL-infra Pipeline │  │
│                                            │ (Ingest, Index, Query) │  │
│                                            └───────────┬────────────┘  │
│                                                        │               │
│                        ┌───────────────────────────────┴──────────┐    │
│                        ▼                                          ▼    │
│             ┌─────────────────────┐                    ┌─────────────┐ │
│             │ Vector Store Engine │                    │ Graph DB    │ │
│             │ (Persistent Chunks) │                    │ (Neo4j RAG) │ │
│             └─────────────────────┘                    └─────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

## Ownership Table

| Domain | Folder | Document | Description |
|--------|--------|----------|-------------|
| shared | `reports/urgent_development/rag-ETL-infra/` | [`01-legacy-rag-bottlenecks-and-architectural-autopsy.md`](01-legacy-rag-bottlenecks-and-architectural-autopsy.md) | Exhaustive autopsy of legacy RAG flaws, fatal anti-patterns, and tech-agnostic modern pipeline architectures |
| shared | `reports/urgent_development/rag-ETL-infra/` | [`02-ambassador-conveyor-architecture-specification.md`](02-ambassador-conveyor-architecture-specification.md) | Technical architecture specification: Microkernel Conveyor Belt, Platform Ambassador, typed decorator auto-map, and Ambassador-defined State Bus |

## Index

- [`01-legacy-rag-bottlenecks-and-architectural-autopsy.md`](01-legacy-rag-bottlenecks-and-architectural-autopsy.md) — Comprehensive technical audit of current bottlenecks (PyTorch bloat, 16 CLI pauses, `exit()` killswitches, $O(N^2)$ JSON rewrites, unindexed embeddings) and evaluation of pluggable multi-client retrieval architectures.
- [`02-ambassador-conveyor-architecture-specification.md`](02-ambassador-conveyor-architecture-specification.md) — Formal specification of the pluggable Ambassador Conveyor Belt engine, type-safe decorator auto-map, and stage-aware error recovery protocols.
