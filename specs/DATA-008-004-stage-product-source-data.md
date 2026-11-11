---
id: DATA-008-004
title: Stage Product source data
type: implementation
agent: analytics-engineer
skills:
  - dbt-development
  - using-dbt-for-analytics-engineering
  - data-modeling
  - data-quality
priority: critical
components:
  - dbt
dependencies:
  - DATA-007-001
requires_approval: true
allowed_paths:
  - warehouse/dbt/models/staging/product/
  - warehouse/dbt/tests/staging/product/
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
  - warehouse/dbt/macros/
  - warehouse/dbt/models/intermediate/
  - warehouse/dbt/models/marts/
  - warehouse/dbt/models/utilities/
  - warehouse/dbt/models/staging/hubspot/
  - warehouse/dbt/models/staging/dealhub/
  - warehouse/dbt/models/staging/marketing/
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

Provide the dbt staging interface for every contracted Product source entity so later warehouse models can consume Product data without reading `raw_product`.

The interface preserves source grain, source identifiers, and source values. It documents that interface and enforces it with tests. It does not resolve canonical identity, build historical dimensions, derive adoption, aggregate, join another source system, or calculate a business metric.

## Business context

GitHub issue #31 (`DATA-008-004 — Stage Product source data`) is the Product child of epic #27 (`DATA-008 — Stage GTM Source Data`). Downstream modeling needs each source staged independently. Product owns the firm as a tenant, the product login, the workflow catalog, usage, and outcomes. It does not own sales stage, bookings, or ARR inputs.

DATA-007-001 initialized `warehouse/dbt/` and declared the landed Product tables as dbt sources. DATA-006 loads those tables into `raw_product` in `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. The physical contracts are `contracts/source/product/`. The logical mapping is `docs/data-model/source-mapping.md`. Canonical entities in `docs/data-model/entities.md` stay downstream of this task.

HubSpot, DealHub, and Marketing staging belong to DATA-008-001, DATA-008-002, and DATA-008-003. This task does not stage those systems and does not wait on their models.

## Scope

The implementation is confined to new Product staging models and Product staging tests under `warehouse/dbt/`.

The source relation for each model is the dbt source already declared in `warehouse/dbt/models/staging/product/_product__sources.yml`. That file points at schema `raw_product` and tables `firm`, `user`, `ai_workflow`, `usage`, and `outcome`. Models select those relations with `source('product', ...)`. They do not hardcode a database or schema name.

### Staged models

Each model is one row-preserving projection of one landed table. The project default materialization is a view. This task does not override it. The column names, column order, and values match the landed table: contract fields in contract order, then `source_system`, `delivery_id`, and `ingested_at`. No column is renamed, dropped, or added.

| Model | Source | History | Grain | Unique key |
|---|---|---|---|---|
| `stg_product__firm` | `source('product', 'firm')` | current | One Product firm. | `product_firm_id` |
| `stg_product__user` | `source('product', 'user')` | observation | One observation of one product user at one `observed_at`. | `product_user_source_id`, `observed_at` |
| `stg_product__ai_workflow` | `source('product', 'ai_workflow')` | current | One AI workflow. | `product_workflow_id` |
| `stg_product__usage` | `source('product', 'usage')` | immutable | One usage of one AI workflow by one product user. | `product_usage_source_id` |
| `stg_product__outcome` | `source('product', 'outcome')` | immutable | One outcome of one product usage event. | `product_outcome_source_id` |

`stg_product__user` is not one current login and not one effective-dated version. Firm and workflow models store one current source row because that is the landed contract, not because this task collapsed history. Usage is not copied onto a lifecycle event. Outcome does not identify the account's first outcome.

### Columns

`stg_product__firm`: `product_firm_id`, `firm_name`, `primary_domain`, `state`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__user`: `product_user_source_id`, `email_normalized`, `status`, `observed_at`, `product_firm_id`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__ai_workflow`: `product_workflow_id`, `workflow_code`, `workflow_name`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__usage`: `product_usage_source_id`, `occurred_at`, `work_unit_count`, `product_user_source_id`, `product_firm_id`, `product_workflow_id`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__outcome`: `product_outcome_source_id`, `occurred_at`, `outcome_type`, `product_usage_source_id`, `product_user_source_id`, `product_firm_id`, `product_workflow_id`, `source_system`, `delivery_id`, `ingested_at`.

Required strings are present and non-empty. A missing optional value stays null. An empty string is invalid and is not converted to null. Product identifiers stay opaque non-empty strings. Their expected shape is not a rejection rule.

`source_system` is `product` on every row. `delivery_id` is a non-empty batch id and is not unique. `ingested_at` is a timestamp and may be later than `observed_at` or `occurred_at`. Late delivery stays valid. `ingested_at` is not required to equal the business timestamp.

Nullable strings, when present, are non-empty. `email_normalized`, when present, is lowercase and trimmed. Duplicate emails are valid, including across firms. `primary_domain`, when present, is a lowercase host with no scheme, no path, no backslash, no `@`, and no whitespace. Duplicate domains are valid. `state`, `workflow_code`, and `workflow_name` stay open strings. `workflow_code` is unique across workflows.

`status` is `invited`, `active`, or `inactive`. `outcome_type` is `draft_completed`, `review_accepted`, or `exported`. `work_unit_count` is an integer of at least 1. Usage has no commercial amount.

### Relationships inside Product

Relationship tests use source identifiers. They do not create canonical foreign keys.

- `stg_product__user.product_firm_id` matches `stg_product__firm.product_firm_id`.
- `stg_product__usage.product_user_source_id` matches `stg_product__user.product_user_source_id`. The user key is not unique; many observations can share one login id.
- `stg_product__usage.product_firm_id` matches `stg_product__firm.product_firm_id`.
- `stg_product__usage.product_workflow_id` matches `stg_product__ai_workflow.product_workflow_id`.
- `stg_product__outcome.product_usage_source_id` matches `stg_product__usage.product_usage_source_id` and is unique among outcomes.
- `stg_product__outcome.product_user_source_id` matches `stg_product__user.product_user_source_id`.
- `stg_product__outcome.product_firm_id` matches `stg_product__firm.product_firm_id`.
- `stg_product__outcome.product_workflow_id` matches `stg_product__ai_workflow.product_workflow_id`.

For each usage row, the user observation in effect is the single `stg_product__user` row with that `product_user_source_id` whose `observed_at` is the greatest value still less than or equal to the usage `occurred_at`. That row's `product_firm_id` equals the usage `product_firm_id`. If no user observation is in effect, the check fails. A later user observation does not replace an earlier firm on an earlier usage. This check reads the staged models. It does not add `effective_start`, `effective_end`, or `is_current`.

On each outcome, `product_user_source_id`, `product_firm_id`, and `product_workflow_id` equal the same fields on the cited usage. The outcome `occurred_at` is greater than or equal to that usage `occurred_at`.

These checks fail while leaving the offending source row in the staged model. Staging does not filter, impute, deduplicate, or quarantine rows.

### Reconciliation

There are no approved reconciliation exceptions.

For each of the five models, the staged row set equals the landed source row set on every column. A missing staged row, an extra staged row, a different value, or a different column set is a failure. Timestamp and integer casts are allowed only when every value still compares equal to the landed value in both development warehouses. A cast that breaks that comparison is not an exception.

The empty exception list is stated in the model documentation. The reconciliation tests fail when any difference is present, so an unapproved difference cannot pass silently.

### Documentation and tests

One schema YAML file in `warehouse/dbt/models/staging/product/`, separate from `_product__sources.yml`, documents the five models. Each model description states its purpose, grain, history class, source table, unique key, and that canonical identity, adoption, and metrics are not applied. Each column description states the source meaning, including whether the column is an identifier, an open string, an enum, a relationship, a measure, or ingestion metadata. Descriptions also state when a column is not a canonical surrogate and not an adoption measure.

Schema tests cover uniqueness of each unique key, not-null constraints on every required column, accepted values for `source_system`, `status`, and `outcome_type`, the Product relationships above, `workflow_code` uniqueness, non-empty required and present optional strings, the email and domain constraints, and `work_unit_count >= 1`.

Singular tests under `warehouse/dbt/tests/staging/product/` cover exact reconciliation to each source, the usage firm in effect, and outcome agreement with the cited usage. Test names identify the entity and the rule. A violation of any rule fails the relevant test.

Generator window bounds, ingest-lag counts, and campaign or commercial rules are not Product staging checks. DATA-005 already validates generated datasets. This task does not copy that suite.

## Deliverables

- `stg_product__firm`, `stg_product__user`, `stg_product__ai_workflow`, `stg_product__usage`, and `stg_product__outcome` in `warehouse/dbt/models/staging/product/`.
- Schema YAML documenting grain, history, columns, and the empty reconciliation-exception list, with the tests listed above.
- Singular reconciliation and cross-row Product tests in `warehouse/dbt/tests/staging/product/`.
- No other files.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/product/` and do not edit it.
- Do not edit `_product__sources.yml`, `dbt_project.yml`, `packages.yml`, `package-lock.yml`, `profiles.yml`, `warehouse/dbt/README.md`, macros, utilities, or another source system's staging directory.
- Do not add a dbt package. `dbt_utils` is already installed and may be used.
- Do not call `effective_date` or `dbt_utils.generate_surrogate_key` in these models.
- Do not add canonical columns: `account_id`, `contact_id`, `product_user_id`, `ai_workflow_id`, `product_usage_id`, `product_outcome_id`, `lifecycle_event_id`, any `surviving_*` column, `commercial_status`, `effective_start`, `effective_end`, `is_current`, `customer_converted`, `adoption_reached`, `emitted_event`, or a metric column.
- Do not join HubSpot, DealHub, or Marketing, and do not match a Product firm to a company on `primary_domain`.
- Do not treat duplicate emails, duplicate domains, or a later user firm as defects to be removed. A user may cite a different `product_firm_id` on a later observation; both observations stay.
- Do not derive adoption, usage intensity, a lifecycle event, or an account-level first outcome.
- Use an isolated target schema whose name starts with `dev` and identifies this issue, such as `dev_data_008_004`. Do not build into `raw_product` or the shared `dev_dbt` schema.
- Validate against `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Do not commit either file, dbt artifacts, or a virtualenv.
- No integration test, end-to-end test, deployment, or production warehouse change is required.

## Acceptance criteria

- [ ] The implementation changes only `warehouse/dbt/models/staging/product/` and `warehouse/dbt/tests/staging/product/`, and it does not modify `_product__sources.yml`.
- [ ] The five models exist, each selects only its own `source('product', ...)` table, and `dbt parse` succeeds.
- [ ] Each model has the grain, history class, unique key, and exact column list in this specification. No canonical, adoption, metric, or other-source column is present.
- [ ] Staged rows and values equal the landed Product rows and values in both development warehouses. The documented reconciliation-exception list is empty, and the reconciliation tests fail when a row or value differs.
- [ ] Required columns, unique keys, enums, Product relationships, non-empty strings, email and domain constraints, unique `workflow_code`, `work_unit_count >= 1`, the in-effect usage firm, and outcome agreement with its usage are enforced by automated tests that fail when the rule is violated.
- [ ] Invalid landed rows are still staged. The models do not filter, deduplicate, or rewrite them to make a test pass.
- [ ] The models contain no adoption derivation, cross-source join, aggregation, canonical identity resolution, historical-dimension columns, or business metric.
- [ ] A downstream model can select every contracted Product column from these models with `ref()` and does not need to query `raw_product`.
- [ ] `dbt build` of the Product staging models and Product staging tests exits zero for `data/warehouse/dev_data_003` and for `data/warehouse/dev_data_004`, using an isolated `dev`-prefixed schema.
- [ ] `contracts/`, `data-generation/`, `docs/`, `analytics/`, and every path outside the two allowed directories are unchanged. No warehouse file is committed.

## Execution notes

Implement this specification only after it has merged and issue #31 is `status:ready`. Use an `impl` worktree and the isolated schema above. Do not merge or deploy without human approval.

Before writing SQL, read the five Product contract files and the Product section of `docs/data-model/source-mapping.md`. From `warehouse/dbt/`, use `dbt show --limit` on `source('product', ...)` against `dev_data_003` to confirm landed column names and values. Repeat that check against `dev_data_004` before calling validation complete. Prefer `{{ source() }}` and CTEs. Keep each model a projection of one source.

Set `EVE_DBT_SCHEMA` to the isolated schema and `EVE_DBT_DUCKDB_PATH` to the warehouse file under test. Run `dbt parse`, then `dbt build` selected to `path:models/staging/product` and `path:tests/staging/product`. If a warehouse file is absent, create it through the merged DATA-006 generate and load path and do not commit it.

Schema tests follow the `data_tests` style already used in `warehouse/dbt/models/utilities/schema.yml`. Singular tests should return the violating rows and return no rows when the rule holds. Reconciliation should compare the staged relation to its source in both directions.

Do not edit the shared README. The schema YAML is the staged-interface documentation for this issue.
