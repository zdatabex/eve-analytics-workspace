# Modeling decisions

These decisions fix the canonical GTM model in `erd.md`, `entities.md`, and `source-mapping.md`. Human approval of this design is the gate for DATA-002. Three choices are unresolved and are marked for review before DATA-002 starts, because each one would change event vocabulary, adoption grain, or revenue-history grain. The rest of the design uses the working assumption stated with each open question so the four documents agree today.

## Historical tracking

A new dimension row opens when a tracked attribute changes. `effective_start` is inclusive, `effective_end` is exclusive, and the current row is the version whose `effective_end` is open. Exactly one current row exists for each surviving entity. Each row stores the attribute values as of `effective_start`. A duplicate row keeps its source identifier and survivor link and does not grow its own dimension history.

Source observations carry `observed_at`. That time becomes `effective_start` of the new version. Source records do not carry the effective-dated row themselves.

| Entity | Approach | Why | Attributes that open a new version | Dimension row grain |
|---|---|---|---|---|
| `account` | Type 2 | Commercial status, owner, segment, practice, ICP fit, and domain change pipeline cuts, retention cuts, or which records join to the firm. | `commercial_status`, `owner_name`, `segment`, `practice_focus`, `icp_fit`, `primary_domain` | One row represents one effective-dated version of one account, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| `contact` | Type 2 | Firm, buying role, and email change pipeline attribution and the link to a product user. | `account_id`, `buying_role`, `email_normalized` | One row represents one effective-dated version of one contact, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| `lead` | Lifecycle events, with the current lead row overwritten | Lead status history is the lead lifecycle events. Pipeline history is the opportunity dimension. A second history of the same status would duplicate those events. | None | One row represents one lead. |
| `opportunity` | Type 2 | Stage, amount, close date, owner, forecast, and type are the pipeline history. | `stage`, `amount`, `expected_close_date`, `owner_name`, `forecast_category`, `opportunity_type` | One row represents one effective-dated version of one opportunity, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| `quote` | Type 2 | Status and quoted amount change the proposal behind a deal. | `status`, `quoted_amount` | One row represents one effective-dated version of one quote, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| `contract` | Type 2 | Status, value, and term dates change the signed context for bookings and retention. A renewal can move `end_date` on this same contract. | `status`, `total_contract_value`, `start_date`, `end_date` | One row represents one effective-dated version of one contract, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| `subscription` | Type 2 | Status, plan, seats, recurring amount, billing frequency, and term are the ARR and retention history. | `status`, `plan_code`, `seat_count`, `recurring_amount`, `billing_frequency`, `term_start`, `term_end` | One row represents one effective-dated version of one subscription, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| `booking` | Immutable fact | The booking is the recognized economic event. A correction is a new booking. | None | One row represents one recognized booking. |
| `campaign` | Type 1 current row | Delivery history is the campaign-day fact. Channel is setup, and it stays for the life of the campaign. | None | One row represents one campaign. |
| `campaign_performance` | Immutable campaign-day fact | The grain is already the day. A correction replaces that campaign-day. | None | One row represents one campaign on one day. |
| `marketing_touch` | Immutable fact | A touch has already happened. | None | One row represents one attribution touch. |
| `activity` | Immutable fact | An activity has already happened. | None | One row represents one sales activity. |
| `product_user` | Type 2 | Status, firm, contact link, and email change the adoption denominator and the identity link. | `status`, `account_id`, `contact_id`, `email_normalized` | One row represents one effective-dated version of one product user, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| `ai_workflow` | Type 1 current row | Usage history is on `product_usage`. The workflow code is stable. | None | One row represents one AI workflow. |
| `product_usage` | Immutable fact | A usage event has already happened. | None | One row represents one usage of one AI workflow by one product user. |
| `product_outcome` | Immutable fact | An outcome has already happened. | None | One row represents one outcome of one product usage event. |
| `lifecycle_event` | Immutable fact | The event is the history of the lifecycle. | None | One row represents one occurrence of one named lifecycle event. |

The business grain of each entity stays one instance of that entity, as stated in `entities.md`. The Type 2 sentences in this table are the dimension row grain. They are a different grain from the business grain.

`firm_name`, `state`, and `hubspot_lifecycle_stage` are carried on the current account row. A change to those fields alone does not open a version, because pipeline, bookings, ARR, retention, and adoption use `commercial_status`, the tracked firmographics, and the lifecycle events. The same pattern applies to descriptive names and titles on the other Type 2 entities: they update the current row.

Source identifiers are immutable. A bad identifier is corrected as a data fix on the row that stores it. It does not open a Type 2 version.

`subscription.contract_id` is fixed at creation. Renewal and expansion keep the subscription and the contract. Durable status stays `active` across terms. Each renewal or expansion observation fires its lifecycle event even when status is unchanged. A change to term, recurring amount, or seats opens a new subscription version. A change to status, including the move to `churned`, also opens a version. A renewal can open a new contract version when the contract end date or value changes.

## Identity resolution

Identity rules for assignment, survivorship, and traceability are in `source-mapping.md`. This section states the business rules those mechanics implement.

### Law firm, contact, and product user

An account is the law firm. A contact is a person in the CRM. A product user is a person who can sign in to the product. The same human can be both a contact and a product user. The link is `product_user.contact_id`, set when the surviving contact has the same `email_normalized` and the same account. A firm is never stored as a contact. A one-person firm is one account, one contact, and, once the product is in use, one product user.

Match keys:

- Firm across HubSpot and Product: equal `primary_domain`. Missing domain, or unequal domains, does not match, including when the firm names are equal.
- Contact inside HubSpot: equal `email_normalized`.
- Product user to contact: equal `email_normalized` and the same account.
- Product user to product user: equal `product_user_source_id`, or equal `email_normalized` with no account requirement.

The surviving canonical identifiers are `account_id`, `contact_id`, and `product_user_id`. A non-surviving duplicate keeps its source identifier and its survivor link: `surviving_account_id`, `surviving_contact_id`, or `surviving_product_user_id`.

A contact belongs to one firm at a time. A move to another firm opens a new contact version. A product user belongs to one firm at a time. A move to another firm opens a new version of the same product user and changes `account_id`. A second source login with the same `email_normalized` at a different firm uses that same rule. It does not create a second surviving product user. `email_normalized` stays unique among surviving product users across accounts. Email history is kept the same way.

### Lead and customer

A lead is an inquiry. A customer is an account whose `commercial_status` is `customer` or, after the last churn, an account that once had `customer_converted` and is now `former_customer`. The canonical customer identifier is `account_id`. There is no customer entity and no customer source identifier.

Conversion sets the lead to `converted`, points the new opportunity at the lead, and requires an account. When the lead has no firm yet, the source process creates the HubSpot company before the deal. The lead keeps `lead_id`. The account keeps `account_id`.

`customer_converted` fires once, on the account's first win. A later win, including a win after churn, is `opportunity_won` plus the commercial records of that deal. `commercial_status` returns to `customer` on a new account version. It does not create a second customer identifier.

### Opportunity and subscription

HubSpot is the only creator of opportunities. DealHub references `hubspot_deal_id`. Two deals with different HubSpot ids are two opportunities. A repeated `hubspot_deal_id` is one opportunity. When two opportunity rows are later found to be the same deal, the earlier `opportunity_id` survives and the other row keeps `hubspot_deal_id` and `surviving_opportunity_id`. The same pattern uses `surviving_lead_id` for a duplicate lead and `surviving_subscription_id` for a duplicate subscription. DealHub is the only creator of subscriptions. The surviving identifiers are `opportunity_id` and `subscription_id`.

`opportunity.subscription_id` is present for expansion and renewal, where the deal targets an existing subscription. It is absent for new business, where the deal creates the subscription. The new subscription is linked from the contract and the booking.

## Synthetic data strategy

DATA-003 generates source records. DATA-004 shapes them into lifecycle scenarios. This section is the logical source schema those generators need. It names source entities, source identifiers, attributes required for canonical mapping, relationships, and the lifecycle events each source emits. Physical field types, nullability, and contract files stay with DATA-002.

Source records carry observed attributes and events. They do not carry ARR, net retention, pipeline coverage, win rate, adoption score, or any other calculated business metric. Observed deal amounts, quote amounts, contract values, booking amounts, and recurring fees are source observations, not those metrics.

A configurable seed makes generation reproducible. Volume and distribution are generator inputs: `account_count`, contacts per account, `lead_count`, `opportunity_win_rate`, opportunity stage mix, `renewal_rate`, `expansion_rate`, `churn_rate`, product users per customer, usage events per user, `campaign_count`, and channel mix. The same seed and the same inputs reproduce the same source identifiers and relationships.

Generators emit change observations for every source entity whose canonical entity is Type 2. Each observation repeats the same source identifier, carries `observed_at`, and carries the tracked attributes as of that time. Immutable events are emitted once.

Referential order: campaigns and AI workflows, then firms that share one domain when they are the same firm, then contacts and product users, then leads, touches, and activities, then opportunities, then quotes, contracts, subscriptions, and bookings, then usage and outcomes. A child source identifier references a parent source identifier that exists in the same dataset.

### HubSpot company

- Source identifier: `hubspot_company_id`.
- Mapping attributes: `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, `hubspot_lifecycle_stage`, `observed_at`.
- Relationships: none.
- Events: none. Canonical `commercial_status` is derived. The company observation still supplies the tracked firmographics.

### HubSpot contact

- Source identifier: `hubspot_contact_id`.
- Mapping attributes: `full_name`, `email_normalized`, `title`, `buying_role`, `observed_at`.
- Relationships: `hubspot_company_id`.
- Events: none.

### HubSpot lead

- Source identifier: `hubspot_lead_id`.
- Mapping attributes: `status`, `created_at`, `observed_at`.
- Relationships: `hubspot_contact_id`, `hubspot_company_id`, `marketing_campaign_id`.
- Events: `lead_created`, `lead_qualified`, `lead_disqualified`, and `lead_converted`. Conversion includes `hubspot_deal_id`. The generator creates the company before a converted lead's deal when the lead had no firm.

### HubSpot deal

- Source identifier: `hubspot_deal_id`.
- Mapping attributes: `opportunity_name`, `opportunity_type`, `stage`, `amount`, `expected_close_date`, `owner_name`, `forecast_category`, `created_at`, `observed_at`.
- Relationships: `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`. Expansion and renewal also reference `dealhub_subscription_id`.
- Events: `opportunity_opened`, `opportunity_stage_changed`, `opportunity_won`, and `opportunity_lost`. The canonical model, not HubSpot, records `customer_converted` for the account's first win.

### HubSpot activity

- Source identifier: `hubspot_activity_id`.
- Mapping attributes: `activity_type`, `subject`, `occurred_at`.
- Relationships: at least one of `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_deal_id`.
- Events: the activity row is the event. It does not emit a lifecycle event.

### DealHub quote

- Source identifier: `dealhub_quote_id`.
- Mapping attributes: `quote_number`, `status`, `quoted_amount`, `observed_at`.
- Relationships: `hubspot_deal_id`, `hubspot_company_id`.
- Events: none. Status and amount changes are observations for the quote dimension.

### DealHub contract

- Source identifier: `dealhub_contract_id`.
- Mapping attributes: `contract_number`, `status`, `total_contract_value`, `start_date`, `end_date`, `observed_at`.
- Relationships: `dealhub_quote_id`, `hubspot_deal_id`, `hubspot_company_id`. The deal is a won `new_business` deal.
- Events: none. Term and value changes, including a renewal that extends `end_date`, are observations for the contract dimension.

### DealHub subscription

- Source identifier: `dealhub_subscription_id`.
- Mapping attributes: `subscription_number`, `status`, `plan_code`, `seat_count`, `recurring_amount`, `billing_frequency`, `term_start`, `term_end`, `observed_at`.
- Relationships: `dealhub_contract_id`, `hubspot_company_id`.
- Events: `subscription_renewed` on every renewal observation, `subscription_expanded` on every expansion observation, and `subscription_churned` when status becomes `churned`. Durable status is `pending`, `active`, or `churned` and stays `active` across terms. A renewal or expansion fires even when status is unchanged. Consecutive renewals each emit `subscription_renewed`. Consecutive expansions each emit `subscription_expanded`. `pending` and `active` do not by themselves emit those events. A change to term, recurring amount, or seats still opens a Type 2 subscription version.

### DealHub booking

- Source identifier: `dealhub_booking_id`.
- Mapping attributes: `booking_number`, `booking_type`, `booking_amount`, `booked_at`.
- Relationships: `hubspot_company_id`, `hubspot_deal_id`, `dealhub_contract_id`, `dealhub_subscription_id`.
- Events: the booking row is the economic event. `booking_type` is `new_business`, `expansion`, or `renewal`. Churn does not emit a booking.

### Marketing campaign

- Source identifier: `marketing_campaign_id`.
- Mapping attributes: `campaign_code`, `campaign_name`, `channel`.
- Relationships: none.
- Events: none.

### Marketing daily delivery

- Source identifier: `marketing_campaign_id` together with `performance_date`.
- Mapping attributes: `spend_amount`, `impression_count`, `click_count`.
- Relationships: `marketing_campaign_id`.
- Events: none. One observation is one campaign-day.

### Marketing attribution touch

- Source identifier: `marketing_touch_source_id`.
- Mapping attributes: `occurred_at`.
- Relationships: `marketing_campaign_id`, and at least one of `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_company_id`.
- Events: the touch row is the attribution event.

### Product firm

- Source identifier: `product_firm_id`.
- Mapping attributes: `firm_name`, `primary_domain`, `state`.
- Relationships: none. The same firm as a HubSpot company uses the same `primary_domain`.
- Events: none.

### Product user

- Source identifier: `product_user_source_id`.
- Mapping attributes: `email_normalized`, `status`, `observed_at`.
- Relationships: `product_firm_id`.
- Events: none. Status changes are observations for the product user dimension. The same `email_normalized` at a different `product_firm_id` is the same product user. That match opens a Type 2 change of `account_id` on the surviving `product_user_id`.

### Product AI workflow

- Source identifier: `product_workflow_id`.
- Mapping attributes: `workflow_code`, `workflow_name`.
- Relationships: none.
- Events: none.

### Product usage

- Source identifier: `product_usage_source_id`.
- Mapping attributes: `occurred_at`, `work_unit_count`.
- Relationships: `product_user_source_id`, `product_firm_id`, `product_workflow_id`.
- Events: each row is the `product_usage` lifecycle event.

### Product outcome

- Source identifier: `product_outcome_source_id`.
- Mapping attributes: `occurred_at`, `outcome_type`.
- Relationships: `product_usage_source_id`, `product_user_source_id`, `product_firm_id`, `product_workflow_id`.
- Events: the outcome row is the completed result. The canonical model, not Product, records `adoption_reached` for the account's first outcome.

## Assumptions

- The seller is a US B2B SaaS company. Amounts are US dollars. There is no second currency and no foreign-exchange rate.
- A solo firm is one account and one contact.
- A contact has one current firm. History of a move is Type 2.
- A lead converts to at most one opportunity.
- New business creates one contract from one accepted quote and one or many subscriptions. Expansion and renewal do not create a contract. They update the existing subscription and can update the existing contract's end date or value.
- Account ARR is computed later from each subscription's `recurring_amount` and `billing_frequency`. This design does not define the annualization formula.
- The working stage and status values are the lists in the open question below.
- Firm-size segment is `solo`, `small`, `mid`, or `large`.
- `icp_fit` is `in_icp` or `out_of_icp`.
- Buying role is `champion`, `decision_maker`, `user`, or `billing`.
- Activity type is `call`, `email`, or `meeting`.
- Campaign channel is stable: `paid_search`, `paid_social`, `email`, `webinar`, `partner`, or `outbound`.
- Sales owner is a name on the account and the opportunity. There is no employee entity.
- There is no calendar entity, invoice entity, or payment entity.
- There is no partial downsell. Churn ends a subscription. Expansion increases it. Churn does not create a negative booking.
- The AI workflow catalog is open. Example capabilities are intake, medical chronology, and demand-letter drafting.
- `plan_code` is an open commercial catalog.
- `practice_focus` is an open firmographic description.
- Customer conversion and adoption are canonical events. Generators emit the winning deal and the product outcome. They do not emit those two derived events, and they do not emit a customer record.
- Two source rows for the same firm carry the same normalized domain. The generator does not rely on a name-only match.

## Constraints and limitations

- The canonical model is independent of physical source layouts. Source-specific identifiers stay on the mapped entities and in this source schema.
- Adding or replacing a source changes `source-mapping.md` and the generator inputs. It does not require a new canonical identifier scheme.
- Metric definitions for ARR, retention rate, pipeline coverage, and adoption rate are later work. The history those metrics need is already named above.

The metric and mart contract in `metric-contract.md` defines sourced pipeline, influenced pipeline, bookings, ARR annualization, retention, adoption as the 0/1 flag, and customer value. Pipeline coverage and an adoption rate remain undefined.
- Reactivation after churn is a later `opportunity_won` and a new or returning commercial status. There is no separate reactivation event.
- A campaign channel correction updates the current campaign row and therefore the channel seen on historical touches.
- This design leaves `contracts/` unchanged.

## Open questions for human review before DATA-002

### Stage and status vocabulary

This vocabulary is unresolved. The event rules in `entities.md` use it as the working set. Confirm or replace it before DATA-002 freezes values in contracts. Replacing a label changes which observation fires which event. It does not change the entity list.

| Subject | Working values |
|---|---|
| Lifecycle stage | `lead`, `opportunity`, `customer`, `adoption`, `renewal` |
| Lead status | `new`, `working`, `qualified`, `disqualified`, `converted` |
| Opportunity stage | `discovery`, `evaluation`, `proposal`, `negotiation`, `closed_won`, `closed_lost` |
| Opportunity type and booking type | `new_business`, `expansion`, `renewal` |
| Forecast category | `pipeline`, `best_case`, `commit`, `closed`, `omitted` |
| Account commercial status | `prospect`, `customer`, `former_customer` |
| Quote status | `draft`, `sent`, `accepted`, `rejected`, `expired` |
| Contract status | `active`, `expired`, `terminated` |
| Subscription status | `pending`, `active`, `churned`. Status stays `active` across renewals and expansions. Renewal and expansion are observations, not durable status values. |
| Product user status | `invited`, `active`, `inactive` |
| Billing frequency | `monthly`, `quarterly`, `annual` |
| Outcome type | `draft_completed`, `review_accepted`, `exported` |

`working`, `pending`, and `active` are included so the current row has a status. They do not each choose a lifecycle event. Renewal and expansion observations choose `subscription_renewed` and `subscription_expanded` even when status stays `active`. The other choosing values are the ones in the event catalog in `entities.md`.

### Adoption grain

This choice is unresolved because the alternative changes grain. The working assumption, used by `erd.md` and `entities.md`, is one `adoption_reached` event per account, ordered by the account's first `product_outcome`, with `subject_entity` of `account` and no product user on that event. Product usage remains one row per user, workflow, and run.

The alternative is one `adoption_reached` event per product user. That would change the grain sentence, require `product_user_id` on `lifecycle_event`, and change the cardinality between product user and lifecycle event. Confirm the working assumption or the alternative before DATA-002.

### Revenue-history grain

This choice is unresolved because the alternative adds a grain. The working assumption is that ARR history is reconstructed later from the subscription dimension: `recurring_amount`, `billing_frequency`, status, and the effective-dated row. Bookings stay on `booking`. HubSpot `amount` stays on `opportunity`. This design has no periodic ARR snapshot entity.

The alternative is a periodic ARR fact, one row per subscription per month. That adds an entity and a grain. Confirm that subscription Type 2 history is sufficient before DATA-002. The revenue-history grain question stays open. The annualization formula is defined in `metric-contract.md`.

## Future sources

Apollo and Clay may arrive later as enrichment sources for account and contact attributes. They are not in `source-mapping.md`. If they are adopted, a later specification adds them. They do not create `account_id` or `contact_id`, and they do not win a match against HubSpot or Product.

## Contracts

This task leaves `contracts/` unchanged. `contracts.changes_required` is false.

DATA-002 should add one source contract for each logical source entity in the synthetic data strategy. Each contract should carry the source identifier, the mapping attributes, the relationships, and the source events named here. Canonical warehouse models and metric definitions stay out of those source contracts. Physical types and nullability are part of DATA-002. This design does not implement those contracts.

## Entities this design does not add

The entity set is the smallest set that covers the lifecycle and the five analyses. A separate customer entity would duplicate the account. A separate person entity would collapse the contact and the product user, which have different source identifiers. Owner, date, invoice, payment, and seat are attributes or later warehouse structures, not canonical entities. Campaign membership is the marketing touch. Usage is its own event so it is not double-counted on `lifecycle_event`.
