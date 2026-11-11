---
id: DATA-009-001
title: Conform account and contact identities
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
  - DATA-008-005
requires_approval: true
allowed_paths:
  - warehouse/dbt/models/intermediate/
  - warehouse/dbt/tests/intermediate/
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
  - warehouse/dbt/models/marts/
  - warehouse/dbt/tests/staging/
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

Provide one governed account model and one governed contact model that later dbt models can `ref()` when they need a law firm or a sales contact.

The same staged organization resolves to the same account under the approved identity rules, and the same staged person resolves to the same contact. Distinct firms and distinct people stay distinct. Duplicate and survivorship results are deterministic. Current and historical rows reconcile to the staged observations. Account and contact references in valid generated data are resolved and consistent.

## Business context

GitHub issue #53 (`DATA-009-001 — Conform account and contact identities`) is a child of epic #52 (`DATA-009 — Build Shared Conformed GTM Models`). It depends on DATA-008-005, which is merged. Later models need one firm identity and one sales-contact identity before leads, opportunities, subscriptions, bookings, or domain marts are built.

The approved identity, history, and ownership rules are in `docs/data-model/entities.md`, `docs/data-model/decisions.md`, and `docs/data-model/source-mapping.md`. This task implements those rules for account and contact. It does not reopen them and does not edit those documents.

An account is one plaintiff law firm. A contact is one person known to sales. A product login is a different entity and is out of scope. A lead is not an account. A customer is an account, and this task does not derive commercial status.

Staged inputs, after DATA-008-005:

| Model | Grain | What this task uses |
|---|---|---|
| `stg_hubspot__company` | One observation of one HubSpot company at one `observed_at` | Firm observations, including repeated observations of one company |
| `stg_hubspot__contact` | One observation of one HubSpot contact at one `observed_at` | Person observations and the cited `hubspot_company_id` |
| `stg_product__firm` | One Product firm | The current tenant. The contract has no `observed_at` |

DealHub, Marketing, leads, deals, activities, product logins, usage, and outcomes are not inputs. Apollo and Clay are not inputs.

The development warehouses are `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Both are local artifacts and stay untracked. `dev_data_004` includes the domain twin (two HubSpot companies with one web address, and one Product firm on that address) and two contacts that share one email. `dev_data_003` includes companies with a blank web address and contacts that share an email. Those rows are the generated duplicate and distinctness cases. The tests encode the rules below, so both warehouses exercise them.

Sibling issues own the next conformed entities:

| Issue | Owns |
|---|---|
| DATA-009-002 | Leads and opportunities |
| DATA-009-003 | Commercial subscriptions and bookings |

This task does not wait for those issues. `commercial_status` is derived from the first won opportunity and from subscription status. Those inputs belong to the sibling issues, so this task does not add `commercial_status`.

## Scope

The implementation adds two intermediate models, their YAML, and the singular tests below. `components` lists only `dbt`, so `testing.integration_tests` is false.

The models live in the intermediate layer already configured in `dbt_project.yml`. One SQL file and one YAML file of the same basename sit directly in `warehouse/dbt/models/intermediate/`. There is no ticket directory and no shared `schema.yml`.

| Model | Business grain | Row grain | Row key |
|---|---|---|---|
| `int_account` | One law firm | One effective-dated version of one surviving firm, or one row for a duplicate firm | `account_version_id` |
| `int_contact` | One sales contact | One effective-dated version of one surviving contact, or one row for a duplicate contact | `contact_version_id` |

`account_id` is the firm. It repeats on every version of that firm. `contact_id` is the person. It repeats on every version of that person. The row key is unique on the model. The business identifier is not.

`dbt_project.yml` materializes the intermediate folder as ephemeral. Ephemeral models cannot carry these tests. Each model YAML sets `materialized: view`. The models are not incremental. Each run rebuilds every row from the staged observations. Do not edit `dbt_project.yml`.

SQL uses CTEs and `ref()`. It reads only `stg_hubspot__company`, `stg_hubspot__contact`, and `stg_product__firm`. It does not call `source()` and does not read a raw schema. `account_id`, `contact_id`, `account_version_id`, and `contact_version_id` come from `dbt_utils.generate_surrogate_key`. Version bounds for a surviving HubSpot company, and for a surviving contact, come from `effective_date`. Do not edit either macro and do not reimplement its hash or its interval logic.

`effective_date` keeps the opening observation's other columns when it collapses a version. `firm_name`, `state`, and `hubspot_lifecycle_stage` on an account version, and `full_name` and `title` on a contact version, are then taken from the latest staged observation in that version's interval. The macro output is not the final descriptive value.

### Columns

The lists below are the output columns, in that order. The YAML column order matches. No other column is selected.

`int_account`: `account_version_id`, `account_id`, `surviving_account_id`, `hubspot_company_id`, `product_firm_id`, `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, `hubspot_lifecycle_stage`, `is_current`, `effective_start`, `effective_end`.

`int_contact`: `contact_version_id`, `contact_id`, `account_id`, `surviving_contact_id`, `hubspot_contact_id`, `full_name`, `email_normalized`, `title`, `buying_role`, `is_current`, `effective_start`, `effective_end`.

`source_system`, `delivery_id`, and `ingested_at` stay on the staged models. `ingested_at` is used only as `effective_start` for a Product-only account, and it is not an output column.

Stored enums stay the staged codes. Descriptions use the ordinary words in the description section.

| Column | Stored values when present |
|---|---|
| `segment` | `solo`, `small`, `mid`, `large` |
| `icp_fit` | `in_icp`, `out_of_icp` |
| `buying_role` | `champion`, `decision_maker`, `user`, `billing` |

A blank staged value stays null. An empty string is not written in place of null, and null is not written in place of a value. These models do not trim, lowercase, or otherwise rewrite a staged string. Staging already enforces the domain and email shape.

### Keys

`account_id` is `dbt_utils.generate_surrogate_key` of the creating source system name and that source identifier, in that order.

- A firm created from a HubSpot company uses `hubspot` and `hubspot_company_id`.
- A firm created from a Product firm uses `product` and `product_firm_id`.
- Attaching the other source identifier does not change `account_id`.
- A duplicate keeps its own `account_id` from its own source identifier. The survivor's identifier is not copied onto the duplicate, and the duplicate's identifier is not copied onto the survivor.

`contact_id` is `dbt_utils.generate_surrogate_key` of `hubspot` and `hubspot_contact_id`, in that order. Product never creates a contact.

`account_version_id` is `dbt_utils.generate_surrogate_key` of `account_id` and `effective_start`, in that order. `contact_version_id` is `dbt_utils.generate_surrogate_key` of `contact_id` and `effective_start`, in that order.

The same staged identifier produces the same `account_id` or `contact_id` on every run.

### Account identity

Resolve HubSpot companies first, then Product firms. Creation order for a company is the earliest `observed_at`, then `hubspot_company_id` ascending as text. Walk every company observation in `observed_at` order, then `hubspot_company_id` ascending. Product firms are applied after that walk, in `product_firm_id` ascending as text.

A blank `primary_domain` matches nothing, including another blank. Equal `firm_name` does not match. Two `hubspot_company_id` values never share a row, because the model stores one `hubspot_company_id`.

At the first observation of a company:

- When `primary_domain` is blank, or no surviving account currently has that domain, create a surviving account.
- When a surviving account currently has that domain, create a duplicate. `surviving_account_id` is that survivor's `account_id`.

At a later observation, when two surviving accounts would then have the same non-blank domain, the account with the later creation order becomes the duplicate. `surviving_account_id` is the earlier account's `account_id`. The earlier account stays the survivor even when the later account was the one that already held the domain. A survivor link is not cleared when a still later observation changes the domain, and it is not moved to a third account.

`surviving_account_id` is the same on every row of that `account_id`. It is null on a survivor. It references a survivor, so the referenced account has a null `surviving_account_id`. An account does not reference itself. There is no chain.

Product firms then attach by current domain. The current domain of a HubSpot-backed account is `primary_domain` on that company's latest observation.

- A non-blank Product domain that equals a surviving account's current domain, and that account has no `product_firm_id`, is stored on that survivor. The Product row does not create a second account. HubSpot still owns the firm attributes.
- A non-blank Product domain that equals a surviving account which already has a `product_firm_id` creates a duplicate account. Its `account_id` is the Product surrogate. `surviving_account_id` is that survivor. The row keeps this `product_firm_id` and the Product `firm_name`, `primary_domain`, and `state`. It does not take the survivor's `hubspot_company_id`.
- A blank Product domain, or a domain that equals no surviving account's current domain, creates a surviving Product-only account. A duplicate HubSpot row that still shows that domain is not a match target.

The lexicographically smaller `product_firm_id` is applied first, so it occupies an empty `product_firm_id` slot before a later firm with the same domain becomes a duplicate.

### Account attributes

On an account that has a `hubspot_company_id`, HubSpot supplies `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, and `hubspot_lifecycle_stage`. Product supplies `product_firm_id` only. Product `firm_name`, `primary_domain`, and `state` are not copied onto that account when the names or addresses differ.

On a Product-only account, Product supplies `firm_name`, `primary_domain`, and `state`. `segment`, `practice_focus`, `icp_fit`, `owner_name`, `hubspot_lifecycle_stage`, and `hubspot_company_id` are null.

A duplicate HubSpot row shows that company's own attributes, not the survivor's. A duplicate Product row shows that firm's own attributes.

### Account history

Tracked account columns are `owner_name`, `segment`, `practice_focus`, `icp_fit`, and `primary_domain`. A change is `is distinct from`, so a blank and a value are different. `firm_name`, `state`, and `hubspot_lifecycle_stage` do not open a version. Source identifiers do not open a version. `surviving_account_id` does not open a version.

`effective_start` is inclusive. `effective_end` is exclusive and null on the open row. `is_current` is true exactly when `effective_end` is null. Each `account_id` has one open row. Versions of one surviving firm do not overlap and do not leave a gap between `effective_start` values.

For a company that is a duplicate from its first observation: one row. `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, and `hubspot_lifecycle_stage` equal the latest observation of that company. `hubspot_company_id` is that company. `product_firm_id` is null. `effective_start` is that company's first `observed_at`. Do not pass the company through `effective_date`.

For a company that becomes a duplicate at a later observation `T`: pass observations with `observed_at <= T` through `effective_date`, partitioned by `hubspot_company_id`, ordered by `observed_at`, tracking the five columns above. Observations with `observed_at > T` do not open a version and do not replace tracked values. They update `firm_name`, `state`, and `hubspot_lifecycle_stage` on the open row.

For a company that never becomes a duplicate: pass every observation of that company through `effective_date` with those same arguments. The row count is one plus the number of observations whose tracked columns differ from the previous observation of that company. A later observation that changes only `firm_name`, `state`, or `hubspot_lifecycle_stage` does not add a row.

On each surviving version, tracked columns equal the observation that opened the version. `firm_name`, `state`, and `hubspot_lifecycle_stage` equal the latest observation of that company whose `observed_at` is at or after `effective_start` and, when `effective_end` is not null, before `effective_end`. The open row uses the latest such observation with no upper bound, including observations after a match time `T`.

A Product-only account, survivor or duplicate, is one row. Do not pass it through `effective_date`. `effective_start` equals that firm's `ingested_at`. `effective_end` is null.

`product_firm_id` is present on every version of the account that stores it.

### Contact identity

Contacts are resolved only from `stg_hubspot__contact`. A product login email does not create a contact and does not match one. Equal `full_name` does not match. A blank `email_normalized` matches nothing, including another blank. Matching compares the staged email as stored.

Creation order is the earliest `observed_at`, then `hubspot_contact_id` ascending as text. Walk observations in `observed_at` order, then `hubspot_contact_id` ascending.

At the first observation:

- When the email is blank, or no surviving contact currently has that email, create a surviving contact.
- When a surviving contact currently has that email, create a duplicate. `surviving_contact_id` is that survivor's `contact_id`. `hubspot_contact_id` stays on the duplicate and is not copied onto the survivor.

At a later observation, when two surviving contacts would then have the same non-blank email, the contact with the later creation order becomes the duplicate. The earlier contact stays the survivor. The link is not cleared when a still later observation changes the email, and it is not moved to a third contact.

`surviving_contact_id` is the same on every row of that `contact_id`. It is null on a survivor, references a survivor, and does not reference itself. There is no chain.

### Contact firm

`account_id` is the `account_id` of the account row that stores the observation's `hubspot_company_id`. When that company is a duplicate account, `account_id` is the duplicate's `account_id`. The contact is not rewritten onto the surviving account. Downstream resolution follows `surviving_account_id` one hop. This model does that hop only for the company lookup: the cited company id selects the one account that stores it.

A blank `hubspot_company_id` stores a null `account_id`. A cited company that has no account is a failed relationship, not a new account.

### Contact history

Tracked contact columns are `account_id`, `buying_role`, and `email_normalized`. `full_name` and `title` do not open a version. `hubspot_contact_id` and `surviving_contact_id` do not open a version.

For a contact that is a duplicate from its first observation: one row. `full_name`, `email_normalized`, `title`, and `buying_role` equal the latest observation. `account_id` is resolved from that observation's company. `hubspot_contact_id` is that contact. `effective_start` is the first `observed_at`. Do not pass the contact through `effective_date`.

For a contact that becomes a duplicate at a later observation `T`: pass observations with `observed_at <= T` through `effective_date`, partitioned by `hubspot_contact_id`, ordered by `observed_at`, tracking `account_id`, `buying_role`, and `email_normalized`. Resolve `account_id` from each observation's company before that call. Observations after `T` update only `full_name` and `title` on the open row.

For a contact that never becomes a duplicate: pass every observation through `effective_date` with those arguments. A later observation that changes only `full_name` or `title` does not add a row. A change of firm, buying role, or email does.

On each surviving version, tracked columns equal the observation that opened the version. `full_name` and `title` equal the latest observation in the version interval, with the open row taking the latest observation and no upper bound.

`effective_start`, `effective_end`, and `is_current` follow the same inclusive, exclusive, and open-row rules as the account. Each `contact_id` has one open row. Versions of one surviving contact do not overlap or gap.

`email_normalized` is unique among open surviving contacts when it is present. A duplicate may keep the same email. `primary_domain` is unique among open surviving accounts when it is present. A duplicate may keep the same domain.

### What stays staged

Every distinct `hubspot_company_id` in `stg_hubspot__company` appears on exactly one `account_id`. Every distinct `product_firm_id` in `stg_product__firm` appears on exactly one `account_id`. Every distinct `hubspot_contact_id` in `stg_hubspot__contact` appears on exactly one `contact_id`. No account exists without one of those firm source identifiers. No contact exists without a `hubspot_contact_id`.

Conformed row counts are not staged row counts. Repeated observations collapse into versions, and a duplicate collapses to one row.

## Deliverables

- `warehouse/dbt/models/intermediate/int_account.sql`
- `warehouse/dbt/models/intermediate/int_account.yml`
- `warehouse/dbt/models/intermediate/int_contact.sql`
- `warehouse/dbt/models/intermediate/int_contact.yml`
- Singular tests under `warehouse/dbt/tests/intermediate/`, named below

`models/intermediate/.gitkeep` may stay. These files are the complete addition.

### Documentation

YAML descriptions follow the Documentation section of `dbt-development`. A model description is the three sentences below and no others. A column description is the one sentence below and no others. Descriptions leave out grain, keys, history class, canonical identity, `source()` and `ref()` mechanics, reconciliation, and the phrase "not on this model." They do not restate `not_null`, `unique`, or a test.

`int_account`:

One law firm as it stood from one change to the next. A duplicate firm stays on a single row and points at the earlier firm. Commercial status, deal amount, contract value, and booking amount live on later models.

`int_contact`:

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

The contact model's `is_current`, `effective_start`, and `effective_end` use the same sentences as the account, with "person" in place of "firm" on `is_current`.

### Tests in the model YAML

Tests use the `data_tests` and `arguments` shape already used by the staging model YAML. The generic tests are `unique`, `not_null`, `accepted_values`, and `relationships`.

`int_account`:

- `account_version_id`: `unique`, `not_null`
- `account_id`: `not_null`
- `surviving_account_id`: `relationships` to `ref('int_account')`, field `account_id`
- `firm_name`: `not_null`
- `segment`: `accepted_values` of `solo`, `small`, `mid`, `large`
- `icp_fit`: `accepted_values` of `in_icp`, `out_of_icp`
- `is_current`: `not_null`
- `effective_start`: `not_null`

`int_contact`:

- `contact_version_id`: `unique`, `not_null`
- `contact_id`: `not_null`
- `account_id`: `relationships` to `ref('int_account')`, field `account_id`
- `surviving_contact_id`: `relationships` to `ref('int_contact')`, field `contact_id`
- `hubspot_contact_id`: `not_null`
- `buying_role`: `accepted_values` of `champion`, `decision_maker`, `user`, `billing`
- `is_current`: `not_null`
- `effective_start`: `not_null`

`unique` is not applied to `account_id`, `contact_id`, `hubspot_company_id`, `product_firm_id`, `hubspot_contact_id`, `primary_domain`, or `email_normalized`. Those values repeat across versions or are shared by a duplicate. `accepted_values` lists the stored codes. A null enum stays null and is not added to the value list.

### Singular tests

Each file is under `warehouse/dbt/tests/intermediate/`. The leading comment states the rule and that `unique`, `not_null`, `accepted_values`, and `relationships` cannot express it. The query returns the violating rows and returns no rows when the rule holds. Expectations are computed from the staged models. The tests do not hardcode a source identifier from either warehouse.

| File | Rule |
|---|---|
| `account_identity.sql` | The account identity walk, the Product attachment rules, surrogate `account_id`, one account per source identifier, no copied identifier, blank and unequal domains staying apart, and equal names staying apart. |
| `account_history.sql` | Version bounds, tracked values, descriptive overlay, lifecycle-only changes adding no row, one open row per `account_id`, duplicate and Product-only collapse, and `effective_start` equal to the opening `observed_at` or the Product `ingested_at`. |
| `account_survivor_link.sql` | One hop, no self link, the same `surviving_account_id` on every row of an `account_id`, and `primary_domain` unique among open surviving rows when present. |
| `contact_identity.sql` | The contact identity walk, surrogate `contact_id`, one contact per `hubspot_contact_id`, and blank emails staying apart. |
| `contact_history.sql` | Contact version bounds, tracked firm, role, and email, descriptive overlay, and duplicate collapse. |
| `contact_firm_link.sql` | `account_id` is null when the observation that set it has a blank company. Otherwise it equals the one account that stores that `hubspot_company_id`, including a duplicate account. For a surviving version that observation is the one that opened the version. For a contact that was a duplicate from the first observation, it is the latest observation. |

A failing test stays failing. The implementation does not drop a staged row, rewrite a value, edit a staging model, or edit a contract to obtain a green test.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read the account and contact sections of the data-model documents and the HubSpot company, HubSpot contact, and Product firm contracts. Leave `contracts/` and `docs/` unchanged.
- Leave staging models, staging tests, `dbt_project.yml`, profiles, packages, the README, macros, utilities, and marts unchanged.
- Do not add a dbt package, a ticket directory, a shared `schema.yml`, a `{% docs %}` block, a metric, an exposure, or a mart.
- Do not add `commercial_status`, `customer_converted`, `adoption_reached`, a lifecycle event, a product login, a lead, an opportunity, a subscription, a booking, or any pipeline, bookings, ARR, retention, or adoption column.
- Do not read DealHub, Marketing, `stg_hubspot__lead`, `stg_hubspot__deal`, `stg_hubspot__activity`, or any Product model other than `stg_product__firm`.
- Use an isolated schema named `dev_data_009_001`, set with `EVE_DBT_SCHEMA`. Do not build into a raw schema or the shared `dev_dbt` schema.
- Validate against `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Do not commit either file, dbt artifacts, or a virtualenv.
- No deployment and no production warehouse change.

## Acceptance criteria

- [ ] The implementation adds only the two intermediate models, their two YAML files, and the six singular tests inside `allowed_paths`.
- [ ] `int_account` and `int_contact` are views. Their YAML sets `materialized: view`. They are not incremental. `dbt_project.yml` is unchanged.
- [ ] Each model has the grain, row key, and exact column list in this specification. Descriptions are the sentences in this specification.
- [ ] `account_id` and `contact_id` are the `dbt_utils.generate_surrogate_key` results specified above. Version bounds for surviving HubSpot companies and surviving contacts come from `effective_date`. The macros are unchanged.
- [ ] The same staged company, Product firm, or contact resolves to the same account or contact on every run. Two HubSpot companies that share a web address produce one survivor and one duplicate. A Product firm with that current web address is stored on the survivor. Blank web addresses, unequal web addresses, and equal firm names stay distinct accounts.
- [ ] Two HubSpot contacts that share an email produce one survivor and one duplicate. Blank emails stay distinct. A contact is not created from a product login.
- [ ] A duplicate does not grow versions. A surviving firm's versions open only for the tracked account columns. A change of only firm name, state, or HubSpot lifecycle label does not add an account row. A contact move between firms opens a version. Current descriptive values match the latest staged observation in the open interval.
- [ ] `commercial_status` is absent. The models contain no pipeline, bookings, ARR, retention, adoption, or other domain metric.
- [ ] Every staged company, Product firm, and contact maps to one conformed entity. `account_id` on a contact points at the account that stores the cited company, including a duplicate account. Survivor links are one hop and do not point at the row itself.
- [ ] From `warehouse/dbt/`, with `EVE_DBT_SCHEMA=dev_data_009_001`, `dbt parse` succeeds and `dbt build --select +int_account +int_contact path:tests/intermediate` succeeds against `data/warehouse/dev_data_003` and against `data/warehouse/dev_data_004`.
- [ ] `dbt show` for `int_account` and `int_contact` returns rows from both warehouses.
- [ ] `contracts/`, `docs/`, staging models, and every path outside the two allowed directories are unchanged. No warehouse file is committed.

## Execution notes

Implement this specification only after it has merged and issue #53 is `status:ready`. Use an `impl` worktree and schema `dev_data_009_001`. Do not merge or deploy without human approval.

Read the `dbt-development`, `using-dbt-for-analytics-engineering`, and `data-modeling` skills. Read the account and contact sections of `docs/data-model/entities.md`, `docs/data-model/decisions.md`, and `docs/data-model/source-mapping.md`, and read the YAML for `stg_hubspot__company`, `stg_hubspot__contact`, and `stg_product__firm` before writing SQL.

From `warehouse/dbt/`, use `dbt show --limit 5` on those three staging models against `dev_data_003`. Confirm the column names this specification selects. Repeat that check against `dev_data_004` before calling validation complete.

Validation runs from `warehouse/dbt/` against each warehouse file:

```bash
export EVE_DBT_SCHEMA=dev_data_009_001
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_003
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select +int_account +int_contact path:tests/intermediate
.venv/bin/dbt show --profiles-dir . --select int_account --limit 5
.venv/bin/dbt show --profiles-dir . --select int_contact --limit 5
```

Repeat the build and both `dbt show` commands with `EVE_DBT_DUCKDB_PATH` pointed at `data/warehouse/dev_data_004`. If a warehouse file is absent, create it through the merged DATA-006 generate and load path, and do not commit it.

The `+` selector builds the staged parents into the empty schema. Do not select the whole project. A difference between a conformed result and the identity or history rules is a stop. Do not make a test pass by dropping rows or by changing a staging model or a contract.
