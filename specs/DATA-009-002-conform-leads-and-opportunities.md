---
id: DATA-009-002
title: Conform leads and opportunities
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
  - warehouse/dbt/models/intermediate/int_account.sql
  - warehouse/dbt/models/intermediate/int_account.yml
  - warehouse/dbt/models/intermediate/int_contact.sql
  - warehouse/dbt/models/intermediate/int_contact.yml
  - warehouse/dbt/tests/staging/
  - warehouse/dbt/tests/intermediate/account_identity.sql
  - warehouse/dbt/tests/intermediate/account_history.sql
  - warehouse/dbt/tests/intermediate/account_survivor_link.sql
  - warehouse/dbt/tests/intermediate/contact_identity.sql
  - warehouse/dbt/tests/intermediate/contact_history.sql
  - warehouse/dbt/tests/intermediate/contact_firm_link.sql
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

Provide one governed lead model, one governed opportunity model, and the shared lifecycle events downstream pipeline analysis refs for an inquiry, a deal, and a firm's first win.

The same staged lead resolves to the same lead, and the same staged deal resolves to the same opportunity. Each lead and opportunity points at the account and contact that store the cited HubSpot firm and person, including a duplicate account or contact. Repeated observations keep the history downstream analysis needs, and the current lead row and the open opportunity row stay the latest observation. Conversion, loss, and a return to an earlier open stage appear in the lifecycle sequence the staged observations already record.

## Business context

GitHub issue #55 (`DATA-009-002 — Conform leads and opportunities`) depends on DATA-009-001, which is merged. Later pipeline models need one inquiry, one deal, and the lifecycle steps of those records before attribution, conversion metrics, subscriptions, or domain marts are built.

The approved identity, history, and event rules are in `docs/data-model/entities.md`, `docs/data-model/decisions.md`, `docs/data-model/source-mapping.md`, and the lifecycle-event column contract in `docs/data-model/metric-contract.md`. This task implements those rules for lead, opportunity, and the lifecycle events a lead or a deal produces. It does not reopen them and does not edit those documents.

A lead is one sales inquiry. It can exist before a firm or a person is known. A lead is not an account, and conversion does not rewrite the lead into the firm. An opportunity is one sales deal for one law firm. New business, expansion, and renewal are types of that deal. HubSpot is the only creator of leads and opportunities. DealHub attaches commercial records to the HubSpot deal and does not create a second opportunity.

Lead status history is the lead lifecycle events. The lead model keeps the current inquiry. Opportunity stage, amount, expected close date, owner, forecast, and type are the pipeline history, so the opportunity model is effective-dated. `customer_converted` is the account's first `opportunity_won`. HubSpot does not send that event. This task records it. It does not derive `commercial_status`, because that status also depends on subscription state owned by DATA-009-003.

Staged inputs, after DATA-008-005, and the conformed identities from DATA-009-001:

| Model | Grain | What this task uses |
|---|---|---|
| `stg_hubspot__lead` | One observation of one HubSpot lead at one `observed_at` | Inquiry observations, including repeated observations of one lead |
| `stg_hubspot__deal` | One observation of one HubSpot deal at one `observed_at` | Deal observations, including repeated observations of one deal |
| `int_account` | One effective-dated version of one surviving firm, or one row for a duplicate firm | The `account_id` that stores `hubspot_company_id` |
| `int_contact` | One effective-dated version of one surviving contact, or one row for a duplicate contact | The `contact_id` that stores `hubspot_contact_id` |

Marketing touches, campaigns, activities, quotes, contracts, subscriptions, bookings, product firms, and product usage are not inputs. Apollo and Clay are not inputs.

The development warehouses are `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Both are local artifacts and stay untracked. `dev_data_004` includes a converting lead with a won deal, a converting lead with a lost deal, a converting lead whose deal moves from proposal back to evaluation and then onward, a later win on a firm that already has a first win, and a domain-twin firm whose lead ends disqualified. `dev_data_003` includes leads with no firm and deals whose amount is null. The tests encode the rules below, so both warehouses exercise them. The tests do not hardcode a source identifier from either warehouse.

DATA-009-003 owns commercial subscriptions and bookings, and it owns `opportunity.subscription_id`. This task does not wait for that issue and does not add that foreign key.

## Scope

The implementation adds three intermediate models, their YAML, and the singular tests below. `components` lists only `dbt`, so `testing.integration_tests` is false.

The models live in the intermediate layer already configured in `dbt_project.yml`. One SQL file and one YAML file of the same basename sit directly in `warehouse/dbt/models/intermediate/`. There is no ticket directory and no shared `schema.yml`.

| Model | Business grain | Row grain | Row key |
|---|---|---|---|
| `int_lead` | One sales inquiry | One lead | `lead_id` |
| `int_opportunity` | One sales deal | One effective-dated version of one opportunity | `opportunity_version_id` |
| `int_lifecycle_event` | One lifecycle step | One occurrence of one named lifecycle event | `lifecycle_event_id` |

`lead_id` is the inquiry. On `int_lead` it is also the row key, so it is unique. `opportunity_id` is the deal. It repeats on every version of that deal. `lifecycle_event_id` is one occurrence. The row key is unique on each model.

`dbt_project.yml` materializes the intermediate folder as ephemeral. Ephemeral models cannot carry these tests. Each model YAML sets `materialized: view`. The models are not incremental. Each run rebuilds every row from the staged observations and the account and contact models. Do not edit `dbt_project.yml`.

SQL uses CTEs and `ref()`. It reads only `stg_hubspot__lead`, `stg_hubspot__deal`, `int_account`, and `int_contact`. `int_lifecycle_event` also reads `int_lead` and `int_opportunity`. `int_lead` does not read `int_opportunity`. The models do not call `source()` and do not read a raw schema.

`lead_id`, `opportunity_id`, `opportunity_version_id`, and `lifecycle_event_id` come from `dbt_utils.generate_surrogate_key`. Version bounds for an opportunity come from `effective_date`. Do not edit either macro and do not reimplement its hash or its interval logic. `int_lead` and `int_lifecycle_event` do not call `effective_date`.

`effective_date` keeps the opening observation's other columns when it collapses a version. `opportunity_name` and `primary_contact_id` are then taken from the latest staged observation in that version's interval. The macro output is not the final value of those two columns.

### Columns

The lists below are the output columns, in that order. The YAML column order matches. No other column is selected.

`int_lead`: `lead_id`, `account_id`, `contact_id`, `surviving_lead_id`, `hubspot_lead_id`, `status`, `created_at`.

`int_opportunity`: `opportunity_version_id`, `opportunity_id`, `account_id`, `primary_contact_id`, `lead_id`, `surviving_opportunity_id`, `hubspot_deal_id`, `opportunity_name`, `opportunity_type`, `stage`, `owner_name`, `forecast_category`, `amount`, `is_current`, `expected_close_date`, `created_at`, `effective_start`, `effective_end`.

`int_lifecycle_event` uses the shared lifecycle-event column contract, in this order: `lifecycle_event_id`, `event_name`, `lifecycle_stage`, `occurred_at`, `subject_entity`, `account_id`, `lead_id`, `opportunity_id`, `subscription_id`.

`source_system`, `delivery_id`, and `ingested_at` stay on the staged models. They are not output columns.

Stored enums stay the staged codes. Descriptions use the ordinary words in the description section.

| Column | Stored values when present |
|---|---|
| `status` | `new`, `working`, `qualified`, `disqualified`, `converted` |
| `opportunity_type` | `new_business`, `expansion`, `renewal` |
| `stage` | `discovery`, `evaluation`, `proposal`, `negotiation`, `closed_won`, `closed_lost` |
| `forecast_category` | `pipeline`, `best_case`, `commit`, `closed`, `omitted` |
| `event_name` | `lead_created`, `lead_qualified`, `lead_disqualified`, `lead_converted`, `opportunity_opened`, `opportunity_stage_changed`, `opportunity_won`, `opportunity_lost`, `customer_converted` |
| `lifecycle_stage` | `lead`, `opportunity`, `customer` |
| `subject_entity` | `lead`, `opportunity`, `account` |

A blank staged value stays null. An empty string is not written in place of null, and null is not written in place of a value. These models do not trim, lowercase, or otherwise rewrite a staged string. A null `amount` stays null. It is not stored as zero. `subscription_id` is null on every lifecycle row this task emits.

### Keys

`lead_id` is `dbt_utils.generate_surrogate_key` of `hubspot` and `hubspot_lead_id`, in that order.

`opportunity_id` is `dbt_utils.generate_surrogate_key` of `hubspot` and `hubspot_deal_id`, in that order.

`opportunity_version_id` is `dbt_utils.generate_surrogate_key` of `opportunity_id` and `effective_start`, in that order.

`lifecycle_event_id` is `dbt_utils.generate_surrogate_key` of `event_name`, `subject_entity`, the subject identifier, and `occurred_at`, in that order. The subject identifier is `lead_id` when `subject_entity` is `lead`, `opportunity_id` when `subject_entity` is `opportunity`, and `account_id` when `subject_entity` is `account`.

The same staged identifier produces the same `lead_id` or `opportunity_id` on every run. The same event inputs produce the same `lifecycle_event_id` on every run.

### Lead identity

HubSpot is the only creator of a lead. One `hubspot_lead_id` is one lead. Repeated observations of that identifier update that lead. They do not create a second lead. Two different `hubspot_lead_id` values are two leads, including when they share a firm, a person, or a campaign. Equal names are not a lead match. This task does not discover a second canonical lead for one inquiry, so `surviving_lead_id` is null on every row. A lead does not reference itself.

The current lead row is the latest observation of that `hubspot_lead_id`: the greatest `observed_at`. The staged model is unique on `hubspot_lead_id` and `observed_at`, so that observation is one row. `status` is that observation's status. `created_at` equals that lead's `created_at`, which is stable, and it equals `observed_at` on the observation whose `emitted_event` is `lead_created`.

`account_id` is the `account_id` of the `int_account` row that stores the latest observation's `hubspot_company_id`. When that company is a duplicate account, `account_id` is the duplicate's `account_id`. The lead is not rewritten onto the surviving account. Downstream resolution follows `surviving_account_id` one hop. This model does that hop only for the company lookup: the cited company id selects the one account that stores it.

`contact_id` is the `contact_id` of the `int_contact` row that stores the latest observation's `hubspot_contact_id`. When that person is a duplicate contact, `contact_id` is the duplicate's `contact_id`. The lead is not rewritten onto the surviving contact.

A blank `hubspot_company_id` stores a null `account_id`. A blank `hubspot_contact_id` stores a null `contact_id`. A cited company or contact that has no conformed row is a failed relationship, not a new account or contact.

`originating_campaign_id` is not a column. `marketing_campaign_id` stays on `stg_hubspot__lead`.

### Opportunity identity

HubSpot is the only creator of an opportunity. One `hubspot_deal_id` is one opportunity. Repeated observations of that identifier are versions of that opportunity. They do not create a second opportunity. Two deals with different HubSpot ids are two opportunities, even when `opportunity_name` is equal. A DealHub quote, contract, subscription, or booking does not create an opportunity. This task does not discover a second canonical opportunity for one deal, so `surviving_opportunity_id` is null on every row. An opportunity does not reference itself.

`account_id` is the `account_id` of the `int_account` row that stores the deal's `hubspot_company_id`, including a duplicate account. The same rule as the lead applies: store the account that holds the cited company, and do not replace it with `surviving_account_id`. `hubspot_company_id` is stable across observations of a deal, so `account_id` is the same on every version. A cited company that has no account is a failed relationship, not a new account. `account_id` is present on every version.

`lead_id` is the `lead_id` of the `int_lead` row that stores the deal's `hubspot_lead_id`, or null when that identifier is null. A non-null `hubspot_lead_id` does not change within the deal, so `lead_id` is the same on every version. `lead_id` is unique across distinct `opportunity_id` values when it is present. Versions of one opportunity repeat it. A deal that cites a lead with no `int_lead` row is a failed relationship, not a new lead.

`primary_contact_id` is the `contact_id` of the `int_contact` row that stores the chosen observation's `hubspot_contact_id`, including a duplicate contact, or null when that identifier is null. The chosen observation is the latest observation in the version interval, defined under history. A cited contact that has no `int_contact` row is a failed relationship, not a new contact.

`dealhub_subscription_id` stays on `stg_hubspot__deal`. `int_opportunity` has no `subscription_id`.

### Opportunity history

Tracked opportunity columns are `stage`, `amount`, `expected_close_date`, `owner_name`, `forecast_category`, and `opportunity_type`. A change is `is distinct from`, so a blank and a value are different, and a null `amount` and a number are different. `opportunity_name` and `primary_contact_id` do not open a version. `account_id`, `lead_id`, `hubspot_deal_id`, `created_at`, and `surviving_opportunity_id` do not open a version.

Pass every observation of the deal through `effective_date`, partitioned by `hubspot_deal_id`, ordered by `observed_at`, tracking those six columns. This task creates no duplicate opportunity, so there is no observation cutoff and no one-row collapse.

`effective_start` is inclusive and equals `observed_at` of the observation that opened the version. `effective_end` is exclusive and null on the open row. `is_current` is true exactly when `effective_end` is null. Each `opportunity_id` has one open row. Versions of one deal do not overlap and do not leave a gap between `effective_start` values. The row count for a deal is one plus the number of observations whose tracked columns differ from the previous observation of that deal.

On each version, the six tracked columns equal the observation that opened the version. `opportunity_name` equals the latest observation of that deal whose `observed_at` is at or after `effective_start` and, when `effective_end` is not null, before `effective_end`. The open row uses the latest observation of the deal and no upper bound. `primary_contact_id` is resolved from that same latest observation. A later observation that changes only `opportunity_name` or `hubspot_contact_id` does not add a row.

A return to an earlier open stage is a tracked stage change. It opens another version and leaves the earlier version in place. The open row's `stage` is the latest observation's stage.

`created_at` is the same on every version and equals the opening observation's `created_at`. The opening observation has `stage` `discovery`, `emitted_event` `opportunity_opened`, and `observed_at` equal to `created_at`.

### Firm on the primary contact

When `primary_contact_id` is present on an opportunity version, the `int_contact` version for that `contact_id` in effect at the opportunity version's `effective_start` has `account_id` equal to the opportunity's `account_id`. In effect means the contact version's `effective_start` is at or before that timestamp and its `effective_end` is null or after that timestamp. The deal and the contact cite the same HubSpot company at that time, so both resolve to the same account, including a duplicate account. A missing contact version at that timestamp is a failed relationship. The implementation does not drop the deal and does not rewrite either account.

### Lifecycle events

Each staged lead or deal row whose `emitted_event` is not null becomes one lifecycle row. `occurred_at` equals that row's `observed_at`. A staged row whose `emitted_event` is null does not become a lifecycle row. `status` `working` is that case for a lead. A later deal observation whose stage is unchanged is that case for a deal, even when amount, close date, owner, forecast, or type change on that observation.

`customer_converted` is the only lifecycle row that has no staged `emitted_event`.

The foreign keys follow the event catalog. Absent means null.

| Event | `subject_entity` | `lifecycle_stage` | `account_id` | `lead_id` | `opportunity_id` |
|---|---|---|---|---|---|
| `lead_created` | `lead` | `lead` | The firm on the emitting observation, null when that observation has no firm | The lead | Null |
| `lead_qualified` | `lead` | `lead` | The firm on the emitting observation, null when that observation has no firm | The lead | Null |
| `lead_disqualified` | `lead` | `lead` | The firm on the emitting observation, null when that observation has no firm | The lead | Null |
| `lead_converted` | `lead` | `lead` | The firm on the converted observation | The lead | The opportunity that stores that observation's `hubspot_deal_id` |
| `opportunity_opened` | `opportunity` | `opportunity` | The opportunity's `account_id` | Null | The opportunity |
| `opportunity_stage_changed` | `opportunity` | `opportunity` | The opportunity's `account_id` | Null | The opportunity |
| `opportunity_won` | `opportunity` | `opportunity` | The opportunity's `account_id` | Null | The opportunity |
| `opportunity_lost` | `opportunity` | `opportunity` | The opportunity's `account_id` | Null | The opportunity |
| `customer_converted` | `account` | `customer` | The winning opportunity's `account_id` | Null | That opportunity |

A lead event resolves `account_id` from the `hubspot_company_id` on the observation that emitted it, using the same account lookup as the lead. A later observation's firm is not written onto an earlier event. The current lead row still takes its firm from the latest observation. When every non-null company on that lead is the same company, every non-null lead-event `account_id` equals the lead's `account_id`.

`lead_converted.account_id` is present. It equals the lead's `account_id` and the opportunity's `account_id`. A converted observation with a blank company is a failed relationship, not a firm copied from the deal.

`customer_converted` is one row per `account_id` that has an `opportunity_won`. Choose the `opportunity_won` with the earliest `occurred_at` for that stored `account_id`. When those times tie, choose the ascending `opportunity_id` text. `occurred_at` and `opportunity_id` on `customer_converted` equal that win. A later win for the same `account_id` keeps its own `opportunity_won` and does not add a second `customer_converted`. An account with no win has no `customer_converted`. The event stays on the stored `account_id`. It is not moved through `surviving_account_id`.

### Sequences

For each lead:

- One `lead_created`. Its `occurred_at` equals the lead's `created_at`, and the emitting observation has `status` `new`.
- At most one `lead_qualified`, at most one `lead_disqualified`, and at most one `lead_converted`.
- `lead_qualified` and `lead_disqualified` do not both exist.
- `lead_converted` exists only after `lead_qualified`, with `occurred_at` at or after the qualification.
- Current `status` `converted` exists exactly when `lead_converted` exists. Current `status` `disqualified` exists exactly when `lead_disqualified` exists. Current `status` `qualified` exists exactly when `lead_qualified` exists and `lead_converted` does not. Current `status` `new` or `working` exists exactly when none of those three events exist.
- A disqualified lead has no opportunity. A converted lead has one opportunity, and that opportunity's `hubspot_deal_id` equals the converted observation's `hubspot_deal_id`. A lead in `new`, `working`, or `qualified` has no opportunity.
- `lead_converted.occurred_at` is at or before that opportunity's `created_at`.

For each opportunity:

- One `opportunity_opened`. Its `occurred_at` equals `created_at`, and the emitting observation has `stage` `discovery`. Opening is not `opportunity_stage_changed`.
- Each later observation whose `emitted_event` is `opportunity_stage_changed` is one event. The stage on that observation is `evaluation`, `proposal`, or `negotiation`, including a return to a stage the deal already passed.
- `discovery`, `closed_won`, and `closed_lost` are not `opportunity_stage_changed`.
- At most one `opportunity_won` and at most one `opportunity_lost`. A deal does not have both.
- The open row's `stage` equals the latest observation's `stage`. That stage is `closed_won` exactly when the deal has `opportunity_won`, and `closed_lost` exactly when the deal has `opportunity_lost`. An open stage has neither event.
- Event `occurred_at` order equals the `observed_at` order of the observations that emitted them.
- When the ordered stages of a deal return to an earlier open stage, the versions ordered by `effective_start` keep both the earlier stage and the later return, and the open row's stage is the last observation's stage. The return is `opportunity_stage_changed`. That deal has neither `opportunity_won` nor `opportunity_lost`.

`dev_data_004` records those sequences as a won conversion, a loss, a proposal that returns to evaluation, and a later win on a firm that already converted. The tests compute the sequences from the staged observations.

### What stays staged

Every distinct `hubspot_lead_id` in `stg_hubspot__lead` appears on exactly one `lead_id`. Every distinct `hubspot_deal_id` in `stg_hubspot__deal` appears on exactly one `opportunity_id`. No lead exists without a `hubspot_lead_id`. No opportunity exists without a `hubspot_deal_id`.

`int_lead` row count equals the count of distinct staged lead identifiers. It does not equal the staged lead row count. Opportunity version counts do not equal the staged deal row count. Each non-null staged `emitted_event` appears as exactly one lifecycle row with the same `occurred_at` and the same lead or deal. `customer_converted` rows are the first-win rows defined above and have no staged `emitted_event`.

## Deliverables

- `warehouse/dbt/models/intermediate/int_lead.sql`
- `warehouse/dbt/models/intermediate/int_lead.yml`
- `warehouse/dbt/models/intermediate/int_opportunity.sql`
- `warehouse/dbt/models/intermediate/int_opportunity.yml`
- `warehouse/dbt/models/intermediate/int_lifecycle_event.sql`
- `warehouse/dbt/models/intermediate/int_lifecycle_event.yml`
- Singular tests under `warehouse/dbt/tests/intermediate/`, named below

`models/intermediate/.gitkeep` may stay. These files are the complete addition. `int_account`, `int_contact`, and their singular tests stay as they are.

### Documentation

YAML descriptions follow the Documentation section of `dbt-development`. A model description is the three sentences below and no others. A column description is the one sentence below and no others. Descriptions leave out grain, keys, history class, canonical identity, `source()` and `ref()` mechanics, reconciliation, and the phrase "not on this model." They do not restate `not_null`, `unique`, or a test.

`int_lead`:

One sales inquiry as it stands now. A later status replaces the status on this row, and the inquiry can name a firm and a person or neither. The steps the inquiry has taken, and the deal it becomes, live on the lifecycle events and the opportunity.

`int_opportunity`:

One sales deal as it stood from one change to the next. A move back to an earlier open stage starts another row, and the earlier stage stays in place. Quote value, contract value, booking amount, and the repeating charge live on later models.

`int_lifecycle_event`:

One recorded step for an inquiry or a deal, including the firm's first win. A move back to an earlier open stage is another step, and a lead that is only being worked adds none. Adoption and renewal steps live on later models.

`int_lead`:

| Column | Description |
|---|---|
| `lead_id` | The inquiry this row belongs to. |
| `account_id` | The firm this inquiry names, when a firm is known. |
| `contact_id` | The person this inquiry names, when a person is known. |
| `surviving_lead_id` | The earlier inquiry, when this inquiry is a duplicate. |
| `hubspot_lead_id` | HubSpot's id for this inquiry. |
| `status` | Where the inquiry stands: new, working, qualified, disqualified, or converted. |
| `created_at` | When the inquiry was opened. |

`int_opportunity`:

| Column | Description |
|---|---|
| `opportunity_version_id` | The span of time this row keeps for the deal. |
| `opportunity_id` | The deal this row belongs to. |
| `account_id` | The firm this deal belongs to. |
| `primary_contact_id` | The person sales names first on this deal. |
| `lead_id` | The inquiry this deal came from. |
| `surviving_opportunity_id` | The earlier deal, when this deal is a duplicate. |
| `hubspot_deal_id` | HubSpot's id for this deal. |
| `opportunity_name` | The deal name in the words sales uses. |
| `opportunity_type` | Why the deal exists: new business, expansion, or renewal. |
| `stage` | Where the deal stands: discovery, evaluation, proposal, negotiation, closed won, or closed lost. |
| `owner_name` | The sales owner of the deal, which may match or differ from the firm-relationship owner. |
| `forecast_category` | How sales forecasts this deal: pipeline, best case, commit, closed, or omitted. |
| `amount` | The deal amount in US dollars as sales entered it, which stays blank when sales left it blank. |
| `is_current` | Whether this row is the deal's open span. |
| `expected_close_date` | The date sales expects the deal to close. |
| `created_at` | When the deal was opened. |
| `effective_start` | When this span began, and this moment is included. |
| `effective_end` | When this span ended, and this moment is not included; the open span has no end. |

`int_lifecycle_event`:

| Column | Description |
|---|---|
| `lifecycle_event_id` | The recorded step this row keeps. |
| `event_name` | The step that happened: the inquiry was created, qualified, disqualified, or converted; the deal opened, changed stage, was won, or was lost; or the firm won its first deal. |
| `lifecycle_stage` | Whether this step is about the inquiry, the deal, or the firm becoming a customer. |
| `occurred_at` | When this step happened. |
| `subject_entity` | Whether this step belongs to the inquiry, the deal, or the firm. |
| `account_id` | The firm this step names, when the step has a firm. |
| `lead_id` | The inquiry this step belongs to. |
| `opportunity_id` | The deal this step belongs to. |
| `subscription_id` | The subscription a renewal or expansion step targets; an inquiry or deal step leaves this blank. |

### Tests in the model YAML

Tests use the `data_tests` and `arguments` shape already used by the staging model YAML. The generic tests are `unique`, `not_null`, `accepted_values`, and `relationships`.

`int_lead`:

- `lead_id`: `unique`, `not_null`
- `account_id`: `relationships` to `ref('int_account')`, field `account_id`
- `contact_id`: `relationships` to `ref('int_contact')`, field `contact_id`
- `surviving_lead_id`: `relationships` to `ref('int_lead')`, field `lead_id`
- `hubspot_lead_id`: `unique`, `not_null`
- `status`: `not_null`, `accepted_values` of `new`, `working`, `qualified`, `disqualified`, `converted`
- `created_at`: `not_null`

`int_opportunity`:

- `opportunity_version_id`: `unique`, `not_null`
- `opportunity_id`: `not_null`
- `account_id`: `not_null`, `relationships` to `ref('int_account')`, field `account_id`
- `primary_contact_id`: `relationships` to `ref('int_contact')`, field `contact_id`
- `lead_id`: `relationships` to `ref('int_lead')`, field `lead_id`
- `surviving_opportunity_id`: `relationships` to `ref('int_opportunity')`, field `opportunity_id`
- `hubspot_deal_id`: `not_null`
- `opportunity_name`: `not_null`
- `opportunity_type`: `not_null`, `accepted_values` of `new_business`, `expansion`, `renewal`
- `stage`: `not_null`, `accepted_values` of `discovery`, `evaluation`, `proposal`, `negotiation`, `closed_won`, `closed_lost`
- `forecast_category`: `accepted_values` of `pipeline`, `best_case`, `commit`, `closed`, `omitted`
- `is_current`: `not_null`
- `created_at`: `not_null`
- `effective_start`: `not_null`

`int_lifecycle_event`:

- `lifecycle_event_id`: `unique`, `not_null`
- `event_name`: `not_null`, `accepted_values` of `lead_created`, `lead_qualified`, `lead_disqualified`, `lead_converted`, `opportunity_opened`, `opportunity_stage_changed`, `opportunity_won`, `opportunity_lost`, `customer_converted`
- `lifecycle_stage`: `not_null`, `accepted_values` of `lead`, `opportunity`, `customer`
- `occurred_at`: `not_null`
- `subject_entity`: `not_null`, `accepted_values` of `lead`, `opportunity`, `account`
- `account_id`: `relationships` to `ref('int_account')`, field `account_id`
- `lead_id`: `relationships` to `ref('int_lead')`, field `lead_id`
- `opportunity_id`: `relationships` to `ref('int_opportunity')`, field `opportunity_id`

`unique` is not applied to `opportunity_id`, `hubspot_deal_id`, `lead_id` on the opportunity, `account_id`, `primary_contact_id`, or `amount`. Those values repeat across versions or are absent on some rows. `accepted_values` lists the stored codes. A null enum stays null and is not added to the value list. `subscription_id` has no generic test. `amount` has no generic test. Staging already guards the amount sign, and the history test compares the stored amount with the staged amount.

### Singular tests

Each file is under `warehouse/dbt/tests/intermediate/`. The leading comment states the rule and that `unique`, `not_null`, `accepted_values`, and `relationships` cannot express it. The query returns the violating rows and returns no rows when the rule holds. Expectations are computed from the staged models and from `int_account` and `int_contact`. The tests do not hardcode a source identifier from either warehouse.

| File | Rule |
|---|---|
| `lead_identity.sql` | One `lead_id` per `hubspot_lead_id`, the HubSpot surrogate, a null `surviving_lead_id`, the latest observation's status, firm, and person, a blank firm or person staying null, and a duplicate firm's own `account_id` stored on the lead. |
| `opportunity_identity.sql` | One `opportunity_id` per `hubspot_deal_id`, the HubSpot surrogate, a null `surviving_opportunity_id`, the firm, person, and inquiry links, `lead_id` unique across deals, a present `lead_id` belonging to a converted inquiry, that converted inquiry pointing at this one deal, a disqualified inquiry pointing at none, the contact version in effect at `effective_start` having the deal's `account_id`, and equal deal names staying two deals. |
| `opportunity_history.sql` | Version bounds, tracked values from the opening observation, name and primary person from the latest observation in the interval, a name-only or contact-only change adding no row, one open row, the open row matching the latest observation, a null amount staying null, and a return to an earlier open stage keeping the earlier version and opening another. |
| `lifecycle_lead.sql` | One lifecycle row per non-null lead `emitted_event` at that `observed_at`, no row for `working`, one `lead_created` at `created_at`, qualification and disqualification not both present, conversion after qualification, current status agreeing with those events, and the converted inquiry's one deal equal to the deal named on that observation. |
| `lifecycle_opportunity.sql` | One lifecycle row per non-null deal `emitted_event` at that `observed_at`, no row for an unchanged stage, opening recorded as `opportunity_opened`, a later open stage including a return recorded as `opportunity_stage_changed`, win and loss not both present, and the open stage agreeing with the latest observation and with the win or loss event. |
| `lifecycle_customer_converted.sql` | One `customer_converted` for the earliest win of a stored `account_id`, a later win adding no second event, that event carrying the win's deal and time, catalog presence of `account_id`, `lead_id`, and `opportunity_id` for every stored event name, `subscription_id` null on every row, and no adoption or subscription event name. |

A failing test stays failing. The implementation does not drop a staged row, rewrite a value, edit a staging model, edit `int_account` or `int_contact`, or edit a contract to obtain a green test.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read the lead, opportunity, and lifecycle-event sections of the data-model documents, the lifecycle-event column contract, and the HubSpot lead and deal contracts. Leave `contracts/` and `docs/` unchanged.
- Leave `int_account`, `int_contact`, their YAML, and their singular tests unchanged. Leave staging models, staging tests, `dbt_project.yml`, profiles, packages, the README, macros, utilities, and marts unchanged.
- Do not add a dbt package, a ticket directory, a shared `schema.yml`, a `{% docs %}` block, a metric, an exposure, a unit-test fixture, or a mart.
- Do not add `originating_campaign_id`, `marketing_campaign_id`, `subscription_id` on `int_opportunity`, `dealhub_subscription_id`, `commercial_status`, `pipeline_amount`, `is_won`, a win rate, a conversion rate, sourced pipeline, influenced pipeline, bookings, ARR, or revenue.
- Do not read DealHub, Marketing, Product, `stg_hubspot__activity`, `stg_hubspot__company`, or `stg_hubspot__contact` except through `int_account` and `int_contact`.
- Use an isolated schema named `dev_data_009_002`, set with `EVE_DBT_SCHEMA`. Do not build into a raw schema or the shared `dev_dbt` schema.
- Validate against `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Do not commit either file, dbt artifacts, or a virtualenv.
- No deployment and no production warehouse change.

## Acceptance criteria

- [ ] The implementation adds only the three intermediate models, their three YAML files, and the six singular tests inside `allowed_paths`.
- [ ] `int_lead`, `int_opportunity`, and `int_lifecycle_event` are views. Their YAML sets `materialized: view`. They are not incremental. `dbt_project.yml` is unchanged.
- [ ] Each model has the grain, row key, and exact column list in this specification. `int_lifecycle_event` column order is the shared lifecycle-event column contract. Descriptions are the sentences in this specification.
- [ ] `lead_id`, `opportunity_id`, `opportunity_version_id`, and `lifecycle_event_id` are the `dbt_utils.generate_surrogate_key` results specified above. Opportunity version bounds come from `effective_date`. The macros are unchanged. The lead and the lifecycle event do not call `effective_date`.
- [ ] The same staged lead or deal resolves to the same lead or opportunity on every run. Repeated observations leave one current lead and one open opportunity version. The current status and the open stage equal the latest staged observation. A return to an earlier open stage keeps the earlier version.
- [ ] A lead and an opportunity store the account and contact that hold the cited HubSpot identifiers, including a duplicate account or contact. A converted lead has one opportunity, a disqualified lead has none, and the primary contact's firm at the version start is the deal's firm.
- [ ] Conversion, loss, and stage regression each produce the lifecycle sequence in this specification. `customer_converted` exists once for the earliest win of a stored account and does not repeat for a later win. Missing, duplicate, and contradictory outcomes fail the singular tests.
- [ ] The models contain no attribution, conversion-rate, pipeline-value, or revenue metric, and no subscription or booking attribute.
- [ ] From `warehouse/dbt/`, with `EVE_DBT_SCHEMA=dev_data_009_002`, `dbt parse` succeeds and `dbt build --select +int_lead +int_opportunity +int_lifecycle_event path:tests/intermediate` succeeds against `data/warehouse/dev_data_003` and against `data/warehouse/dev_data_004`. The existing account and contact tests in that path still pass.
- [ ] `dbt show` for `int_lead`, `int_opportunity`, and `int_lifecycle_event` returns rows from both warehouses.
- [ ] `contracts/`, `docs/`, staging models, `int_account`, `int_contact`, and every path outside the two allowed directories are unchanged. No warehouse file is committed.

## Execution notes

Implement this specification only after it has merged and issue #55 is `status:ready`. Use an `impl` worktree and schema `dev_data_009_002`. Do not merge or deploy without human approval.

Read the `dbt-development`, `using-dbt-for-analytics-engineering`, and `data-modeling` skills. Read the lead, opportunity, and lifecycle-event sections of `docs/data-model/entities.md`, `docs/data-model/decisions.md`, and `docs/data-model/source-mapping.md`, the lifecycle-event column contract in `docs/data-model/metric-contract.md`, and the YAML for `stg_hubspot__lead`, `stg_hubspot__deal`, `int_account`, and `int_contact` before writing SQL.

From `warehouse/dbt/`, use `dbt show --limit 5` on `stg_hubspot__lead`, `stg_hubspot__deal`, `int_account`, and `int_contact` against `dev_data_003`. Confirm the column names this specification selects. Repeat that check against `dev_data_004` before calling validation complete.

Validation runs from `warehouse/dbt/` against each warehouse file:

```bash
export EVE_DBT_SCHEMA=dev_data_009_002
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_003
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select +int_lead +int_opportunity +int_lifecycle_event path:tests/intermediate
.venv/bin/dbt show --profiles-dir . --select int_lead --limit 5
.venv/bin/dbt show --profiles-dir . --select int_opportunity --limit 5
.venv/bin/dbt show --profiles-dir . --select int_lifecycle_event --limit 5
```

Repeat the build and the three `dbt show` commands with `EVE_DBT_DUCKDB_PATH` pointed at `data/warehouse/dev_data_004`. If a warehouse file is absent, create it through the merged DATA-006 generate and load path, and do not commit it.

The `+` selector builds the staged parents and the account and contact models into the empty schema. Do not select the whole project. A difference between a conformed result and the identity, history, or lifecycle rules is a stop. Do not make a test pass by dropping rows or by changing a staging model, `int_account`, `int_contact`, or a contract.
