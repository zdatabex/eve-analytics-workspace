# Task Specifications

This directory contains version-controlled specifications for work tracked in GitHub Issues.

## Purpose

GitHub Issues is the source of truth for backlog management, including priorities, assignments, dependencies, and task status.

Specification files provide agents with the detailed context and instructions needed to execute individual tasks.

## Organization

Each task that requires a specification has one Markdown file:

```text
specs/
├── README.md
├── GTM-001-design-canonical-data-model.md
├── GTM-002-define-source-schemas.md
└── GTM-003-implement-data-generators.md
```

The filename should begin with the corresponding GitHub Issue ID.

## Specification Format

Each file uses Markdown with YAML frontmatter.

The frontmatter identifies the task and provides execution metadata, such as:

- `id`: GitHub Issue ID
- `title`: Task title
- `type`: Task category
- `status`: Execution readiness
- `agent`: Primary responsible agent
- `priority`: Task priority
- `components`: Affected project components
- `dependencies`: Prerequisite tasks
- `requires_approval`: Whether human approval is required

The Markdown body describes:

- Objective
- Business context
- Scope
- Deliverables
- Constraints
- Acceptance criteria
- Execution instructions

## Agent Workflow

1. Find the assigned task in GitHub Issues.
2. Read its corresponding specification.
3. Review relevant project documentation, standards, and existing implementation.
4. Confirm dependencies and approval requirements.
5. Execute the task in an isolated Git worktree.
6. Validate deliverables against the acceptance criteria.
7. Submit changes through a pull request.

## Guidelines

- GitHub Issues remains the authoritative backlog.
- Each substantial task should have one corresponding specification file.
- Keep specifications focused on requirements and expected outcomes, not implementation details that agents should determine.
- Update specifications through pull requests when approved requirements or decisions change.
- Do not create separate backlogs for individual agents.
