---
id: DATA-003
title: Implement Synthetic Data Generators
type: implementation
agent: data-engineer
skills:
  - data-generation
  - data-quality
priority: high
components:
  - data-generation
dependencies:
  - DATA-002
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

Implement reproducible Python generators that emit synthetic source records for the approved GTM source contracts, write those records as source data output, and load them into an isolated development schema.

The work product lives under `data-generation/`. Named customer-journey scenarios, the full validation suite, and warehouse transformations belong to later issues.

## Business context

GitHub issue #4 (`DATA-003 — Implement Synthetic Data Generators`) depends on DATA-002. DATA-002 is merged on `main` and GitHub issue #3 is closed. The physical source schemas are the contract files under `contracts/source/`. The logical generator inputs are the synthetic data strategy in `docs/data-model/decisions.md`.

The company is a fictional AI-native B2B SaaS vendor. The customer is a plaintiff law firm. The lifecycle the generated records must be able to support is Lead → Opportunity → Customer → Adoption → Renewal. This task emits the source rows that later metrics read. It does not define pipeline, bookings, ARR, retention, or adoption metrics, and it does not derive `customer_converted` or `adoption_reached`.

DATA-002 assigns generators and generated datasets to this issue. The parent epic names four source systems: HubSpot, DealHub, Marketing, and Product. Apollo and Clay remain future enrichment sources. This task does not generate them.

`contracts/source/` is normative for field names, types, nullability, keys, relationships, timestamps, status values, lifecycle signals, and ingestion metadata. Where this specification summarizes a contract rule, the merged YAML file wins.

## Scope

The implementation adds the generator package, configuration, source output, loader, component tests, and usage documentation listed under Deliverables. It covers:

1. Synthetic records for every logical source entity in the merged contract inventory, including sales activities, attribution touches, bookings, campaign-day performance, AI workflows, and product outcomes. Those entities are part of HubSpot, DealHub, Marketing, and Product. Referential integrity across the contracts requires them.
2. Referential integrity across those source systems, in the contract referential order.
3. Configurable record volumes, date ranges, random seed, and scenario distributions.
4. Repeatable generation when the seed and configuration are unchanged.
5. Realistic timestamps and business attributes that satisfy the contract type system and closed vocabularies.
6. A loader that places the generated dataset into the isolated development schema `dev_data_003`.

`components` lists `data-generation` only. A specification that lists more than one component requires integration tests. This specification lists one, so `testing.integration_tests` is false. The local warehouse file is a library target of this component, not a `dbt`, `infrastructure`, or `orchestration` change.

Later issues own the work in the table below. This specification stops at generators, their output, and the load into `dev_data_003`.

| Issue | Owns |
|---|---|
| DATA-001 | Canonical model. Merged. This task consumes it and does not change it. |
| DATA-002 | Source contracts. Merged. This task reads `contracts/source/` and does not change it. |
| DATA-003 | Synthetic data generators, generation configuration, source data output, the development-schema loader, component tests, and usage documentation. |
| DATA-004 | Named GTM lifecycle journeys, journey configuration, and the journey-specific edge cases in GitHub issue #5. |
| DATA-005 | The validation suite, data-quality report, and defect review for generated data. |
| Later warehouse work | dbt sources, staging, intermediate models, and marts, owned by `analytics-engineer`. |
| Later analytics work | Hex and Omni assets, owned by `analyst`. |

Orchestration workflows, infrastructure provisioning, and deployment are outside this task.

## Deliverables

The implementation adds files under `data-generation/` only. `data-generation/README.md` is the usage guide. It documents install, configuration keys, the generate command, the load command, the component test command, the output layout, the schema and table names, and the environment variables the loader reads.

The Python package exposes separate HubSpot, DealHub, Marketing, and Product generators and a dataset builder that calls them in referential order. Shared helpers may draw identifiers, timestamps, decimals, and catalog values. Business rates, catalogs, volumes, and the date range are read from configuration.

Committed configuration includes:

- `data-generation/config/default.yaml`, the development dataset.
- `data-generation/config/test.yaml`, the dataset the component tests generate and load.

`data-generation/.gitignore` ignores `data-generation/output/`. Generated datasets and the local warehouse file are written there and are not committed.

## Generation behavior

### Entities

Each run emits one dataset that can contain every contract entity. The test configuration does contain every entity. The generator reads field names, types, nullability, `allowed_values`, relationships, events, and rules from the merged contracts. It emits each `fields` entry and each `ingestion` entry. It emits no other column.

| Contract | History the generator honors |
|---|---|
| HubSpot company, contact, lead, deal | `observation`. Several rows may share the source identifier. `observed_at` distinguishes them. |
| HubSpot activity | `immutable`. One row per `hubspot_activity_id`. No `observed_at`. |
| DealHub quote, contract, subscription | `observation`. |
| DealHub booking | `immutable`. One row per `dealhub_booking_id`. No `observed_at`. |
| Marketing campaign | `current`. One row per `marketing_campaign_id`. No `observed_at`. |
| Marketing campaign performance | `immutable` campaign-day. One row per `marketing_campaign_id` and `performance_date`. |
| Marketing touch | `immutable`. One row per `marketing_touch_source_id`. |
| Product firm, AI workflow | `current`. One row per source identifier. No `observed_at`. |
| Product user | `observation`. |
| Product usage, product outcome | `immutable`. One row per source identifier. |

Opening observations of a lead or a deal set `observed_at` equal to `created_at`. A later observation of the same source identifier uses a later `observed_at`. A business change on an observation entity is a new `observed_at`. The generator does not rewrite an observation in place. Activity, booking, touch, usage, and outcome rows are emitted once per source identifier. Campaign and current-row corrections are out of this dataset: each current entity is emitted as the single current row.

### Population

Count keys are exact distinct-entity targets for the dataset. Rate keys are seeded probabilities. The README states which parent each rate applies to. The draw uses only the configured seed. `activity_count` and `touch_count` are global exact totals.

| Key | Meaning |
|---|---|
| `account_count` | Distinct `hubspot_company_id` values. |
| `contacts_per_account` | Distinct contacts for each company. Contact count equals `account_count` times this value. |
| `lead_count` | Distinct `hubspot_lead_id` values. |
| `campaign_count` | Distinct campaigns. |
| `activity_count` | Global exact total of distinct `hubspot_activity_id` values. The sampler emits this many activities. |
| `touch_count` | Global exact total of distinct `marketing_touch_source_id` values. The sampler emits this many attribution touches. |
| `product_users_per_customer` | Distinct product users on each Product firm. |
| `usage_events_per_user` | Usage rows for each product user. |
| `opportunity_win_rate` | Share of new-business deals whose latest stage is `closed_won`. |
| `stage_mix` | Relative weights for the latest stage of new-business deals. The `closed_won` weight divided by the total weight equals `opportunity_win_rate`. The generator rejects a file where those two disagree. |
| `lead_status_mix` | Relative weights for the latest lead status across `new`, `working`, `qualified`, `disqualified`, and `converted`. |
| `renewal_rate` | Share of subscriptions that receive at least one `subscription_renewed` observation while `status` stays `active`. |
| `expansion_rate` | Share of subscriptions that receive at least one `subscription_expanded` observation while `status` stays `active`. |
| `churn_rate` | Share of subscriptions that end with `status` `churned` and `emitted_event` `subscription_churned`. |
| `channel_mix` | Relative weights for the campaign channel vocabulary. |
| `outcome_rate` | Probability that a usage row is cited by one outcome. |
| `domain_match_rate` | Share of customer Product firms whose `primary_domain` equals the linked HubSpot company. |

DealHub quote, contract, subscription, and booking counts are consequences of wins, expansions, renewals, and churn. They are not a second set of targets that can contradict those rates.

These additional YAML keys control contract-legal variation. The README defines each one: `null_company_domain_rate`, `duplicate_contact_email_rate`, `orphan_lead_rate`, `null_deal_amount_rate`, `single_parent_activity_rate`, `null_performance_measure_rate`, `clicks_exceed_impressions_rate`, `null_user_email_rate`, `company_change_rate`, and `lifecycle_stage_catalog`. `default.yaml` and `test.yaml` set them so the cases under Contract conformance occur. Duplicate emails are two generated contacts that share `email_normalized`. An orphan lead has a null company and a null contact and is not `converted`. `single_parent_activity_rate` is the share of the `activity_count` activities with exactly one parent. The test dataset's single-parent activity is one of those rows. `lifecycle_stage_catalog` is an open list of `hubspot_lifecycle_stage` values and includes at least one value other than `prospect`, `customer`, and `former_customer`. `company_change_rate` is the share of companies that receive a second observation at a later `observed_at`.

Campaigns and AI workflows are created before any row cites them. One performance row is emitted per campaign per calendar day from `start_date` through `end_date` inclusive. Channel stays on the current campaign row. Spend and impressions are performance fields. Attribution touches are the `touch_count` rows in the sampler below. A campaign-day performance row stays on the performance entity.

The baseline sampler then emits companies, contacts, and leads, then the global touch and pre-deal activity totals, then deals, then the activities that cite a deal:

1. For each firm, creates the HubSpot company and its contacts.
2. Attaches leads until `lead_count` is reached. A `converted` lead is preceded by `lead_qualified` on an earlier observation. `qualified` and `disqualified` do not both occur. `working` has a null `emitted_event`. A converted lead cites `hubspot_deal_id`. Orphan leads are not converted.
3. After campaigns, companies, contacts, and leads exist, emits exactly `touch_count` touches. Each touch cites `marketing_campaign_id` and at least one of `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_company_id`. When the touch includes `hubspot_company_id` and a cited lead or contact has a company, those company identifiers agree, using the lead or contact observation in effect at `occurred_at`.
4. In that same stage, emits the activities that do not cite a deal. `hubspot_deal_id` on each of those rows is null. Every activity has at least one parent, so each of these rows has at least one of `hubspot_company_id`, `hubspot_contact_id`, and `hubspot_lead_id`. When `activity_count` is at least 2, this stage emits the greatest integer less than or equal to half of `activity_count`. When `activity_count` is 1, this stage emits that one activity. When `activity_count` is 0, this stage emits no activity.
5. Creates one new-business deal for each converted lead. The deal opens at `discovery` with `opportunity_opened`, then records each later stage through the stage drawn from `stage_mix`. Reaching `evaluation`, `proposal`, or `negotiation` emits `opportunity_stage_changed`. A deal is not both won and lost.
6. For a deal whose winning observation is `new_business` and `closed_won`, emits one accepted quote with a non-null `quoted_amount`, one contract, one or more subscriptions, and one `new_business` booking.
7. Applies expansion, then renewal, then churn, in that order. Each expansion or renewal adds a deal that opens at `discovery` with `opportunity_opened` and whose latest stage is `closed_won`. `opportunity_type` on the winning observation is `expansion` or `renewal`. Those deals are outside `stage_mix`. They cite the existing subscription, keep subscription `status` `active`, and set the subscription `emitted_event`. They do not create a contract. They may append a contract observation that changes `total_contract_value` or `end_date`. Churn appends one `subscription_churned` observation and does not emit a booking.
8. After the deals from steps 5 and 7 exist, emits the activities that cite a deal. This stage emits `activity_count` minus the step 4 count. Each of these rows sets `hubspot_deal_id` to a deal whose observations are already in the dataset. The row may also cite a company, contact, or lead. Every activity still has at least one parent.
9. Creates one Product firm for each company with a won new-business deal. A share of those firms, `domain_match_rate`, copy that company's `primary_domain`. The others use a different domain or a null domain. The generator does not match firms on `firm_name`.
10. Creates product users, usage, and outcomes. Usage `product_firm_id` is the firm on the user observation in effect at `occurred_at`. An outcome cites one usage, uses the same user, firm, and workflow as that usage, and has `occurred_at` at or after the usage. At most one outcome cites a usage.

Steps 4 and 8 together emit exactly `activity_count` activities. When `activity_count` is at least 2, both stages emit at least one activity. `default.yaml` and `test.yaml` set `activity_count` to at least 2 and `touch_count` to at least 1. `single_parent_activity_rate` is the share of those `activity_count` activities with exactly one parent. The test dataset's single-parent activity is one of those rows.

Company agreement for an activity uses the same `occurred_at` rule as a touch. When the activity includes `hubspot_company_id` and another parent that has a company, the company identifiers agree, using the parent observation in effect at `occurred_at`. A deal has a company. A contact or a lead has a company when `hubspot_company_id` is present on the observation in effect at `occurred_at`. A parent with no company leaves the activity's company unconstrained. `occurred_at` on a touch or an activity is at or after the `observed_at` of each cited parent observation that this agreement rule uses.

`booking_type` equals `opportunity_type` on the deal observation in effect at `booked_at`. `booking_amount` is not negative. A renewal booking and an expansion booking use their own amounts.

The dataset builder accepts an alternate population in place of this sampler. DATA-004 uses that extension point for named journeys. This task ships the sampler and does not ship those journeys.

### Contract conformance

Generated rows satisfy the merged contracts, including:

- Required strings are present and non-empty. A missing optional value is null, not an empty string.
- Enum fields use only `allowed_values`. `hubspot_lifecycle_stage`, `practice_focus`, `plan_code`, `workflow_code`, `workflow_name`, `state`, display names, and `owner_name` stay open strings. `hubspot_lifecycle_stage` is not limited to `prospect`, `customer`, or `former_customer`.
- Decimals are non-negative base-10 amounts in US dollars with at most two fraction digits. Integers honor each field's minimum. `work_unit_count` is at least 1. `seat_count` is at least 0.
- Dates are ISO-8601 calendar dates. Timestamps are ISO-8601 UTC. Business dates and timestamps fall inside the inclusive configured window. `ingested_at` is at or after that row's business timestamp and inside the same window.
- `email_normalized`, when present, is lowercase and trimmed. `primary_domain`, when present, is a lowercase host with no scheme and no path.
- Source identifiers are non-empty and stable. HubSpot identifiers are numeric strings. DealHub identifiers are prefixed strings. Marketing and Product identifiers are opaque strings. The README documents the prefixes.
- `quote_number`, `contract_number`, `subscription_number`, `booking_number`, `campaign_code`, and `workflow_code` are present, stable across observations of the same source identifier, and unique across source identifiers of that entity.
- A relationship value, when present, equals a source identifier emitted in the same dataset. Parents are emitted before children. Optional parents may be absent. When a deal observation includes `hubspot_contact_id`, the contact observation in effect at the deal's `observed_at` has the same `hubspot_company_id`. When a deal includes `dealhub_subscription_id`, that subscription's company equals the deal's company. When a touch includes `hubspot_company_id` and a cited lead or contact has a company, those company identifiers agree, using the lead or contact observation in effect at `occurred_at`. When an activity includes `hubspot_company_id` and another parent that has a company, the company identifiers agree, using the parent observation in effect at `occurred_at`. Every activity has at least one parent. Every touch cites `marketing_campaign_id` and at least one of contact, lead, and company. An activity cites a deal only after that deal's rows exist.
- Lead, deal, and subscription `emitted_event` values follow the contract event tables. `subscription_churned` occurs at most once per subscription. Renewals and expansions may repeat.
- `source_system`, `delivery_id`, and `ingested_at` are present. One generation run uses one `delivery_id`, derived from the seed. `source_system` matches the contract.
- The same `observation_key` is not emitted twice with different business attributes.

Amounts are drawn from the configured ranges onto their own fields. HubSpot `amount`, `quoted_amount`, `total_contract_value`, `booking_amount`, `recurring_amount`, and `spend_amount` are not copies of one another. `seat_count` is not the number of product users. Company `owner_name` and deal `owner_name` are drawn independently. `expected_close_date` and contract `start_date` are drawn independently. Contract `end_date` is on or after `start_date`. Subscription `term_end` is on or after `term_start`.

The test configuration's dataset includes, at least once, a null `primary_domain` on a company, a duplicate `email_normalized` on two contact identifiers, a lead with null company and null contact, a deal with null `amount`, an activity with a single parent, a performance row with a null measure, a performance row whose `click_count` exceeds `impression_count`, one domain-matched Product firm, one unmatched Product firm, a product user with null email, an active subscription observation whose `emitted_event` is `subscription_renewed` or `subscription_expanded`, a churn with no booking, a `hubspot_lifecycle_stage` outside `prospect`, `customer`, and `former_customer`, and two observations of one `hubspot_company_id`.

That dataset contains exactly `touch_count` touches and exactly `activity_count` activities. It includes an activity with a null `hubspot_deal_id` and an activity that cites a deal already emitted. The activity with a single parent is one of the `activity_count` rows, and that row has exactly one parent.

### Reproducibility

The same seed, the same configuration file, and the same generator version produce the same source identifiers, relationships, business attributes, ingestion values, row order, and file bytes. The seed is the only source of randomness. Output files are ordered by `observation_key`. The generator does not read the wall clock.

A run whose date range cannot hold the ordered timestamps fails with an error. `default.yaml` spans at least 18 months. `test.yaml` uses a shorter range that still holds the ordered events for its volumes.

## Output and warehouse load

### Source files

The generate command writes `data-generation/output/<dataset>/`. Each source entity has one JSON Lines file. Decimal values are JSON strings with at most two fraction digits. Integers are JSON integers. Dates and timestamps are JSON strings. Nulls are JSON null. Object keys are sorted. Each file ends with a trailing newline.

`manifest.json` in that directory records the seed, the configuration file name, `start_date`, `end_date`, `delivery_id`, and the row count of each entity. It contains no wall-clock timestamp.

### Loader

The load command reads that directory and loads it into schema `dev_data_003`. The schema name uses `environment.schema_prefix`. The default target is an embedded database file at `data-generation/output/warehouse/dev_data_003`, created by the loader, using an embedded engine that supports schemas. The README names the engine and the Python dependency.

Table names are `src_<source_system>_<source_entity>`, for example `src_hubspot_company` and `src_marketing_campaign_performance`. Columns are the contract `fields` followed by the ingestion fields, and no others. Warehouse types preserve text, exact decimal, integer, date, UTC timestamp, and null. A load replaces the table contents in `dev_data_003`. A second load of the same dataset does not append a duplicate copy.

The loader reads an optional target from the environment, documented in `data-generation/README.md` and `data-generation/.env.example`. The example file contains empty placeholders. Credentials are not committed. When the variables are unset, the loader uses the embedded file above. Component tests use that default target. This task does not provision a remote warehouse and does not add a dbt profile.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/` and do not edit it.
- One owning agent, `data-engineer`, writes the generators, configuration, loader, tests, and README.
- Follow the data-generation skill. Keep source generation free of canonical transformation: no survivorship, no effective dating, no annualized ARR, no `commercial_status`, and no `customer_converted` or `adoption_reached` column.
- Keep volumes, rates, date bounds, owner names, practice focuses, plan codes, and workflow catalogs in the YAML configuration. The Python package reads them from that file.
- Keep HubSpot, DealHub, Marketing, and Product as separate generator modules.
- Preserve the inconsistencies the contracts allow. Do not coerce source labels into canonical values, and do not drop rows to hide nulls, duplicate emails, or duplicate domains.
- Do not generate Apollo or Clay records.
- Do not add source columns for account health, adoption score, soft delete, merged-account survivorship, or workflow failure. Those are outside the contracts. Named journeys that need them are DATA-004 work and require a later contract change before a new column exists.
- Do not edit `docs/data-model/`, `warehouse/`, `analytics/`, `orchestration/`, `infrastructure/`, or `tests/`.
- Human approval is required. `delivery.deployment_required` is false.
- `environment.isolated_schema` is true. The only schema this task creates is `dev_data_003` on the loader target.
- `testing.component_tests` is true. `testing.integration_tests` and `testing.end_to_end_tests` are false. DATA-005 owns cross-component validation.

## Acceptance criteria

- [ ] The implementation changes files only under `data-generation/`.
- [ ] Python generators exist for HubSpot, DealHub, Marketing, and Product and emit every entity in the `contracts/source/` inventory. Apollo and Clay are absent.
- [ ] `config/default.yaml` and `config/test.yaml` supply the seed, date range, count keys, rate keys, mixes, amount ranges, and catalogs in this specification. Business rates and catalogs are not hardcoded in Python.
- [ ] `default.yaml` spans at least 18 months. The test configuration produces at least one row of every source entity, exactly `activity_count` activities, and exactly `touch_count` touches, and at least one of each lead, deal, and subscription `emitted_event` value, including `subscription_renewed`, `subscription_expanded`, and `subscription_churned`. Those activities include one that does not cite a deal and one that cites a deal. The single-parent activity is one of the `activity_count` rows.
- [ ] Two generations with the same seed and configuration produce identical output bytes. Distinct seeds are supported by configuration.
- [ ] Every emitted row matches that entity's contract fields and ingestion envelope, uses the contract types and allowed values, and omits canonical surrogate keys, `surviving_*` links, effective-dating columns, `commercial_status`, `customer_converted`, `adoption_reached`, and metric fields.
- [ ] Referential integrity holds for the test dataset: relationship values point at emitted source identifiers, parent companies agree where the contract requires it, each touch cites a campaign and at least one of contact, lead, and company, every activity has at least one parent, an activity cites a deal only after that deal exists, and company identifiers on a touch or an activity agree at `occurred_at` when the contract requires it. A new-business win has an accepted quote, one contract, at least one subscription, and a booking, and expansion or renewal does not create another contract.
- [ ] Document numbers are stable and unique. HubSpot, DealHub, Marketing, and Product identifiers follow the shapes in this specification. Nulls, duplicate emails, duplicate domains, and the other test-configuration cases listed under Contract conformance are present.
- [ ] The generate command writes JSON Lines and `manifest.json` under `data-generation/output/`. That directory is gitignored. Generated datasets are not committed.
- [ ] The load command creates schema `dev_data_003`, loads one `src_<source_system>_<source_entity>` table per entity, preserves nulls and exact decimals, and replaces table contents on reload.
- [ ] `data-generation/README.md` documents install, configuration, generate, load, test, schema `dev_data_003`, table names, and the optional target environment variables. `data-generation/.env.example` has empty placeholders and no secrets.
- [ ] The documented component test command passes and covers reproducibility, contract shape, referential integrity, configured volumes and rates, the date window, and a load that reads rows back from `dev_data_003`.
- [ ] `contracts/`, `warehouse/`, `analytics/`, `orchestration/`, `infrastructure/`, `docs/`, and `tests/` are unchanged.

## Execution notes

Implement this specification only after it has merged and the issue label is `status:ready`. Use an `impl` worktree. Leave this specification unchanged unless a human changes the approved requirements.

Read the data-generation skill before writing generators, seeds, and output. Read the data-quality skill before writing component tests of completeness, uniqueness, values, relationships, and timestamps. Read `contracts/source/README.md` and each entity YAML as the schema. Read the synthetic data strategy in `docs/data-model/decisions.md` for the population inputs. Do not edit those files.

The baseline sampler in this specification is the DATA-003 population. Keep it replaceable so DATA-004 can supply named journeys without rewriting entity generators. Do not implement the GitHub issue #5 journey catalog here.

Component tests run locally against `config/test.yaml` and the embedded warehouse file. They do not require a remote warehouse, and they do not modify `dev` schemas other than `dev_data_003` on that local target. No integration test, end-to-end test, or deployment is required for this task.

Validation of this task is the component test command in `data-generation/README.md`, plus a review of the acceptance criteria. Human approval is required before merge.
