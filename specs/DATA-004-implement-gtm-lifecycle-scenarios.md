---
id: DATA-004
title: Implement GTM Lifecycle Scenarios
type: implementation
agent: data-engineer
skills:
  - data-generation
  - data-quality
priority: high
components:
  - data-generation
dependencies:
  - DATA-003
requires_approval: true
allowed_paths:
  - data-generation/
excluded_paths:
  - contracts/
  - warehouse/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - tests/
  - docs/
  - specs/
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

Implement named, reproducible GTM lifecycle scenarios that connect the synthetic HubSpot, DealHub, Marketing, and Product records into coherent customer journeys.

The work product lives under `data-generation/`. The scenario population composes the merged source contracts. It does not add source columns, derive canonical lifecycle events, or build warehouse models.

## Business context

GitHub issue #5 (`DATA-004 — Implement GTM Lifecycle Scenarios`) depends on DATA-003. DATA-003 is merged on `main` and GitHub issue #4 is closed. The generator package, baseline sampler, JSON Lines writer, and `dev_data_003` loader are already in `data-generation/`. `build_dataset(config, population=None)` calls `baseline_population` unless the caller supplies another population. This issue supplies the named journeys through that hook.

The physical source schemas are the contract files under `contracts/source/`. The lifecycle those sources support is Lead → Opportunity → Customer → Adoption → Renewal. The company is a fictional AI-native B2B SaaS vendor. The customer is a plaintiff law firm. This task does not define pipeline, bookings, ARR, retention, or adoption metrics, and it does not derive `customer_converted` or `adoption_reached`.

`contracts/source/` is normative for field names, types, nullability, keys, relationships, timestamps, status values, lifecycle signals, and ingestion metadata. Where this specification summarizes a contract rule, the merged YAML file wins.

DATA-003 emits a seeded population with independent rates. This task emits prescribed journeys. `config/default.yaml` and `config/test.yaml` stay the baseline population.

## Scope

The implementation adds the scenario population, scenario configuration, component tests, and the README section listed under Deliverables. It covers:

1. Lead-to-customer conversion, including a qualified lead that becomes a deal.
2. Opportunity stage history, including more than one stage change and one path that returns to an earlier open stage.
3. Won and lost deal outcomes.
4. Quote history, a new-business booking, and later observations of the same contract.
5. New business, expansion, renewal, and churn as separate journeys.
6. Product adoption and AI workflow usage on the customer account, joined by `primary_domain`.
7. Account engagement through HubSpot activities, and customer health expressed only by the source rows named in this specification.
8. The edge cases in GitHub issue #5, represented with the existing contract fields listed under Edge cases.

`components` lists `data-generation` only. A specification that lists more than one component requires integration tests. This specification lists one, so `testing.integration_tests` is false. Loading the scenario dataset into `dev_data_004` uses the existing loader. It is not a `dbt`, `infrastructure`, or `orchestration` change.

Later issues own the work in the table below.

| Issue | Owns |
|---|---|
| DATA-001 | Canonical model. Merged. This task consumes it and does not change it. |
| DATA-002 | Source contracts. Merged. This task reads `contracts/source/` and does not change it. |
| DATA-003 | Baseline generators, `config/default.yaml`, `config/test.yaml`, and schema `dev_data_003`. Merged. This task calls those generators and does not replace the baseline sampler. |
| DATA-004 | Named GTM lifecycle journeys, journey configuration, journey tests, and the edge-case rows in this specification. |
| DATA-005 | The validation suite, data-quality report, and defect review for generated data. |
| Later warehouse work | dbt sources, staging, intermediate models, and marts. |
| Later analytics work | Hex and Omni assets. |

Orchestration workflows, infrastructure provisioning, and deployment are outside this task.

## Deliverables

The implementation adds and updates files under `data-generation/` only.

- A scenario population selected by `build_dataset` when the loaded configuration contains `journeys`. The CLI stays `python3 -m eve_data_generation generate --config <file>` and `python3 -m eve_data_generation load --config <file>`. No new subcommand is required.
- `data-generation/config/scenarios.yaml`, the development journey dataset.
- `data-generation/config/scenarios-test.yaml`, the dataset the scenario component tests generate and load.
- Component tests under `data-generation/tests/`.
- A scenario section in `data-generation/README.md` that documents the journey names, the configuration keys added by this task, the edge-case assumptions in this specification, the generate command, the load command, the test command, and schema `dev_data_004`.

`data-generation/.gitignore` already ignores `data-generation/output/`. Scenario datasets and the local warehouse file are written there and are not committed.

`config/default.yaml` and `config/test.yaml` remain unchanged. When `journeys` is absent, `build_dataset` still calls `baseline_population`.

## Scenario catalog

Each journey count is a positive integer. Both committed scenario files set every count to 1. Each instance uses its own HubSpot company, its own non-null `primary_domain`, and its own contacts, leads, and deals. Customer journeys do not share a subscription or a contract.

A customer journey is one whose company has a new-business win. Those journeys are `new_business_conversion`, `expansion`, `renewal`, `churn`, and `low_adoption`. `lost_opportunity` and `stage_regression` are not customer journeys.

The domain twin described under Edge cases is an additional company. It is not one of the seven journey instances.

### Sequences

Converting leads use this status sequence. `observed_at` strictly increases. The opening `observed_at` equals `created_at`.

| Order | `status` | `emitted_event` |
|---|---|---|
| 1 | `new` | `lead_created` |
| 2 | `working` | null |
| 3 | `qualified` | `lead_qualified` |
| 4 | `converted` | `lead_converted` |

`hubspot_deal_id` is set only on the `lead_converted` observation. That deal's `created_at` and opening `observed_at` equal the `lead_converted` `observed_at`. The deal opens at `discovery` with `opportunity_opened`.

Won and lost deals then follow the forward stage list. Each step is a new observation. `forecast_category` comes from `forecast_by_stage` for that stage.

| Stage | `emitted_event` |
|---|---|
| `discovery` | `opportunity_opened` |
| `evaluation` | `opportunity_stage_changed` |
| `proposal` | `opportunity_stage_changed` |
| `negotiation` | `opportunity_stage_changed` |
| `closed_won` or `closed_lost` | `opportunity_won` or `opportunity_lost` |

A deal has at most one of `opportunity_won` and `opportunity_lost`. `created_at`, `hubspot_company_id`, and `hubspot_lead_id` stay stable across that deal's observations.

Quote observations of one `dealhub_quote_id` use a strictly increasing `observed_at`. `quote_number` stays stable. `quoted_amount` may be null while `status` is `draft`. `sent`, `accepted`, `rejected`, and `expired` observations carry a non-null `quoted_amount`.

| Journey | Quote sequence |
|---|---|
| Customer journeys | `draft`, then `sent`, then `accepted` |
| `lost_opportunity` | `draft`, then `sent`, then `rejected` |
| `stage_regression` | `draft`, then `sent`, then `expired` |

The accepted observation is at or before the winning deal observation. The contract's first `observed_at` is at or after that winning observation. The contract cites that quote. Lost and regression deals have no contract and no booking.

The DATA-003 component validator rejects a new-business win when any quote row for that deal has a status other than `accepted`. Quote history requires the earlier `draft` and `sent` rows. Change that check so the quote observation in effect at the contract's first `observed_at` has `status` `accepted` and a non-null `quoted_amount`. Baseline datasets emit only the accepted observation and still pass.

A new-business win creates one subscription. Its first observation has `status` `pending` and a null `emitted_event`. The next observation has `status` `active` and a null `emitted_event`. `subscription_number`, `plan_code`, and `billing_frequency` stay stable across later observations of that subscription. `term_end` is on or after `term_start`.

Each customer company opens with `hubspot_lifecycle_stage` `prospect` and has a later observation with `hubspot_lifecycle_stage` `customer` at or after the new-business win. Those values are source labels. The row does not contain `commercial_status`.

Each customer company has one Product firm. The firm's `primary_domain` equals the company's `primary_domain`. Both values are non-null lowercase hosts. Usage and outcomes for that journey cite that firm. The first product-user observation is at or before that firm's first usage `occurred_at`. Usage `occurred_at` is at or after the new-business win.

`seat_count` is not the number of product users on the firm. Deal `amount`, `quoted_amount`, `total_contract_value`, `booking_amount`, and `recurring_amount` are drawn as separate amounts. The scenario does not copy one field onto another. `expected_close_date` and contract `start_date` are chosen independently.

### `new_business_conversion`

One converting lead, one new-business deal that ends `closed_won`, the accepted-quote sequence, one contract whose first `status` is `active`, the pending-then-active subscription, and one booking with `booking_type` `new_business`. The booking cites that deal, that contract, and that subscription. `booked_at` is at or after the winning `observed_at`.

The company has exactly two contacts. They share one non-null `email_normalized` and have different `hubspot_contact_id` values. The deal cites one of them. The company has no expansion deal, no renewal deal, and no `subscription_churned` observation.

The journey includes one call, one email, and one meeting. Each activity cites the deal and the company. `occurred_at` is after `created_at` on the deal and at or before the winning `observed_at`.

The firm has one usage for each workflow code except `case_analysis`, and these outcomes:

| Workflow code | Usage | Outcome |
|---|---|---|
| `case_intake` | one usage | none required |
| `document_collection` | `work_unit_count` equals the configured maximum, which is at least 2 | none required |
| `medical_record_review` | one usage | none required |
| `document_summarization` | one usage | `exported` |
| `demand_letter_generation` | one usage | `draft_completed` |
| `settlement_preparation` | one usage | `review_accepted` |

Each outcome cites its usage. Outcome `occurred_at` is at or after that usage `occurred_at`. The user, firm, and workflow on the outcome equal the usage.

### `expansion`

The journey includes its own new-business win, contract, subscription, new-business booking, and domain-matched firm. It then opens a second deal with `opportunity_type` `expansion` that cites that subscription. The expansion deal uses the forward stage list and ends `closed_won`.

After that win, the same subscription gains an observation with `status` `active`, `emitted_event` `subscription_expanded`, `seat_count` equal to the prior `seat_count` plus `expansion_seat_increase`, and `recurring_amount` equal to the prior `recurring_amount` plus `expansion_recurring_increase`. The same contract gains an observation with `status` `active` and `total_contract_value` equal to the prior value plus `contract_value_increase`. `contract_number` is unchanged. One booking with `booking_type` `expansion` cites the expansion deal, the original contract, and the same subscription. Its `booked_at` is at or after the expansion win.

The expansion deal does not create a contract. The latest subscription `status` is `active`. The subscription has no `subscription_churned` observation.

### `renewal`

The journey includes its own new-business win, contract, subscription, new-business booking, and domain-matched firm. It then opens a second deal with `opportunity_type` `renewal` that cites that subscription. The renewal deal uses the forward stage list and ends `closed_won`.

After that win, the same subscription gains an observation with `status` `active`, `emitted_event` `subscription_renewed`, and `term_end` equal to the prior `term_end` plus `term_days`. `seat_count` and `recurring_amount` stay equal to the prior observation. The same contract gains an observation with `status` `active`, the same `total_contract_value`, and `end_date` equal to the prior `end_date` plus `term_days`. `end_date` remains on or after `start_date`. One booking with `booking_type` `renewal` cites the renewal deal, the original contract, and the same subscription. Its `booked_at` is at or after the renewal win.

The renewal deal does not create a contract. The latest subscription `status` is `active`. The subscription has no `subscription_churned` observation.

### `churn`

The journey includes its own new-business win, contract, subscription, new-business booking, and domain-matched firm. The firm has exactly two usage rows and no outcome. Both `occurred_at` values are after the subscription's first `active` observation and before churn. The earlier `work_unit_count` equals the configured maximum. The later `work_unit_count` equals the configured minimum. The committed range has a minimum of at least 1 and a maximum strictly greater than the minimum.

A later subscription observation has `status` `churned` and `emitted_event` `subscription_churned`. No booking for that subscription has `booked_at` at or after that `observed_at`. The earlier new-business booking remains. A later contract observation has `status` `terminated` and `observed_at` at or after the churn observation. The company gains an observation with `hubspot_lifecycle_stage` `former_customer` at or after churn. One product user on the firm has a later observation with `status` `inactive` and `observed_at` after the later usage row.

### `lost_opportunity`

One converting lead and one new-business deal that uses the forward stage list and ends `closed_lost`. The quote sequence ends `rejected`. The rejected observation is at or before `opportunity_lost`. The deal has no contract, no subscription, and no booking. The company has no Product firm.

### `stage_regression`

One converting lead and one new-business deal that never reaches `closed_won` or `closed_lost`. After the opening observation, the stage order is `evaluation`, `proposal`, `evaluation`, `negotiation`. Each of those four observations has `emitted_event` `opportunity_stage_changed`. The latest stage is `negotiation`.

The quote sequence ends `expired`. The `expired` observation falls after the first `proposal` observation and before the return to `evaluation`. The deal has no contract, no subscription, and no booking. The company has no Product firm.

### `low_adoption`

The journey includes its own new-business win, contract, active subscription, new-business booking, and domain-matched firm. The firm has one usage of `case_analysis` and no outcome. The latest subscription `status` is `active`. The company has no expansion deal, no renewal deal, and no churn observation.

### Records that accompany the catalog

Each converting lead's company has at least one marketing touch with `occurred_at` at or before that lead's `created_at`. That touch cites the campaign and the company. It does not cite the lead. The scenario run emits the campaign and AI workflow rows it cites. Campaign-day performance still has one row per campaign and day in the configured window.

The workflow catalog on both scenario files is exactly:

| `workflow_code` | `workflow_name` |
|---|---|
| `case_intake` | Case intake |
| `document_collection` | Document collection |
| `medical_record_review` | Medical record review |
| `document_summarization` | Document summarization |
| `demand_letter_generation` | Demand letter generation |
| `case_analysis` | Case analysis |
| `settlement_preparation` | Settlement preparation |

`lifecycle_stage_catalog` includes `prospect`, `customer`, `former_customer`, and at least one other label. The domain twin's company observation uses that other label. The committed files use `sql` for that label.

Identifiers, document numbers, and `delivery_id` keep the DATA-003 shapes. `delivery_id` is `dlv_<seed>`. Document numbers stay stable across observations of one source identifier and unique across identifiers of that entity. A run emits every contract field and the ingestion envelope, and no other column.

`ingested_at` is never earlier than the row's business timestamp. `late_event_count` immutable rows, at least one in the committed files, set `ingested_at` exactly `ingest_lag_days` after the business timestamp. Those timestamps remain inside the configured window. The business order of the journey uses `created_at`, `observed_at`, `occurred_at`, and `booked_at`. A later `ingested_at` does not move the journey.

The same seed, the same scenario file, and the same generator version produce the same source identifiers, relationships, business attributes, ingestion values, row order, and file bytes. The seed is the only source of randomness. Output files stay ordered by `observation_key`. The generator does not read the wall clock. `manifest.json` records the same deterministic fields as a DATA-003 run and has no wall-clock timestamp. A date range that cannot hold the ordered timestamps fails with the existing date-range error.

## Edge cases

GitHub issue #5 names edge cases that the merged contracts store without new columns. The scenario dataset represents each one as follows.

| Issue edge case | Rows that satisfy it |
|---|---|
| Duplicate contacts | The two contacts on the `new_business_conversion` company share `email_normalized` and keep different `hubspot_contact_id` values. |
| Merged accounts | One extra company copies the `new_business_conversion` company's `primary_domain`, uses a different `hubspot_company_id`, and has no won deal. The Product firm for that journey uses the same domain, so both companies match one firm. |
| Deals changing stages multiple times | Every forward deal has three `opportunity_stage_changed` observations. The regression deal also returns from `proposal` to `evaluation`. |
| Late-arriving events | `late_event_count` immutable rows have `ingested_at` after the business timestamp by `ingest_lag_days`. |
| Contract amendments | The expansion journey raises `total_contract_value` on a later observation of the same contract. The renewal journey moves `end_date` later on a later observation of the same contract. |
| Canceled subscriptions | The churn journey's latest subscription observation is `status` `churned` with `emitted_event` `subscription_churned`, and the contract's later observation is `terminated`. |
| Soft-deleted records | The churn journey's product user ends `inactive`. The domain twin has one lead whose sequence is `new` with `lead_created`, then `disqualified` with `lead_disqualified`, and that lead never converts. The regression quote ends `expired`. Those rows stay in the dataset. |
| Low or declining product adoption | `low_adoption` has usage and no outcome. `churn` has a later usage row with a strictly smaller `work_unit_count` than its earlier usage row. |

The domain twin's disqualified lead cites the twin company. It has no `hubspot_deal_id`. The twin is not a journey instance.

No scenario row contains `is_deleted`, `surviving_account_id`, `surviving_contact_id`, or any other `surviving_*` field. Source duplicates remain separate source identifiers. Canonical survivorship stays downstream.

## Bookings and subscription fees

A booking is a `dealhub.booking` row. `booking_type` is `new_business`, `expansion`, or `renewal`. `booking_amount` is that row's amount. `booked_at` is when it was recognized.

Subscription fees stay on `dealhub.subscription` as `recurring_amount` and `billing_frequency`. The scenario does not annualize `recurring_amount`, does not write an ARR amount, and does not emit a booking for churn. `booking_type` equals `opportunity_type` on the deal observation in effect at `booked_at`.

Tests distinguish the two by entity and field:

- Each new-business win has one booking with `booking_type` `new_business` and no booking of another type on that deal.
- Each expansion win has one booking with `booking_type` `expansion` on the expansion deal and does not create a contract.
- Each renewal win has one booking with `booking_type` `renewal` on the renewal deal and does not create a contract.
- A churned subscription has no booking with `booked_at` at or after the churn `observed_at`.
- `booking_amount` is absent from subscription rows. `recurring_amount` and `billing_frequency` are absent from booking rows.

## Configuration

The configuration loader rejects unknown keys today. This task extends it with optional keys. Absent keys preserve the DATA-003 parse and the baseline sampler.

| Key | Required on scenario files | Behavior |
|---|---|---|
| `journeys` | yes | Map of the seven journey names to positive integers. Its presence selects the scenario population. |
| `schema` | yes | Scenario files set `dev_data_004`. When the key is absent, the loader uses `dev_data_003`. |
| `ingest_lag_days` | yes | Positive integer. Committed files set `1`. |
| `late_event_count` | yes | Positive integer. Committed files set `1`. |
| `expansion_seat_increase` | yes | Positive integer. Committed files set `1`. |
| `expansion_recurring_increase` | yes | Positive decimal with at most two fraction digits. Committed files set `"10.00"`. |
| `contract_value_increase` | yes | Positive decimal with at most two fraction digits. Committed files set `"100.00"`. |

Scenario files still include every key the DATA-003 loader requires, because the loader rejects a missing key. `stage_mix`, `lead_status_mix`, `channel_mix`, and `forecast_by_stage` still satisfy the existing vocabulary checks, including the `opportunity_win_rate` identity. Those retained count and rate keys also have to pass `ensure_window` for the file's date range. The scenario population does not use `account_count`, `contacts_per_account`, `lead_count`, `campaign_count`, `activity_count`, `touch_count`, `product_users_per_customer`, `usage_events_per_user`, or the rate keys to decide journey size or journey outcomes. Journey counts and the sequences in this specification decide those records. The README states that split.

`scenarios.yaml` uses seed `1004`, `start_date` `2024-01-01`, and `end_date` `2025-07-01`. `scenarios-test.yaml` uses seed `4004` and a shorter inclusive window that still holds every ordered timestamp and every date field. A renewal adds `term_days` to `term_end` and `end_date`, and those dates have to fall inside the window, so the test window is longer than 180 days and shorter than the development window. Both files set every journey count to `1`. Amount ranges, integer ranges, `term_days`, and catalogs are read from the file. The test file's `work_unit_count` range has minimum at least 1 and maximum at least 2, with the maximum strictly greater than the minimum. `term_days` is a positive integer. Committed files set `term_days` to `180`.

Business rates, catalogs, journey counts, lags, and amount deltas stay in YAML. The Python package reads them from that file. The scenario does not encode Eve's real prices, win rates, or customer economics.

## Business assumptions

`data-generation/README.md` records these assumptions next to the journey list.

- A canceled subscription is `status` `churned` and `emitted_event` `subscription_churned`. The subscription vocabulary has no `canceled` value. The related contract ends `terminated`. Churn does not create a booking.
- A soft-deleted record remains in the extract. Product-user removal is a later `inactive` observation. A lead that will not proceed ends `disqualified`. A quote that will not be signed ends `expired` or `rejected`. The contracts have no delete flag, and observation history is kept.
- A merged account is two HubSpot companies with the same `primary_domain` and different source identifiers. The source row does not name a survivor. One Product firm uses that domain.
- A workflow start is a product usage row. Processing volume is `work_unit_count`. A completion is an outcome of `draft_completed` or `exported`. A human review is an outcome of `review_accepted`. A run that does not complete is a usage row with no outcome. The usage contract has no failure status.
- Customer health is not a generated score. A healthy journey is the new-business company with an active subscription, an active product user, sales activities, and an outcome. A declining journey is the churn company: falling `work_unit_count`, then `subscription_churned`, a terminated contract, `former_customer`, and an `inactive` user. Low adoption is a won company with usage and no outcome.
- `hubspot_lifecycle_stage` values `prospect`, `customer`, and `former_customer` are unconstrained source labels. They are not canonical `commercial_status`.
- Bookings and subscription fees answer different questions. Bookings are immutable booking rows. Subscription fees are `recurring_amount` and `billing_frequency`. This task does not annualize those fees.
- The domain twin and the duplicate contacts are intentional source duplicates. Identity resolution remains downstream.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/` and do not edit it.
- One owning agent, `data-engineer`, writes the scenario population, configuration, tests, and README. This task does not assign work to another agent.
- Follow the data-generation skill. Keep source generation free of canonical transformation: no survivorship, no effective dating, no annualized ARR, no `commercial_status`, and no `customer_converted` or `adoption_reached` column.
- Follow the data-quality skill for the scenario tests: completeness of each journey, uniqueness of source identifiers, legal values, relationships, and timestamp order.
- Keep `baseline_population` as the default sampler. Leave the baseline stage list and the baseline converted-lead path in place for `config/test.yaml`. Scenario sequences that add `working`, quote history, or a backward stage use an additional path.
- Extend `World.emit` so a scenario row can set a later `ingested_at`. The default remains the business timestamp. `ingested_at` stays inside the window and is never earlier than the business timestamp.
- Preserve the inconsistencies the contracts allow. Do not coerce `hubspot_lifecycle_stage` into a canonical enum, and do not drop duplicate emails, duplicate domains, or terminal-status rows.
- Do not generate Apollo or Clay records.
- Do not edit `contracts/`, `docs/`, `warehouse/`, `analytics/`, `orchestration/`, `infrastructure/`, or `tests/`.
- Human approval is required. `delivery.deployment_required` is false.
- `environment.isolated_schema` is true. Scenario loads use schema `dev_data_004`. Baseline loads keep schema `dev_data_003`.
- `testing.component_tests` is true. `testing.integration_tests` and `testing.end_to_end_tests` are false. DATA-005 owns cross-component validation.

## Acceptance criteria

- [ ] The implementation changes files only under `data-generation/`. `config/default.yaml` and `config/test.yaml` are unchanged.
- [ ] `config/scenarios.yaml` and `config/scenarios-test.yaml` exist. Both set every journey count to 1, the workflow catalog in this specification, and the optional keys in the configuration table. `scenarios.yaml` uses seed `1004` and the window `2024-01-01` through `2025-07-01`. `scenarios-test.yaml` uses seed `4004` and a window longer than 180 days and shorter than that development window.
- [ ] `python3 -m eve_data_generation generate --config config/scenarios-test.yaml` runs the scenario population. The same command with `config/test.yaml` still runs `baseline_population`.
- [ ] Two generations of `scenarios-test.yaml` produce identical output bytes. The manifest has no wall-clock timestamp. Generated files are not committed.
- [ ] The scenario-test dataset contains one instance of each journey, the domain twin, and the disqualified lead, and each instance matches the sequences, quote statuses, bookings, subscription events, and product rows in this specification.
- [ ] Lifecycle timestamps on a journey are ordered as this specification requires. `observed_at` strictly increases across observations of one source identifier. Won and lost remain mutually exclusive. A new-business win has one contract. Expansion and renewal do not create another contract.
- [ ] Booking rows and subscription fee fields stay on their own entities. Churn adds no booking at or after the churn observation. The expansion and renewal amendments are later observations of the original contract.
- [ ] Every customer journey's Product firm shares `primary_domain` with that journey's company. The domain twin shares the new-business domain and has no won deal. Usage and outcomes cite that firm.
- [ ] The seven workflow codes, all three outcome types, one usage with no outcome, one `work_unit_count` greater than 1, and one of each activity type `call`, `email`, and `meeting` are present.
- [ ] The edge-case table is satisfied, including one late immutable row, duplicate contact emails, the shared domain, the backward stage move, the inactive user, and the expired quote. No row contains a canonical surrogate key, a `surviving_*` link, effective-dating columns, `commercial_status`, `customer_converted`, `adoption_reached`, `is_deleted`, or an ARR field.
- [ ] Every emitted row still matches the contract fields and ingestion envelope and passes `validate_dataset`, including the adjusted accepted-quote check.
- [ ] The load command writes schema `dev_data_004` for the scenario-test file, replaces table contents on reload, and the scenario test reads rows back from that schema. It does not write `dev_data_003`. Baseline tests still load `dev_data_003`.
- [ ] `data-generation/README.md` documents the journeys, the new keys, the assumptions in this specification, generate, load, test, and schema `dev_data_004`.
- [ ] `python3 -m pytest tests` from `data-generation` passes. The tests cover journey structure, temporal order, booking versus subscription fields, domain linkage, edge cases, reproducibility, and the `dev_data_004` load.
- [ ] `contracts/`, `warehouse/`, `analytics/`, `orchestration/`, `infrastructure/`, `docs/`, and `tests/` are unchanged.

## Execution notes

Implement this specification only after it has merged and the issue label is `status:ready`. Use an `impl` worktree. Leave this specification unchanged unless a human changes the approved requirements.

Read the data-generation skill before writing the scenario population, seeds, and output. Read the data-quality skill before writing the scenario tests. Read `contracts/source/README.md` and each entity YAML as the schema. Read `specs/DATA-003-implement-synthetic-data-generators.md` for the baseline sampler, the loader, and the population hook. Do not edit the contracts, the canonical model, or the DATA-003 specification.

`baseline_population` remains the sampler for configurations without `journeys`. The scenario population calls the HubSpot, DealHub, Marketing, and Product generators. Extend those generators only far enough to emit the sequences in this specification.

Component tests run locally against `config/scenarios-test.yaml` and an embedded warehouse file. They do not require a remote warehouse. They do not modify `dev_data_003`. No integration test, end-to-end test, or deployment is required for this task.

Validation of this task is `python3 -m pytest tests` from `data-generation`, plus a review of the acceptance criteria. Human approval is required before merge.
