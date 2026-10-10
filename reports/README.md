
# 📚 Cold Wind AI — Reports Library

Long-form architecture reports for the **Cold Wind AI** (`ai-workflow-task-agent`) project.
These documents capture architectural decisions, subsystem blueprints, debugging
investigations, and learning artifacts. They are the project's **high-cost context
library** — read the report you need, don't pre-load all of them.

## Conventions

- **System-first shelves**: one folder per system: `logging-system/`, `event-system/`, `model-management/`… never numbers, never one-off topic names.
- **Domain packages**: inside each system, subfolders are `core/`, `desktop/`, `server/`, or `shared/` — one per platform. Adding a new platform = adding a new folder, not restructuring.
- Each system folder has a strict `README.md` skeleton: Domain → Overview → Interdependence Map → Ownership Table → Index.
- Reports follow the **report-protocol** structure: Executive summary → System context → Detailed analysis (with diagrams) → Code walkthrough → Testing → Learning outcomes → Quick reference → Glossary → Q&A.
- Reports are written in **tutor voice**: plain English first, physical metaphors allowed, one concept at a time.

## Index

| System | Domain(s) | Folder | Contents |
|--------|-----------|--------|----------|
| **Logging System** | core, desktop | [`logging-system/`](logging-system/README.md) | Handler architecture, routing, text-archiving, dashboard handler, socket transport, dashboard printer. Full DIY-handler tutorial. |
| **UV Package Manager** | shared | [`uv-package-manager/`](uv-package-manager/README.md) | Essentials-only uv curriculum: packaging foundations (virtualenv, wheels, editable/.pth, namespace packages), then uv setup, dependency lifecycle, pyproject/hatchling, lockfile mechanics, and the workspace capstone. |
| **Cold Wind AI Vision** | shared | [`new_wind_ai/`](new_wind_ai/COLD_WIND_AI_VISION.md) | Long-term architecture blueprint: headless agent engine, pluggable Slint/Rust GUI, MCP cloud pods, and modernized single-shot RAG. |
| **RAG & ETL Infrastructure** | core, shared | [`urgent_development/rag-ETL-infra/`](urgent_development/rag-ETL-infra/README.md) | Legacy RAG architectural autopsy, fatal bottlenecks (PyTorch bloat, process exit traps, 16 terminal pauses), and pluggable dual-plane pipeline design. |
| **Documentation Audit (v2.0.0)** | shared | [`urgent_development/docs-updated-2026-10-08.md`](urgent_development/docs-updated-2026-10-08.md) | Final report of the repo-wide docs staleness audit (issue #7): root + 11 core + 2 desktop READMEs rewritten to verified v2.0.0 reality; MCP `"servers"` key fix; latent code bugs flagged to the memory graph. |

## Future Systems

- **event-system/** — listeners, exit tickets, shutdown protocol
- **runtime-context/** — `ContextRegistry`, dynamic service store, `CoreRunTimeObjects`
- **model-management/** — model loading, caching, `ModelManager`
- **agent-orchestration/** — `AgentGraphCore`, `spawn_agent`, hierarchical sub-agents
- **mcp-integration/** — dynamic tool registration, `.mcp.json` loading

## Related

- Repo-level rules and invariants: [`../AGENTS.md`](../AGENTS.md)
- Core logging source: [`../core/src/coldwind/core/system_logging/`](../core/src/coldwind/core/system_logging/)
- Desktop dashboard source: [`../desktop/src/coldwind/desktop/dashboard/`](../desktop/src/coldwind/desktop/dashboard/)
