# Task Specifications

This directory contains version-controlled specifications for work tracked in GitHub Issues.

## Purpose

GitHub Issues are the source of truth for task status, assignment, priority, and dependencies. Status is a single `status:` label. See `docs/development/agent-workflow.md`.

Specification files are the implementation contract for an approved issue. The owning agent writes the specification during `status:needs-spec` and implements it only after that specification has merged and the issue is `status:ready`.

## Organization

Each task has one Markdown file:

```text
specs/
├── README.md
├── DATA-001-design-canonical-data-model.md
├── DATA-002-define-source-schemas.md
└── DATA-003-implement-data-generators.md
```

The filename begins with the issue id, using the `DATA-` prefix, followed by a short slug.

Copy `agent-platform/templates/spec.md` when creating a specification.

## Specification format

Each file uses Markdown with YAML frontmatter.

The frontmatter identifies the task:

- `id`: Issue id, such as `DATA-123`
- `title`: Task title
- `type`: Task category
- `agent`: The one owning agent
- `skills`: Skills required for the task
- `priority`: Task priority
- `components`: Affected project components
- `dependencies`: Prerequisite issue ids
- `requires_approval`: Whether human approval is required
- `allowed_paths`: Paths the implementation may change
- `excluded_paths`: Paths the implementation must not change
- `contracts`: Whether shared contracts change, and which ones
- `testing`: Component, integration, and end-to-end test flags
- `environment`: Isolated schema settings
- `delivery`: Pull request, human approval, and deployment flags

The frontmatter has no `status` field. GitHub labels are the only status.

The Markdown body describes:

- Objective
- Business context
- Scope
- Deliverables
- Constraints
- Acceptance criteria
- Execution notes

## Phases

1. On `status:needs-spec`, the owning agent writes this specification and opens a pull request. The agent does not implement the task.
2. The reviewer checks the specification against the issue. The label stays `status:spec-review`. When changes are requested, the owning agent updates the specification on the open pull request and does not implement. A human approves and merges it. A human rejects it by closing the pull request without merging and setting `status:blocked`.
3. On `status:ready` or `status:in-progress`, the owning agent implements the merged specification in an isolated worktree. On `status:review`, requested changes stay on the open implementation pull request.

The full sequence, label setters, and ownership rules are in `docs/development/agent-workflow.md`.

## Guidelines

- GitHub Issues remain the authoritative backlog.
- Each task has one specification file.
- Keep specifications focused on requirements and expected outcomes, not implementation details the owning agent should determine.
- Update specifications through pull requests when approved requirements change.
- Do not create separate backlogs for individual agents.
- One issue has one `agent`. Work for another domain agent becomes a dependent issue.
- The owning agent may edit `contracts/` only when `contracts.changes_required` is true.
- More than one entry in `components` requires integration tests.
