---
id: DATA-005
title: Validate Generated Data
type: implementation
agent: data-engineer
skills:
  - data-quality
  - data-generation
  - data-modeling
priority: high
components:
  - data-generation
  - contracts
dependencies:
  - DATA-004
requires_approval: true
allowed_paths:
  - tests/integration/
excluded_paths:
  - data-generation/
  - contracts/
  - warehouse/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - docs/
  - specs/
  - tests/e2e/
contracts:
  changes_required: false
  affected_contracts: []
testing:
  component_tests: false
  integration_tests: true
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

Validate the synthetic GTM datasets against the merged source contracts and the generation behavior those datasets claim to implement. The work product is an automated validation suite, a data-quality report, a defect list a later change can reproduce, and a written record of the assumptions the checks use.

The suite reads `contracts/source/` and the output of the existing generator. It does not change either one.

## Business context

GitHub issue #6 (`DATA-005 — Validate Generated Data`) depends on DATA-004. DATA-004 is merged on `main` and GitHub issue #5 is closed. The physical source schemas are the contract files under `contracts/source/`. The generator, the baseline sampler, the scenario population, and the loader are in `data-generation/`.

The issue names `data-quality-reviewer`. The workflow has one owning agent per issue, and `data-quality` is a skill of that agent. This specification assigns `data-engineer`, the owner of generated source data. The implementation reports defects with enough detail to reproduce them and leaves the generator unchanged.

The company is a fictional AI-native B2B SaaS vendor. The customer is a plaintiff law firm. The lifecycle the sources support is Lead → Opportunity → Customer → Adoption → Renewal. This task does not define pipeline, bookings, ARR, retention, or adoption metrics, and it does not derive `customer_converted` or `adoption_reached`.

`contracts/source/` is normative for field names, types, nullability, keys, relationships, timestamps, status values, lifecycle signals, and ingestion metadata. Where this specification summarizes a contract rule, the merged YAML file wins. `contracts/source/README.md` is the cross-entity rule set. DATA-003 and DATA-004 state the generation behavior the committed datasets claim. A dataset that breaks one of those published generation rules is a defect even when the row is still contract-legal.

DATA-002, DATA-003, and DATA-004 assign this issue the validation of generated records. Their component tests remain in `data-generation/tests/`. This suite is independent of `eve_data_generation.validate`.

## Scope

The implementation adds the integration suite, the report, and the assumption notes listed under Deliverables. It covers the ten checks in GitHub issue #6:

1. Schema compliance for every source entity.
2. Uniqueness of each entity's `observation_key`.
3. Foreign-key relationships, including conditional parents and company agreement.
4. Required-field completeness, with legal nulls left as nulls.
5. Lifecycle transitions for leads, deals, and subscriptions.
6. Temporal consistency, including the in-effect observation and late ingestion.
7. Booking, contract, and subscription consistency.
8. Product usage and outcome relationships.
9. Reproducibility of the committed datasets.
10. Distributions and the edge cases the committed datasets claim to contain.

`components` lists `data-generation` and `contracts` because the suite tests that boundary. A specification that lists more than one component requires integration tests, so `testing.integration_tests` is true. `contracts.changes_required` is false. The files this task writes are under `tests/integration/` only.

`testing.component_tests` is false. This task does not add tests under `data-generation/tests/` and does not treat those tests as the oracle. `testing.end_to_end_tests` is false. dbt, Hex, and Omni are later work.

Later issues own the work in the table below.

| Issue | Owns |
|---|---|
| DATA-001 | Canonical model. Merged. This task reads it and does not change it. |
| DATA-002 | Source contracts. Merged. This task reads `contracts/source/` and does not change it. |
| DATA-003 | Baseline generators, `config/default.yaml`, `config/test.yaml`, and schema `dev_data_003`. Merged. This task generates those datasets and does not edit the sampler. |
| DATA-004 | Named GTM lifecycle journeys, `config/scenarios.yaml`, `config/scenarios-test.yaml`, and schema `dev_data_004`. Merged. This task generates those datasets and does not edit the journeys. |
| DATA-005 | The validation suite, the data-quality report, the defect list, and the assumption notes. |
| Later warehouse work | dbt sources, staging, intermediate models, and marts, owned by `analytics-engineer`. |
| Later analytics work | Hex and Omni assets, owned by `analyst`. |

Orchestration workflows, infrastructure provisioning, and deployment are outside this task.

## Deliverables

The implementation adds files under `tests/integration/` only.

- `tests/integration/generated_data/`, the suite that generates the four committed datasets, checks them, loads them, and writes the report.
- `tests/integration/generated_data/README.md`, the run instructions, the oracle, and the difference between a defect and a recommendation.
- `tests/integration/generated_data/ASSUMPTIONS.md`, the validation assumptions in this specification.
- `tests/integration/generated_data/DATA-005-report.md`, the committed data-quality report. It has no wall-clock timestamp.
- One sentence in `tests/integration/README.md` pointing at `generated_data/`. The rest of that file stays as it is.

The suite invokes the existing commands from a checkout where `data-generation` is installed editable with its `dev` extra:

```bash
python3 -m pip install -e "data-generation[dev]"
python3 -m eve_data_generation generate --config data-generation/config/<file>.yaml --output <temp directory>
python3 -m eve_data_generation load --config data-generation/config/<file>.yaml --dataset-dir <temp directory> --warehouse <temp duckdb file>
python3 -m pytest tests/integration/generated_data
```

Paths are from the repository root. The suite passes `--output`, `--dataset-dir`, and `--warehouse`. It does not write `data-generation/output/` and it does not write `data-generation/output/warehouse/dev_data_003`.

The suite parses the contract YAML itself. It does not call `eve_data_generation.validate`. It does not add a Python dependency. PyYAML, DuckDB, and pytest are the dependencies already declared by `data-generation`.

## Datasets

The suite validates these four committed configurations. Each run is one `delivery_id`, `dlv_<seed>`, shared by the manifest and every row.

| Configuration | Population | Seed | Window | Load schema |
|---|---|---|---|---|
| `data-generation/config/default.yaml` | Baseline sampler | `1003` | `2024-01-01` through `2025-07-01` | `dev_data_003` |
| `data-generation/config/test.yaml` | Baseline sampler | `7` | `2024-03-01` through `2024-04-14` | `dev_data_003` |
| `data-generation/config/scenarios.yaml` | Scenario population | `1004` | `2024-01-01` through `2025-07-01` | `dev_data_004` |
| `data-generation/config/scenarios-test.yaml` | Scenario population | `4004` | Longer than 180 days and shorter than the scenario development window | `dev_data_004` |

`default.yaml` spans at least 18 months. The two scenario files set every journey count to 1. A committed file that disagrees with this table is a defect. The suite does not edit the file.

Baseline checks apply to `default.yaml` and `test.yaml`. Scenario checks apply to `scenarios.yaml` and `scenarios-test.yaml`. Contract checks, temporal checks, reproducibility, and the load read-back apply to all four.

The load uses a temporary DuckDB file per dataset. The schema name inside that file is the schema in the table. A second load of `test.yaml` into the same temporary file replaces the table contents. The suite deletes its temporary files. It does not create `dev_data_005` and it does not add a `schema` key to a baseline file.

## Oracle and results

A contract check reads the merged YAML and `contracts/source/README.md`. A generation check reads the published rules in DATA-003, DATA-004, and `data-generation/README.md` that this specification restates. The generator's own validator is not a source of truth. A row the contract allows and the generator's validator would reject is still valid here. Identifier shape is the stated case: the contract accepts any non-empty source identifier, and shape is an assumption.

Each failed check is a defect. The report records, for every defect:

- the configuration path, seed, and generate command
- the check name
- the contract file and rule sentence, or the generation rule in this specification
- the entity, the `observation_key`, and the field
- the actual value

A recommendation is a contract-legal pattern worth a later generator change. Recommendations do not fail the suite. The report may contain recommendations when every check passes.

The intentional cases under Edge cases are valid source data. The suite records them as present. It does not report them as defects and it does not drop the rows.

`pytest` exits non-zero when any defect exists. The report is still written. Acceptance of this issue requires that command to exit zero, which is the issue criterion that the datasets conform. A failing suite does not authorize an edit under `data-generation/`, `contracts/`, or `docs/`. Those paths stay unchanged, and a human decides any follow-up correction.

## Schema compliance

For every entity in the `contracts/source/` inventory, each dataset has one JSON Lines file named `<source_system>_<source_entity>.jsonl`. Apollo and Clay files are absent. Every committed dataset contains at least one row of every entity.

A row's keys are exactly that entity's `fields` plus its `ingestion` fields. The suite rejects an extra column and a missing column. The forbidden extras include canonical surrogate keys, every `surviving_*` link, `commercial_status`, `effective_start`, `effective_end`, `is_current`, `customer_converted`, `adoption_reached`, a `lifecycle_event` payload, `is_deleted`, and any ARR, net retention, pipeline coverage, win rate, or adoption-score field.

Types follow the contract type system:

- A required string is present and non-empty. A missing optional value is null, not an empty string.
- An enum value is one of that field's `allowed_values`.
- A decimal is a non-negative base-10 amount with at most two fraction digits, carried as a JSON string. A binary float is invalid. There is no currency field.
- An integer is a JSON integer. `seat_count` is at least 0. `work_unit_count` is at least 1. `spend_amount`, `impression_count`, and `click_count`, when present, are at least 0.
- A date is an ISO-8601 calendar date. A timestamp is an ISO-8601 UTC timestamp.
- `email_normalized`, when present, is lowercase and trimmed. `primary_domain`, when present, is a lowercase host with no scheme and no path.
- `source_system` equals the contract's `source_system`.

`hubspot_lifecycle_stage`, `practice_focus`, `plan_code`, `workflow_code`, `workflow_name`, `state`, `owner_name`, and display names stay open strings. `hubspot_lifecycle_stage` is not limited to `prospect`, `customer`, or `former_customer`.

`manifest.json` records the seed, the configuration file name, `start_date`, `end_date`, `delivery_id`, and the row count of each entity. Those counts match the files. The manifest has no wall-clock timestamp. One run uses one `delivery_id`.

## Keys

The row key is the contract `observation_key`. It is unique inside the entity.

Observation history may repeat a source identifier. `observed_at` distinguishes those rows. A repeated source identifier on an observation entity is not a duplicate primary key. Current entities and immutable entities whose `observation_key` is the source identifier have one row per source identifier. Campaign performance is unique on `marketing_campaign_id` plus `performance_date`.

`quote_number`, `contract_number`, `subscription_number`, `booking_number`, `campaign_code`, and `workflow_code` are stable across observations of one source identifier and unique across source identifiers of that entity.

A second payload at an existing `observation_key` is a duplicate key. One generate run does not emit a replay, and it does not emit two current rows for one source identifier.

## Foreign keys

A relationship value, when present, equals a source identifier emitted in the same dataset. A required relationship is present. An omitted optional parent stays valid.

Conditional requirements:

- A lead's `hubspot_deal_id` is present when `emitted_event` is `lead_converted`, and null on every other observation of that lead.
- A deal observation with `opportunity_type` `new_business` has a null `dealhub_subscription_id`. An observation with `expansion` or `renewal` has one, and that subscription's `hubspot_company_id` equals the deal's.
- A touch has `marketing_campaign_id` and at least one of `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_company_id`.
- An activity has at least one of `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_deal_id`.

The observation in effect at a timestamp is the row for that source identifier whose `observed_at` is the latest at or before the timestamp. If no such row exists, a rule that needs one fails.

Company agreement:

- When a deal observation includes `hubspot_contact_id`, the contact observation in effect at the deal's `observed_at` has the same `hubspot_company_id`.
- When an activity or a touch includes `hubspot_company_id` and another parent that has a company, the company identifiers agree, using the parent observation in effect at `occurred_at`. A deal has a company. A contact or a lead has a company when that observation has `hubspot_company_id`. A parent with no company leaves the activity or touch company unconstrained.
- An activity that cites a deal fails when no observation of that deal is in effect at `occurred_at`.
- A quote's `hubspot_company_id` equals the company on the deal observation in effect at the quote's `observed_at`.
- A contract's company matches the cited deal and the cited quote.
- A subscription's `hubspot_company_id` matches the cited contract. `dealhub_contract_id` is stable across that subscription's observations.
- A booking's company matches the cited deal, contract, and subscription. All four booking parents are present.

A lead and a company remain different source records. Conversion cites `hubspot_deal_id` and does not turn the lead into a company. A product user has no contact identifier. A product-user email does not create a contact. The Product firm contract has no `hubspot_company_id`. Equal `primary_domain` values are the only cross-system firm match, and the contracts do not require that match. Duplicate emails and duplicate domains remain valid.

At most one deal cites a given lead. A lead cites at most one deal. At most one contract cites a given quote. At most one contract cites a given deal.

## Completeness

A field with `nullable: false` is present and non-null. Required strings are non-empty. Enum fields use their `allowed_values`.

A null optional field meets the completeness rule. Null is not zero, and it is not an empty string. The suite does not fill null amounts, null measures, null emails, or null domains.

## Lifecycle transitions

Lead observations for one `hubspot_lead_id` are ordered by `observed_at`.

- The first observation has `status` `new`, `emitted_event` `lead_created`, and `observed_at` equal to `created_at`. `created_at` is stable. Exactly one `lead_created` exists.
- `status` `qualified` has `emitted_event` `lead_qualified`. `status` `disqualified` has `emitted_event` `lead_disqualified`. `status` `converted` has `emitted_event` `lead_converted`. Each of those three events occurs at most once.
- `status` `working` has a null `emitted_event`.
- `qualified` and `disqualified` do not both occur.
- `lead_converted` is preceded by `lead_qualified` at an earlier `observed_at`.
- A disqualified lead has no `hubspot_deal_id`.
- A lead with a null company and a null contact is not `converted`.
- `hubspot_lead_id` on a deal is stable when it is present. A deal comes from at most one lead.

Deal observations for one `hubspot_deal_id` are ordered by `observed_at`.

- The first observation has `stage` `discovery`, `emitted_event` `opportunity_opened`, and `observed_at` equal to `created_at`. Exactly one `opportunity_opened` exists. That opening is not `opportunity_stage_changed`.
- `created_at` and `hubspot_company_id` are stable.
- An observation whose stage differs from the previous observation and is `evaluation`, `proposal`, or `negotiation` has `emitted_event` `opportunity_stage_changed`.
- An observation whose stage is `closed_won` has `emitted_event` `opportunity_won`. An observation whose stage is `closed_lost` has `emitted_event` `opportunity_lost`. Each occurs at most once. A deal does not have both.
- An observation whose stage equals the previous observation has a null `emitted_event`. Amount, close date, owner, forecast, and `opportunity_type` may still change.

Subscription observations:

- `subscription_renewed` and `subscription_expanded` have `status` `active`. They may repeat.
- `status` `pending` has a null `emitted_event`. `status` `active` has a null `emitted_event` unless the observation is a renewal or an expansion.
- `subscription_churned` occurs at most once. That observation has `status` `churned`, and a `churned` observation has `emitted_event` `subscription_churned`.
- No booking for that subscription has `booked_at` at or after the churn `observed_at`.

Quotes, contracts, bookings, activities, touches, campaign rows, campaign-day rows, firms, users, workflows, usage, and outcomes do not carry an `emitted_event` column. Usage is the usage row. It is not also a lifecycle-event payload.

## Temporal consistency

`observed_at` is at or after `created_at` where both exist. For one source identifier on an observation entity, `observed_at` values are unique, so the ordered observations strictly increase.

`end_date` is on or after `start_date` on every contract observation. `term_end` is on or after `term_start` on every subscription observation. An outcome's `occurred_at` is at or after the cited usage `occurred_at`.

`ingested_at` may be later than the business timestamp. Late delivery is valid. The business timestamp is `observed_at` when the row has it, otherwise `occurred_at`, otherwise `booked_at`. For a campaign-day row, the business timestamp is `performance_date` at `00:00:00` UTC. A current campaign, Product firm, or AI workflow has no business-timestamp field. Its check is that `ingested_at` falls inside the configured window.

On every dataset, each business timestamp, each business date, and each `ingested_at` falls inside the inclusive configured window. Where a row has a business timestamp, `ingested_at` is at or after it. A later `ingested_at` does not change `created_at`, `observed_at`, `occurred_at`, `booked_at`, or `performance_date`.

On a scenario dataset the same bound is an equality, except for the late immutable rows. A row with `observed_at`, `occurred_at`, or `booked_at` has `ingested_at` equal to that timestamp unless it is one of the late immutable rows. A campaign-day row has `ingested_at` equal to `performance_date` at `00:00:00` UTC. Current rows stay inside the window and are not part of that equality.

Dates have no time. Timestamps are UTC.

## Bookings, contracts, and subscriptions

Contract creation follows the winning observation. That observation has `emitted_event` `opportunity_won`, `stage` `closed_won`, and `opportunity_type` `new_business`. It has exactly one contract, and the contract's `hubspot_deal_id` is that deal. The quote observation in effect at the contract's first `observed_at` has `status` `accepted`, a non-null `quoted_amount`, and the same `hubspot_deal_id`. A baseline dataset that emits only the accepted quote still passes.

A deal whose winning observation is `expansion` or `renewal` has no contract. A later observation of the winning deal may change `opportunity_type` without adding or removing the contract. The deal observation in effect at a later contract `observed_at` leaves that decision unchanged. A later observation of the same contract may change `total_contract_value` or `end_date`. That observation is not a second contract.

A new-business win has at least one subscription on its contract and exactly one booking with `booking_type` `new_business` on that deal. The booking cites that deal, that contract, and a subscription of that contract. `booked_at` has a deal observation in effect, and `booking_type` equals `opportunity_type` on that observation. `booking_amount` is not negative.

`booking_amount` stays on the booking. `recurring_amount` and `billing_frequency` stay on the subscription. The suite does not require HubSpot `amount`, `quoted_amount`, `total_contract_value`, `booking_amount`, `recurring_amount`, and `spend_amount` to be equal. It does not annualize `recurring_amount`. It does not require `seat_count` to equal the number of product users. `expected_close_date` and contract `start_date` may differ. Company `owner_name` and deal `owner_name` may differ.

`quoted_amount` may be null while `status` is `draft`. The non-null amount rule for a quote is the accepted quote cited by a contract, at the contract's first `observed_at`.

Churn does not create a booking and does not use a negative amount. The earlier new-business booking remains.

## Product usage

A usage row cites a product user, a Product firm, and an AI workflow that exist in the dataset. `product_firm_id` is the firm on the user observation in effect at `occurred_at`. `work_unit_count` is at least 1. Usage has no commercial amount.

At most one outcome cites a usage. `product_usage_source_id` is unique among outcomes. The outcome's user, firm, and workflow equal the usage, and its `occurred_at` is at or after the usage. A usage with no outcome is valid. The suite does not derive `adoption_reached`.

`seat_count` does not constrain `work_unit_count` or the number of users.

## Reproducibility

For each of the four configurations, two generate commands with the same file and an explicit output directory produce the same file bytes, including `manifest.json` and row order. The seed is the only source of randomness. The generator is not asked to read the wall clock, and the report has no validation timestamp.

The suite records the four committed seeds. It does not add a fifth configuration.

## Distributions

Baseline distributions use `default.yaml` and `test.yaml` only. Scenario files keep the baseline count and rate keys because the loader requires them. The scenario population does not use those keys to size journeys. The suite does not apply the baseline count and rate checks to a file that contains `journeys`.

Count checks, as distinct entities:

| Observed count | Equals |
|---|---|
| HubSpot companies | `account_count` |
| Contacts | `account_count` times `contacts_per_account` |
| Leads | `lead_count` |
| Campaigns | `campaign_count` |
| Activities | `activity_count` |
| Touches | `touch_count` |
| Product firms | Companies that have a won new-business deal, one firm each |
| Product users | Product firms times `product_users_per_customer` |
| Usage rows | Product users times `usage_events_per_user` |
| Campaign-day rows | `campaign_count` times the inclusive days from `start_date` through `end_date` |

Quote, contract, subscription, and booking counts are consequences of wins, expansions, renewals, and churn. They are not a second set of targets.

Latest lead status across all leads, latest stage across new-business deals, and channel across campaigns equal a largest-remainder allocation. The allocation gives each label the floor of `count * weight / total weight`, then gives each remaining count to the largest fractional part. Equal fractional parts go to the label that sorts first. The number of new-business deals equals the allocated `converted` lead count. `stage_mix` does not include expansion or renewal deals. The `closed_won` weight divided by the total `stage_mix` weight equals `opportunity_win_rate`.

`share_count(population, rate)` is the selected count for a rate. A population of 0 or a rate of 0 selects 0. A rate of 1 or more selects the whole population. Otherwise the product is rounded half up, halves away from zero, then raised to 1 when it rounds below 1, and lowered to `population - 1` when the population is greater than 1 and the product rounds to the whole population.

These observed counts equal `share_count` of the stated population:

| Rate | Population | Observed count |
|---|---|---|
| `renewal_rate` | Subscriptions | Subscriptions with at least one `subscription_renewed` on an `active` observation |
| `expansion_rate` | Subscriptions | Subscriptions with at least one `subscription_expanded` on an `active` observation |
| `churn_rate` | Subscriptions | Subscriptions whose latest observation is `churned` with `subscription_churned` |
| `outcome_rate` | Usage rows | Usage rows cited by one outcome |
| `null_company_domain_rate` | Companies | Companies whose `primary_domain` is null |
| `orphan_lead_rate` | Leads | Leads whose latest observation has a null company and a null contact |
| `null_deal_amount_rate` | Deals | Deals whose `amount` is null |
| `single_parent_activity_rate` | Activities | Activities with exactly one parent |
| `null_performance_measure_rate` | Campaign-day rows | Rows whose `spend_amount` is null |
| `clicks_exceed_impressions_rate` | Campaign-day rows | Rows whose `click_count` and `impression_count` are both present and whose clicks exceed impressions |
| `null_user_email_rate` | Product users | Product users whose email is null |
| `company_change_rate` | Companies | Companies with more than one observation |

When `activity_count` is at least 2, the activities with a null `hubspot_deal_id` number `activity_count // 2`, and the other activities cite a deal. Both committed baseline files set `activity_count` to at least 2 and `touch_count` to at least 1.

`duplicate_contact_email_rate` and `domain_match_rate` are reported as observed count beside `share_count`. They do not fail the suite by themselves. Duplicate contacts are produced by copying one source email onto the selected recipients, so the contacts that share an email include that source when the source was not selected. A customer firm whose company has a null domain cannot match on `primary_domain`. The report may recommend a difference. The edge-case presence checks below still apply.

Every baseline dataset also contains at least one of each lead, deal, and subscription `emitted_event` value.

## Edge cases

Both baseline datasets contain each of these at least once:

- a company with a null `primary_domain`
- two contacts with the same `email_normalized` and different `hubspot_contact_id` values
- a lead with a null company and a null contact
- a deal with a null `amount`
- an activity with exactly one parent
- an activity with a null `hubspot_deal_id` and an activity that cites a deal
- a campaign-day row with a null `spend_amount`
- a campaign-day row whose `click_count` exceeds `impression_count`
- one Product firm whose `primary_domain` equals a HubSpot company, and one whose domain does not
- a product user with a null email
- an `active` subscription observation whose `emitted_event` is `subscription_renewed` or `subscription_expanded`
- a `subscription_churned` observation with no booking at or after that `observed_at`
- a `hubspot_lifecycle_stage` outside `prospect`, `customer`, and `former_customer`
- two observations of one `hubspot_company_id`

Both scenario datasets contain one instance of each journey, the domain twin, and the rows in this table. Journey companies do not share a subscription or a contract. Each has its own non-null `primary_domain`.

| Case | Rows that satisfy it |
|---|---|
| Duplicate contacts | The two contacts on the `new_business_conversion` company share `email_normalized` and keep different `hubspot_contact_id` values. |
| Merged accounts | One extra company copies that journey's `primary_domain`, uses a different `hubspot_company_id`, and has no won deal. The Product firm for that journey uses the same domain. |
| Repeated stage changes | Every forward deal has three `opportunity_stage_changed` observations. The regression deal also returns from `proposal` to `evaluation`. |
| Late-arriving events | `late_event_count` immutable rows have `ingested_at` exactly `ingest_lag_days` after `occurred_at` or `booked_at`. Committed files set both values to 1. Every other immutable row has `ingested_at` equal to `occurred_at` or `booked_at`. |
| Contract amendments | The expansion journey raises `total_contract_value` by `contract_value_increase` on a later observation of the same contract. The renewal journey moves `end_date` later by `term_days` on a later observation of the same contract. |
| Canceled subscriptions | The churn journey's latest subscription observation is `churned` with `subscription_churned`. A later contract observation is `terminated`. There is no `canceled` status. |
| Soft-deleted records | The churn journey's product user ends `inactive`. The domain twin has one lead that goes from `new` / `lead_created` to `disqualified` / `lead_disqualified` and never converts. The regression quote ends `expired`. Those rows stay in the dataset. |
| Low or declining adoption | `low_adoption` has one `case_analysis` usage and no outcome. `churn` has a later usage row with a strictly smaller `work_unit_count` than its earlier usage row. |

Converting scenario leads use `new` / `lead_created`, `working` / null, `qualified` / `lead_qualified`, then `converted` / `lead_converted`. `observed_at` strictly increases. The opening `observed_at` equals `created_at`. `hubspot_deal_id` is set only on `lead_converted`. That deal opens at the same timestamp with `discovery` and `opportunity_opened`.

Won and lost deals then follow `discovery`, `evaluation`, `proposal`, `negotiation`, and `closed_won` or `closed_lost`. `discovery` emits `opportunity_opened`. Each later open stage emits `opportunity_stage_changed`. The closing stage emits `opportunity_won` or `opportunity_lost`. `forecast_category` comes from `forecast_by_stage` for that stage. `created_at`, `hubspot_company_id`, and `hubspot_lead_id` stay stable.

`stage_regression` never reaches `closed_won` or `closed_lost`. After the opening observation the stages are `evaluation`, `proposal`, `evaluation`, `negotiation`, each with `opportunity_stage_changed`. The latest stage is `negotiation`. Its quote is `draft`, `sent`, then `expired`. The `expired` observation is after the first `proposal` and before the return to `evaluation`. The deal has no contract, subscription, booking, or Product firm.

`lost_opportunity` ends `closed_lost`. Its quote is `draft`, `sent`, then `rejected`. The rejected observation is at or before `opportunity_lost`. The deal has no contract, subscription, booking, or Product firm.

Customer journeys are `new_business_conversion`, `expansion`, `renewal`, `churn`, and `low_adoption`. Their quote observations are `draft`, `sent`, then `accepted`. `quoted_amount` may be null on `draft` and is present on `sent`, `accepted`, `rejected`, and `expired`. The accepted observation is at or before the winning deal observation. The contract's first `observed_at` is at or after that win, and the contract cites that quote. The subscription's first observation is `pending` with a null `emitted_event`. The next is `active` with a null `emitted_event`. `subscription_number`, `plan_code`, and `billing_frequency` stay stable. The company opens at `hubspot_lifecycle_stage` `prospect` and has a later observation `customer` at or after the new-business win.

Each customer company has one Product firm with the same `primary_domain`. Usage and outcomes cite that firm. The first product-user observation is at or before that firm's first usage. Usage `occurred_at` is at or after the new-business win.

`new_business_conversion` has the two shared-email contacts, no expansion deal, no renewal deal, and no churn. It includes one `call`, one `email`, and one `meeting`. Each cites the deal and the company. `occurred_at` is after the deal's `created_at` and at or before the winning `observed_at`. The firm has one usage for each workflow code except `case_analysis`, and these outcomes:

| Workflow code | Usage | Outcome |
|---|---|---|
| `case_intake` | one usage | none required |
| `document_collection` | `work_unit_count` equals the configured maximum, which is at least 2 | none required |
| `medical_record_review` | one usage | none required |
| `document_summarization` | one usage | `exported` |
| `demand_letter_generation` | one usage | `draft_completed` |
| `settlement_preparation` | one usage | `review_accepted` |

`expansion` keeps that subscription `active`, emits `subscription_expanded`, raises `seat_count` by `expansion_seat_increase` and `recurring_amount` by `expansion_recurring_increase`, and raises `total_contract_value` by `contract_value_increase` on the original contract. It adds one `expansion` booking on the expansion deal. It does not create a contract and it does not churn.

`renewal` keeps that subscription `active`, emits `subscription_renewed`, leaves `seat_count` and `recurring_amount` unchanged, and moves `term_end` and the contract `end_date` later by `term_days`. `total_contract_value` stays the same. It adds one `renewal` booking on the renewal deal. It does not create a contract and it does not churn. Committed files set `term_days` to 180, `expansion_seat_increase` to 1, `expansion_recurring_increase` to `10.00`, and `contract_value_increase` to `100.00`.

`churn` has exactly two usage rows and no outcome. Both `occurred_at` values are after the first `active` subscription observation and before churn. The earlier `work_unit_count` is the configured maximum. The later one is the configured minimum, and the maximum is greater. The new-business booking remains. No booking has `booked_at` at or after the churn observation. The contract's later observation is `terminated`. The company has `former_customer` at or after churn. One product user on the firm has a later `inactive` observation after the later usage.

`low_adoption` has one `case_analysis` usage, no outcome, an `active` subscription, and no expansion, renewal, or churn.

The domain twin is not a journey instance. It copies the `new_business_conversion` domain, has no won deal, and its disqualified lead cites that company and has no `hubspot_deal_id`. The committed lifecycle catalog includes `prospect`, `customer`, `former_customer`, and `sql`. The twin uses `sql`.

Each converting lead's company has at least one touch with `occurred_at` at or before that lead's `created_at`. The touch cites the campaign and the company and does not cite the lead. The workflow catalog on both scenario files is exactly the seven codes in the table above, plus `case_analysis` / `Case analysis`.

Scenario rows still pass the contract checks. In particular, the accepted quote is judged at the contract's first `observed_at`, so the earlier `draft` and `sent` observations stay in the dataset.

## Load read-back

For each dataset, the load command writes the schema in the dataset table into the temporary warehouse file. Table names are `src_<source_system>_<source_entity>`. Columns are the contract fields followed by the ingestion fields. Values match the JSON Lines, including nulls and exact decimals. The second load of `test.yaml` does not append a duplicate copy.

A mismatch is a defect. The suite does not edit the loader.

## Report and assumptions

`DATA-005-report.md` has one section for each of the ten checks in the issue. For every dataset it records the configuration path, seed, window, `delivery_id`, and row count of each entity. Each check is `pass` or `defect`, with the failure count. Defects use the fields under Oracle and results. The distribution section shows configured values beside observed values for the baseline files, and the journey inventory for the scenario files. The edge-case section shows each case as present or missing. Recommendations are a separate section and may be empty.

The committed report matches a fresh run. The fresh run has no wall-clock timestamp.

`ASSUMPTIONS.md` records these assumptions:

- The row key is `observation_key`. An observation entity may repeat its source identifier.
- Identifier shape is not a rejection rule. HubSpot identifiers are expected to be numeric strings, DealHub identifiers prefixed strings, and Marketing and Product identifiers opaque strings.
- Null optional values, duplicate emails, duplicate domains, clicks above impressions, and an open `hubspot_lifecycle_stage` are valid.
- Late `ingested_at` is valid. One generate run emits one `delivery_id` and does not emit a second replay row.
- Bookings and subscription fees are different fields. `seat_count` is not a user count. This suite does not compute ARR, retention, pipeline coverage, win rate, or an adoption score.
- Domain equality is not a contract rule. Scenario customer journeys still match on `primary_domain` because DATA-004 says they do.
- A canceled subscription is `churned` with `subscription_churned`. A soft-deleted record stays in the extract as `inactive`, `disqualified`, `expired`, or `rejected`.
- The edge cases in this specification are intentional. They are not defects.
- `eve_data_generation.validate` is not the oracle. A stricter generator check, including identifier shape, is a recommendation when the emitted rows still satisfy the contract.
- The duplicate-email construction and the null-domain firm swap are recorded beside `duplicate_contact_email_rate` and `domain_match_rate`.
- Apollo and Clay are outside this dataset.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/` and do not edit it.
- One owning agent, `data-engineer`, writes the suite, the report, and the assumption notes.
- Follow the data-quality skill. Checks are explicit and measurable. Failures name the row. Legal nulls, duplicates, and late rows stay in the dataset.
- Follow the data-generation skill as a review constraint. The suite does not add transformation logic, survivorship, effective dating, or canonical events to the generator.
- Use the data-modeling skill for grain, keys, and the difference between a source identifier and `observation_key`.
- Do not edit `data-generation/`, including generators, configuration, the loader, `eve_data_generation.validate`, and `data-generation/tests/`.
- Do not edit `contracts/`, `docs/`, `warehouse/`, `analytics/`, `orchestration/`, `infrastructure/`, `agent-platform/`, `specs/`, or `tests/e2e/`.
- Do not generate Apollo or Clay records, and do not add source columns.
- Human approval is required. `delivery.deployment_required` is false.
- `environment.isolated_schema` is true. The temporary warehouse file holds `dev_data_003` or `dev_data_004` for the duration of the load check. The suite does not replace the default warehouse file.
- `testing.integration_tests` is true. `testing.component_tests` and `testing.end_to_end_tests` are false.

## Acceptance criteria

- [ ] The implementation changes files only under `tests/integration/`. `data-generation/`, `contracts/`, and `docs/` are unchanged.
- [ ] `python3 -m pytest tests/integration/generated_data` generates all four committed configurations through the existing generate command, using temporary output and warehouse paths.
- [ ] Every dataset conforms to the contract inventory: column set, types, nullability, allowed values, ingestion envelope, and the absence of canonical columns. Apollo and Clay are absent. Each dataset has at least one row of every source entity.
- [ ] `observation_key` is unique. Observation entities may repeat a source identifier. Document numbers are stable and unique.
- [ ] Relationship values point at emitted source identifiers. Conditional parents, company agreement, and the in-effect rule hold. Optional parents may be absent. Duplicate emails and duplicate domains are present and are not reported as defects.
- [ ] Required fields are complete. Legal nulls remain null.
- [ ] Lead, deal, and subscription lifecycle transitions match this specification. Won and lost are mutually exclusive. Churn occurs at most once and adds no later booking.
- [ ] Temporal order holds, including `observed_at`, contract and subscription dates, outcome time, the configured window, and `ingested_at` at or after the business timestamp. Late ingestion is valid.
- [ ] A new-business win has one contract, an accepted quote in effect at that contract's first `observed_at`, at least one subscription, and one new-business booking. Expansion and renewal do not create a contract. `booking_type` matches the deal in effect at `booked_at`. Booking fields and subscription fee fields stay on their own entities.
- [ ] Usage cites the user, firm, and workflow required by the contract. The firm matches the user in effect at `occurred_at`. An outcome matches its usage, is not earlier than that usage, and is the only outcome for that usage.
- [ ] Two generations of each committed configuration produce identical output bytes. The manifest and the report have no wall-clock timestamp.
- [ ] Baseline counts, mixes, and the `share_count` rates in this specification match the committed files. Both baseline files contain the baseline edge cases and every lead, deal, and subscription `emitted_event`.
- [ ] Both scenario files contain one of each journey, the domain twin, the scenario sequences, and the edge-case table. Baseline count and rate keys are not applied to those files as population targets.
- [ ] The load read-back matches the JSON Lines in a temporary warehouse file, and a second load of `test.yaml` replaces the tables. The default warehouse file is untouched.
- [ ] `DATA-005-report.md` records each check, the distributions, the edge cases, and any recommendations. `ASSUMPTIONS.md` records the assumptions in this specification. A fresh run matches the committed report.
- [ ] The suite exits zero. Defects are not cleared by editing the generator, the contracts, or the canonical model.

## Execution notes

Implement this specification only after it has merged and the issue label is `status:ready`. Use an `impl` worktree. Leave this specification unchanged unless a human changes the approved requirements.

Read the data-quality skill before writing the checks, the report, and the defect records. Read the data-generation skill as a constraint on what the generator is allowed to own. Read the data-modeling skill before treating a source identifier as a primary key. Read `contracts/source/README.md` and each entity YAML as the schema. Read `specs/DATA-003-implement-synthetic-data-generators.md`, `specs/DATA-004-implement-gtm-lifecycle-scenarios.md`, and `data-generation/README.md` for the generation behavior this suite checks. Do not edit those files.

The suite calls the public generate and load commands. It parses the contracts itself. It does not import `eve_data_generation.validate`.

If a check fails, write the defect in the report and stop. Do not change the generator to make the suite pass. A red suite does not meet the acceptance criteria. The implementation pull request still includes the report, and a human decides whether a later issue corrects the data.

Validation of this task is `python3 -m pytest tests/integration/generated_data` from the repository root, plus a review of the report against the acceptance criteria. The command needs the editable `data-generation[dev]` install. It does not need a remote warehouse. No end-to-end test or deployment is required. Human approval is required before merge.
