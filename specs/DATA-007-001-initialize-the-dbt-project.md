---
id: DATA-007-001
title: Initialize the dbt project
type: implementation
agent: analytics-engineer
skills:
  - dbt-development
  - using-dbt-for-analytics-engineering
  - data-modeling
priority: critical
components:
  - dbt
dependencies:
  - DATA-006
requires_approval: true
allowed_paths:
  - warehouse/dbt/
excluded_paths:
  - contracts/
  - data-generation/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - docs/
  - specs/
  - tests/
  - data/
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

Initialize the dbt component under `warehouse/dbt/` so later warehouse issues can add models inside ticket-owned model directories without changing shared project configuration or raw-source declarations.

The project must parse and compile against the baseline DuckDB warehouse landed by DATA-006. It must also provide the common warehouse structures and macros that later staging, intermediate, and mart work will reuse.

## Business context

GitHub issue #25 (`DATA-007-001 — Initialize the dbt project`) is the foundation for warehouse transformation work. DATA-006 lands the generated source data in one DuckDB file per dataset, with one raw schema per source system. This task exposes that landed layout to dbt and establishes shared conventions; it does not transform source entities or define business metrics.

The baseline warehouse file is `data/warehouse/dev_data_003`. The scenario warehouse file is `data/warehouse/dev_data_004`. Both files use the same raw schemas and tables. These warehouse files are generated local artifacts and must not be committed.

DATA-007-002 owns the metric and mart contract and may proceed independently. This task must not define metric formulas or build metric marts.

## Scope

The implementation is confined to `warehouse/dbt/` and covers:

1. A dbt project and local DuckDB connection configuration that can target the warehouse file selected for the run.
2. One dbt source YAML file for each source system, pointed at the raw schemas and tables landed by DATA-006.
3. Tracked model-layer directories for staging, intermediate models, and marts.
4. A shared date spine model.
5. Shared macros for deterministic surrogate keys and effective dating.
6. Component documentation and tests for the foundation created here.

The source inventory is:

| Source system | DuckDB schema | Declared tables |
|---|---|---|
| HubSpot | `raw_hubspot` | `company`, `contact`, `lead`, `deal`, `activity` |
| DealHub | `raw_dealhub` | `quote`, `contract`, `subscription`, `booking` |
| Marketing | `raw_marketing` | `campaign`, `campaign_performance`, `touch` |
| Product | `raw_product` | `firm`, `user`, `ai_workflow`, `usage`, `outcome` |

Source declarations expose the landed tables as sources only. This task adds no entity staging SQL, identity resolution, conformed dimensions, lifecycle-event models, business marts, semantic definitions, or metric calculations.

The date spine is a warehouse utility, not a canonical calendar entity. It has one row per calendar date at a documented inclusive range, with a unique, non-null date key. Its configured range must cover the dates in the baseline development dataset without deriving a new business entity.

The effective-dating macro must implement the approved historical convention from `docs/data-model/decisions.md`: `effective_start` is inclusive, `effective_end` is exclusive, the current row has an open end, and exactly one current row exists for each surviving entity. The macro interface and output columns must be documented so later model issues can reuse it consistently. The surrogate-key macro must produce deterministic, null-safe keys from an ordered set of input fields.

## Deliverables

- A valid dbt project rooted at `warehouse/dbt/`, including the project, profile or connection configuration, dependency metadata when required, and ignore rules for local dbt artifacts.
- Exactly one source YAML file per source system, declaring every raw table in the source inventory and no unlanded source.
- Tracked `staging`, `intermediate`, and `marts` model-layer directories.
- A queryable date spine model with schema documentation and uniqueness and not-null tests for its date key.
- Shared surrogate-key and effective-dating macros, with usage and semantics documented.
- `warehouse/dbt/README.md`, documenting:
  - setup and validation commands;
  - `data/warehouse/dev_data_003` as the baseline warehouse file;
  - `data/warehouse/dev_data_004` as the scenario warehouse file;
  - the four raw schema names;
  - the date-spine and macro conventions;
  - the directory-ownership rule for later issues.

The directory-ownership rule is: every later warehouse issue adds models only in its own child directory under the appropriate model layer. Later issues do not edit `dbt_project.yml` or the four source YAML files created by this task. Any future shared-project or raw-source change requires a separately scoped task.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/` but do not edit it.
- Treat the DATA-006 landed schema and table names as the source interface. Do not rename, reshape, or copy raw tables in this task.
- Configure the warehouse path without committing a machine-specific absolute path, credentials, or a DuckDB file.
- Use an isolated development target/schema for implementation validation. The schema name must use the `dev` prefix and must not overwrite another developer's objects.
- Keep generated dbt artifacts, local environment files, and DuckDB warehouse files untracked.
- Follow dbt dependency and package-lock conventions if an external package is used. Do not add a package when the required behavior can be maintained clearly in the project itself.
- Preserve explicit grain and keys. The date spine grain is one row per calendar date.
- Do not add entity staging models merely to exercise sources or macros.
- Do not define formulas for sourced or influenced pipeline, bookings, ARR, retention, adoption, customer value, or executive metrics.
- Do not change `contracts/`, `data-generation/`, `analytics/`, `docs/data-model/`, or any other path outside `warehouse/dbt/`.
- No integration test, end-to-end test, deployment, or production warehouse change is required.

## Acceptance criteria

- [ ] The implementation changes only `warehouse/dbt/`.
- [ ] From `warehouse/dbt/`, `dbt parse` succeeds with the documented project configuration.
- [ ] With `data/warehouse/dev_data_003` present and selected, `dbt compile` succeeds using an isolated `dev`-prefixed target/schema.
- [ ] One source YAML file exists for each of HubSpot, DealHub, Marketing, and Product. Each points to its corresponding `raw_<source_system>` schema and declares every table in the source inventory exactly once.
- [ ] `dbt source freshness` is not required unless freshness rules are explicitly added; the source declarations do not invent freshness guarantees absent from the landed contracts.
- [ ] Staging, intermediate, and mart directories are present in the tracked project, and no entity staging model, identity-resolution model, conformed dimension, lifecycle-event model, business mart, semantic definition, or metric definition is added.
- [ ] The date spine builds in the isolated development target and can be queried. It returns one row per calendar date in its documented inclusive range, and its date key passes uniqueness and not-null tests.
- [ ] The surrogate-key macro exists, is deterministic and null-safe for an ordered set of input fields, and has documented usage.
- [ ] The effective-dating macro exists and documents or emits inclusive `effective_start`, exclusive `effective_end`, an open end for the current row, and exactly one current row per surviving entity.
- [ ] `warehouse/dbt/README.md` documents both warehouse files, all four raw schemas, setup and validation, shared utilities, and the later-issue directory rule.
- [ ] Component validation runs only selected foundation resources and includes `dbt parse`, `dbt compile`, building the date spine, and testing its key. All documented validation commands exit zero.
- [ ] No file under `data/warehouse/` is committed. Generated dbt artifacts and local credentials or environment files are not committed.
- [ ] `contracts/`, `data-generation/`, `analytics/`, `docs/data-model/`, and all other paths outside `warehouse/dbt/` are unchanged.

## Execution notes

Implement this specification only after it has merged and issue #25 has moved to `status:ready`. Use an `impl` worktree and an isolated `dev`-prefixed target/schema. Do not merge or deploy without human approval.

Before implementation, read the DATA-006 specification and inspect the landed baseline warehouse through dbt. Use `dbt show` with limits to confirm source columns and values before later model work; this initialization task does not need to reproduce source columns in staging models.

Keep project-wide configuration in this task so later issues can remain within ticket-owned model directories. Prefer standard dbt references and source declarations over hardcoded relation names. Document any environment variable used to switch between `dev_data_003` and `dev_data_004`, with the baseline file as the development default.

Validation is local component validation from `warehouse/dbt/`: parse and compile the project against the DATA-006 baseline warehouse, build only the date spine, run its selected tests, and query a limited sample. If `data/warehouse/dev_data_003` is absent, create it through the merged DATA-006 generate/load path; never commit it.
