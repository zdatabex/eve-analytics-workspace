# GTM metric and mart contract

This contract defines the metrics that answer the four GTM demo questions. Entities, grains, keys, history, and events stay in `entities.md`, `decisions.md`, `erd.md`, and `source-mapping.md`. This document adds formulas only. It does not reopen entity design, stage vocabulary, identity rules, or source mapping.

The company is the fictional AI-native B2B SaaS vendor. The customer is a plaintiff law firm. Amounts are US dollars. There is no second currency.

A mart name here is the business mart that owns the metric. This contract does not assign dbt model filenames, SQL, or warehouse types.

The four questions are:

1. Which marketing channels and campaigns generate the most valuable pipeline?
2. How effectively is Sales converting opportunities into revenue?
3. Does adoption of Eve's AI-powered workflows translate into customer value and retention?
4. How healthy is the overall GTM engine?

The marketing mart answers the first question. The sales mart answers the second. The Customer Success mart answers the third. The executive scorecard answers the fourth by reading those marts. It owns no metric of its own.

The adoption-grain question and the revenue-history grain question in `decisions.md` stay open. This contract uses the working assumptions already in force: one `adoption_reached` event per account, and ARR history reconstructed from the subscription's effective-dated `recurring_amount` and `billing_frequency`.

## Shared rules

These rules apply to every formula below.

- Metrics count surviving entities. A row with a `surviving_<entity>_id` is excluded.
- Before every metric match and rollup, resolve `lead_id`, `contact_id`, `opportunity_id`, `account_id`, `subscription_id`, and `product_user_id` through the stored `surviving_<entity>_id` on the referenced row. The resolution is one hop: the survivor has no survivor of its own. That is the same rule `source-mapping.md` already uses for lead, contact, opportunity, account, subscription, and product user. Follow that survivor link only. Do not copy a duplicate's source identifier onto the survivor, and do not rewrite the child row.
- A later Type 2 change of `account_id` on a product user does not move historical `product_usage` or `product_outcome` onto that later account. Those rows keep the account stored on them, resolved only through `surviving_account_id`.
- Each surviving opportunity is counted on its surviving account, the account reached by resolving the opportunity's stored `account_id`. That assignment is what makes the scorecard equality true: the sum of account `pipeline_amount` equals the sum of `pipeline_amount` across surviving opportunities.
- The lifecycle-event column list stays a copy of the stored keys. This resolution is a metric rule. It does not change the foreign keys the column contract copies from the event catalog.
- The pipeline amount of an opportunity is `opportunity.amount` on the effective-dated row in effect at the as-of time. `effective_start` is inclusive and `effective_end` is exclusive. The current row is the row whose `effective_end` is open. `quoted_amount`, `total_contract_value`, `booking_amount`, `recurring_amount`, and annualized ARR are not the pipeline amount.
- The current sales and marketing marts use the current opportunity row. An account-month reading uses the row in effect at month end.
- Month membership is the calendar month of the stored timestamp. Month end is the last moment of that calendar month. This contract does not add a timezone conversion or a calendar entity.
- Money measures are US dollars. Adoption is 1 or 0. Retention is a ratio. Usage measures are counts.
- `seat_count`, `plan_code`, `forecast_category`, quote attributes, and activity attributes do not enter the formulas below.

## Metric definitions

Each metric is defined once, in the section that names it.

### `pipeline_amount`

- Grain: one surviving opportunity at an as-of time.
- Formula: `amount` on the opportunity version in effect at that time.
- Source entities: `opportunity`.
- Owning mart: sales. Marketing and the executive scorecard reuse this amount.

### `sourced_pipeline`

- Grain: one campaign. One row represents one campaign.
- Formula: the sum of `pipeline_amount` for surviving opportunities whose surviving lead has `originating_campaign_id` equal to that campaign. The as-of time is the current opportunity row.
- An opportunity has at most one lead, and a lead has at most one originating campaign, so an opportunity contributes to at most one campaign.
- An opportunity with no lead, or a lead with no originating campaign, contributes to no campaign.
- The sum includes every current stage. A reading limited to `discovery`, `evaluation`, `proposal`, and `negotiation` is the same amount with that stage filter applied. `forecast_category` does not filter the sum.
- Channel totals group the same campaign measure by `campaign.channel`. Channel is an attribute of the campaign, not a second formula.
- Source entities: `opportunity`, `lead`, `campaign`.
- Owning mart: marketing.

### `influenced_pipeline`

- Grain: one campaign.
- A campaign influences an opportunity when at least one `marketing_touch` for that campaign shares the opportunity's surviving `lead_id` or `primary_contact_id`, and `marketing_touch.occurred_at` is at or before the opportunity's `created_at`. A touch that does not share that lead or primary contact does not attach, including a touch that has only an account.
- Formula: the sum of `pipeline_amount` for distinct surviving opportunities influenced by that campaign. The full pipeline amount is added to each influencing campaign. There is no fractional split. The same opportunity is counted once per campaign.
- Sourced pipeline and influenced pipeline stay separate. They are not added together. An opportunity may appear in both, including on its originating campaign.
- The same open-stage filter used for sourced pipeline may be applied. It remains a filter on `pipeline_amount`.
- Source entities: `opportunity`, `marketing_touch`, `campaign`, `lead`, `contact`.
- Owning mart: marketing.

### `bookings`

- Grain: the sum is defined on `booking`. The sales mart stores it at opportunity grain: one row represents one surviving opportunity, and the value is the sum of `booking_amount` for that opportunity's bookings.
- Formula: the sum of `booking.booking_amount`.
- `booking_type` slices that sum into `new_business`, `expansion`, and `renewal`. `expansion_bookings` is the `expansion` slice. It is the same bookings formula. Sales owns `bookings` and every `booking_type` slice, including `expansion_bookings`.
- Customer Success does not own `expansion_bookings`. When it computes `customer_value`, it reads the account-month slice of the sales definition: `booking_type = expansion` and `booked_at` in the month. It does not calculate that slice a second time.
- An account-month reading sums `booking_amount` for bookings whose `booked_at` falls in the month and whose resolved account is that surviving account. The resolved account is the account reached through `surviving_account_id`.
- Churn does not create a booking. A correction is another booking and is included when its own `booking_amount` is summed.
- Source entities: `booking`. The opportunity, account, contract, and subscription foreign keys select the grain. They do not replace `booking_amount`.
- Owning mart: sales.

`quoted_amount` and `total_contract_value` are not substitutes for `booking_amount` or for opportunity `amount`. Opportunity `amount` remains pipeline.

### `arr`

- Grain: one subscription version, then summed to one account at an as-of time. The Customer Success mart stores account ARR at month end. One row of that mart represents one account in one calendar month.
- Formula: annualize the version's `recurring_amount` by `billing_frequency`, then sum the contributions that are in effect.

| `billing_frequency` | Annualized amount |
|---|---|
| `monthly` | `recurring_amount * 12` |
| `quarterly` | `recurring_amount * 4` |
| `annual` | `recurring_amount` |

- A version contributes that annualized amount only when its `status` is `active`. A `pending` or `churned` version contributes zero.
- The version in effect follows the Type 2 rule: `effective_start` inclusive, `effective_end` exclusive, and an open end for the current row.
- Account ARR at a time is the sum of those contributions for subscriptions whose resolved `account_id` is that surviving account. A subscription row with `surviving_subscription_id` is excluded. A subscription whose stored `account_id` points at a duplicate account is counted on the surviving account.
- Account-month ARR is account ARR at month end.
- The account-month snapshot is a mart built from subscription history. It is not a canonical entity, not a row in `erd.md`, and not a periodic ARR fact. The revenue-history grain question in `decisions.md` stays open.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

### `retained_arr`

- Grain: one account in one calendar month.
- Formula: for each surviving subscription whose resolved `account_id` is that account, and that is `active` at the prior month end and still `active` at this month end, add the annualized amount of the version in effect at the prior month end. A subscription row with `surviving_subscription_id` is excluded. A subscription that is `churned` or otherwise not `active` at this month end contributes zero. A subscription that was not `active` at the prior month end contributes zero.
- An increase in `recurring_amount` during the month stays out of `retained_arr`. That increase is recognized through `expansion_bookings`.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

### `beginning_arr`

- Grain: one account in one calendar month.
- Formula: `arr` at the prior month end. It is the ARR metric at another as-of time.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

### `customer_value`

- Grain: one account in one calendar month.
- Formula: `retained_arr` plus the account-month `expansion_bookings` slice. Customer Success reads that slice from the sales definition (`booking_type = expansion` and `booked_at` in the month). It does not own `expansion_bookings` and does not calculate the slice a second time.
- `retained_arr` is the stock defined above. The slice is the flow of `booking_amount` in that month. The contract adds them because that sum is the customer-value definition for the retention question.
- Source entities: `subscription`, `booking`, `account`.
- Owning mart: Customer Success owns `customer_value`. Sales owns the `expansion_bookings` input.

### `retention`

- Grain: one account in one calendar month.
- Formula: `retained_arr / beginning_arr`.
- When `beginning_arr` is zero, `retention` is null.
- Logo retention, net revenue retention, and any other ratio are not this metric.
- Source entities: `subscription`, `account`.
- Owning mart: Customer Success.

### `adoption`

- Grain: one account. The event grain remains one `adoption_reached` event per account, ordered by that account's first `product_outcome` of any `outcome_type`, with `subject_entity` of `account` and no product user on the event. The adoption-grain question in `decisions.md` stays open. This contract uses that working assumption.
- Formula: the account has adopted when that event exists.
- The Customer Success mart stores the account-month reading: 1 when `adoption_reached.occurred_at` is at or before month end, otherwise 0. That flag is the monthly reading of the same event. The account is the event's stored `account_id`, resolved through `surviving_account_id`. The stored key on the lifecycle-event column list is not rewritten.
- Source entities: `lifecycle_event`, `product_outcome`, `account`.
- Owning mart: Customer Success.

### `usage_work_units` and `outcome_count`

- Grain: one account in one calendar month.
- `usage_work_units` is the sum of `product_usage.work_unit_count` for that account whose `occurred_at` falls in the month.
- `outcome_count` is the count of `product_outcome` rows for that account whose `occurred_at` falls in the month.
- The account is the account stored on the usage or outcome row, resolved through `surviving_account_id`. `product_user_id` resolves through `surviving_product_user_id`. A later Type 2 change of `account_id` on the product user does not move the historical row onto that later account.
- These measures describe usage intensity. They are not `adoption`, not an adoption score, and they are not copied onto `lifecycle_event`.
- Source entities: `product_usage`, `product_outcome`, `account`.
- Owning mart: Customer Success.

## Sales conversion

The sales question is answered from the sales mart without a second pipeline or bookings formula.

- `is_won` is 1 when the surviving opportunity has its `opportunity_won` event, and 0 otherwise. Current stage `closed_won` is the choosing value for that event. The metric is the event.
- An opportunity's revenue is its `bookings`. Its pipeline comparison uses `pipeline_amount` on the same row.
- A later aggregate win rate counts opportunities with `opportunity_won` divided by opportunities with `opportunity_won` or `opportunity_lost`. That aggregate is a count of those events. It does not recompute `bookings` or `pipeline_amount`. The executive scorecard does not define its own win rate.

## Mart ownership

| Mart | Grain | Metrics it owns |
|---|---|---|
| Marketing | One row represents one campaign. | `sourced_pipeline`, `influenced_pipeline`. |
| Sales | One row represents one surviving opportunity. | `pipeline_amount`, `bookings`, every `booking_type` slice including `expansion_bookings`, `is_won`. |
| Customer Success | One row represents one account in one calendar month. | `arr`, `retained_arr`, `beginning_arr`, `customer_value`, `retention`, `adoption`, `usage_work_units`, `outcome_count`. |
| Executive scorecard | One row represents one account in one calendar month. | None. It reads the domain marts. |

The marketing mart may carry the campaign's summed `spend_amount`, `impression_count`, and `click_count` from `campaign_performance` as context. Those columns are not pipeline, and the contract does not define a return on spend.

The sales mart may carry quote and activity attributes as context for the sales question. Context includes the current `quoted_amount` and activity counts. Those columns are not metrics. Quote and activity do not enter sourced pipeline, influenced pipeline, bookings, ARR, retention, adoption, customer value, or usage intensity, and they do not enter the marketing or Customer Success formulas.

`total_contract_value` is not a metric in this contract.

## Executive scorecard

The scorecard grain is account-month. It reads the domain definitions and does not define a second formula for pipeline, bookings, ARR, retention, or adoption.

- `pipeline_amount` is the sum of the sales definition for the account's surviving opportunities, using the opportunity version in effect at month end. The account is the opportunity's stored `account_id`, resolved through `surviving_account_id`, so each surviving opportunity is counted on its surviving account. Opportunities with `created_at` after month end are excluded. Opportunities with no originating campaign are included here and excluded from every campaign's `sourced_pipeline`.
- `bookings` is the bookings sum for that account whose `booked_at` falls in the month. Sales owns that sum and every `booking_type` slice, including `expansion_bookings`. The account is the booking's stored `account_id`, resolved through `surviving_account_id`.
- `arr`, `retained_arr`, `beginning_arr`, `customer_value`, `retention`, `adoption`, `usage_work_units`, and `outcome_count` are the Customer Success values for that account-month. The scorecard does not recompute them from subscriptions, bookings, or product events. `customer_value` includes the sales-owned `expansion_bookings` slice because Customer Success reads that slice (`booking_type = expansion` and `booked_at` in the month) when it computes `customer_value`. The scorecard reads that slice through that Customer Success use of the sales definition. It does not calculate `expansion_bookings` again.
- `sourced_pipeline` and `influenced_pipeline` stay on the marketing mart. The scorecard does not allocate pipeline across campaigns and does not add those two measures together.

Summing `sourced_pipeline` across campaigns equals the sum of current `pipeline_amount` for opportunities that have an originating campaign. Summing account `pipeline_amount` across accounts, at the same as-of time, equals the sum of `pipeline_amount` across surviving opportunities, because each surviving opportunity is counted on its surviving account.

## Lifecycle-event column contract

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

`subject_entity` and the presence or absence of each foreign key are copied from the event catalog in `entities.md`, unchanged:

| Event | `subject_entity` | `account_id` | `lead_id` | `opportunity_id` | `subscription_id` |
|---|---|---|---|---|---|
| `lead_created` | `lead` | Present when the lead has a firm | Present | Absent | Absent |
| `lead_qualified` | `lead` | Present when the lead has a firm | Present | Absent | Absent |
| `lead_disqualified` | `lead` | Present when the lead has a firm | Present | Absent | Absent |
| `lead_converted` | `lead` | Present | Present | Present | Absent |
| `opportunity_opened` | `opportunity` | Present | Absent | Present | Absent |
| `opportunity_stage_changed` | `opportunity` | Present | Absent | Present | Absent |
| `opportunity_won` | `opportunity` | Present | Absent | Present | Absent |
| `opportunity_lost` | `opportunity` | Present | Absent | Present | Absent |
| `customer_converted` | `account` | Present | Absent | Present | Absent |
| `adoption_reached` | `account` | Present | Absent | Absent | Absent |
| `subscription_renewed` | `subscription` | Present | Absent | Absent | Present |
| `subscription_expanded` | `subscription` | Present | Absent | Absent | Present |
| `subscription_churned` | `subscription` | Present | Absent | Absent | Present |

The column list is a copy of the stored keys. Metric resolution of survivor links does not rewrite those stored keys and does not add or remove a column. `product_usage` stays on `product_usage` and is not part of this column list.

A later union selects this list in this order. Shared lifecycle-event models add no other column. This task does not assign events to domains and does not build the models.

## Decisions for human review

The rules above are the working rules. The formulas are not left blank, and they are not replaced by a different rule in this document. A human can require one of the alternatives below before any mart issue starts.

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

Pipeline coverage is undefined. The canonical model has no quota.

## Approval

No mart issue is eligible to start until a human has approved `docs/data-model/metric-contract.md`. This task changes no file under `warehouse/dbt/`, `contracts/`, `data-generation/`, or `analytics/`.
