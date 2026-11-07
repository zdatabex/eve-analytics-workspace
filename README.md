# Eve Analytics Platform

An end-to-end, modular data and analytics platform.

## Architecture

This repository contains independently managed components:

- `contracts/` - Shared data contracts, schemas, and metadata.
- `data-generation/` - Source data generation and ingestion.
- `warehouse/dbt/` - Warehouse transformations and data models.
- `analytics/hex/` - Hex notebooks, applications, and workflows.
- `analytics/omni/` - Omni analytics and semantic assets.
- `agent-platform/` - Agent orchestration and ticket workflows.
- `infrastructure/` - Infrastructure as code and deployment configuration.
- `tests/` - Cross-component integration and end-to-end tests.

## Development principles

1. Components own their implementation and tests.
2. Shared interfaces are defined in `contracts/`.
3. Changes should be independently testable.
4. Every ticket should have an isolated Git worktree.
5. Agents should work within explicitly assigned component boundaries.
6. Cross-component changes must include integration tests.
7. Deployments should be independently manageable.

## Getting started

See:
- `docs/development/local-development.md`
- `docs/architecture/system-overview.md`
- `docs/development/agent-workflow.md`

## Working on a ticket

```bash
./scripts/worktree.sh create EVE-123 add-customer-attribute
```

Each ticket gets its own branch and worktree under `.worktrees/`.
