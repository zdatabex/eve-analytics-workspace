# System Overview

## Component boundaries

### Contracts
Defines shared interfaces between components:
- Data schemas
- Event definitions
- Naming conventions
- Entity definitions
- Data ownership metadata

### Data Generation
Creates or ingests source data for development and testing.

### Orchestration
Executes data pipelines:
- Workflow definitions
- Scheduling and triggering
- Task dependencies
- Retries and failure handling
- Backfills and reprocessing
- Execution monitoring

Orchestrator-specific implementations (Airflow, Prefect, etc.)
live under `orchestration/`.

The dispatcher in `agent-platform/dispatcher` moves issue status
and assigns the owning agent. It does not run data pipelines.

### Warehouse / dbt
Owns:
- Staging models
- Intermediate transformations
- Marts
- Data quality tests
- Documentation

### Analytics
Hex and Omni consume governed warehouse models and shared metadata.

### Agent Platform
Houses the dispatcher, specification templates, and ticket workflow.

The dispatcher assigns the owning agent and moves issue status.
Domain agents prepare specifications and implement them.
The reviewer evaluates specifications and implementations.

### Infrastructure
Owns infrastructure provisioning, environments, permissions,
and deployment configuration.

## Dependency direction

Contracts are the shared interface.

Data generation produces source data.
dbt transforms source data into governed models.
Analytics applications consume governed models.

Agents coordinate work across these boundaries without
taking ownership away from the components.
