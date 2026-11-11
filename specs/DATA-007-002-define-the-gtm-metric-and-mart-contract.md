---
id: DATA-007-002
title: Define the GTM metric and mart contract
type: design
agent: analytics-engineer
skills:
  - data-modeling
  - dbt-development
  - using-dbt-for-analytics-engineering
priority: critical
components: []
dependencies:
  - DATA-001
requires_approval: true
allowed_paths:
  - docs/data-model/
excluded_paths:
  - contracts/
  - data-generation/
  - data/
  - warehouse/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - tests/
  - docs/architecture/
  - docs/development/
  - specs/
contracts:
  changes_required: false
  affected_contracts: []
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

Write the metric and mart contract for the four GTM demo questions, and present it for human approval before any mart is built.

The work product is `docs/data-model/metric-contract.md`. It states each metric's name, grain, formula, source entities, and owning mart. It also states the shared lifecycle-event column contract. Human approval of that document is the gate for later mart issues.

## Business context

GitHub issue #26 (`DATA-007-002 — Define the GTM metric and mart contract`) is a design issue. It depends on DATA-001. It does not depend on DATA-007-001 and does not wait for the dbt project.

The canonical model in `docs/data-model/` is the source of entities, grains, keys, history, and events. This task adds formulas only. It does not reopen entity design, stage vocabulary, identity rules, or source mapping.

The company is the fictional AI-native B2B SaaS vendor from DATA-001. The customer is a plaintiff law firm. Amounts are US dollars. There is no second currency.

The four questions are:

1. Which marketing channels and campaigns generate the most valuable pipeline?
2. How effectively is Sales converting opportunities into revenue?
3. Does adoption of Eve's AI-powered workflows translate into customer value and retention?
4. How healthy is the overall GTM engine?

`components` is empty. The files in scope are design documents under `docs/data-model/`, and `docs` is not a component in `workspace.yaml`. This specification lists no component, so `testing.integration_tests` is false.

## Scope

The implementation writes `docs/data-model/metric-contract.md` and adds a pointer from the existing data-model documents to that file. It covers:

1. One definition each for sourced pipeline, influenced pipeline, bookings, ARR, adoption, customer value, and retention.
2. The mart that owns each metric, and the rule that the executive scorecard reuses those definitions.
3. The shared column contract for domain lifecycle-event models.
4. Annualization of `recurring_amount` by `billing_frequency`, and the account-month snapshot as a mart grain.
5. The working decisions below, written so a human can approve or replace them before any mart issue starts.

This specification stops at the design document. Later issues own warehouse models, semantic topics, and demo pages.

| Issue | Owns |
|---|---|
| DATA-007-001 | dbt project initialization, raw sources, the date spine, and shared macros. Independent of this task. |
| Later mart issues | dbt models that implement this contract, after a human has approved `metric-contract.md`. |
| Later analytics work | Hex and Omni assets, owned by `analyst`. |

Orchestration, infrastructure, deployment, source contracts, and data generation are outside this task.

## Deliverables

Create `docs/data-model/metric-contract.md`. Add the two pointer sentences named under Pointers. Those edits are the complete file set.

The contract uses the canonical names in `entities.md`. It does not assign dbt model filenames, SQL, or warehouse types. A mart name in this contract is the business mart that owns the metric.

### Shared rules

The contract states these rules once and uses them in every formula:

- Metrics count surviving entities. A row with a `surviving_<entity>_id` is excluded. Lead, contact, and opportunity references resolve to the surviving lead, contact, and opportunity before a match.
- The pipeline amount of an opportunity is `opportunity.amount` on the effective-dated row in effect at the as-of time. `effective_start` is inclusive and `effective_end` is exclusive. The current row is the row whose `effective_end` is open. `quoted_amount`, `total_contract_value`, `booking_amount`, `recurring_amount`, and annualized ARR are not the pipeline amount.
- The current sales and marketing marts use the current opportunity row. An account-month reading uses the row in effect at month end.
- Month membership is the calendar month of the stored timestamp. Month end is the last moment of that calendar month. This contract does not add a timezone conversion or a calendar entity.
- Money measures are US dollars. Adoption is 1 or 0. Retention is a ratio. Usage measures are counts.
- `seat_count`, `plan_code`, `forecast_category`, quote attributes, and activity attributes do not enter the formulas below.

### Metric definitions

Each metric is defined once. The contract gives each metric a section with its name, grain, formula, source entities, and owning mart.

#### `pipeline_amount`

- Grain: one surviving opportunity at an as-of time.
- Formula: `amount` on the opportunity version in effect at that time.
- Source entities: `opportunity`.
- Owning mart: sales. Marketing and the executive scorecard reuse this amount.

#### `sourced_pipeline`

- Grain: one campaign. One row represents one campaign.
- Formula: the sum of `pipeline_amount` for surviving opportunities whose surviving lead has `originating_campaign_id` equal to that campaign. The as-of time is the current opportunity row.
- An opportunity has at most one lead, and a lead has at most one originating campaign, so an opportunity contributes to at most one campaign.
- An opportunity with no lead, or a lead with no originating campaign, contributes to no campaign.
- The sum includes every current stage. A reading limited to `discovery`, `evaluation`, `proposal`, and `negotiation` is the same amount with that stage filter applied. `forecast_category` does not filter the sum.
- Channel totals group the same campaign measure by `campaign.channel`. Channel is an attribute of the campaign, not a second formula.
- Source entities: `opportunity`, `lead`, `campaign`.
- Owning mart: marketing.

#### `influenced_pipeline`

- Grain: one campaign.
- A campaign influences an opportunity when at least one `marketing_touch` for that campaign shares the opportunity's surviving `lead_id` or `primary_contact_id`, and `marketing_touch.occurred_at` is at or before the opportunity's `created_at`. A touch that does not share that lead or primary contact does not attach, including a touch that has only an account.
- Formula: the sum of `pipeline_amount` for distinct surviving opportunities influenced by that campaign. The full pipeline amount is added to each influencing campaign. There is no fractional split. The same opportunity is counted once per campaign.
- Sourced pipeline and influenced pipeline stay separate. They are not added together. An opportunity may appear in both, including on its originating campaign.
- The same open-stage filter used for sourced pipeline may be applied. It remains a filter on `pipeline_amount`.
- Source entities: `opportunity`, `marketing_touch`, `campaign`, `lead`, `contact`.
- Owning mart: marketing.

#### `bookings`

- Grain: the sum is defined on `booking`. The sales mart stores it at opportunity grain: one row represents one surviving opportunity, and the value is the sum of `booking_amount` for that opportunity's bookings.
- Formula: the sum of `booking.booking_amount`.
- `booking_type` slices that sum into `new_business`, `expansion`, and `renewal`. `expansion_bookings` is the `expansion` slice. It is the same bookings formula.
- An account-month reading sums `booking_amount` for bookings whose `booked_at` falls in the month and whose account is that account.
- Churn does not create a booking. A correction is another booking and is included when its own `booking_amount` is summed.
- Source entities: `booking`. The opportunity, account, contract, and subscription foreign keys select the grain. They do not replace `booking_amount`.
- Owning mart: sales.

#### `arr`

- Grain: one subscription version, then summed to one account at an as-of time. The Customer Success mart stores account ARR at month end. One row of that mart represents one account in one calendar month.
- Annualization of the version's `recurring_amount`:

| `billing_frequency` | Annualized amount |
|---|---|
| `monthly` | `recurring_amount * 12` |
| `quarterly` | `recurring_amount * 4` |
| `annual` | `recurring_amount` |

- A version contributes that annualized amount only when its `status` is `active`. A `pending` or `churned` version contributes zero.
- The version in effect follows the Type 2 rule: `effective_start` inclusive, `effective_end` exclusive, and an open end for the current row.
- Account ARR at a time is the sum of those contributions for the account's surviving subscriptions.
- Account-month ARR is account ARR at month end.
- The account-month snapshot is a mart built from subscription history. It is not a canonical entity, not a row in `erd.md`, and not a periodic ARR fact.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

#### `retained_arr`

- Grain: one account in one calendar month.
- Formula: for each surviving subscription that is `active` at the prior month end and still `active` at this month end, add the annualized amount of the version in effect at the prior month end. A subscription that is `churned` or otherwise not `active` at this month end contributes zero. A subscription that was not `active` at the prior month end contributes zero.
- An increase in `recurring_amount` during the month stays out of `retained_arr`. That increase is recognized through `expansion_bookings`.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

#### `beginning_arr`

- Grain: one account in one calendar month.
- Formula: `arr` at the prior month end. It is the ARR metric at another as-of time.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

#### `customer_value`

- Grain: one account in one calendar month.
- Formula: `retained_arr` plus `expansion_bookings` for that account-month.
- `retained_arr` is the stock defined above. `expansion_bookings` is the flow of `booking_amount` with `booking_type = expansion` and `booked_at` in the month. The contract adds them because that sum is the customer-value definition for the retention question.
- Source entities: `subscription`, `booking`, `account`.
- Owning mart: Customer Success.

#### `retention`

- Grain: one account in one calendar month.
- Formula: `retained_arr / beginning_arr`.
- When `beginning_arr` is zero, `retention` is null.
- Logo retention, net revenue retention, and any other ratio are not this metric.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

#### `adoption`

- Grain: one account. The event grain remains one `adoption_reached` event per account, ordered by that account's first `product_outcome` of any `outcome_type`, with `subject_entity` of `account` and no product user on the event.
- Formula: the account has adopted when that event exists.
- The Customer Success mart stores the account-month reading: 1 when `adoption_reached.occurred_at` is at or before month end, otherwise 0. That flag is the monthly reading of the same event.
- Source entities: `lifecycle_event`, `product_outcome`, `account`.
- Owning mart: Customer Success.

#### `usage_work_units` and `outcome_count`

- Grain: one account in one calendar month.
- `usage_work_units` is the sum of `product_usage.work_unit_count` for that account whose `occurred_at` falls in the month.
- `outcome_count` is the count of `product_outcome` rows for that account whose `occurred_at` falls in the month.
- These measures describe usage intensity. They are not `adoption`, not an adoption score, and they are not copied onto `lifecycle_event`.
- Source entities: `product_usage`, `product_outcome`, `account`.
- Owning mart: Customer Success.

#### Sales conversion

The sales question is answered from the sales mart without a second pipeline or bookings formula.

- `is_won` is 1 when the surviving opportunity has its `opportunity_won` event, and 0 otherwise. Current stage `closed_won` is the choosing value for that event. The metric is the event.
- An opportunity's revenue is its `bookings`. Its pipeline comparison uses `pipeline_amount` on the same row.
- A later aggregate win rate counts opportunities with `opportunity_won` divided by opportunities with `opportunity_won` or `opportunity_lost`. That aggregate is a count of those events. It does not recompute `bookings` or `pipeline_amount`. The executive scorecard does not define its own win rate.

### Mart ownership

| Mart | Grain | Metrics it owns |
|---|---|---|
| Marketing | One row represents one campaign. | `sourced_pipeline`, `influenced_pipeline`. |
| Sales | One row represents one surviving opportunity. | `pipeline_amount`, `bookings`, the `booking_type` slices, `is_won`. |
| Customer Success | One row represents one account in one calendar month. | `arr`, `retained_arr`, `beginning_arr`, `expansion_bookings`, `customer_value`, `retention`, `adoption`, `usage_work_units`, `outcome_count`. |
| Executive scorecard | One row represents one account in one calendar month. | None. It reads the domain marts. |

The marketing mart may carry the campaign's summed `spend_amount`, `impression_count`, and `click_count` from `campaign_performance` as context. Those columns are not pipeline, and the contract does not define a return on spend.

The sales mart may carry quote and activity attributes as context for the sales question. Context includes the current `quoted_amount` and activity counts. Those columns are not metrics. Quote and activity do not enter sourced pipeline, influenced pipeline, bookings, ARR, retention, adoption, customer value, or usage intensity, and they do not enter the marketing or Customer Success formulas.

`total_contract_value` is not a metric in this contract.

### Executive scorecard

The scorecard grain is account-month. It reads the domain definitions and does not define a second formula for pipeline, bookings, ARR, retention, or adoption.

- `pipeline_amount` is the sum of the sales definition for the account's surviving opportunities, using the opportunity version in effect at month end. Opportunities with `created_at` after month end are excluded. Opportunities with no originating campaign are included here and excluded from every campaign's `sourced_pipeline`.
- `bookings` is the bookings sum for that account whose `booked_at` falls in the month, including the `expansion_bookings` slice.
- `arr`, `retained_arr`, `beginning_arr`, `customer_value`, `retention`, `adoption`, `usage_work_units`, and `outcome_count` are the Customer Success values for that account-month. The scorecard does not recompute them from subscriptions, bookings, or product events.
- `sourced_pipeline` and `influenced_pipeline` stay on the marketing mart. The scorecard does not allocate pipeline across campaigns and does not add those two measures together.

Summing `sourced_pipeline` across campaigns equals the sum of current `pipeline_amount` for opportunities that have an originating campaign. Summing account `pipeline_amount` across accounts, at the same as-of time, equals the sum of `pipeline_amount` across surviving opportunities.

### Lifecycle-event column contract

Domain lifecycle-event models that later issues emit share one column list, in this order:

| Column | Meaning |
|---|---|
| `lifecycle_event_id` | Surrogate of one occurrence. |
| `event_name` | One catalog name stored on `lifecycle_event`. |
| `lifecycle_stage` | `lead`, `opportunity`, `customer`, `adoption`, or `renewal`. |
| `occurred_at` | The timestamp that orders the event. |
| `subject_entity` | `lead`, `opportunity`, `account`, or `subscription`. |
| `account_id` | Account foreign key, present or absent as the catalog requires. |
| `lead_id` | Lead foreign key, present or absent as the catalog requires. |
| `opportunity_id` | Opportunity foreign key, present or absent as the catalog requires. |
| `subscription_id` | Subscription foreign key, present or absent as the catalog requires. |

The allowed `event_name` values are `lead_created`, `lead_qualified`, `lead_disqualified`, `lead_converted`, `opportunity_opened`, `opportunity_stage_changed`, `opportunity_won`, `opportunity_lost`, `customer_converted`, `adoption_reached`, `subscription_renewed`, `subscription_expanded`, and `subscription_churned`.

The contract copies `subject_entity` and the presence or absence of each foreign key from the event catalog in `entities.md`, unchanged. `product_usage` stays on `product_usage` and is not part of this column list.

A later union selects this list in this order. Shared lifecycle-event models add no other column. This task does not assign events to domains and does not build the models.

### Decisions for human review

The contract repeats the working decisions in a review section. The implementation records them as the rules above. It does not leave the formulas blank, and it does not replace them with a different rule. The review section names the alternative that a human can choose before mart issues start:

| Decision | Working rule in this specification | Alternative a reviewer may require |
|---|---|---|
| Pipeline amount version | `amount` on the version in effect at the as-of time. Current marts use the open-ended row. | `amount` at `opportunity_opened`. |
| Stage scope | `sourced_pipeline` and `influenced_pipeline` include every stage. Open stages are a filter on the same amount. | Limit the metric itself to open stages. |
| Influenced attachment | Lead or primary contact, touch at or before `created_at`, full amount on each campaign. | Any touch on the account, or a fractional split. |
| ARR status | Only `active` versions contribute. | `pending` versions also contribute. |
| Account-month as-of | Month end. | Month start. |
| Retained ARR | Prior month-end annualized amount of subscriptions still `active`. Expansion in the month stays in `expansion_bookings`. | Ending ARR of surviving subscriptions. |
| Retention | `retained_arr / beginning_arr`, null when `beginning_arr` is zero. Logo retention is undefined. | Add logo retention as a separate named metric. |
| Usage intensity | Monthly `usage_work_units` and `outcome_count`. | A different usage count, such as distinct product users. |
| Customer value | `retained_arr` plus monthly `expansion_bookings`. | A rate, or another pair of inputs. |

Pipeline coverage is undefined. The canonical model has no quota. The contract says so in the review section.

### Pointers

Add one sentence to the end of the amounts paragraph in `docs/data-model/entities.md` that begins "Amounts are observed commercial amounts in US dollars." The new sentence is: "The metric and mart contract for those formulas is `metric-contract.md`."

Add one sentence immediately after the bullet in `docs/data-model/decisions.md` that begins "Metric definitions for ARR, retention rate, pipeline coverage, and adoption rate are later work." The new sentence is: "The metric and mart contract that defines those formulas is `metric-contract.md`."

Leave the existing sentences in place. Do not edit entity sections, grains, keys, the event catalog, the open questions, `erd.md`, or `source-mapping.md`.

### Document close

The contract states that no mart issue is eligible to start until a human has approved `docs/data-model/metric-contract.md`. It states that this task changes no file under `warehouse/dbt/`, `contracts/`, `data-generation/`, or `analytics/`.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/` and `docs/data-model/` and do not edit contracts.
- Treat `entities.md`, `decisions.md`, `erd.md`, and `source-mapping.md` as the source of entities, grains, and events. Add formulas only.
- Keep the DATA-001 working assumptions that this contract uses: one `adoption_reached` event per account, and ARR history reconstructed from the subscription's effective-dated `recurring_amount` and `billing_frequency`. Do not edit those open-question sections.
- The account-month snapshot is a mart grain. Do not add a canonical entity for it.
- Quote and activity are context for the sales question. They stay out of the marketing and Customer Success formulas.
- Do not create dbt models, semantic topics, demo pages, source records, or metric columns on canonical entities.
- Do not define a second formula for pipeline, bookings, ARR, retention, or adoption on the executive scorecard.
- One owning agent, `analytics-engineer`, writes the document.
- Human approval is required. `delivery.human_approval_required` is true.
- An isolated warehouse schema is not required. Deployment is not required.
- This task does not depend on DATA-007-001 and does not edit `warehouse/dbt/`.

## Acceptance criteria

- [ ] `docs/data-model/metric-contract.md` exists.
- [ ] The only edits under `docs/data-model/` are that new file and the two pointer sentences in `entities.md` and `decisions.md`.
- [ ] `sourced_pipeline`, `influenced_pipeline`, `bookings`, `arr`, `adoption`, and `customer_value` are each defined once, with a grain, a formula, the source entities, and the owning mart.
- [ ] `retention`, `retained_arr`, `beginning_arr`, `usage_work_units`, and `outcome_count` are each defined once, and the executive scorecard reuses the domain definitions.
- [ ] The contract states the marketing, sales, Customer Success, and executive-scorecard grains, and states which mart owns each metric.
- [ ] The executive scorecard reads pipeline and bookings from the sales definitions and reads ARR, retention, adoption, customer value, and usage intensity from the Customer Success definitions. It does not define a second formula for pipeline, bookings, ARR, retention, or adoption.
- [ ] Sourced pipeline uses the lead's originating campaign, so one opportunity is counted on one campaign. Influenced pipeline is a separate touch measure and can count the same opportunity on more than one campaign. The two measures are not added together.
- [ ] Bookings use `booking_amount`. Opportunity `amount` remains pipeline. `quoted_amount` and `total_contract_value` are not substitutes for either measure.
- [ ] Annualization is `recurring_amount * 12` for `monthly`, `recurring_amount * 4` for `quarterly`, and `recurring_amount` for `annual`. Only `active` subscription versions contribute. The account-month snapshot is described as a mart, not a new canonical entity.
- [ ] Adoption remains one `adoption_reached` event per account, ordered by that account's first `product_outcome`. Usage intensity is the separate monthly usage and outcome measures.
- [ ] Customer value for the retention question is `retained_arr` plus `expansion_bookings`.
- [ ] The lifecycle-event column list, column order, allowed event names, and foreign-key presence are explicit, and the presence rules match `entities.md`. `product_usage` is outside that column list.
- [ ] Quote and activity are documented as sales context and are excluded from the marketing and Customer Success formulas.
- [ ] The contract includes the review table of working decisions and states that pipeline coverage is undefined.
- [ ] The contract states that a human must approve it before any mart issue is eligible to start.
- [ ] `warehouse/dbt/`, `contracts/`, `data-generation/`, and `analytics/` are unchanged.
- [ ] `erd.md`, `source-mapping.md`, entity grains, keys, the event catalog, and the DATA-001 open questions are unchanged apart from the two pointer sentences.

## Execution notes

Implement this specification only after it has merged and issue #26 is `status:ready`. Use an `impl` worktree. Write the contract and the two pointer sentences. Leave this specification file unchanged unless a human changes the approved requirements.

Read `docs/data-model/entities.md`, `docs/data-model/decisions.md`, and `docs/data-model/erd.md` before writing. Read the data-modeling skill before writing grains and ownership. Read the dbt skills only as a constraint on what this document must leave to later model issues. Do not implement staging, intermediate models, or marts.

Present the working decisions in the contract's review section. Do not reopen entity design. Where this specification already chooses a formula, write that formula. Do not replace it with an alternative from the review table unless a human has changed this specification.

Validation is a review of `metric-contract.md` and the two pointer sentences against the acceptance criteria. `testing.component_tests`, `testing.integration_tests`, and `testing.end_to_end_tests` are false. `environment.isolated_schema` is false. `delivery.deployment_required` is false.

The approval gate for later mart issues is a human's approval of the implementation pull request that adds `metric-contract.md`. Do not merge or deploy without human approval.
