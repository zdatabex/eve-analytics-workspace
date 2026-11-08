---
id: DATA-000
title: Example task
type: implementation
agent: analytics-engineer
skills:
  - dbt-development
priority: medium
components:
  - dbt
dependencies: []
requires_approval: true
allowed_paths:
  - warehouse/dbt/
excluded_paths: []
contracts:
  changes_required: false
  affected_contracts: []
testing:
  component_tests: true
  integration_tests: false
  end_to_end_tests: false
environment:
  isolated_schema: true
  schema_prefix: dev
delivery:
  pull_request_required: true
  human_approval_required: true
  deployment_required: false
---

## Objective

Describe the desired outcome.

## Business context

Describe the business need from the GitHub Issue.

## Scope

List the components and paths this task may change.

## Deliverables

- Deliverable

## Constraints

- Stay inside `allowed_paths`.
- Change `contracts/` only when `contracts.changes_required` is true.

## Acceptance criteria

- Criterion

## Execution notes

Notes for the implementation phase. Leave implementation choices to the owning agent.
