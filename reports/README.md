
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
