# Task Index — Feature 1694265

**Status:** 0/7 tasks complete | 7 in-progress | 0 pending

| ID | Title | Status | Assignee | Area |
|----|-------|--------|----------|------|
| [2216015](task-2216015.md) | Task 2216015 — Add shared executor, authentication coordinator, and interaction policy | Active | — | — |
| [2216016](task-2216016.md) | Task 2216016 — Add Azure CLI provider and explicit login contract | Active | — | — |
| [2216017](task-2216017.md) | Task 2216017 — Implement identity binding and atomic auth state | Active | — | — |
| [2216018](task-2216018.md) | Task 2216018 — Implement shared chooser and exactly-once continuation | Active | — | — |
| [2216019](task-2216019.md) | Task 2216019 — Implement passive and active status, stable errors, and source-local logout | Active | — | — |
| [2216020](task-2216020.md) | Task 2216020 — Integrate HTTP, SDK bridge, deploy, and batch paths | Active | — | — |
| [2216021](task-2216021.md) | Task 2216021 — Complete release matrix, docs, telemetry, and Skills pilot | Active | — | — |

## Task Summaries

### [2216015: Task 2216015 — Add shared executor, authentication coordinator, and interaction policy](task-2216015.md)

Implement the Fabric CLI execution foundation for Feature 1694265: - Route one-shot commands, auth subcommands, REPL commands, and batch commands through one parsed-command executor. - Add command cla

### [2216016: Task 2216016 — Add Azure CLI provider and explicit login contract](task-2216016.md)

Implement the explicit Azure CLI authentication source in the Fabric CLI repo: - Add the `azure-identity` dependency and provider protocol agreed with Task 2216015. - Extend `fab auth login` with `--s

### [2216017: Task 2216017 — Implement identity binding and atomic auth state](task-2216017.md)

Implement secure source state and identity binding in the Fabric CLI repo: - Add the versioned configured-source record and idempotent migration of legacy direct-source state. - Refactor environment c

### [2216018: Task 2216018 — Implement shared chooser and exactly-once continuation](task-2216018.md)

Implement the attended authentication experience in the Fabric CLI repo: - Add bounded, safe Azure CLI user discovery only when interaction is eligible. - Integrate Azure CLI into the existing shared 

### [2216019: Task 2216019 — Implement passive and active status, stable errors, and source-local logout](task-2216019.md)

Implement authentication observability and lifecycle behavior in the Fabric CLI repo: - Make plain `fab auth status` passive and add active `--check --audience`. - Preserve the current text ordering a

### [2216020: Task 2216020 — Integrate HTTP, SDK bridge, deploy, and batch paths](task-2216020.md)

Integrate the effective authentication provider across Fabric CLI execution surfaces: - Route `fab_api_client.do_request` token acquisition through the effective provider without interaction. - Genera

### [2216021: Task 2216021 — Complete release matrix, docs, telemetry, and Skills pilot](task-2216021.md)

Complete release readiness for Feature 1694265 in the Fabric CLI repo: - Execute and document the full requirement and test-plan evidence matrix. - Complete Windows, Linux, macOS, identity, drift, rac
