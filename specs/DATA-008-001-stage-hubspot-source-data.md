---
id: DATA-008-001
title: Stage HubSpot source data
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
  - warehouse/dbt/models/staging/hubspot/data_008_001/
  - warehouse/dbt/tests/data_008_001/
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
  - warehouse/dbt/dbt_project.yml
  - warehouse/dbt/profiles.yml
  - warehouse/dbt/packages.yml
  - warehouse/dbt/package-lock.yml
  - warehouse/dbt/README.md
  - warehouse/dbt/macros/
  - warehouse/dbt/models/utilities/
  - warehouse/dbt/models/intermediate/
  - warehouse/dbt/models/marts/
  - warehouse/dbt/models/staging/hubspot/_hubspot__sources.yml
  - warehouse/dbt/models/staging/dealhub/
  - warehouse/dbt/models/staging/marketing/
  - warehouse/dbt/models/staging/product/
  - warehouse/dbt/tests/test_generate_surrogate_key.sql
  - warehouse/dbt/tests/test_effective_date.sql
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

Provide a trusted dbt staging interface for every contracted HubSpot entity so later warehouse models can consume HubSpot through `ref()` and can leave `raw_hubspot` unread.

The interface preserves source grain, source identifiers, and source values. It documents that interface and enforces it with automated checks, including an exact reconciliation to the landed HubSpot tables.

## Business context

GitHub issue #28 (`DATA-008-001 — Stage HubSpot source data`) is a child of epic #27 (`DATA-008 — Stage GTM Source Data`). It depends on DATA-007-001. The dbt project already declares `source('hubspot', ...)` over the tables DATA-006 loaded into schema `raw_hubspot`.

HubSpot owns the CRM record of firms, people, inquiries, deals, and sales activities. Downstream identity resolution, conformed dimensions, lifecycle events, and GTM metrics need those records staged as observations, with the source meaning still visible.

The supported development datasets are the baseline warehouse `data/warehouse/dev_data_003` and the scenario warehouse `data/warehouse/dev_data_004`. Both files use schema `raw_hubspot` and the same HubSpot tables. They are local artifacts and stay untracked.

Sibling issues own the other source systems:

| Issue | Owns |
|---|---|
| DATA-008-002 | DealHub staging |
| DATA-008-003 | Marketing staging |
| DATA-008-004 | Product staging |

This task does not wait for those issues and does not edit their files.

## Scope

The implementation adds five view models, their schema documentation, and the checks below. It reads the merged HubSpot contracts and the landed tables. It does not change either.

| Model | Source | History | Grain | Unique key |
|---|---|---|---|---|
| `stg_hubspot__company` | `source('hubspot', 'company')` | observation | One landed observation of one HubSpot company | `hubspot_company_id`, `observed_at` |
| `stg_hubspot__contact` | `source('hubspot', 'contact')` | observation | One landed observation of one HubSpot contact | `hubspot_contact_id`, `observed_at` |
| `stg_hubspot__lead` | `source('hubspot', 'lead')` | observation | One landed observation of one HubSpot lead | `hubspot_lead_id`, `observed_at` |
| `stg_hubspot__deal` | `source('hubspot', 'deal')` | observation | One landed observation of one HubSpot deal | `hubspot_deal_id`, `observed_at` |
| `stg_hubspot__activity` | `source('hubspot', 'activity')` | immutable | One landed HubSpot activity | `hubspot_activity_id` |

A repeated source identifier on an observation model is a later observation when `observed_at` differs. It is not a duplicate row to collapse. Activity has no `observed_at`. One `hubspot_activity_id` is one activity.

Each model selects from that one source table. The model SQL does not join another entity, another source system, or another staging model. Rules that compare two HubSpot entities are tests.

The files live in the issue-owned directory `warehouse/dbt/models/staging/hubspot/data_008_001/`. Singular tests, when a schema test cannot express a rule, live only in `warehouse/dbt/tests/data_008_001/`. Shared project files and `_hubspot__sources.yml` stay as DATA-007-001 left them.

## Deliverables

### Staged interface

Create these model files:

- `warehouse/dbt/models/staging/hubspot/data_008_001/stg_hubspot__company.sql`
- `warehouse/dbt/models/staging/hubspot/data_008_001/stg_hubspot__contact.sql`
- `warehouse/dbt/models/staging/hubspot/data_008_001/stg_hubspot__lead.sql`
- `warehouse/dbt/models/staging/hubspot/data_008_001/stg_hubspot__deal.sql`
- `warehouse/dbt/models/staging/hubspot/data_008_001/stg_hubspot__activity.sql`

Each model is a view under the project default materialization. The model SQL uses `source('hubspot', '<entity>')` and does not hardcode `raw_hubspot` or a warehouse path.

The staged column set is exactly the contract `fields` plus the ingestion fields `source_system`, `delivery_id`, and `ingested_at`. Names stay the contract names. Column order may differ from the contract file. Types stay the landed types: text for `string` and `enum`, `DECIMAL(18,2)` for `decimal`, `DATE` for `date`, and `TIMESTAMP` for `timestamp`.

`stg_hubspot__company` columns: `hubspot_company_id`, `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, `hubspot_lifecycle_stage`, `observed_at`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__contact` columns: `hubspot_contact_id`, `full_name`, `email_normalized`, `title`, `buying_role`, `observed_at`, `hubspot_company_id`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__lead` columns: `hubspot_lead_id`, `status`, `created_at`, `observed_at`, `emitted_event`, `hubspot_company_id`, `hubspot_contact_id`, `marketing_campaign_id`, `hubspot_deal_id`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__deal` columns: `hubspot_deal_id`, `opportunity_name`, `opportunity_type`, `stage`, `amount`, `expected_close_date`, `owner_name`, `forecast_category`, `created_at`, `observed_at`, `emitted_event`, `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, `dealhub_subscription_id`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__activity` columns: `hubspot_activity_id`, `activity_type`, `subject`, `occurred_at`, `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, `hubspot_deal_id`, `source_system`, `delivery_id`, `ingested_at`.

Values pass through. A null stays null. An empty string is not substituted for null, and null is not substituted for an empty string. `amount` null stays null and is not stored as zero. Source identifiers stay the landed strings. HubSpot identifiers are expected to be numeric strings in the generator; that shape is not a staging rejection rule.

`marketing_campaign_id` and `dealhub_subscription_id` stay on the HubSpot row as opaque source identifiers. This task does not look up the campaign or the subscription.

The supported development drops contain one row per observation key. The staging models keep every landed row. They do not deduplicate, filter, or choose a survivor. If a landed table ever contains two rows with the same unique key, both rows remain in the model, and both the uniqueness check and the reconciliation check fail. That failure is the visible violation.

### Documentation

Add schema YAML beside the models. Document every model and every column.

Each model description states the grain, the history kind, the source table, and that downstream models `ref()` this relation instead of reading `raw_hubspot`.

Column descriptions state the source meaning a later model needs. These columns need an explicit distinction:

- `hubspot_lifecycle_stage` is the HubSpot label stored for reconciliation. It is not canonical `commercial_status`.
- `amount` is the HubSpot-entered deal amount. It is not bookings and not ARR. Null means unreported.
- `emitted_event` is the source signal stored on the observation. It is not a `lifecycle_event` row, and this task does not emit `customer_converted`.
- `marketing_campaign_id` and `dealhub_subscription_id` are unresolved identifiers from other source systems.
- `primary_domain` and `email_normalized` may repeat across source identifiers. Staging does not pick a survivor.
- `source_system`, `delivery_id`, and `ingested_at` are delivery metadata. They are not business attributes and they are not part of the observation key. Late `ingested_at` is valid.

Descriptions that only repeat the column name do not satisfy this section.

### Reconciliation

For each entity, an automated check compares the staged model with `source('hubspot', '<entity>')`.

The check fails when any of these differ:

- row count
- the unique key set named in the grain table
- the staged column set
- any contracted column value, including nulls, decimals at two fraction digits, dates, and timestamps

The approved exception set is empty. The check has no waiver list, tolerance, or quarantine that removes a difference from the staging model. A failed check is the visible exception. A later specification may approve an exception only by naming the waived difference and adding a tested output that lists it.

### Data-quality checks

Automated checks fail when a staged row violates the rules in this section. The development datasets are expected to satisfy them. A failing dataset stays failing: the implementation does not drop the row, rewrite the value, or edit `contracts/` to obtain a green test.

These checks constrain the preserved source columns. They do not build a lifecycle-event model, a current-row extract, or an effective-dated dimension.

Nullability follows the `nullable` flag in the HubSpot contract for that column. A required string is present and non-empty. An optional string is either null or non-empty. Required timestamps, dates, and enums are present. Optional enums accept null or one listed value.

Shared checks, applied to every model:

- `source_system` equals `hubspot`.
- `delivery_id` is present and non-empty.
- `ingested_at` is present. A value later than `observed_at` or `occurred_at` is valid.
- The unique key in the grain table is unique and not null.
- The source identifier is present and non-empty. A repeated source identifier on an observation model is valid.

Company:

- `segment`, when present, is `solo`, `small`, `mid`, or `large`.
- `icp_fit`, when present, is `in_icp` or `out_of_icp`.
- `hubspot_lifecycle_stage` has no closed vocabulary check.
- `primary_domain`, when present, equals its lowercase trimmed form and contains neither a scheme nor a path.
- `primary_domain` and `firm_name` have no uniqueness check.

Contact:

- `buying_role`, when present, is `champion`, `decision_maker`, `user`, or `billing`.
- `email_normalized`, when present, equals its lowercase trimmed form.
- `email_normalized` has no uniqueness check.
- A present `hubspot_company_id` equals a `hubspot_company_id` on `stg_hubspot__company`.

Lead:

- `status` is `new`, `working`, `qualified`, `disqualified`, or `converted`.
- `emitted_event`, when present, is `lead_created`, `lead_qualified`, `lead_disqualified`, or `lead_converted`.
- `created_at` is present and is the same value on every observation of one `hubspot_lead_id`.
- `observed_at` is at or after `created_at`.
- Each lead has one `lead_created` observation. That row has `status` `new` and `observed_at` equal to `created_at`.
- `qualified`, `disqualified`, and `converted` each occur on at most one observation of a lead, and the row's `emitted_event` is `lead_qualified`, `lead_disqualified`, or `lead_converted` respectively.
- `working` has `emitted_event` null.
- One lead does not have both `qualified` and `disqualified`.
- A `lead_converted` observation has `observed_at` at or after that lead's `lead_qualified` observation.
- `hubspot_deal_id` is present only on the `lead_converted` observation, and that value equals a `hubspot_deal_id` on `stg_hubspot__deal`. Every other lead observation has `hubspot_deal_id` null.
- A present `hubspot_company_id` equals a company identifier on `stg_hubspot__company`. A present `hubspot_contact_id` equals a contact identifier on `stg_hubspot__contact`.
- `marketing_campaign_id` is not tested against Marketing.

Deal:

- `opportunity_type` is `new_business`, `expansion`, or `renewal`.
- `stage` is `discovery`, `evaluation`, `proposal`, `negotiation`, `closed_won`, or `closed_lost`.
- `forecast_category`, when present, is `pipeline`, `best_case`, `commit`, `closed`, or `omitted`.
- `emitted_event`, when present, is `opportunity_opened`, `opportunity_stage_changed`, `opportunity_won`, or `opportunity_lost`.
- `amount`, when present, is greater than or equal to zero. A null `amount` remains null.
- `created_at` and `hubspot_company_id` are each the same value on every observation of one deal.
- Every non-null `hubspot_lead_id` on one deal is the same value.
- `observed_at` is at or after `created_at`.
- Each deal has one `opportunity_opened` observation. That row has `stage` `discovery` and `observed_at` equal to `created_at`.
- When `stage` changes to `evaluation`, `proposal`, or `negotiation`, `emitted_event` is `opportunity_stage_changed`.
- When `stage` changes to `closed_won`, `emitted_event` is `opportunity_won`. When `stage` changes to `closed_lost`, `emitted_event` is `opportunity_lost`. Each of those two signals occurs at most once per deal, and a deal does not carry both.
- An observation whose `stage` equals the prior observation of the same deal has `emitted_event` null. The prior observation is the row with the greatest `observed_at` still earlier than this row.
- On a `new_business` observation, `dealhub_subscription_id` is null. On an `expansion` or `renewal` observation, `dealhub_subscription_id` is present and non-empty. Existence of that subscription is not tested.
- `hubspot_company_id` equals a company identifier on `stg_hubspot__company`.
- A present `hubspot_contact_id` equals a contact identifier on `stg_hubspot__contact`. A present `hubspot_lead_id` equals a lead identifier on `stg_hubspot__lead`.
- Among distinct `hubspot_deal_id` values, a non-null `hubspot_lead_id` belongs to one deal.
- When `hubspot_contact_id` is present, the contact observation in effect at the deal's `observed_at` has the same `hubspot_company_id` as the deal.

Activity:

- `activity_type` is `call`, `email`, or `meeting`.
- `occurred_at` is present.
- At least one of `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_deal_id` is present.
- A present parent identifier equals that identifier on the corresponding HubSpot staging model.
- When `hubspot_company_id` is present and another parent has a company on the observation in effect at `occurred_at`, the company identifiers are equal. A deal has a company. A contact or a lead constrains the activity only when that in-effect observation has `hubspot_company_id`. A parent with no company does not constrain the activity.

The observation in effect at a timestamp is the row for that source identifier whose `observed_at` is the latest at or before the timestamp. When no such row exists, a rule that requires an in-effect observation fails.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/hubspot/` and leave it unchanged.
- Leave `dbt_project.yml`, `profiles.yml`, `packages.yml`, `package-lock.yml`, `warehouse/dbt/README.md`, `macros/`, the four source YAML files, and the date spine unchanged.
- Leave DealHub, Marketing, and Product models and sources unchanged.
- Use an isolated schema whose name is `dev_data_008_001`, set with `EVE_DBT_SCHEMA`. The default schema `dev_dbt` is the foundation schema and is not the validation target.
- Keep warehouse files, dbt artifacts, and local environment files untracked.
- Add no dbt package. `dbt_utils` is already available for tests.
- Preserve the grains and keys in the scope table. Add no `effective_start`, `effective_end`, `is_current`, canonical surrogate, or `surviving_*` column.
- Add no cross-source join and no `source()` call other than `source('hubspot', ...)`.
- Add no intermediate model, mart, metric, semantic definition, or lifecycle-event model.
- `testing.integration_tests` is false because `components` lists only `dbt`.

## Acceptance criteria

- [ ] The implementation changes only `warehouse/dbt/models/staging/hubspot/data_008_001/` and, if a singular test is required, `warehouse/dbt/tests/data_008_001/`.
- [ ] `stg_hubspot__company`, `stg_hubspot__contact`, `stg_hubspot__lead`, `stg_hubspot__deal`, and `stg_hubspot__activity` exist, each selecting one `source('hubspot', ...)` table and exposing exactly the contracted columns for that entity.
- [ ] Each model is a view. Observation models keep one row per landed observation, and `stg_hubspot__activity` keeps one row per landed activity. Source values, nulls, and `amount` pass through unchanged.
- [ ] Schema YAML documents every model grain and the column distinctions named under Documentation.
- [ ] Reconciliation checks fail when the staged row count, unique keys, column set, or column values differ from the landed HubSpot source. The exception set is empty.
- [ ] The data-quality checks in this specification fail for a violating row, including required fields, accepted values, within-HubSpot identifier existence, and the lead, deal, and activity rules listed above.
- [ ] `marketing_campaign_id` and `dealhub_subscription_id` remain columns, and no test or model reads DealHub, Marketing, or Product.
- [ ] The models contain no canonical identity, effective dating, lifecycle-event entity, cross-source join, or business metric.
- [ ] From `warehouse/dbt/`, with `EVE_DBT_SCHEMA=dev_data_008_001`, `dbt parse` succeeds and `dbt build --select stg_hubspot__company stg_hubspot__contact stg_hubspot__lead stg_hubspot__deal stg_hubspot__activity` succeeds against `data/warehouse/dev_data_003` and against `data/warehouse/dev_data_004`.
- [ ] `dbt show` returns rows for each staged model from the baseline warehouse.
- [ ] No file under `data/warehouse/` is committed. `contracts/`, `data-generation/`, `docs/`, and the shared dbt files named under Constraints are unchanged.

## Execution notes

Implement this specification only after it has merged and issue #28 is `status:ready`. Use an `impl` worktree and schema `dev_data_008_001`. Do not merge or deploy without human approval.

Before writing SQL, read the five HubSpot contract files and inspect the landed baseline tables with `dbt show --limit 5`. Confirm column names and values from that output. Use `source()` and `ref()` rather than hardcoded relation names.

The model SQL for each entity is a projection of one source table. Put multi-entity rules in tests. Schema tests live with the models. A singular test belongs under `warehouse/dbt/tests/data_008_001/` only when a schema test cannot express the rule.

Validation runs from `warehouse/dbt/` against each warehouse file:

```bash
export EVE_DBT_SCHEMA=dev_data_008_001
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_003
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select stg_hubspot__company stg_hubspot__contact stg_hubspot__lead stg_hubspot__deal stg_hubspot__activity
.venv/bin/dbt show --profiles-dir . --select stg_hubspot__company --limit 5
```

Repeat the build and a limited `dbt show` with `EVE_DBT_DUCKDB_PATH` pointed at `data/warehouse/dev_data_004`. If a warehouse file is absent, create it through the merged DATA-006 generate and load path, and do not commit it.

A red check on a listed rule is a stop. Do not make the check pass by dropping rows or by changing a contract.
