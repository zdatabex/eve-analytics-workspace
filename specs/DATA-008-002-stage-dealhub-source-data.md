---
id: DATA-008-002
title: Stage DealHub source data
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
  - warehouse/dbt/models/staging/dealhub/
  - warehouse/dbt/tests/dealhub/
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
  - warehouse/dbt/models/staging/hubspot/
  - warehouse/dbt/models/staging/marketing/
  - warehouse/dbt/models/staging/product/
  - warehouse/dbt/models/intermediate/
  - warehouse/dbt/models/marts/
  - warehouse/dbt/models/utilities/
  - warehouse/dbt/macros/
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

Provide a trusted dbt staging interface for every contracted DealHub entity so later warehouse models can consume DealHub observations without reading `raw_dealhub`.

The staged grain is the source grain. Quote, contract, and subscription stay one observation per source identifier and `observed_at`. Booking stays one immutable booking. Commercial amounts stay on the entity that observed them. The models do not resolve canonical identity, build historical dimensions, derive lifecycle events, annualize revenue, or calculate business metrics.

## Business context

GitHub issue #30 (`DATA-008-002 — Stage DealHub source data`) is a child of epic #27. It depends on DATA-007-001. HubSpot, Marketing, and Product staging are separate issues and are not inputs to this task.

DATA-006 lands DealHub in `raw_dealhub` as `quote`, `contract`, `subscription`, and `booking`. DATA-007-001 declares those tables through `source('dealhub', ...)`. The physical types already follow the source contracts: strings and enums are `VARCHAR`, decimals are `DECIMAL(18,2)`, `seat_count` is `BIGINT`, dates are `DATE`, and timestamps are `TIMESTAMP`.

The contracts in `contracts/source/dealhub/` are the staging contract. `docs/data-model/source-mapping.md` says DealHub owns quotes, contracts, subscriptions, and bookings, and does not create accounts, contacts, leads, or opportunities. Canonical surrogate keys, effective dating, survivorship, and ARR annualization belong to later warehouse work. `docs/data-model/metric-contract.md` annualizes `recurring_amount` by `billing_frequency` in a mart. This task stores those two inputs and does not apply that formula.

The supported development warehouses are `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Both use the same raw schema and table names. They are local artifacts and must not be committed.

## Scope

The implementation adds four staging models, their schema documentation and column tests, and DealHub reconciliation and integrity tests. It reads the DealHub source contracts and the existing `source('dealhub', ...)` declarations. It does not edit those declarations.

| Model | Source | History | Grain | Observation key |
|---|---|---|---|---|
| `stg_dealhub__quote` | `source('dealhub', 'quote')` | observation | One observation of one DealHub quote at one `observed_at`. | `dealhub_quote_id`, `observed_at` |
| `stg_dealhub__contract` | `source('dealhub', 'contract')` | observation | One observation of one DealHub contract at one `observed_at`. | `dealhub_contract_id`, `observed_at` |
| `stg_dealhub__subscription` | `source('dealhub', 'subscription')` | observation | One observation of one DealHub subscription at one `observed_at`. | `dealhub_subscription_id`, `observed_at` |
| `stg_dealhub__booking` | `source('dealhub', 'booking')` | immutable | One recognized booking. | `dealhub_booking_id` |

Each model selects only the contracted business fields and the ingestion envelope below, by name, from its own DealHub source. Column names stay the source names. The model does not join, filter, deduplicate, aggregate, or impute. A row that violates a test remains in the model so the test can fail.

`delivery_id` and `ingested_at` are retained for traceability. They are not part of the observation key. `ingested_at` may be later than `observed_at` or `booked_at`. Late delivery is valid.

### Columns

`quote`: `dealhub_quote_id`, `quote_number`, `status`, `quoted_amount`, `observed_at`, `hubspot_deal_id`, `hubspot_company_id`, `source_system`, `delivery_id`, `ingested_at`.

`contract`: `dealhub_contract_id`, `contract_number`, `status`, `total_contract_value`, `start_date`, `end_date`, `observed_at`, `dealhub_quote_id`, `hubspot_deal_id`, `hubspot_company_id`, `source_system`, `delivery_id`, `ingested_at`.

`subscription`: `dealhub_subscription_id`, `subscription_number`, `status`, `plan_code`, `seat_count`, `recurring_amount`, `billing_frequency`, `term_start`, `term_end`, `observed_at`, `emitted_event`, `dealhub_contract_id`, `hubspot_company_id`, `source_system`, `delivery_id`, `ingested_at`.

`booking`: `dealhub_booking_id`, `booking_number`, `booking_type`, `booking_amount`, `booked_at`, `hubspot_company_id`, `hubspot_deal_id`, `dealhub_contract_id`, `dealhub_subscription_id`, `source_system`, `delivery_id`, `ingested_at`.

Nullable columns are `quoted_amount` and `emitted_event`. Every other column is required. A required string is non-empty. A missing value stays null. The model does not turn an empty string into null.

### Commercial values

These observed values stay on their own models and stay distinct from one another:

| Column | Model | Meaning preserved |
|---|---|---|
| `quoted_amount` | `stg_dealhub__quote` | Proposal amount. Not bookings and not ARR. Null is allowed while `status` is `draft`. |
| `total_contract_value` | `stg_dealhub__contract` | Signed agreement value. Not ARR and not `booking_amount`. |
| `recurring_amount` | `stg_dealhub__subscription` | Recurring fee. Not an annualized amount. |
| `billing_frequency` | `stg_dealhub__subscription` | `monthly`, `quarterly`, or `annual`. Stored beside `recurring_amount` and not applied to it. |
| `booking_amount` | `stg_dealhub__booking` | Recognized booking amount. Not ARR and not the HubSpot deal amount. |
| `seat_count` | `stg_dealhub__subscription` | Commercial seats. Not a count of product users. |

`start_date` is the agreement start. It is not an opportunity close date. `observed_at` is the source observation time. It is not `effective_start`. `emitted_event` is the source signal. It is not a `lifecycle_event` row. DealHub identifiers are source identifiers. They are not canonical surrogate keys.

### Documentation

One schema YAML file in `warehouse/dbt/models/staging/dealhub/`, other than `_dealhub__sources.yml`, documents the four models. Use the project's `data_tests` key.

Each model description states the grain, the history class, the DealHub source it passes through, and that the row is a source observation rather than a canonical quote, contract, subscription, or booking. Column descriptions state the distinguishing meaning in the tables above. A description that only repeats the column name does not meet this requirement.

### Quality checks

Tests use the built-in dbt tests and the dbt_utils tests already installed by DATA-007-001. Do not add a package.

Shared checks, applied to every model:

- The observation key is unique and not null.
- Every non-nullable column is not null.
- Every required string is non-empty. Required strings are the identifier, document-number, relationship, `plan_code`, and `delivery_id` columns. Enums are covered by accepted values instead.
- `source_system` accepts only `dealhub`.
- Document numbers are stable and exclusive. For quote, contract, and subscription, one source identifier has one document number, and one document number belongs to one source identifier. `booking_number` is unique.

Enum values:

| Column | Accepted values |
|---|---|
| `stg_dealhub__quote.status` | `draft`, `sent`, `accepted`, `rejected`, `expired` |
| `stg_dealhub__contract.status` | `active`, `expired`, `terminated` |
| `stg_dealhub__subscription.status` | `pending`, `active`, `churned` |
| `stg_dealhub__subscription.billing_frequency` | `monthly`, `quarterly`, `annual` |
| `stg_dealhub__subscription.emitted_event` | `subscription_renewed`, `subscription_expanded`, `subscription_churned` |
| `stg_dealhub__booking.booking_type` | `new_business`, `expansion`, `renewal` |

`plan_code` stays an open string. Identifier shape is not a test. A DealHub prefix is an assumption, not a rejection rule.

Row-local commercial checks:

- `quoted_amount` is null or greater than or equal to zero. When `status` is not `draft`, `quoted_amount` is not null.
- `total_contract_value`, `recurring_amount`, and `booking_amount` are greater than or equal to zero.
- `seat_count` is greater than or equal to zero.
- `end_date` is greater than or equal to `start_date`.
- `term_end` is greater than or equal to `term_start`.

Subscription `status` and `emitted_event` stay paired as source validity. The test does not create an event from status.

| `status` | `emitted_event` |
|---|---|
| `pending` | null |
| `active` | null, `subscription_renewed`, or `subscription_expanded` |
| `churned` | `subscription_churned` |

Any other pair fails. `subscription_churned` occurs on at most one row per `dealhub_subscription_id`. Renewal and expansion may repeat.

DealHub-only relationship checks compare these staging models. They do not read HubSpot.

- Every `dealhub_quote_id` on a contract exists on `stg_dealhub__quote`.
- Every `dealhub_contract_id` on a subscription or a booking exists on `stg_dealhub__contract`.
- Every `dealhub_subscription_id` on a booking exists on `stg_dealhub__subscription`.
- Each `dealhub_quote_id` is cited by at most one distinct `dealhub_contract_id`. Repeated observations of that contract are one citation.
- Each `hubspot_deal_id` on `stg_dealhub__contract` is cited by at most one distinct `dealhub_contract_id`.
- One `dealhub_subscription_id` has one `dealhub_contract_id` across its observations.
- For a cited quote, contract, or subscription source identifier, the parent rows and the child rows that cite it share exactly one `hubspot_company_id`. The pairs are contract to quote, subscription to contract, booking to contract, and booking to subscription.

### Reconciliation

For each entity, an automated test compares `stg_dealhub__*` with `source('dealhub', ...)`.

The test fails when the staged row count differs from the landed row count, when the multiset of observation keys differs, or when the multiset of contracted column values differs. Nulls must match. Decimals must match the landed `DECIMAL(18,2)` values. Dates and timestamps must match without reformatting.

This specification approves no exception. Do not drop, rewrite, or quarantine a row. Do not add an exception model. A difference fails the test. That failure is the visible check the issue requires.

### Checks this task does not implement

These rules need HubSpot, or they need the source "observation in effect" lookup. They stay out of this task.

- A quote or contract company equals the HubSpot company on the cited deal.
- A contract exists only for the winning `new_business` / `closed_won` deal observation.
- The quote observation in effect when a contract is first observed is `accepted`.
- `booking_type` equals `opportunity_type` on the deal observation in effect at `booked_at`.
- No booking is recognized at or after `subscription_churned`.

Canonical identity resolution, `surviving_*` links, effective dating, lifecycle-event models, cross-source joins, annualized revenue, and business metrics are also out of scope.

## Deliverables

- `warehouse/dbt/models/staging/dealhub/stg_dealhub__quote.sql`
- `warehouse/dbt/models/staging/dealhub/stg_dealhub__contract.sql`
- `warehouse/dbt/models/staging/dealhub/stg_dealhub__subscription.sql`
- `warehouse/dbt/models/staging/dealhub/stg_dealhub__booking.sql`
- One schema YAML file in that directory, documenting the four models, their grain, and the checks in this specification.
- Singular tests under `warehouse/dbt/tests/dealhub/` for reconciliation, document-number stability, subscription event pairing, and the DealHub relationship rules that a column test cannot express.

Staging SQL references only its own `source('dealhub', '<entity>')`. It does not reference another source, another model, `raw_dealhub` by name, `effective_date`, or `generate_surrogate_key`. Tests under `warehouse/dbt/tests/dealhub/` may reference those four models and the four DealHub sources. They may not reference HubSpot, Marketing, Product, intermediate models, or marts.

Materialization stays the project default view. Do not set a custom schema. The isolated schema comes from `EVE_DBT_SCHEMA`.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/dealhub/` and do not edit it.
- Do not edit `_dealhub__sources.yml`, `dbt_project.yml`, `profiles.yml`, `packages.yml`, `package-lock.yml`, or `warehouse/dbt/README.md`.
- Do not edit HubSpot, Marketing, or Product staging paths. Those belong to DATA-008-001, DATA-008-003, and DATA-008-004.
- Do not add columns that are absent from the DealHub contracts, including canonical keys, `effective_start`, `effective_end`, `is_current`, `surviving_subscription_id`, annualized ARR, or a copied amount.
- Do not filter invalid rows out of the models. Tests fail while the rows remain.
- Do not treat identifier prefixes as rejection rules.
- Do not fail a row because `ingested_at` is later than the business timestamp.
- Use an isolated development schema whose name starts with `dev` and identifies this task, such as `dev_data_008_002`. Do not validate in the default `dev_dbt` schema.
- Keep DuckDB warehouse files, generated dbt artifacts, and local environment files untracked.
- No integration test, end-to-end test, deployment, or production warehouse change is required.

## Acceptance criteria

- [ ] The implementation changes only `warehouse/dbt/models/staging/dealhub/` and `warehouse/dbt/tests/dealhub/`, and it does not modify `_dealhub__sources.yml`.
- [ ] `stg_dealhub__quote`, `stg_dealhub__contract`, `stg_dealhub__subscription`, and `stg_dealhub__booking` exist, each built from its own `source('dealhub', ...)` relation, at the grain and observation key in this specification.
- [ ] Each model contains every contracted column listed above and no additional column. Names match the source contracts. `quoted_amount`, `total_contract_value`, `recurring_amount`, `billing_frequency`, `booking_amount`, and `seat_count` are present and unchanged.
- [ ] The models contain no join, no canonical key, no effective-dating columns, no derived lifecycle event, no annualized amount, and no business metric.
- [ ] Schema documentation states grain, history, and the meaning that keeps the commercial amounts distinct. Required columns have not-null tests. Observation keys have uniqueness tests. Enums have accepted-value tests. Required strings have non-empty tests.
- [ ] Automated checks fail for a broken observation key, a value outside an approved enum, a negative amount, a reversed contract or subscription term, a negative seat count, a non-draft quote with a null `quoted_amount`, an invalid `status` and `emitted_event` pair, a second `subscription_churned` for one subscription, an unstable or shared document number, a missing DealHub parent identifier, more than one contract for one quote or one `hubspot_deal_id`, an unstable subscription contract, or disagreeing `hubspot_company_id` values inside the DealHub pairs named above.
- [ ] Reconciliation tests fail when a staged row, a landed row, or a contracted value does not match. No exception set is introduced.
- [ ] A downstream model can select every contracted DealHub column from these four models with `ref`. It does not need `source('dealhub', ...)` or `raw_dealhub`.
- [ ] The checks that need HubSpot or an in-effect observation are not implemented.
- [ ] From `warehouse/dbt/`, with `EVE_DBT_SCHEMA` set to the isolated `dev`-prefixed schema, `dbt build` of the DealHub staging models and `tests/dealhub` exits zero against `data/warehouse/dev_data_003` and against `data/warehouse/dev_data_004`.
- [ ] `dbt show` can return a limited sample of each staging model from the baseline warehouse.
- [ ] No file under `data/warehouse/` is committed. `contracts/`, `docs/`, and the other excluded paths are unchanged.

## Execution notes

Implement this specification only after it has merged and issue #30 is `status:ready`. Use an `impl` worktree and the isolated schema. Do not merge or deploy without human approval.

Before writing SQL, read the four DealHub contract files and `warehouse/dbt/models/staging/dealhub/_dealhub__sources.yml`. Use `dbt show --limit` on each DealHub source, then on each staging model, against `data/warehouse/dev_data_003`. Confirm the contracted columns and a sample of null `quoted_amount` and null `emitted_event` values before treating the model as done.

Run `dbt deps` from `warehouse/dbt/` when `dbt_packages` is absent. Do not change package files.

If a warehouse file is absent, create it through the merged DATA-006 generate and load path. Never commit it.

Validate from `warehouse/dbt/` with `--profiles-dir .`. Select only this task's models and tests. One target schema covers both warehouse files, selected one at a time with `EVE_DBT_DUCKDB_PATH`.

```bash
export EVE_DBT_SCHEMA=dev_data_008_002
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_003
dbt build --profiles-dir . --select path:models/staging/dealhub path:tests/dealhub
dbt show --profiles-dir . --select stg_dealhub__quote --limit 5
dbt show --profiles-dir . --select stg_dealhub__contract --limit 5
dbt show --profiles-dir . --select stg_dealhub__subscription --limit 5
dbt show --profiles-dir . --select stg_dealhub__booking --limit 5
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_004
dbt build --profiles-dir . --select path:models/staging/dealhub path:tests/dealhub
```

`path:models/staging/dealhub` also parses the existing source YAML. That file stays unchanged. The build does not need to rebuild `date_spine` or any other model.
