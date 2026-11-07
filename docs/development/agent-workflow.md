# Agent Development Workflow

Every ticket is an isolated unit of work.

## Workflow

1. Read the ticket specification.
2. Analyze dependencies and affected components.
3. Identify contract changes.
4. Create an isolated Git worktree.
5. Create an isolated development schema/environment.
6. Assign implementation to component-specific agents.
7. Run component tests.
8. Run cross-component integration tests.
9. Perform independent code and data review.
10. Validate acceptance criteria.
11. Open a pull request.
12. Obtain human approval before merging.

## Parallel execution

Agents may work simultaneously when their changes do not conflict.

Use separate worktrees and development schemas for each ticket.

Agents must not:
- Modify files outside their assigned scope without approval.
- Change shared contracts without identifying downstream impact.
- Modify another ticket's worktree.
- Merge or deploy without authorization.

## Completion requirements

A ticket is complete only when:
- Acceptance criteria are met.
- Tests pass.
- Documentation is updated.
- Downstream dependencies are validated.
- Changes are reviewed.
