# Issue Workflow

GitHub Issues are the source of truth for task status, assignment, priority, and dependencies. Specifications in `specs/` are the version-controlled implementation contract. Pull requests are the delivery and review mechanism.

The dispatcher in `agent-platform/dispatcher` assigns the owning agent and records issue status. It sets `status:ready` after the specification merges and `status:needs-close` after the implementation checks pass. It does not implement the work. Data pipeline scheduling stays in `orchestration/` and is owned by `data-engineer`.

## Workflow

1. A human opens a GitHub Issue with the business need, scope, and acceptance criteria. The issue stays open until the work is accepted.
2. The human adds `status:needs-spec`. The dispatcher determines the owning agent from the ownership rules below.
3. The owning agent reviews the issue, repository documentation, architecture, contracts, and relevant skills. The agent writes `specs/DATA-<id>-<slug>.md` and does not implement the task.
4. The agent opens a specification pull request and sets `status:spec-review`. The reviewer checks the specification against the issue and project standards and reports findings on the pull request. The reviewer does not change the label or the files. When changes are requested, the label stays `status:spec-review`. The owning agent updates `specs/DATA-<id>-<slug>.md` on the existing `spec/` branch and pushes to the open pull request. The agent does not open a second pull request and does not implement. A human approves and merges the specification, or rejects it by closing the pull request without merging and setting `status:blocked` with a comment on why.
5. After the specification is approved and merged, a human or the dispatcher sets `status:ready`. The dispatcher confirms dependencies and names the implementation agent. The implementation agent is the same owner unless the specification says otherwise. `status:ready` is not set before that merge.
6. The owning agent sets `status:in-progress`, creates an `impl` worktree, and implements the merged specification inside `allowed_paths`. The agent creates an isolated development schema when the specification requires one, writes and runs the required tests, updates documentation, checks downstream contracts and models, and validates the acceptance criteria.
7. The agent opens an implementation pull request and sets `status:review`. The reviewer evaluates the implementation against the merged specification, the acceptance criteria, and project standards. The reviewer reports findings on the pull request and does not modify implementation code or the label. When changes are requested, the label stays `status:review`. The owning agent updates the existing `impl/` branch and pushes to the open pull request. A human approves and merges it, or rejects it by closing the pull request without merging and setting `status:blocked` with a comment on why.
8. A human approves the pull request where required, and the approved changes merge to the main branch.
9. After the pull request is merged and required checks have passed, the dispatcher sets `status:needs-close`. A human closes the GitHub Issue. Dependent issues stay put until their prerequisites are closed. They then become eligible for specification or implementation according to their own status label.

Agents do not resume an issue labeled `status:blocked`. Restarting rejected work is a later human decision: close the issue, or remove the old branch and set `status:needs-spec`.

Deployment is a separate human gate. It happens only when the specification sets `delivery.deployment_required`.

## Agent ownership

| Agent | Responsibility |
|---|---|
| `data-engineer` | Data generation, ingestion, source schemas, and data pipeline orchestration under `orchestration/` |
| `analytics-engineer` | Warehouse transformations in dbt, including canonical warehouse models |
| `analyst` | Hex and Omni analytics implementation |
| `reviewer` | Independent review of specifications and implementations |
| `dispatcher` | Assigns the owning agent and records issue status. Does not implement. |

`data-modeling` follows the layer it changes. Source schemas belong to `data-engineer`. Warehouse models belong to `analytics-engineer`. `data-quality` is a skill used by the owning agent and by `reviewer`.

Infrastructure work stays `status:blocked` until a human assigns it.

One issue has one owning agent. That agent may edit `contracts/` only when the specification sets `contracts.changes_required`. Work that needs another domain agent becomes a dependent issue. A specification that lists more than one component requires integration tests.

## Status labels

| Label | Meaning |
|---|---|
| `status:needs-spec` | Specification preparation is requested. |
| `status:spec-review` | The specification is submitted for review. |
| `status:ready` | The specification is approved and implementation can begin. |
| `status:in-progress` | Implementation is underway. |
| `status:review` | The implementation is submitted for review. |
| `status:needs-close` | The implementation has merged, the checks have passed, and a human closes the issue. |
| `status:blocked` | Work is waiting on clarification, a decision, or a dependency. |

Only one `status:` label is active on an issue. The dispatcher `set` command enforces that rule. Agents do not advance an issue labeled `status:blocked`.

| Label | Setter |
|---|---|
| `status:needs-spec` | Human |
| `status:spec-review` | Owning agent, when the specification pull request opens |
| `status:ready` | Human or dispatcher, after the specification pull request merges |
| `status:in-progress` | Owning agent, when implementation starts |
| `status:review` | Owning agent, when the implementation pull request opens |
| `status:needs-close` | Dispatcher, after the implementation pull request merges and required checks pass |
| `status:blocked` | Human |

Create the labels with `./agent-platform/dispatcher/dispatcher.sh create-labels`.

## Worktrees

Specification and implementation use different branches:

```bash
./scripts/worktree.sh create spec DATA-123 add-customer-attribute
./scripts/worktree.sh create impl DATA-123 add-customer-attribute
```

Agents may work on independent issues at the same time. Each issue uses its own worktree and, during implementation, its own development schema.

Agents must not:
- Modify files outside their assigned scope without approval.
- Change shared contracts unless the specification allows it.
- Modify another issue's worktree.
- Merge or deploy without human approval.
- Implement a task while its label is `status:needs-spec` or `status:spec-review`.

## Completion

An issue is complete only when:
- The implementation pull request has merged.
- Acceptance criteria are met.
- Required tests have passed.
- Documentation is updated.
- Downstream contracts and models have been checked.
- The reviewer has reported findings and a human has approved the merge.
- Required checks have passed and a human has closed the issue.
