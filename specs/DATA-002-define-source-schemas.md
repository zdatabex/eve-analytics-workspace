---
id: DATA-002
title: Define Source Schemas and Data Contracts
type: implementation
agent: data-engineer
skills:
  - data-modeling
  - data-quality
priority: high
components:
  - contracts
dependencies:
  - DATA-001
requires_approval: true
allowed_paths:
  - contracts/source/
  - contracts/README.md
excluded_paths:
  - data-generation/
  - data/
  - warehouse/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - tests/
  - docs/
  - specs/
contracts:
  changes_required: true
  affected_contracts:
    - contracts/source/README.md
    - contracts/source/hubspot/company.yaml
    - contracts/source/hubspot/contact.yaml
    - contracts/source/hubspot/lead.yaml
    - contracts/source/hubspot/deal.yaml
    - contracts/source/hubspot/activity.yaml
    - contracts/source/dealhub/quote.yaml
    - contracts/source/dealhub/contract.yaml
    - contracts/source/dealhub/subscription.yaml
    - contracts/source/dealhub/booking.yaml
    - contracts/source/marketing/campaign.yaml
    - contracts/source/marketing/campaign_performance.yaml
    - contracts/source/marketing/touch.yaml
    - contracts/source/product/firm.yaml
    - contracts/source/product/user.yaml
    - contracts/source/product/ai_workflow.yaml
    - contracts/source/product/usage.yaml
    - contracts/source/product/outcome.yaml
testing:
  component_tests: false
  integration_tests: false
  end_to_end_tests: false
environment:
  isolated_schema: false
  schema_prefix: dev
delivery:
  pull_request_required: true
  human_approval_required: true
  deployment_required: false
---

## Objective

Define the physical source schemas and data contracts for the synthetic GTM foundation. Each contract states the field names, data types, nullability, keys, relationships, timestamps, status values, lifecycle signals, and ingestion metadata for one logical source entity in the approved canonical model.

The work product is contract files under `contracts/source/`. Generators, generated datasets, and dbt models belong to later issues.

## Business context

GitHub issue #3 (`DATA-002 — Define Source Schemas and Data Contracts`) depends on DATA-001. DATA-001 is merged on `main` and GitHub issue #2 is closed. The approved design is:

- `specs/DATA-001-design-canonical-gtm-data-model.md`
- `docs/data-model/erd.md`
- `docs/data-model/entities.md`
- `docs/data-model/source-mapping.md`
- `docs/data-model/decisions.md`

The company is a fictional AI-native B2B SaaS vendor. The customer is a plaintiff law firm. The lifecycle the sources must be able to support is Lead → Opportunity → Customer → Adoption → Renewal. This task does not define pipeline, bookings, ARR, retention, or adoption metrics. It defines the source records those later metrics read.

`decisions.md` records three working answers that were marked for review before this issue: the stage and status vocabulary, one `adoption_reached` event per account, and ARR history reconstructed from subscription observations rather than a periodic ARR snapshot. This specification freezes those working answers. Source contracts use that vocabulary and those grains. This task does not edit `docs/data-model/` and does not reopen the canonical entity list.

The parent epic names four source systems: HubSpot, DealHub, Marketing, and Product. Apollo and Clay remain future enrichment sources. They do not get contracts in this task.

DATA-001 leaves `contracts/` unchanged and assigns physical field types, nullability, and contract files to DATA-002. The logical source entities, mapping attributes, relationships, and emitted events are the synthetic data strategy in `decisions.md`. This specification turns that logical schema into files a later generator can target and a later warehouse model can read. It does not collapse those sources into canonical tables.

## Scope

The implementation writes the contract files listed under Deliverables. It covers:

1. One source schema for each logical source entity of HubSpot, DealHub, Marketing, and Product.
2. Field names, data types, nullability, and closed value sets.
3. Source identifiers, observation keys, and relationship fields that reference those source identifiers.
4. Timestamps, status fields, and the lifecycle signal each source emits.
5. Shared ingestion metadata and the historical form of each source record.
6. Expected source behavior, including the inconsistencies the approved model keeps.
7. Assumptions and source limitations a later generator and a later validation issue can rely on.

`components` lists `contracts` only. `docs` is not a component in `workspace.yaml`. A specification that lists more than one component requires integration tests. This specification lists one, so `testing.integration_tests` is false.

Later issues own the work in the table below. This specification stops at the source contracts.

| Issue | Owns |
|---|---|
| DATA-001 | Canonical model. Merged. This task consumes it and does not change it. |
| DATA-003 | Synthetic data generators and generated datasets |
| DATA-004 | GTM lifecycle scenario implementations |
| DATA-005 | Validation of generated data against these contracts |
| Later warehouse work | dbt staging, intermediate models, and marts, owned by `analytics-engineer` |
| Later analytics work | Hex and Omni assets, owned by `analyst` |

Orchestration workflows, infrastructure, and deployment are outside this task. An isolated warehouse schema is not required. These contracts are files, not a database schema.

## Deliverables

The implementation adds the files in `contracts.affected_contracts` and no others. `contracts/README.md` keeps its current ownership text and gains a short pointer to `contracts/source/README.md`.

`contracts/source/README.md` is the shared contract guide. It contains:

- The source inventory and the canonical entity each source entity maps to.
- The ingestion envelope and the history classes defined below.
- The type system, identifier rules, and closed vocabularies.
- The cross-contract relationship and referential rules.
- The inconsistency catalog, assumptions, and source limitations.
- A statement that canonical surrogate keys, effective dating, derived lifecycle events, and business metrics are not source fields.

Each YAML file is the schema and the field-level contract for one source entity. It must be usable without opening the other YAML files. It repeats the ingestion fields, the relationships, the events, and the rules that apply to that entity. The README is the index and the cross-entity rule set.

Every YAML file uses this shape:

```yaml
id: hubspot.company
title: HubSpot company
source_system: hubspot
source_entity: company
canonical_entity: account
history: observation
grain: One row represents one observation of one HubSpot company at one observed_at.
source_identifier:
  - hubspot_company_id
observation_key:
  - hubspot_company_id
  - observed_at
fields: []
ingestion: []
relationships: []
events: []
rules: []
```

`history` is `observation`, `current`, or `immutable`, as assigned per entity below.

`observation_key` is required on every contract. The example above is an `observation` contract, so its key is the source identifier plus `observed_at`. That pair is not the key for every class. History classes below assign it: `observation` uses the source identifier plus `observed_at`; `current` uses the source identifier; a single-identifier `immutable` entity uses that source identifier; campaign performance uses `marketing_campaign_id` plus `performance_date`. A `current` contract and a single-identifier `immutable` contract do not add `observed_at`.

`fields` entries have `name`, `type`, `nullable`, `maps_to`, and `description`. A closed set also has `allowed_values`. `maps_to` is the canonical `entity.attribute` the field feeds, or null when the field is a source signal that is not itself a canonical attribute. `ingestion` entries use the same field shape and always have `maps_to: null`.

`relationships` entries name the local field, the referenced `source_system.source_entity.field`, whether the field is required, and the cardinality in source terms. `events` entries name a lifecycle signal and the condition that emits it. `rules` entries are the entity-specific integrity and inconsistency sentences.

### Source inventory

| File | Source identifier | History | Canonical entity | Row grain |
|---|---|---|---|---|
| `contracts/source/hubspot/company.yaml` | `hubspot_company_id` | observation | `account` | One observation of one HubSpot company at one `observed_at`. |
| `contracts/source/hubspot/contact.yaml` | `hubspot_contact_id` | observation | `contact` | One observation of one HubSpot contact at one `observed_at`. |
| `contracts/source/hubspot/lead.yaml` | `hubspot_lead_id` | observation | `lead` | One observation of one HubSpot lead at one `observed_at`. |
| `contracts/source/hubspot/deal.yaml` | `hubspot_deal_id` | observation | `opportunity` | One observation of one HubSpot deal at one `observed_at`. |
| `contracts/source/hubspot/activity.yaml` | `hubspot_activity_id` | immutable | `activity` | One sales activity. |
| `contracts/source/dealhub/quote.yaml` | `dealhub_quote_id` | observation | `quote` | One observation of one DealHub quote at one `observed_at`. |
| `contracts/source/dealhub/contract.yaml` | `dealhub_contract_id` | observation | `contract` | One observation of one DealHub contract at one `observed_at`. |
| `contracts/source/dealhub/subscription.yaml` | `dealhub_subscription_id` | observation | `subscription` | One observation of one DealHub subscription at one `observed_at`. |
| `contracts/source/dealhub/booking.yaml` | `dealhub_booking_id` | immutable | `booking` | One recognized booking. |
| `contracts/source/marketing/campaign.yaml` | `marketing_campaign_id` | current | `campaign` | One marketing campaign. |
| `contracts/source/marketing/campaign_performance.yaml` | `marketing_campaign_id` and `performance_date` | immutable | `campaign_performance` | One campaign on one day. |
| `contracts/source/marketing/touch.yaml` | `marketing_touch_source_id` | immutable | `marketing_touch` | One attribution touch. |
| `contracts/source/product/firm.yaml` | `product_firm_id` | current | `account` | One Product firm. |
| `contracts/source/product/user.yaml` | `product_user_source_id` | observation | `product_user` | One observation of one product user at one `observed_at`. |
| `contracts/source/product/ai_workflow.yaml` | `product_workflow_id` | current | `ai_workflow` | One AI workflow. |
| `contracts/source/product/usage.yaml` | `product_usage_source_id` | immutable | `product_usage` | One usage of one AI workflow by one product user. |
| `contracts/source/product/outcome.yaml` | `product_outcome_source_id` | immutable | `product_outcome` | One outcome of one product usage event. |

Every file states the `observation_key` for its history class, as defined under History classes. An `observation` file uses its source identifier plus `observed_at`. A `current` file uses its source identifier. Activity, booking, touch, usage, and outcome use their source identifier alone. Campaign performance uses `marketing_campaign_id` plus `performance_date`. No other file adds `observed_at` to its key.

There is no source contract for `lifecycle_event`, `account` as a merged firm, or a customer object. `customer_converted` and `adoption_reached` are canonical events derived downstream. Product usage remains the usage row. It is not also a `lifecycle_event` payload.

## Shared contract rules

### Types

| Type | Meaning |
|---|---|
| `string` | Unicode text. A required string is present and non-empty. A missing value is null, not an empty string. |
| `enum` | A string whose `allowed_values` are the frozen working vocabulary. No other value is valid. |
| `decimal` | A non-negative base-10 amount in US dollars with at most two fraction digits. The contract forbids a binary float. There is no currency field. |
| `integer` | A whole number. Each field states its minimum. |
| `date` | An ISO-8601 calendar date. No time and no timezone. |
| `timestamp` | An ISO-8601 timestamp in UTC. |

### Ingestion envelope

Every contract includes these three fields. They are platform delivery metadata. They are not canonical business attributes and they do not open a canonical Type 2 version by themselves.

| Field | Type | Null | Description |
|---|---|---|---|
| `source_system` | enum | no | `hubspot`, `dealhub`, `marketing`, or `product`. The value equals that file's `source_system`. |
| `delivery_id` | string | no | The extraction batch. Many rows may share one `delivery_id`. A replay uses a new `delivery_id` and the same business attributes. |
| `ingested_at` | timestamp | no | When this delivery was accepted. It may be later than `observed_at`, `occurred_at`, or `booked_at`. Late delivery is valid. |

### History classes

Source records do not carry `effective_start`, `effective_end`, `is_current`, canonical surrogate keys, or `surviving_*` links. Canonical effective dating is downstream. `observed_at` on an observation is the time that later becomes `effective_start` of a new canonical version. The source row is not that version.

The observation of a source identifier in effect at a timestamp is the row with that identifier whose `observed_at` is the latest at or before that timestamp. If no row of that identifier has `observed_at` at or before the timestamp, no observation is in effect, and a rule that requires one is not satisfied.

`observation_key` is required on every contract. `source_system`, `delivery_id`, and `ingested_at` are delivery metadata. They are not part of `observation_key` and they are not business attributes.

| History | `observation_key` | Row |
|---|---|---|
| `observation` | The source identifier plus `observed_at`. | One observation of one source identifier. Many rows may share the source identifier. `observed_at` distinguishes them. |
| `current` | The source identifier. | The current source record for a campaign, a Product firm, or an AI workflow. The contract stores that record only. It has no `observed_at`. |
| `immutable`, one source identifier | That source identifier. | One business event: an activity, a booking, a touch, a usage, or an outcome. The contract has no `observed_at`. |
| `immutable`, campaign performance | `marketing_campaign_id` plus `performance_date`. | One campaign on one day. The contract has no `observed_at`. |

A delivery has one of three outcomes.

| Outcome | Rule |
|---|---|
| Replay | The same `observation_key` and the same business attributes arrive with a new `delivery_id`. This applies to every history class. A different payload at the same `observation_key` is not a replay. |
| In-place correction | A full replacement of a `history: current` row, or a replacement of one campaign-day's measures. The `observation_key` stays the same. The contract does not keep the replaced values. |
| New source identifier | A correction of a booking, activity, touch, usage, or outcome. The correction uses a new source identifier. A second delivery of an existing identifier is a replay only when the business attributes match. A different payload does not rewrite that event. |

A different payload at an existing `history: observation` key is invalid. A business change for that class is a new `observed_at`, and therefore a new `observation_key`. A different payload for an existing booking, activity, touch, usage, or outcome identifier is invalid for the same reason: that change is a new source identifier, not a rewrite. A different payload for a `history: current` key, or for a campaign-day key, is the in-place correction above.

### Identifiers and document numbers

Source identifiers are opaque non-empty strings issued by the source system. They are not canonical surrogate keys. The README records the expected shape as an assumption: HubSpot identifiers are numeric strings, DealHub identifiers are prefixed strings, and Marketing and Product identifiers are opaque strings. The contract accepts any non-empty string. It does not reject a value solely for its shape.

`quote_number`, `contract_number`, `subscription_number`, `booking_number`, `campaign_code`, and `workflow_code` are required. Each is stable across observations of the same source identifier and unique across different source identifiers of that entity.

`email_normalized`, when present, is lowercase and trimmed. `primary_domain`, when present, is a lowercase host with no scheme and no path. Those constraints describe the match keys the approved model uses. They do not merge records inside the source contract. Duplicate emails and duplicate domains are valid source data.

### Closed vocabularies

These are the frozen working values from `decisions.md`. Contracts that use them list them as `allowed_values`.

| Subject | Allowed values |
|---|---|
| Lead status | `new`, `working`, `qualified`, `disqualified`, `converted` |
| Opportunity stage | `discovery`, `evaluation`, `proposal`, `negotiation`, `closed_won`, `closed_lost` |
| Opportunity type and booking type | `new_business`, `expansion`, `renewal` |
| Forecast category | `pipeline`, `best_case`, `commit`, `closed`, `omitted` |
| Quote status | `draft`, `sent`, `accepted`, `rejected`, `expired` |
| Contract status | `active`, `expired`, `terminated` |
| Subscription status | `pending`, `active`, `churned` |
| Product user status | `invited`, `active`, `inactive` |
| Billing frequency | `monthly`, `quarterly`, `annual` |
| Outcome type | `draft_completed`, `review_accepted`, `exported` |
| Buying role | `champion`, `decision_maker`, `user`, `billing` |
| Activity type | `call`, `email`, `meeting` |
| Campaign channel | `paid_search`, `paid_social`, `email`, `webinar`, `partner`, `outbound` |
| Firm segment | `solo`, `small`, `mid`, `large` |
| ICP fit | `in_icp`, `out_of_icp` |
| Lifecycle signal | The `emitted_event` values named on lead, deal, and subscription below |

`practice_focus`, `plan_code`, `workflow_code`, `workflow_name`, `state`, `owner_name`, display names, and `hubspot_lifecycle_stage` stay open strings. `hubspot_lifecycle_stage` is not the canonical `commercial_status` enum and is not constrained to `prospect`, `customer`, or `former_customer`.

`working` does not emit a lead event. `pending` and `active` do not by themselves emit a subscription event. Renewal and expansion are explicit signals on a subscription observation whose status remains `active`.

### Fields that no source contract contains

- Canonical surrogate keys such as `account_id`, `contact_id`, `lead_id`, `opportunity_id`, `quote_id`, `contract_id`, `subscription_id`, `booking_id`, `campaign_id`, `campaign_performance_id`, `marketing_touch_id`, `activity_id`, `product_user_id`, `ai_workflow_id`, `product_usage_id`, `product_outcome_id`, and `lifecycle_event_id`.
- `surviving_account_id`, `surviving_contact_id`, `surviving_lead_id`, `surviving_opportunity_id`, `surviving_subscription_id`, and `surviving_product_user_id`.
- `commercial_status`, `effective_start`, `effective_end`, and `is_current`.
- `customer_converted`, `adoption_reached`, and any `lifecycle_event` payload. The source signal is `emitted_event` or the immutable row itself.
- Calculated ARR, net retention, pipeline coverage, win rate, adoption score, or any amount copied from one source entity onto another.

Relationship fields store the parent source identifier. They do not embed the parent record.

## HubSpot

HubSpot owns the CRM record of firms, people, inquiries, deals, and sales activities. It does not send a customer object. Its company observations supply the tracked firmographics. Canonical `commercial_status` is derived downstream.

### Company

`maps_to` values are attributes of `account` unless noted.

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `hubspot_company_id` | string | no | Source identifier. | `account.hubspot_company_id` |
| `firm_name` | string | no | Display name. | `account.firm_name` |
| `primary_domain` | string | yes | Lowercase host when present. | `account.primary_domain` |
| `state` | string | yes | Principal US state. Open text. | `account.state` |
| `segment` | enum | yes | `solo`, `small`, `mid`, `large`. | `account.segment` |
| `practice_focus` | string | yes | Open catalog. | `account.practice_focus` |
| `icp_fit` | enum | yes | `in_icp`, `out_of_icp`. | `account.icp_fit` |
| `owner_name` | string | yes | Firm-relationship owner. | `account.owner_name` |
| `hubspot_lifecycle_stage` | string | yes | Source lifecycle label. Not `commercial_status`. | `account.hubspot_lifecycle_stage` |
| `observed_at` | timestamp | no | Observation time. | null. Downstream, this time starts a new account version when a tracked firmographic changes. |

Relationships: none.

Events: none.

Rules:

- Two companies may share `primary_domain` or `firm_name`. The contract does not deduplicate them.
- A missing `primary_domain` is valid. It does not match a Product firm.
- `hubspot_lifecycle_stage` may disagree with any later canonical commercial status. The contract stores the HubSpot label unchanged.

### Contact

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `hubspot_contact_id` | string | no | Source identifier. | `contact.hubspot_contact_id` |
| `full_name` | string | yes | Name as sales knows it. | `contact.full_name` |
| `email_normalized` | string | yes | Lowercase trimmed email when present. | `contact.email_normalized` |
| `title` | string | yes | Role title. | `contact.title` |
| `buying_role` | enum | yes | `champion`, `decision_maker`, `user`, `billing`. | `contact.buying_role` |
| `observed_at` | timestamp | no | Observation time. | null. Downstream, this time starts a new contact version when firm, role, or email changes. |
| `hubspot_company_id` | string | yes | Current firm link. | Reference to `account` through `account.hubspot_company_id`. |

Relationships:

- `hubspot_company_id` references `hubspot.company.hubspot_company_id`. Optional. Many contacts may cite one company. The cited company exists in the same dataset when the field is present.

Events: none.

Rules:

- The same `email_normalized` may appear on more than one `hubspot_contact_id`. The contract does not choose a survivor.
- A contact may change `hubspot_company_id` on a later observation of the same source identifier.
- A contact without an email is valid and cannot match a product user by email.

### Lead

The canonical lead dimension keeps the current lead and stores status history as lifecycle events. The source contract still uses `history: observation`, because each status change is a separate source signal. One current-row schema cannot carry that sequence.

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `hubspot_lead_id` | string | no | Source identifier. | `lead.hubspot_lead_id` |
| `status` | enum | no | Lead status vocabulary. | `lead.status` |
| `created_at` | timestamp | no | When the inquiry opened. Stable across observations of this lead. | `lead.created_at` |
| `observed_at` | timestamp | no | At or after `created_at`. The creation observation sets them equal. | null |
| `emitted_event` | enum | yes | `lead_created`, `lead_qualified`, `lead_disqualified`, `lead_converted`. | null. Downstream this chooses `lifecycle_event.event_name`. |
| `hubspot_company_id` | string | yes | Firm link. | Reference to the lead's account. |
| `hubspot_contact_id` | string | yes | Person link. | Reference to the lead's contact. |
| `marketing_campaign_id` | string | yes | Originating campaign. | Reference to `campaign.marketing_campaign_id`. |
| `hubspot_deal_id` | string | yes | Required when `emitted_event` is `lead_converted`. Otherwise null. | Reference to `opportunity.hubspot_deal_id`. |

Relationships:

- `hubspot_company_id` references `hubspot.company.hubspot_company_id`. Optional.
- `hubspot_contact_id` references `hubspot.contact.hubspot_contact_id`. Optional.
- `marketing_campaign_id` references `marketing.campaign.marketing_campaign_id`. Optional.
- `hubspot_deal_id` references `hubspot.deal.hubspot_deal_id`. Required only on `lead_converted`.

Events:

| Signal | When |
|---|---|
| `lead_created` | `status` is `new` on the creation observation. One per lead. `observed_at` equals `created_at`. |
| `lead_qualified` | `status` is `qualified`. At most one per lead. |
| `lead_disqualified` | `status` is `disqualified`. At most one per lead. |
| `lead_converted` | `status` is `converted`. At most one per lead. `hubspot_deal_id` is present. |
| none | `status` is `working`. `emitted_event` is null. |

Rules:

- `qualified` and `disqualified` do not both occur for one lead.
- `lead_converted` occurs only after `lead_qualified` for that `hubspot_lead_id`.
- A disqualified lead has no `hubspot_deal_id`.
- A lead may omit both the company and the contact. A converted lead's deal still has a company. The source creates that company before the deal when the lead had no firm.
- The lead contract does not contain a customer record.

### Deal

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `hubspot_deal_id` | string | no | Source identifier. | `opportunity.hubspot_deal_id` |
| `opportunity_name` | string | no | Deal name. | `opportunity.opportunity_name` |
| `opportunity_type` | enum | no | `new_business`, `expansion`, `renewal`. The type as of this observation's `observed_at`. A later observation of the same deal may change it. | `opportunity.opportunity_type` |
| `stage` | enum | no | Opportunity stage vocabulary. | `opportunity.stage` |
| `amount` | decimal | yes | HubSpot-entered amount. Not bookings and not ARR. | `opportunity.amount` |
| `expected_close_date` | date | yes | Sales expectation. Not a contract start. | `opportunity.expected_close_date` |
| `owner_name` | string | yes | Deal owner. Independent of the company owner. | `opportunity.owner_name` |
| `forecast_category` | enum | yes | Forecast vocabulary. | `opportunity.forecast_category` |
| `created_at` | timestamp | no | When the deal opened. Stable across observations. | `opportunity.created_at` |
| `observed_at` | timestamp | no | At or after `created_at`. The opening observation sets them equal. | null. Downstream, a tracked deal attribute change starts a new opportunity version. |
| `emitted_event` | enum | yes | `opportunity_opened`, `opportunity_stage_changed`, `opportunity_won`, `opportunity_lost`. | null. Downstream this chooses `lifecycle_event.event_name`. |
| `hubspot_company_id` | string | no | The firm. Stable across observations of this deal. | Reference to the opportunity's account. |
| `hubspot_contact_id` | string | yes | Primary contact. | Reference to the opportunity's primary contact. |
| `hubspot_lead_id` | string | yes | Originating lead. Stable when present. | Reference to `lead.hubspot_lead_id`. |
| `dealhub_subscription_id` | string | yes | On this observation, required when `opportunity_type` is `expansion` or `renewal`, and null when it is `new_business`. | Reference to the targeted subscription. |

Relationships:

- `hubspot_company_id` references `hubspot.company.hubspot_company_id`. Required. Many deals may cite one company.
- `hubspot_contact_id` references `hubspot.contact.hubspot_contact_id`. Optional. When present, the contact observation in effect at the deal's `observed_at` has the same `hubspot_company_id` as the deal.
- `hubspot_lead_id` references `hubspot.lead.hubspot_lead_id`. Optional. At most one deal cites a given lead.
- `dealhub_subscription_id` references `dealhub.subscription.dealhub_subscription_id`. On that observation, required when `opportunity_type` is `expansion` or `renewal`, and null when it is `new_business`. When present, that subscription's `hubspot_company_id` equals the deal's `hubspot_company_id`.

Events:

| Signal | When |
|---|---|
| `opportunity_opened` | The creation observation, with `stage` `discovery`. One per deal. `observed_at` equals `created_at`. |
| `opportunity_stage_changed` | `stage` becomes `evaluation`, `proposal`, or `negotiation`. |
| `opportunity_won` | `stage` becomes `closed_won`. At most one per deal. |
| `opportunity_lost` | `stage` becomes `closed_lost`. At most one per deal. |
| none | A later observation whose stage is unchanged. `emitted_event` is null. Amount, close date, owner, forecast, and `opportunity_type` may still change. The observation carries the type as of its `observed_at`. |

Rules:

- A deal is not both won and lost.
- Opening at `discovery` is `opportunity_opened`, not `opportunity_stage_changed`.
- Each observation carries `opportunity_type` as of `observed_at`. On an observation whose type is `new_business`, `dealhub_subscription_id` is null. On an observation whose type is `expansion` or `renewal`, `dealhub_subscription_id` is required and cites an existing subscription. That observation does not create a subscription.
- When `hubspot_contact_id` is present, the contact observation in effect at the deal's `observed_at` has the same `hubspot_company_id` as the deal.
- When `dealhub_subscription_id` is present, that subscription's `hubspot_company_id` equals the deal's `hubspot_company_id`.
- `amount` may be null. Null is an unreported amount, not zero.
- The deal contract does not emit `customer_converted`. The account's first win becomes that canonical event downstream.
- Two deals for one company are two deals when their `hubspot_deal_id` values differ, even when the names match.

### Activity

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `hubspot_activity_id` | string | no | Source identifier. | `activity.hubspot_activity_id` |
| `activity_type` | enum | no | `call`, `email`, `meeting`. | `activity.activity_type` |
| `subject` | string | yes | Short description. | `activity.subject` |
| `occurred_at` | timestamp | no | When the interaction happened. | `activity.occurred_at` |
| `hubspot_company_id` | string | yes | At least one parent is present. | Reference to the activity's account. |
| `hubspot_contact_id` | string | yes | At least one parent is present. | Reference to the activity's contact. |
| `hubspot_lead_id` | string | yes | At least one parent is present. | Reference to the activity's lead. |
| `hubspot_deal_id` | string | yes | At least one parent is present. | Reference to the activity's opportunity. |

Relationships: each parent field references that HubSpot entity's source identifier. Each is optional. At least one is present.

Events: none. The row is the activity. It does not emit a lifecycle event and it has no `observed_at`.

Rules:

- `observation_key` is `hubspot_activity_id`. The contract has no `observed_at`.
- An activity is immutable. A correction or a distinct interaction is a new `hubspot_activity_id`. A second delivery of an existing identifier is a replay only when the business attributes match. It does not rewrite the activity.
- At least one parent is present. Omitting an optional parent is valid. The contract does not require all four.
- When the activity includes `hubspot_company_id` and another parent that has a company, the company identifiers agree. The other parent's company comes from the parent observation in effect at `occurred_at`. A deal has a company. A contact or lead has a company when that observation's `hubspot_company_id` is present. A parent with no company does not constrain the activity's company.

## DealHub

DealHub owns quotes, contracts, subscriptions, and bookings. It does not create companies, contacts, leads, or deals. It references HubSpot identifiers. It does not carry firmographics. Each commercial amount stays on its own entity.

### Quote

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `dealhub_quote_id` | string | no | Source identifier. | `quote.dealhub_quote_id` |
| `quote_number` | string | no | Stable document number. Unique per quote id. | `quote.quote_number` |
| `status` | enum | no | Quote status vocabulary. | `quote.status` |
| `quoted_amount` | decimal | yes | Proposal amount. Not bookings and not ARR. | `quote.quoted_amount` |
| `observed_at` | timestamp | no | Observation time. | null. Downstream, a status or amount change starts a new quote version. |
| `hubspot_deal_id` | string | no | The deal being proposed. | Reference to the quote's opportunity. |
| `hubspot_company_id` | string | no | The firm. | Reference to the quote's account. |

Relationships:

- `hubspot_deal_id` references `hubspot.deal.hubspot_deal_id`. Required.
- `hubspot_company_id` references `hubspot.company.hubspot_company_id`. Required. It is the same company as the cited deal.

Events: none. Status and amount changes are observations.

Rules:

- A quote does not create an opportunity.
- `quoted_amount` may be null while the quote is `draft`. A quote cited by a contract has `status` `accepted` and a non-null `quoted_amount`.

### Contract

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `dealhub_contract_id` | string | no | Source identifier. | `contract.dealhub_contract_id` |
| `contract_number` | string | no | Stable document number. Unique per contract id. | `contract.contract_number` |
| `status` | enum | no | `active`, `expired`, `terminated`. | `contract.status` |
| `total_contract_value` | decimal | no | Signed agreement value. Not ARR and not the booking amount. | `contract.total_contract_value` |
| `start_date` | date | no | Agreement start. | `contract.start_date` |
| `end_date` | date | no | Agreement end. Greater than or equal to `start_date`. | `contract.end_date` |
| `observed_at` | timestamp | no | Observation time. | null. Downstream, a status, value, or term change starts a new contract version. |
| `dealhub_quote_id` | string | no | The accepted quote. | Reference to the contract's quote. |
| `hubspot_deal_id` | string | no | The won new-business deal. | Reference to the contract's opportunity. |
| `hubspot_company_id` | string | no | The firm. | Reference to the contract's account. |

Relationships:

- `dealhub_quote_id` references `dealhub.quote.dealhub_quote_id`. Required. One quote is cited by at most one contract.
- `hubspot_deal_id` references `hubspot.deal.hubspot_deal_id`. Required. One deal is cited by at most one contract.
- `hubspot_company_id` references `hubspot.company.hubspot_company_id`. Required.

Events: none.

Rules:

- The cited deal is a `new_business` deal that has emitted `opportunity_won`. Expansion and renewal do not create a contract.
- The cited quote is the accepted quote of that deal.
- The company identifier matches the company on the cited deal and the cited quote.
- A renewal may change `end_date` or `total_contract_value` on a later observation of the same `dealhub_contract_id`. That observation is not a second contract.

### Subscription

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `dealhub_subscription_id` | string | no | Source identifier. | `subscription.dealhub_subscription_id` |
| `subscription_number` | string | no | Stable document number. Unique per subscription id. | `subscription.subscription_number` |
| `status` | enum | no | `pending`, `active`, `churned`. | `subscription.status` |
| `plan_code` | string | no | Open commercial catalog. | `subscription.plan_code` |
| `seat_count` | integer | no | Minimum 0. Commercial seats, not a count of product users. | `subscription.seat_count` |
| `recurring_amount` | decimal | no | Recurring fee. Not annualized ARR. | `subscription.recurring_amount` |
| `billing_frequency` | enum | no | `monthly`, `quarterly`, `annual`. | `subscription.billing_frequency` |
| `term_start` | date | no | Current term start. | `subscription.term_start` |
| `term_end` | date | no | Current term end. Greater than or equal to `term_start`. | `subscription.term_end` |
| `observed_at` | timestamp | no | Observation time. | null. Downstream, a tracked subscription attribute change starts a new subscription version. |
| `emitted_event` | enum | yes | `subscription_renewed`, `subscription_expanded`, `subscription_churned`. | null. Downstream this chooses `lifecycle_event.event_name`. |
| `dealhub_contract_id` | string | no | Granting contract. Stable across observations of this subscription. | Reference to the subscription's contract. |
| `hubspot_company_id` | string | no | The firm. | Reference to the subscription's account. |

Relationships:

- `dealhub_contract_id` references `dealhub.contract.dealhub_contract_id`. Required. One contract may be cited by many subscriptions.
- `hubspot_company_id` references `hubspot.company.hubspot_company_id`. Required. It matches the company on the cited contract.

Events:

| Signal | When |
|---|---|
| `subscription_renewed` | A renewal observation. `status` is `active`. Many renewals may occur for one subscription. |
| `subscription_expanded` | An expansion observation. `status` is `active`. Many expansions may occur for one subscription. |
| `subscription_churned` | `status` is `churned`. One per subscription. |
| none | `status` is `pending`, or `status` is `active` and the observation is not a renewal or expansion. `emitted_event` is null. |

Rules:

- Durable status stays `active` across renewals and expansions. The event is not inferred from status alone. `emitted_event` carries it.
- A renewal or expansion may also change `term_start`, `term_end`, `recurring_amount`, or `seat_count` on that same observation.
- `pending` does not emit `subscription_renewed` or `subscription_expanded`.
- Churn does not emit a booking and does not use a negative amount.
- There is no periodic ARR snapshot in this contract. `recurring_amount` and `billing_frequency` are the ARR inputs.
- A second purchased product is a second `dealhub_subscription_id`.

### Booking

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `dealhub_booking_id` | string | no | Source identifier. | `booking.dealhub_booking_id` |
| `booking_number` | string | no | Stable document number. Unique per booking id. | `booking.booking_number` |
| `booking_type` | enum | no | `new_business`, `expansion`, `renewal`. | `booking.booking_type` |
| `booking_amount` | decimal | no | Recognized booking amount. Not ARR and not the HubSpot deal amount. | `booking.booking_amount` |
| `booked_at` | timestamp | no | When the booking was recognized. | `booking.booked_at` |
| `hubspot_company_id` | string | no | The firm. | Reference to the booking's account. |
| `hubspot_deal_id` | string | no | The deal. | Reference to the booking's opportunity. |
| `dealhub_contract_id` | string | no | The contract. | Reference to the booking's contract. |
| `dealhub_subscription_id` | string | no | The subscription. | Reference to the booking's subscription. |

Relationships: all four parent fields are required. Each references that entity's source identifier. One deal, contract, or subscription may be cited by many bookings.

Events: none. The row is the economic event. `booking_type` classifies it. There is no `observed_at` and no `emitted_event`.

Rules:

- `observation_key` is `dealhub_booking_id`. The contract has no `observed_at`.
- A booking is immutable. A correction or a later commercial event is a new `dealhub_booking_id`. A second delivery of an existing identifier is a replay only when the business attributes match. It does not rewrite the booking.
- `booking_type` equals `opportunity_type` on the deal observation in effect at `booked_at`.
- The company identifier matches the company on the cited deal, contract, and subscription.
- Churn does not create a booking. `booking_amount` is not negative.

## Marketing

Marketing owns programs, daily delivery, and attribution. It does not create firms, contacts, leads, or pipeline amounts. A lead's originating campaign is a HubSpot lead field that cites `marketing_campaign_id`.

### Campaign

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `marketing_campaign_id` | string | no | Source identifier. | `campaign.marketing_campaign_id` |
| `campaign_code` | string | no | Stable code. Unique per campaign id. | `campaign.campaign_code` |
| `campaign_name` | string | no | Program name. | `campaign.campaign_name` |
| `channel` | enum | no | Channel vocabulary. Stable for the life of the campaign. | `campaign.channel` |

Relationships: none.

Events: none.

Rules:

- History is `current`. `observation_key` is `marketing_campaign_id`. This contract has no `observed_at`. Spend and impressions are not fields on the campaign.
- A channel correction replaces the current campaign record. The contract does not keep the prior channel.

### Campaign performance

`source_identifier` and `observation_key` are `marketing_campaign_id` together with `performance_date`. There is no separate performance document id.

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `marketing_campaign_id` | string | no | Campaign. | Reference to `campaign.marketing_campaign_id`. |
| `performance_date` | date | no | Delivery day. | `campaign_performance.performance_date` |
| `spend_amount` | decimal | yes | Minimum 0 when present. | `campaign_performance.spend_amount` |
| `impression_count` | integer | yes | Minimum 0 when present. | `campaign_performance.impression_count` |
| `click_count` | integer | yes | Minimum 0 when present. | `campaign_performance.click_count` |

Relationships:

- `marketing_campaign_id` references `marketing.campaign.marketing_campaign_id`. Required. One campaign has many days.

Events: none.

Rules:

- `observation_key` is `marketing_campaign_id` plus `performance_date`. The contract has no `observed_at`.
- One row is one campaign-day. A second delivery of the same pair with the same measures is a replay. A second delivery that changes the measures replaces that campaign-day. It does not create a second row.
- Null on a measure means the source did not report it. Null is not zero.
- The contract does not require `click_count` to be less than or equal to `impression_count`.

### Touch

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `marketing_touch_source_id` | string | no | Source identifier. | `marketing_touch.marketing_touch_source_id` |
| `occurred_at` | timestamp | no | When the touch happened. | `marketing_touch.occurred_at` |
| `marketing_campaign_id` | string | no | The program. | Reference to the touch's campaign. |
| `hubspot_contact_id` | string | yes | At least one of the three HubSpot parents is present. | Reference to the touch's contact. |
| `hubspot_lead_id` | string | yes | At least one of the three HubSpot parents is present. | Reference to the touch's lead. |
| `hubspot_company_id` | string | yes | At least one of the three HubSpot parents is present. | Reference to the touch's account. |

Relationships:

- `marketing_campaign_id` references `marketing.campaign.marketing_campaign_id`. Required.
- Each HubSpot field references that entity's source identifier. Each is optional. At least one is present.

Events: none. The row is the attribution event. It has no `observed_at`.

Rules:

- `observation_key` is `marketing_touch_source_id`. The contract has no `observed_at`.
- A touch is immutable. A correction is a new `marketing_touch_source_id`. A second delivery of an existing identifier is a replay only when the business attributes match. It does not rewrite the touch.
- When the touch includes `hubspot_company_id` and a cited lead or contact has a company, the company identifiers agree, using the lead or contact observation in effect at `occurred_at`. Omitting an optional HubSpot parent is valid.
- Marketing does not create the contact, lead, or company it cites.

## Product

Product owns the firm as a tenant, the product login, the workflow catalog, usage, and outcomes. It does not own sales stage, bookings, or ARR inputs. It does not create a HubSpot contact. It does not emit `adoption_reached`.

### Firm

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `product_firm_id` | string | no | Source identifier. | `account.product_firm_id` |
| `firm_name` | string | no | Product's name for the tenant. | `account.firm_name` only while no HubSpot company is linked. |
| `primary_domain` | string | yes | Lowercase host when present. | `account.primary_domain` for cross-system matching. |
| `state` | string | yes | Open text. | `account.state` only while no HubSpot company is linked. |

Relationships: none. The same firm as a HubSpot company shares `primary_domain`. The Product contract does not store `hubspot_company_id`.

Events: none.

Rules:

- History is `current`. `observation_key` is `product_firm_id`. This contract has no `observed_at`. Tracked firmographic history arrives on HubSpot company observations once a company is linked.
- Product `firm_name` and `primary_domain` may differ from HubSpot. Both are stored on their own contracts. Equal domains are the only cross-system firm match. Unequal domains, or a missing domain, remain two accounts downstream.
- The contract does not deduplicate two Product firms that share a name or a domain.

### User

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `product_user_source_id` | string | no | Source identifier. | `product_user.product_user_source_id` |
| `email_normalized` | string | yes | Lowercase trimmed email when present. | `product_user.email_normalized` |
| `status` | enum | no | `invited`, `active`, `inactive`. | `product_user.status` |
| `observed_at` | timestamp | no | Observation time. | null. Downstream, a status, firm, or email change starts a new product-user version. |
| `product_firm_id` | string | no | The tenant. | Reference to the product user's account. |

Relationships:

- `product_firm_id` references `product.firm.product_firm_id`. Required. Many users may cite one firm.

Events: none. Status changes are observations. Product user status does not choose a lifecycle event.

Rules:

- The contract does not include `hubspot_contact_id`. A matching contact is a downstream link.
- The same `email_normalized` may appear on two `product_user_source_id` values, including at different firms. The contract does not merge them and does not contain a survivor link.
- The same `product_user_source_id` may cite a different `product_firm_id` on a later observation.
- A user without an email is valid and cannot match another user or a contact by email.

### AI workflow

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `product_workflow_id` | string | no | Source identifier. | `ai_workflow.product_workflow_id` |
| `workflow_code` | string | no | Stable code. Unique per workflow id. Open catalog. | `ai_workflow.workflow_code` |
| `workflow_name` | string | no | Capability name. | `ai_workflow.workflow_name` |

Relationships: none. A workflow is not owned by a firm.

Events: none.

Rules:

- History is `current`. `observation_key` is `product_workflow_id`. This contract has no `observed_at`. Usage history is the usage contract.
- Example capabilities are intake, medical chronology, and demand-letter drafting. The contract does not close that list.

### Usage

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `product_usage_source_id` | string | no | Source identifier. | `product_usage.product_usage_source_id` |
| `occurred_at` | timestamp | no | When the run happened. | `product_usage.occurred_at` |
| `work_unit_count` | integer | no | Minimum 1. A single run is 1. Not an adoption score. | `product_usage.work_unit_count` |
| `product_user_source_id` | string | no | The login. | Reference to the usage's product user. |
| `product_firm_id` | string | no | The tenant. | Reference to the usage's account. |
| `product_workflow_id` | string | no | The capability. | Reference to the usage's workflow. |

Relationships: all three parents are required and reference that Product entity's source identifier.

Events: none as `emitted_event`. Each row is the `product_usage` lifecycle event. It is not repeated on a lifecycle-event contract.

Rules:

- `observation_key` is `product_usage_source_id`. The contract has no `observed_at`.
- A usage row is immutable. A correction is a new `product_usage_source_id`. A second delivery of an existing identifier is a replay only when the business attributes match. It does not rewrite the usage.
- `product_firm_id` is the firm cited by that `product_user_source_id` observation in effect at `occurred_at`.
- Seat count on a subscription does not constrain `work_unit_count` or the number of users.

### Outcome

| Field | Type | Null | Constraints | Maps to |
|---|---|---|---|---|
| `product_outcome_source_id` | string | no | Source identifier. | `product_outcome.product_outcome_source_id` |
| `occurred_at` | timestamp | no | When the outcome completed. | `product_outcome.occurred_at` |
| `outcome_type` | enum | no | `draft_completed`, `review_accepted`, `exported`. | `product_outcome.outcome_type` |
| `product_usage_source_id` | string | no | The run. Unique among outcomes. | Reference to the outcome's usage. |
| `product_user_source_id` | string | no | The login on that run. | Reference to the outcome's product user. |
| `product_firm_id` | string | no | The tenant on that run. | Reference to the outcome's account. |
| `product_workflow_id` | string | no | The capability on that run. | Reference to the outcome's workflow. |

Relationships:

- `product_usage_source_id` references `product.usage.product_usage_source_id`. Required. At most one outcome cites a usage.
- The user, firm, and workflow fields reference those Product source identifiers and are required.

Events: none as `emitted_event`. The row is the completed result. The account's first outcome becomes canonical `adoption_reached` downstream. This contract does not contain that event, an adoption score, or a product-user adoption event.

Rules:

- `observation_key` is `product_outcome_source_id`. The contract has no `observed_at`.
- An outcome is immutable. A correction is a new `product_outcome_source_id`. A second delivery of an existing identifier is a replay only when the business attributes match. It does not rewrite the outcome.
- `occurred_at` is at or after the cited usage's `occurred_at`.
- The user, firm, and workflow equal the same fields on the cited usage.
- Adoption grain is one canonical event per account, derived from the first outcome. The alternative, one adoption event per product user, is not a source field.

## Cross-contract rules

`contracts/source/README.md` states these rules in one place. Each YAML file repeats the sentences that bind its own fields.

- A relationship value, when present, equals a source identifier defined by the referenced contract in the same dataset.
- When a deal observation has `hubspot_contact_id`, the contact observation in effect at the deal's `observed_at` has the same `hubspot_company_id`. When a deal observation has `dealhub_subscription_id`, that subscription's `hubspot_company_id` equals the deal's. When an activity or a touch includes `hubspot_company_id` and another parent that has a company, the company identifiers agree, using the parent observation in effect at `occurred_at`. Omitting an optional parent stays valid.
- Referential order for a valid dataset is campaigns and AI workflows, then HubSpot companies and Product firms, then contacts and product users, then leads and touches, then deals, then activities that cite a deal, then quotes, contracts, subscriptions, and bookings, then usage and outcomes. A parent source identifier exists before a child cites it.
- HubSpot company and Product firm are the same firm downstream only when `primary_domain` is present and equal. The source contracts do not perform that match.
- HubSpot wins firmographics when a company is linked. Product firm fields remain on the Product contract either way.
- A product user email does not create a contact. The Product user contract has no contact identifier.
- DealHub amounts, HubSpot `amount`, and Marketing `spend_amount` are separate fields. No contract copies one onto another.
- Opportunity `expected_close_date` and contract `start_date` are different fields. Both may be present and they may differ.
- Account `owner_name` on the company and deal `owner_name` are different fields. Both may be present and they may differ.
- Subscription `seat_count` and the number of product users are different quantities.
- A lead and an account are different source records. Conversion cites `hubspot_deal_id`. It does not rewrite the lead into a company.
- New business produces one contract from one accepted quote and one or many subscriptions. Expansion and renewal keep the subscription and may update the existing contract. They do not create a contract.
- One `lead_created` and one `opportunity_opened` exist for each lead and deal that exist. Won and lost are mutually exclusive. Churn is at most once per subscription. Renewals and expansions may repeat.
- Canonical identity resolution, survivorship, and effective-dated versions are downstream of these contracts. Source duplicates remain separate source identifiers.

## Inconsistencies the contracts preserve

The README reproduces this catalog. Each contract's `rules` include the items that apply to it.

1. HubSpot `hubspot_lifecycle_stage` is an unconstrained source label. It is not canonical `commercial_status`.
2. HubSpot `amount`, DealHub `quoted_amount`, `total_contract_value`, `booking_amount`, and `recurring_amount`, and Marketing `spend_amount`, use different names and stay on different entities.
3. Product `firm_name` and `primary_domain` may disagree with the HubSpot company. Domain equality is not enforced inside either contract.
4. `primary_domain` and `email_normalized` are nullable. Duplicate values across source identifiers are valid.
5. A lead may omit its company and contact. A deal may omit its contact, lead, amount, close date, and forecast. An activity or touch may omit any optional parent. When that row also includes `hubspot_company_id`, a parent that has a company uses that same company.
6. Marketing measures are independently nullable, and clicks may exceed impressions.
7. Subscription renewal and expansion are `emitted_event` values while `status` stays `active`. Status alone does not mean renewal.
8. Timestamps are not one column. Creation, observation, occurrence, booking, performance day, and term dates stay distinct. Dates have no time. Timestamps are UTC.
9. Product users are not contacts and are not seats. Usage does not carry a commercial amount.
10. A booking, activity, touch, usage, or outcome is not rewritten in place. A correction of one of those events is a new source identifier. A business change on an observation is a new `observed_at` for the same source identifier, not an effective-dated canonical row. A campaign-day correction replaces that day's measures. A current-row correction replaces the current record.
11. A replay is a new `delivery_id` for an existing `observation_key` whose business attributes match. A different payload at that key is not a replay and is not a second business event. It is invalid except for an in-place correction of a current row or of one campaign-day's measures.
12. The contracts do not contain ARR, retention, pipeline coverage, win rate, or adoption score.

## Assumptions and source limitations

The README records these as assumptions inherited from the approved model.

- Amounts are US dollars. There is no second currency and no foreign-exchange rate.
- Missing optional values are null, not empty strings.
- A solo firm can be one HubSpot company and one contact. The source contracts do not require a contact for every company.
- A lead converts to at most one deal. A deal comes from at most one lead.
- Sales owner is a name. There is no employee, calendar, invoice, or payment source.
- There is no partial downsell source record. Churn ends a subscription. Expansion increases it.
- `practice_focus`, `plan_code`, and the workflow catalog are open.
- `state` is open text for a US state, not a closed list of postal codes.
- Product firm history before a HubSpot company is linked is only the current Product firm record.
- Campaign channel history is only the current campaign record. Daily delivery is the campaign-day fact.
- Customer conversion and adoption are not source records. Generators later emit the winning deal and the product outcome. They do not emit those two derived events.
- Apollo and Clay are not source systems in this contract set.
- These files do not annualize `recurring_amount`. The annualization formula is later metric work.
- These files do not validate a generated dataset. DATA-005 owns that validation. The rules above are the expectations that validation can enforce.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is true. The implementation adds only the files named in `affected_contracts`.
- Follow the merged DATA-001 model. Field names for business attributes are the mapping attributes in the synthetic data strategy. Do not invent a second physical name for the same attribute.
- Keep HubSpot, DealHub, Marketing, and Product as separate contracts. Do not normalize them into canonical entity files, staging models, or a single account schema.
- Preserve the inconsistencies in the catalog. Do not silently coerce them into canonical values.
- Do not add generator code, generated data, orchestration, or dbt models.
- Do not edit `docs/data-model/` or `specs/DATA-001-design-canonical-gtm-data-model.md`.
- One owning agent, `data-engineer`, writes the contracts.
- Human approval is required. `delivery.deployment_required` is false.
- `environment.isolated_schema` is false. No warehouse schema is created.
- `testing.component_tests`, `testing.integration_tests`, and `testing.end_to_end_tests` are false. The repository has no contract test runner, and DATA-005 is the issue that validates generated records. Completeness of this task is a review of the contract files against the acceptance criteria.

## Acceptance criteria

- [ ] The files listed in `affected_contracts` exist, and they are the only files the implementation adds or edits.
- [ ] `contracts/README.md` still describes component ownership and points to `contracts/source/README.md`.
- [ ] HubSpot, DealHub, Marketing, and Product each have the source entities in the inventory. Apollo, Clay, `lifecycle_event`, and a customer object have no source contract.
- [ ] Every business field in the entity sections is present with the stated type, nullability, constraints, and `maps_to`.
- [ ] Every contract includes `source_system`, `delivery_id`, and `ingested_at` as ingestion metadata with `maps_to` null.
- [ ] Every contract states `history`, a row-grain sentence, `source_identifier`, and `observation_key`. The key is the source identifier plus `observed_at` for `observation`, the source identifier for `current` and for a single-identifier `immutable` entity, and `marketing_campaign_id` plus `performance_date` for campaign performance.
- [ ] Source identifiers and document numbers follow the identifier rules. Canonical surrogate keys, `surviving_*` fields, `commercial_status`, and effective-dating columns are absent.
- [ ] Relationship fields reference source identifiers, state whether they are required, and do not embed parent payloads.
- [ ] Lead, deal, and subscription document `emitted_event` and the choosing rules in those sections. `working`, `pending`, and a non-event `active` observation emit no lifecycle signal. Renewal and expansion are explicit while status stays `active`.
- [ ] Activity, booking, touch, usage, and outcome are immutable rows. A correction of one of them is a new source identifier. A second delivery of an existing identifier matches the stored business attributes. Usage is the product-usage event. Outcome does not contain `adoption_reached`. Booking does not contain churn.
- [ ] Closed vocabularies match the frozen working values. Open catalogs remain unconstrained strings. `hubspot_lifecycle_stage` is not the canonical commercial-status enum.
- [ ] The README and the entity rules document the inconsistency catalog, the cross-contract referential rules, the assumptions, and the source limitations.
- [ ] No field stores ARR, retention, pipeline coverage, win rate, adoption score, or an amount copied from another source entity.
- [ ] `docs/data-model/`, `data-generation/`, `warehouse/`, `analytics/`, and `orchestration/` are unchanged.

## Execution notes

Implement this specification only after it has merged and the issue label is `status:ready`. Use an `impl` worktree. Write the contract files. Leave this specification unchanged unless a human changes the approved requirements.

Read the data-modeling skill before writing keys, grain, and source-to-canonical mappings. Read the data-quality skill before writing nullability, uniqueness, allowed values, and referential rules. Read `docs/data-model/source-mapping.md` and the synthetic data strategy in `docs/data-model/decisions.md` as the logical schema this task makes physical. Read the data-generation skill only as a constraint: a later generator must be able to emit referentially consistent observations from these contracts. Do not write that generator.

The frozen vocabulary, the account-level adoption derivation, and the subscription-observation approach to revenue history are inputs from the merged DATA-001 design. Do not replace them in the contracts.

Review the YAML files against the README before opening the implementation pull request. Check that field names, types, nullability, keys, relationships, and event rules agree across the files, and that no canonical or metric field has been added.

Validation of this task is a review of the contract files against the acceptance criteria. No component, integration, or end-to-end test is required. No isolated schema is required. No deployment is required.
