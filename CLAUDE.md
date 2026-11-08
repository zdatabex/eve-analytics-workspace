# Eve Analytics Workspace

## Project Overview

This repository is a modular analytics and data engineering workspace.

It contains independently managed components for data generation,
data transformation, analytics, workflow orchestration, infrastructure,
and AI agent coordination.

See `README.md` and `docs/architecture/system-overview.md`
for the overall platform architecture.

## Repository Structure

- `specs/` - Version-controlled task specifications associated with GitHub Issues.
- `contracts/` - Shared schemas, data contracts, and metadata.
- `data-generation/` - Source data generation and ingestion.
- `warehouse/dbt/` - Warehouse transformations and data models.
- `analytics/` - Analytics applications and assets.
- `orchestration/` - Workflow definitions and orchestrator implementations.
- `agent-platform/` - Agent coordination and execution.
- `infrastructure/` - Infrastructure as code and deployment configuration.
- `docs/` - Architecture, decisions, and development documentation.
- `tests/` - Integration and end-to-end tests.

See `workspace.yaml` for component definitions and dependencies.

## Task Management

GitHub Issues is the source of truth for backlog management.

For tasks with detailed requirements:

1. Locate the corresponding GitHub Issue.
2. Read its specification in `specs/`.
3. Review relevant architecture and component documentation.
4. Confirm dependencies, scope, and approval requirements.
5. Implement changes within the assigned component boundaries.
6. Validate acceptance criteria and tests.
7. Submit changes through a pull request.

Specifications use Markdown with YAML frontmatter.

Do not create separate agent backlogs or duplicate task tracking
inside the repository.

## Engineering Principles

- Respect component boundaries and ownership.
- Use `contracts/` for shared interfaces between components.
- Keep business logic outside workflow orchestrators.
- Prefer reusable, maintainable, and testable implementations.
- Avoid duplicating transformation and business logic.
- Preserve existing conventions unless the task requires a change.
- Consider downstream dependencies before modifying shared contracts.
- Document architectural decisions when they affect multiple components.

## Agent Collaboration

- Follow the assigned agent role and task scope.
- Work in an isolated Git worktree when executing independent tickets.
- Do not modify files outside assigned scope without authorization.
- Coordinate changes that affect shared contracts or multiple components.
- Do not overwrite another agent's work.
- Do not merge pull requests or deploy changes without human approval.

## Validation

Before completing a task:

- Run relevant component tests.
- Run integration tests when multiple components are affected.
- Validate data quality and model grain where applicable.
- Update relevant documentation.
- Verify all specification acceptance criteria.

Do not claim completion when validation has not been performed.

## Security

- Never commit credentials, secrets, or sensitive production data.
- Use approved development environments and access permissions.
- Do not modify production resources without explicit authorization.
