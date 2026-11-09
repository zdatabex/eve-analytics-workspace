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

GitHub Issues are the source of truth for task status, assignment, priority, and dependencies. Status is a single `status:` label. See `docs/development/agent-workflow.md`.

1. A human opens an issue with the business need, scope, and acceptance criteria.
2. The human adds `status:needs-spec`. The dispatcher names the owning agent.
3. The owning agent writes `specs/DATA-*.md` and opens a specification pull request. The agent does not implement.
4. The reviewer checks the specification. The label stays `status:spec-review`. When changes are requested, the owning agent updates the open specification pull request and does not implement. A human approves and merges it, or rejects it by closing the pull request without merging and setting `status:blocked`.
5. The issue moves to `status:ready` only after the specification pull request merges.
6. The owning agent implements the merged specification in an isolated worktree and isolated schema when the specification requires one.
7. The agent validates acceptance criteria and tests, then opens an implementation pull request.
8. The reviewer checks the implementation. The label stays `status:review`. When changes are requested, the owning agent updates the open implementation pull request. A human approves and merges it, or rejects it by closing the pull request without merging and setting `status:blocked`.
9. After required checks pass, a human closes the issue.

Specifications use Markdown with YAML frontmatter. The template is `agent-platform/templates/spec.md`.

Do not deploy unless the specification sets `delivery.deployment_required` and a human approves the deployment.

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
