---
id: DATA-010-001
title: Build core customer dimensions
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
  - DATA-009-001
  - DATA-007-002
requires_approval: true
allowed_paths:
  - warehouse/dbt/models/marts/
  - warehouse/dbt/tests/marts/
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
  - warehouse/dbt/models/staging/
  - warehouse/dbt/models/intermediate/
  - warehouse/dbt/tests/staging/
  - warehouse/dbt/tests/intermediate/
  - warehouse/dbt/tests/test_effective_date.sql
  - warehouse/dbt/tests/test_generate_surrogate_key.sql
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

Provide one governed account dimension and one governed contact dimension that later GTM marts can `ref()` when they need a law firm or a sales contact.

The customer is the account. `account_id` is the customer identifier. The same conformed firm is the same account, and the same conformed person is the same contact. Current and historical rows stay the conformed rows. A contact stays on the firm the conformed contact already stores, including a duplicate firm. Later facts join these dimensions and do not join a source system to obtain firm or contact attributes.

## Business context

GitHub issue #63 (`DATA-010-001 — Build core customer dimensions`) is a child of epic #61 (`DATA-010 — Build Dimensional GTM Marts`). It depends on DATA-009-001 and DATA-007-002, which are merged.

DATA-009-001 publishes `int_account` and `int_contact`. Those models already resolve HubSpot companies, Product firms, and HubSpot contacts, and they already keep effective-dated history. This task publishes that conformed account and that conformed contact as the dimensions domain facts join. It does not resolve identities again.

The approved entities, history, and identity rules are in `docs/data-model/entities.md`, `docs/data-model/decisions.md`, and `docs/data-model/source-mapping.md`. The metric and mart contract is in `docs/data-model/metric-contract.md`. This task uses those documents. It does not edit them and does not reopen them.

An account is one plaintiff law firm. A contact is one person known to sales. A product login is a different entity and is out of scope. A lead is not an account. There is no customer entity and no `dim_customer`.

`commercial_status` is a canonical account attribute. `int_account` does not carry it. Deriving it needs the account's first win and subscription status. DATA-009-002 records `customer_converted` and still does not derive `commercial_status`. DATA-009-003 owns subscription status. This task does not depend on either issue, does not read those models, and does not add `commercial_status`. `hubspot_lifecycle_stage` stays the HubSpot label copied from `int_account`. It is not rewritten into `prospect`, `customer`, or `former_customer`.

Conformed inputs:

| Model | Grain | What this task uses |
|---|---|---|
| `int_account` | One effective-dated version of one surviving firm, or one row for a duplicate firm | Every column, copied |
| `int_contact` | One effective-dated version of one surviving contact, or one row for a duplicate contact | Every column, copied |

Staging models, raw schemas, leads, opportunities, lifecycle events, quotes, contracts, subscriptions, bookings, campaigns, touches, activities, and product usage are not inputs. Apollo and Clay are not inputs.

The development warehouses are `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Both are local artifacts and stay untracked. `dev_data_004` includes the domain twin and two contacts that share one email. `dev_data_003` includes companies with a blank web address and contacts that share an email. The tests compare the dimensions to `int_account` and `int_contact` and check the history and survivor rules below, so both warehouses exercise them. The tests do not hardcode a source identifier from either warehouse.

Sibling issues own the domain marts. They consume these dimensions. This task does not build them.

| Issue | Owns |
|---|---|
| DATA-010-002 | Marketing facts and dimensions |
| DATA-010-003 | Sales and revenue facts and dimensions |
| DATA-010-004 | Product adoption facts and dimensions |
| DATA-010-005 | Retention and customer lifecycle facts |

## Scope

The implementation adds two mart models, their YAML, and the singular tests below. `components` lists only `dbt`, so `testing.integration_tests` is false.

The models live in the marts layer already configured in `dbt_project.yml`. One SQL file and one YAML file of the same basename sit directly in `warehouse/dbt/models/marts/`. There is no ticket directory and no shared `schema.yml`.

| Model | Business grain | Row grain | Row key |
|---|---|---|---|
| `dim_account` | One law firm, which is the customer | One effective-dated version of one surviving firm, or one row for a duplicate firm | `account_version_id` |
| `dim_contact` | One sales contact | One effective-dated version of one surviving contact, or one row for a duplicate contact | `contact_version_id` |

`account_id` is the firm and the customer identifier. It repeats on every version of that firm. `contact_id` is the person. It repeats on every version of that person. The row key is unique on the model. The business identifier is not.

There is no second model for the current row and no second model for history. The current analytical view is the row whose `is_current` is true. The historical analytical view is the row in effect at a time: `effective_start` is inclusive and `effective_end` is exclusive, and the open row has a null `effective_end`. Both views are these two models.

`dbt_project.yml` materializes the marts folder as a table. The model YAML does not set `materialized`. The SQL does not set a config. The models are not incremental. Each run rebuilds every row from the conformed model. Do not edit `dbt_project.yml`.

SQL uses one CTE and `ref()`. `dim_account` reads only `int_account`. `dim_contact` reads only `int_contact`. The models do not call `source()`, do not read a raw schema, and do not `ref()` a staging model, `int_lead`, `int_opportunity`, or `int_lifecycle_event`. They do not call `dbt_utils.generate_surrogate_key` or `effective_date`. Keys and version bounds are copied. They are not regenerated.

`dim_account`:

```sql
with conformed as (

    select
        account_version_id,
        account_id,
        surviving_account_id,
        hubspot_company_id,
        product_firm_id,
        firm_name,
        primary_domain,
        state,
        segment,
        practice_focus,
        icp_fit,
        owner_name,
        hubspot_lifecycle_stage,
        is_current,
        effective_start,
        effective_end
    from {{ ref('int_account') }}

)

select * from conformed
```

`dim_contact`:

```sql
with conformed as (

    select
        contact_version_id,
        contact_id,
        account_id,
        surviving_contact_id,
        hubspot_contact_id,
        full_name,
        email_normalized,
        title,
        buying_role,
        is_current,
        effective_start,
        effective_end
    from {{ ref('int_contact') }}

)

select * from conformed
```

The select list is the full output. There is no filter, join, aggregation, rename, or calculation. A null stays null. An empty string stays an empty string. A duplicate row stays. A closed version stays. The models do not keep only surviving rows and do not keep only current rows.

### Columns

The lists in the SQL are the output columns, in that order. The YAML column order matches. No other column is selected.

Stored enums stay the conformed codes. Descriptions use the ordinary words in the description section.

| Column | Stored values when present |
|---|---|
| `segment` | `solo`, `small`, `mid`, `large` |
| `icp_fit` | `in_icp`, `out_of_icp` |
| `buying_role` | `champion`, `decision_maker`, `user`, `billing` |

### Keys and relationships

`account_version_id`, `account_id`, `surviving_account_id`, `hubspot_company_id`, and `product_firm_id` are the values on the matching `int_account` row. `contact_version_id`, `contact_id`, `account_id`, `surviving_contact_id`, and `hubspot_contact_id` are the values on the matching `int_contact` row.

`surviving_account_id` is null on a survivor. When it is present, it is the earlier firm's `account_id`, that firm has a null `surviving_account_id`, and the link does not point at the row itself. The same `surviving_account_id` is on every row of that `account_id`. There is no chain.

`surviving_contact_id` follows the same one-hop rule on `contact_id`.

`dim_contact.account_id` is the conformed contact's `account_id`. A null stays null. A duplicate firm stays the contact's firm. The dimension does not replace it with `surviving_account_id`. A metric that counts surviving firms follows that link when it reads the dimension. This task does not perform that hop.

`primary_domain` is unique among open surviving accounts when it is present. A duplicate may keep the same domain. `email_normalized` is unique among open surviving contacts when it is present. A duplicate may keep the same email.

### History

`effective_start` is inclusive. `effective_end` is exclusive and null on the open row. `is_current` is true exactly when `effective_end` is null. Each `account_id` has one open row. Each `contact_id` has one open row.

Versions of one `account_id`, ordered by `effective_start`, do not overlap and do not leave a gap. The next `effective_start` equals the previous `effective_end`. When `effective_end` is not null, `effective_start` is earlier than `effective_end`. Versions of one `contact_id` follow the same rule.

These bounds are the conformed bounds. This task does not open, close, or collapse a version.

### What stays conformed

Every `account_version_id` in `int_account` appears on exactly one `dim_account` row, and every `dim_account` row has an `account_version_id` from `int_account`. Every `contact_version_id` in `int_contact` appears on exactly one `dim_contact` row, and every `dim_contact` row has a `contact_version_id` from `int_contact`. The dimension row counts equal the conformed row counts.

For each matched account version, `account_id`, `surviving_account_id`, `hubspot_company_id`, `product_firm_id`, `is_current`, `effective_start`, and `effective_end` equal the conformed row. For each matched contact version, `contact_id`, `account_id`, `surviving_contact_id`, `hubspot_contact_id`, `is_current`, `effective_start`, and `effective_end` equal the conformed row.

Descriptive columns are selected by name from the conformed model. The singular tests do not compare `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, `hubspot_lifecycle_stage`, `full_name`, `email_normalized`, `title`, or `buying_role` to the conformed model. A pass-through model does not get a singular test that compares every column to its upstream model.

### How later facts use the dimensions

A later fact `ref()`s `dim_account` or `dim_contact`. It joins `account_id` or `account_version_id`, and `contact_id` or `contact_version_id`. The current firm or person is the row with `is_current` true. The firm or person in effect at a time is the row whose `effective_start` is at or before that time and whose `effective_end` is null or after that time.

Firm name, web address, segment, owner, contact name, email, title, and buying role come from these dimensions. Source identifiers on the dimensions are the trace back to HubSpot and Product. A later fact does not join `stg_hubspot__company`, `stg_hubspot__contact`, `stg_product__firm`, or a raw schema to obtain them. This task does not build those facts.

Metric resolution stays the one-hop rule in `metric-contract.md`. These models do not apply it, and they do not store a resolved customer key beside `account_id`.

## Deliverables

- `warehouse/dbt/models/marts/dim_account.sql`
- `warehouse/dbt/models/marts/dim_account.yml`
- `warehouse/dbt/models/marts/dim_contact.sql`
- `warehouse/dbt/models/marts/dim_contact.yml`
- Singular tests under `warehouse/dbt/tests/marts/`, named below

`models/marts/.gitkeep` may stay. These files are the complete addition.

### Documentation

YAML descriptions follow the Documentation section of `dbt-development`. A model description is the three sentences below and no others. A column description is the one sentence below and no others. Descriptions leave out grain, keys, history class, canonical identity, `source()` and `ref()` mechanics, reconciliation, and the phrase "not on this model." They do not restate `not_null`, `unique`, or a test.

`dim_account`:

One law firm as it stood from one change to the next. A duplicate firm stays on a single row and points at the earlier firm. Commercial status, deal amount, contract value, and booking amount live on later models.

`dim_contact`:

One sales contact as that person stood from one change to the next. A shared email points the later person at the earlier person, and a move to another firm starts another row. Deal amount and product logins live on later models.

| Column | Description |
|---|---|
| `account_version_id` | The span of time this row keeps for the firm. |
| `account_id` | The firm this row belongs to. |
| `surviving_account_id` | The earlier firm, when this firm is a duplicate. |
| `hubspot_company_id` | HubSpot's id for this firm. |
| `product_firm_id` | Product's id for this firm. |
| `firm_name` | The firm's display name, from HubSpot when a HubSpot company is on the firm and from Product when only Product knows the firm. |
| `primary_domain` | The firm's web address, which a duplicate firm may still share with the earlier firm. |
| `state` | The firm's principal US state. |
| `segment` | Firm-size band: solo, small, mid, or large. |
| `practice_focus` | The firm's principal plaintiff practice, in the source's own wording. |
| `icp_fit` | Whether the firm is in the ideal customer profile, or outside it. |
| `owner_name` | The sales owner of the firm relationship, which may match or differ from a deal owner. |
| `hubspot_lifecycle_stage` | HubSpot's own lifecycle label for the firm, and those words are not limited to prospect, customer, or former customer. |
| `is_current` | Whether this row is the firm's open span. |
| `effective_start` | When this span began, and this moment is included. |
| `effective_end` | When this span ended, and this moment is not included; the open span has no end. |
| `contact_version_id` | The span of time this row keeps for the person. |
| `contact_id` | The person this row belongs to. |
| `account_id` | The firm this person belonged to during this span. |
| `surviving_contact_id` | The earlier person, when this person is a duplicate. |
| `hubspot_contact_id` | HubSpot's id for this person. |
| `full_name` | The person's name as sales knows it. |
| `email_normalized` | The person's email in lowercase, which another HubSpot contact may share. |
| `title` | The person's role title at the firm. |
| `buying_role` | The person's part in a purchase: champion, decision maker, user, or billing. |

On `dim_account`, `account_id` uses the firm sentence. On `dim_contact`, `account_id` uses the person sentence. The contact model's `is_current`, `effective_start`, and `effective_end` use the same sentences as the account, with "person" in place of "firm" on `is_current`.

### Tests in the model YAML

Tests use the `data_tests` and `arguments` shape already used by `int_account.yml` and `int_contact.yml`. The generic tests are `unique`, `not_null`, `accepted_values`, and `relationships`.

`dim_account`:

- `account_version_id`: `unique`, `not_null`
- `account_id`: `not_null`
- `surviving_account_id`: `relationships` to `ref('dim_account')`, field `account_id`
- `firm_name`: `not_null`
- `segment`: `accepted_values` of `solo`, `small`, `mid`, `large`
- `icp_fit`: `accepted_values` of `in_icp`, `out_of_icp`
- `is_current`: `not_null`
- `effective_start`: `not_null`

`dim_contact`:

- `contact_version_id`: `unique`, `not_null`
- `contact_id`: `not_null`
- `account_id`: `relationships` to `ref('dim_account')`, field `account_id`
- `surviving_contact_id`: `relationships` to `ref('dim_contact')`, field `contact_id`
- `hubspot_contact_id`: `not_null`
- `buying_role`: `accepted_values` of `champion`, `decision_maker`, `user`, `billing`
- `is_current`: `not_null`
- `effective_start`: `not_null`

`unique` is not applied to `account_id`, `contact_id`, `hubspot_company_id`, `product_firm_id`, `hubspot_contact_id`, `primary_domain`, or `email_normalized`. Those values repeat across versions or are shared by a duplicate. `accepted_values` lists the stored codes. A null enum stays null and is not added to the value list.

### Singular tests

Each file is under `warehouse/dbt/tests/marts/`. The leading comment states the rule and that `unique`, `not_null`, `accepted_values`, and `relationships` cannot express it. The query returns the violating rows and returns no rows when the rule holds. The tests read `dim_account`, `dim_contact`, `int_account`, and `int_contact` only. They do not read a staging model and do not re-walk source identity. They do not hardcode a source identifier from either warehouse.

| File | Rule |
|---|---|
| `dim_account_history.sql` | On `dim_account`, `is_current` is true exactly when `effective_end` is null. Each `account_id` has one open row. Versions of one `account_id` ordered by `effective_start` do not overlap, the next `effective_start` equals the previous `effective_end`, and a closed row has `effective_start` earlier than `effective_end`. |
| `dim_account_reconciles.sql` | The set of `account_version_id` equals `int_account`. Row counts are equal. For each version, `account_id`, `surviving_account_id`, `hubspot_company_id`, `product_firm_id`, `is_current`, `effective_start`, and `effective_end` equal the conformed row. Descriptive columns are not compared. |
| `dim_account_survivor_link.sql` | One hop, no self link, the same `surviving_account_id` on every row of an `account_id`, and `primary_domain` unique among open surviving rows when present. |
| `dim_contact_history.sql` | The account history rules, applied to `dim_contact` and `contact_id`. |
| `dim_contact_reconciles.sql` | The set of `contact_version_id` equals `int_contact`. Row counts are equal. For each version, `contact_id`, `account_id`, `surviving_contact_id`, `hubspot_contact_id`, `is_current`, `effective_start`, and `effective_end` equal the conformed row. `account_id` is not replaced by the surviving account. Descriptive columns are not compared. |
| `dim_contact_survivor_link.sql` | One hop, no self link, the same `surviving_contact_id` on every row of a `contact_id`, and `email_normalized` unique among open surviving rows when present. |

A failing test stays failing. The implementation does not drop a conformed row, keep only survivors, keep only current rows, rewrite a value, edit an intermediate model, or edit a contract to obtain a green test.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read the account and contact sections of the data-model documents, `metric-contract.md`, and the YAML for `int_account` and `int_contact`. Leave `contracts/` and `docs/` unchanged.
- Leave staging models, intermediate models, intermediate tests, `dbt_project.yml`, profiles, packages, the README, macros, and utilities unchanged.
- Do not add a dbt package, a ticket directory, a shared `schema.yml`, a `{% docs %}` block, a metric, an exposure, a semantic model, an analysis, or a snapshot.
- Do not add `commercial_status`, `customer_converted`, `adoption_reached`, a lifecycle event, a product login, a lead, an opportunity, a subscription, a booking, or any pipeline, bookings, ARR, retention, adoption, customer-value, or usage column.
- Do not read DealHub, Marketing, Product usage, `stg_hubspot__company`, `stg_hubspot__contact`, `stg_product__firm`, or any intermediate model other than `int_account` and `int_contact`.
- Use an isolated schema named `dev_data_010_001`, set with `EVE_DBT_SCHEMA`. Do not build into a raw schema or the shared `dev_dbt` schema.
- Validate against `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Do not commit either file, dbt artifacts, or a virtualenv.
- No deployment and no production warehouse change.

## Acceptance criteria

- [ ] The implementation adds only the two mart models, their two YAML files, and the six singular tests inside `allowed_paths`.
- [ ] `dim_account` and `dim_contact` are tables through the marts folder config. Their YAML does not set `materialized`. They are not incremental. `dbt_project.yml` is unchanged.
- [ ] Each model has the grain, row key, and exact column list in this specification. The SQL is the single `conformed` CTE in this specification. Descriptions are the sentences in this specification.
- [ ] Keys and version bounds are copied from `int_account` and `int_contact`. The models do not call `generate_surrogate_key` or `effective_date`. Duplicate rows and closed versions remain.
- [ ] `dim_account` row counts and `account_version_id` values match `int_account`. `dim_contact` row counts and `contact_version_id` values match `int_contact`. The identity and history columns named in the reconcile tests match the conformed row.
- [ ] Each firm and each contact has one open row. `is_current` is true exactly when `effective_end` is null. Versions of one firm or one contact do not overlap or gap.
- [ ] A contact's `account_id` equals the conformed contact's `account_id`, including null and including a duplicate firm. Survivor links are one hop and do not point at the row itself. `primary_domain` is unique among open surviving firms when present. `email_normalized` is unique among open surviving contacts when present.
- [ ] `commercial_status` is absent. The models contain no pipeline, bookings, ARR, retention, adoption, customer-value, usage, semantic-layer, or presentation logic.
- [ ] From `warehouse/dbt/`, with `EVE_DBT_SCHEMA=dev_data_010_001`, `dbt parse` succeeds and `dbt build --select +dim_account +dim_contact path:tests/marts` succeeds against `data/warehouse/dev_data_003` and against `data/warehouse/dev_data_004`.
- [ ] `dbt show` for `dim_account` and `dim_contact` returns rows from both warehouses, with the columns in the specified order.
- [ ] `contracts/`, `docs/`, staging models, intermediate models, and every path outside the two allowed directories are unchanged. No warehouse file is committed.

## Execution notes

Implement this specification only after it has merged and issue #63 is `status:ready`. Use an `impl` worktree and schema `dev_data_010_001`. Do not merge or deploy without human approval.

Read the `dbt-development`, `using-dbt-for-analytics-engineering`, and `data-modeling` skills. Read the account and contact sections of `docs/data-model/entities.md`, `docs/data-model/decisions.md`, and `docs/data-model/source-mapping.md`, and the shared rules in `docs/data-model/metric-contract.md`. Read the YAML for `int_account` and `int_contact` before writing SQL.

From `warehouse/dbt/`, use `dbt show --limit 5` on `int_account` and `int_contact` against `dev_data_003`. Confirm the column names this specification selects. Repeat that check against `dev_data_004` before calling validation complete.

Validation runs from `warehouse/dbt/` against each warehouse file:

```bash
export EVE_DBT_SCHEMA=dev_data_010_001
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_003
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select +dim_account +dim_contact path:tests/marts
.venv/bin/dbt show --profiles-dir . --select dim_account --limit 5
.venv/bin/dbt show --profiles-dir . --select dim_contact --limit 5
```

Repeat the build and both `dbt show` commands with `EVE_DBT_DUCKDB_PATH` pointed at `data/warehouse/dev_data_004`. If a warehouse file is absent, create it through the merged DATA-006 generate and load path, and do not commit it.

The `+` selector builds the conformed parents and their staged parents into the empty schema. Do not select the whole project. A difference between a dimension and the conformed identity or history rules is a stop. Do not make a test pass by dropping rows or by changing an intermediate model or a contract.
