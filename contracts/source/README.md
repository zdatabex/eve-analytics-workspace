# Source schemas and data contracts

Physical source schemas for the synthetic GTM foundation. Each file under this directory is the schema and the field-level contract for one logical source entity. Generators, generated datasets, and dbt models are later work. These files do not collapse HubSpot, DealHub, Marketing, and Product into canonical tables.

Canonical surrogate keys, effective dating (`effective_start`, `effective_end`, `is_current`), derived lifecycle events (`customer_converted`, `adoption_reached`, and any `lifecycle_event` payload), and business metrics (calculated ARR, net retention, pipeline coverage, win rate, and adoption score) are not source fields.

The approved canonical model stays in `docs/data-model/`. This directory freezes the working vocabulary, one downstream `adoption_reached` event per account, and ARR history reconstructed later from subscription observations. There is no periodic ARR snapshot in these contracts.

A YAML file repeats the ingestion fields, relationships, events, and rules that apply to that entity. This README is the index and the cross-entity rule set.

## Source inventory

| File | Source identifier | History | Canonical entity | Row grain |
|---|---|---|---|---|
| `hubspot/company.yaml` | `hubspot_company_id` | observation | `account` | One observation of one HubSpot company at one `observed_at`. |
| `hubspot/contact.yaml` | `hubspot_contact_id` | observation | `contact` | One observation of one HubSpot contact at one `observed_at`. |
| `hubspot/lead.yaml` | `hubspot_lead_id` | observation | `lead` | One observation of one HubSpot lead at one `observed_at`. |
| `hubspot/deal.yaml` | `hubspot_deal_id` | observation | `opportunity` | One observation of one HubSpot deal at one `observed_at`. |
| `hubspot/activity.yaml` | `hubspot_activity_id` | immutable | `activity` | One sales activity. |
| `dealhub/quote.yaml` | `dealhub_quote_id` | observation | `quote` | One observation of one DealHub quote at one `observed_at`. |
| `dealhub/contract.yaml` | `dealhub_contract_id` | observation | `contract` | One observation of one DealHub contract at one `observed_at`. |
| `dealhub/subscription.yaml` | `dealhub_subscription_id` | observation | `subscription` | One observation of one DealHub subscription at one `observed_at`. |
| `dealhub/booking.yaml` | `dealhub_booking_id` | immutable | `booking` | One recognized booking. |
| `marketing/campaign.yaml` | `marketing_campaign_id` | current | `campaign` | One marketing campaign. |
| `marketing/campaign_performance.yaml` | `marketing_campaign_id` and `performance_date` | immutable | `campaign_performance` | One campaign on one day. |
| `marketing/touch.yaml` | `marketing_touch_source_id` | immutable | `marketing_touch` | One attribution touch. |
| `product/firm.yaml` | `product_firm_id` | current | `account` | One Product firm. |
| `product/user.yaml` | `product_user_source_id` | observation | `product_user` | One observation of one product user at one `observed_at`. |
| `product/ai_workflow.yaml` | `product_workflow_id` | current | `ai_workflow` | One AI workflow. |
| `product/usage.yaml` | `product_usage_source_id` | immutable | `product_usage` | One usage of one AI workflow by one product user. |
| `product/outcome.yaml` | `product_outcome_source_id` | immutable | `product_outcome` | One outcome of one product usage event. |

There is no source contract for `lifecycle_event`, for `account` as a merged firm, or for a customer object. `customer_converted` and `adoption_reached` are canonical events derived downstream. Product usage remains the usage row. It is not also a `lifecycle_event` payload. Apollo and Clay are future enrichment sources. They do not have contracts in this set.

## Contract file shape

Every YAML file has `id`, `title`, `source_system`, `source_entity`, `canonical_entity`, `history`, `grain`, `source_identifier`, `observation_key`, `fields`, `ingestion`, `relationships`, `events`, and `rules`.

`history` is `observation`, `current`, or `immutable`.

`fields` entries have `name`, `type`, `nullable`, `maps_to`, and `description`. A closed set also has `allowed_values`. `maps_to` is the canonical `entity.attribute` the field feeds, or null when the field is a source signal or a relationship that is not itself a canonical attribute. `ingestion` entries use the same field shape and always have `maps_to: null`.

`relationships` entries name the local field, the referenced `source_system.source_entity.field`, whether the field is required, and the cardinality in source terms. A conditional requirement is `required: false` plus a `requirement` sentence.

`events` entries name a lifecycle signal and the condition that emits it. `rules` entries are the entity-specific integrity and inconsistency sentences.

## Ingestion envelope

Every contract includes these three fields. They are platform delivery metadata. They are not canonical business attributes and they do not open a canonical Type 2 version by themselves. They are not part of `observation_key`.

| Field | Type | Null | Description |
|---|---|---|---|
| `source_system` | enum | no | `hubspot`, `dealhub`, `marketing`, or `product`. The value equals that file's `source_system`. |
| `delivery_id` | string | no | The extraction batch. Many rows may share one `delivery_id`. A replay uses a new `delivery_id` and the same business attributes. |
| `ingested_at` | timestamp | no | When this delivery was accepted. It may be later than `observed_at`, `occurred_at`, or `booked_at`. Late delivery is valid. |

## History classes

Source records do not carry `effective_start`, `effective_end`, `is_current`, canonical surrogate keys, or `surviving_*` links. Canonical effective dating is downstream. `observed_at` on an observation is the time that later becomes `effective_start` of a new canonical version. The source row is not that version.

The observation of a source identifier in effect at a timestamp is the row with that identifier whose `observed_at` is the latest at or before that timestamp. If no row of that identifier has `observed_at` at or before the timestamp, no observation is in effect, and a rule that requires one is not satisfied.

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

## Type system

| Type | Meaning |
|---|---|
| `string` | Unicode text. A required string is present and non-empty. A missing value is null, not an empty string. |
| `enum` | A string whose `allowed_values` are the frozen working vocabulary. No other value is valid. |
| `decimal` | A non-negative base-10 amount in US dollars with at most two fraction digits. The contract forbids a binary float. There is no currency field. |
| `integer` | A whole number. Each field states its minimum. |
| `date` | An ISO-8601 calendar date. No time and no timezone. |
| `timestamp` | An ISO-8601 timestamp in UTC. |

## Identifier rules

Source identifiers are opaque non-empty strings issued by the source system. They are not canonical surrogate keys. The expected shape is an assumption: HubSpot identifiers are numeric strings, DealHub identifiers are prefixed strings, and Marketing and Product identifiers are opaque strings. The contract accepts any non-empty string. It does not reject a value solely for its shape.

`quote_number`, `contract_number`, `subscription_number`, `booking_number`, `campaign_code`, and `workflow_code` are required. Each is stable across observations of the same source identifier and unique across different source identifiers of that entity.

`email_normalized`, when present, is lowercase and trimmed. `primary_domain`, when present, is a lowercase host with no scheme and no path. Those constraints describe the match keys the approved model uses. They do not merge records inside the source contract. Duplicate emails and duplicate domains are valid source data.

## Closed vocabularies

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
| Lead `emitted_event` | `lead_created`, `lead_qualified`, `lead_disqualified`, `lead_converted` |
| Deal `emitted_event` | `opportunity_opened`, `opportunity_stage_changed`, `opportunity_won`, `opportunity_lost` |
| Subscription `emitted_event` | `subscription_renewed`, `subscription_expanded`, `subscription_churned` |

`practice_focus`, `plan_code`, `workflow_code`, `workflow_name`, `state`, `owner_name`, display names, and `hubspot_lifecycle_stage` stay open strings. `hubspot_lifecycle_stage` is not the canonical `commercial_status` enum and is not constrained to `prospect`, `customer`, or `former_customer`.

`working` does not emit a lead event. `pending` and `active` do not by themselves emit a subscription event. Renewal and expansion are explicit signals on a subscription observation whose status remains `active`.

## Fields that no source contract contains

- Canonical surrogate keys such as `account_id`, `contact_id`, `lead_id`, `opportunity_id`, `quote_id`, `contract_id`, `subscription_id`, `booking_id`, `campaign_id`, `campaign_performance_id`, `marketing_touch_id`, `activity_id`, `product_user_id`, `ai_workflow_id`, `product_usage_id`, `product_outcome_id`, and `lifecycle_event_id`.
- `surviving_account_id`, `surviving_contact_id`, `surviving_lead_id`, `surviving_opportunity_id`, `surviving_subscription_id`, and `surviving_product_user_id`.
- `commercial_status`, `effective_start`, `effective_end`, and `is_current`.
- `customer_converted`, `adoption_reached`, and any `lifecycle_event` payload. The source signal is `emitted_event` or the immutable row itself.
- Calculated ARR, net retention, pipeline coverage, win rate, adoption score, or any amount copied from one source entity onto another.

Relationship fields store the parent source identifier. They do not embed the parent record.

## Cross-contract relationship and referential rules

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
- The observation that emits `opportunity_won` produces one contract when that observation has `opportunity_type` `new_business` and `stage` `closed_won`, from one accepted quote and one or many subscriptions. The contract's `hubspot_deal_id` is that deal. A later observation of the same deal may change `opportunity_type`, and a later contract observation may change `total_contract_value` or `end_date`, without removing the contract. A deal whose winning observation is `expansion` or `renewal` keeps the subscription and may update the existing contract. It does not create a contract. The type that creates the contract is the type on that winning observation. A later deal observation, and the deal observation in effect at a later contract `observed_at`, leave that decision unchanged. `booking_type` equals `opportunity_type` on the deal observation in effect at `booked_at`.
- One `lead_created` and one `opportunity_opened` exist for each lead and deal that exist. Won and lost are mutually exclusive. Churn is at most once per subscription. Renewals and expansions may repeat.
- Canonical identity resolution, survivorship, and effective-dated versions are downstream of these contracts. Source duplicates remain separate source identifiers.

## Inconsistencies the contracts preserve

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
- HubSpot identifiers are expected to be numeric strings, DealHub identifiers prefixed strings, and Marketing and Product identifiers opaque strings. Shape is not a rejection rule.
