# Source-to-canonical mapping

This mapping reconciles HubSpot, DealHub, Marketing, and Product into the canonical entities in `erd.md` and `entities.md`. Apollo and Clay are future enrichment sources. They are named in `decisions.md` and are not part of this mapping.

Canonical identifiers are the surrogate primary keys. Source identifiers are stored on the canonical entity they map to. Physical field types, nullability, and contract files are DATA-002 work. This file names the logical identifiers and the ownership rules DATA-002 implements.

## How a canonical identifier is assigned

1. Look up the source identifier on the canonical entity, including non-surviving duplicate rows.
2. When the row has a `surviving_<entity>_id`, the canonical identifier is that survivor.
3. When the row has no survivor, the row's primary key is the canonical identifier.

Each source identifier is stored on exactly one row. A match that is known before a canonical row exists creates one row and stores every matching source identifier on it. A match discovered after two canonical rows exist keeps the earlier primary key as the survivor. The later row keeps its source identifier and its `surviving_<entity>_id`. Those source identifiers are not copied onto the survivor.

The source that wins an attribute is the system that owns that attribute. The surviving canonical identifier is always the surrogate primary key. It is never a source identifier.

## HubSpot

HubSpot owns the CRM record of firms, people, inquiries, deals, and sales activities.

| Source concept | Source identifier | Canonical entity | What HubSpot owns |
|---|---|---|---|
| Company | `hubspot_company_id` | `account` | `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, and `hubspot_lifecycle_stage` when a HubSpot company is linked. |
| Contact | `hubspot_contact_id` | `contact` | `full_name`, `email_normalized`, `title`, `buying_role`, and the contact's account link. |
| Lead | `hubspot_lead_id` | `lead` | `status`, `created_at`, and the lead's links to account, contact, and originating campaign. |
| Deal | `hubspot_deal_id` | `opportunity` | `opportunity_name`, `opportunity_type`, `stage`, `amount`, `expected_close_date`, `owner_name`, `forecast_category`, `created_at`, and the deal's links to account, primary contact, lead, and, for expansion or renewal, the targeted subscription. |
| Activity | `hubspot_activity_id` | `activity` | `activity_type`, `subject`, `occurred_at`, and the activity's links to account, contact, lead, and opportunity. |

HubSpot signals also choose the lead and opportunity lifecycle events, including the account's first win that becomes `customer_converted`. The canonical model records `customer_converted`. HubSpot does not send a customer object.

HubSpot wins the firm when both HubSpot and Product describe it: HubSpot owns the firmographic and sales attributes. Product still contributes `product_firm_id`. HubSpot wins the contact. A product user email does not create a contact. HubSpot wins the lead and the opportunity. A DealHub quote attaches to the HubSpot deal and does not create a second opportunity.

## DealHub

DealHub owns quotes, contracts, subscriptions, and bookings. It does not create accounts, contacts, leads, or opportunities.

| Source concept | Source identifier | Canonical entity | What DealHub owns |
|---|---|---|---|
| Quote | `dealhub_quote_id` | `quote` | `quote_number`, `status`, and `quoted_amount`. |
| Contract | `dealhub_contract_id` | `contract` | `contract_number`, `status`, `total_contract_value`, `start_date`, and `end_date`. |
| Subscription | `dealhub_subscription_id` | `subscription` | `subscription_number`, `status`, `plan_code`, `seat_count`, `recurring_amount`, `billing_frequency`, `term_start`, and `term_end`. |
| Booking | `dealhub_booking_id` | `booking` | `booking_number`, `booking_type`, `booking_amount`, and `booked_at`. |

DealHub subscription signals choose `subscription_renewed`, `subscription_expanded`, and `subscription_churned`. Durable status stays `pending`, `active`, or `churned`, and can remain `active` across terms. A renewal or expansion observation fires its event even when status is unchanged. A change to term, amount, or seats still opens a Type 2 subscription version.

A quote references the HubSpot deal and the HubSpot company. A contract references the accepted quote, the new-business HubSpot deal, and the HubSpot company. A subscription references the DealHub contract and the HubSpot company. A booking references the HubSpot company, the HubSpot deal, the DealHub contract, and the DealHub subscription. Those references resolve through the source identifiers already mapped to canonical foreign keys.

DealHub wins subscription identity. Two deliveries of the same `dealhub_subscription_id` are one subscription. The surviving canonical identifier is `subscription_id`.

## Marketing

Marketing owns programs, daily delivery, and attribution. It does not create firms, contacts, leads, or pipeline amounts.

| Source concept | Source identifier | Canonical entity | What Marketing owns |
|---|---|---|---|
| Campaign | `marketing_campaign_id` | `campaign` | `campaign_code`, `campaign_name`, and `channel`. |
| Daily delivery | `marketing_campaign_id` together with `performance_date` | `campaign_performance` | `spend_amount`, `impression_count`, and `click_count` for that day. |
| Attribution touch | `marketing_touch_source_id` | `marketing_touch` | `occurred_at` and the links to the campaign and to the lead, contact, or account that was touched. |

A lead's originating campaign is a HubSpot lead attribute that references `marketing_campaign_id`. Marketing owns the campaign. HubSpot owns the lead.

## Product

Product owns the firm as a tenant, the product login, the workflow catalog, usage, and outcomes. It does not own sales stage, bookings, or ARR inputs.

| Source concept | Source identifier | Canonical entity | What Product owns |
|---|---|---|---|
| Firm | `product_firm_id` | `account` | `product_firm_id`. When no HubSpot company is linked, Product also supplies `firm_name`, `primary_domain`, and `state` until HubSpot links. |
| User | `product_user_source_id` | `product_user` | `email_normalized`, `status`, and the user's firm. |
| AI workflow | `product_workflow_id` | `ai_workflow` | `workflow_code` and `workflow_name`. |
| Usage | `product_usage_source_id` | `product_usage` | `occurred_at`, `work_unit_count`, and the links to user, firm, and workflow. |
| Outcome | `product_outcome_source_id` | `product_outcome` | `occurred_at`, `outcome_type`, and the link to the usage event. |

Product wins the product user. The surviving canonical identifier is `product_user_id`. The same `email_normalized` matches one surviving product user across firms. A login at a second firm records a Type 2 change of `account_id` on that `product_user_id`. Email may set `contact_id` when a surviving contact has the same email and the same account. Product does not create that contact.

The account's first product outcome chooses `adoption_reached`. The canonical model records that event. Product does not send an adoption score.

## Lifecycle events

`lifecycle_event` stores every lifecycle step except product usage. Product usage is the `product_usage` entity. Source systems emit the observations below. `customer_converted` and `adoption_reached` are derived in the canonical model and have no source identifier.

| Canonical event | Source signal |
|---|---|
| `lead_created` | HubSpot lead created at status `new`. |
| `lead_qualified` | HubSpot lead status becomes `qualified`. |
| `lead_disqualified` | HubSpot lead status becomes `disqualified`. |
| `lead_converted` | HubSpot lead status becomes `converted`, with the new `hubspot_deal_id`. |
| `opportunity_opened` | HubSpot deal created at stage `discovery`. |
| `opportunity_stage_changed` | HubSpot deal stage becomes `evaluation`, `proposal`, or `negotiation`. |
| `opportunity_won` | HubSpot deal stage becomes `closed_won`. |
| `opportunity_lost` | HubSpot deal stage becomes `closed_lost`. |
| `customer_converted` | Derived from the account's first `opportunity_won`. |
| `adoption_reached` | Derived from the account's first Product outcome, under the working grain in `decisions.md`. |
| `product_usage` | Each Product usage observation. Stored on `product_usage`, not on `lifecycle_event`. |
| `subscription_renewed` | Each DealHub renewal observation, including when subscription status stays `active`. |
| `subscription_expanded` | Each DealHub expansion observation, including when subscription status stays `active`. |
| `subscription_churned` | DealHub subscription status becomes `churned`. |

## Canonical attributes with no source owner

These attributes are derived in the canonical model from the events and commercial records above. Source records do not carry them.

| Canonical attribute or event | Rule |
|---|---|
| `account.commercial_status` | `prospect` before `customer_converted`; `customer` after `customer_converted` while any subscription is `pending` or `active`; `former_customer` after `customer_converted` when every subscription is `churned`. A later win returns the account to `customer`. Renewal and expansion leave subscription status `active`. |
| `customer_converted` | The account's first `opportunity_won`. The customer identifier is `account_id`. |
| `adoption_reached` | The account's first `product_outcome`, under the working grain in `decisions.md`. |

## Who wins when two systems describe the same thing

| Subject | Match that makes them the same | Source that wins attributes | Surviving canonical identifier |
|---|---|---|---|
| Firm | The same `primary_domain` on a HubSpot company and a Product firm. | HubSpot owns firmographics and sales attributes. Product owns `product_firm_id`. DealHub owns none of the firm attributes. | `account_id` of the row created first. If neither row exists yet, one new `account_id` receives both source identifiers. |
| Contact | The same `email_normalized` inside HubSpot. | HubSpot. Product never creates a contact. | `contact_id` of the row created first. |
| Lead | The same `hubspot_lead_id`. | HubSpot. No other source creates a lead. | `lead_id`. A repeated delivery updates that lead. A second canonical lead discovered to be the same inquiry keeps its source identifier and `surviving_lead_id`. |
| Opportunity | The same `hubspot_deal_id`. | HubSpot. DealHub attaches quotes, contracts, and bookings to that deal. | `opportunity_id`. A second canonical opportunity later found to be the same deal keeps its source identifier and `surviving_opportunity_id`. |
| Customer | A firm that has `customer_converted`. | The customer is the account. HubSpot's lifecycle value stays on `hubspot_lifecycle_stage`. | `account_id`. |
| Subscription | The same `dealhub_subscription_id`. | DealHub. | `subscription_id`. |
| Product user | The same `product_user_source_id`, or the same `email_normalized` across accounts. | Product. | `product_user_id`. |

A lead and a customer are not the same subject. Conversion links `lead_id` to `opportunity_id` and the opportunity to `account_id`. Both identifiers remain.

A firm, a contact, and a product user are not the same subject. A one-person firm is one account, one contact, and, once the product is used, one product user.

## Duplicate cases the model expects

| Case | Result |
|---|---|
| HubSpot company and Product firm share a domain, and no account exists yet. | One account stores both source identifiers. |
| Two accounts already exist and then match on domain. | The earlier `account_id` survives. The later row keeps its source identifier and `surviving_account_id`. |
| Two HubSpot companies share a domain. | Same survivor rule. Each company id stays on exactly one row. |
| Two HubSpot contacts share an email. | The earlier `contact_id` survives. The later row keeps `hubspot_contact_id` and `surviving_contact_id`. |
| The same `hubspot_lead_id` or `hubspot_deal_id` arrives twice. | One canonical row. |
| Two canonical opportunities are later found to be the same HubSpot deal. | The earlier `opportunity_id` survives. The later row keeps `hubspot_deal_id` and `surviving_opportunity_id`. |
| Two deals for one firm, with different HubSpot deal ids. | Two opportunities, even when the names match. |
| The same `dealhub_subscription_id` arrives twice. | One subscription. |
| Two subscriptions already exist for that same DealHub id. | The earlier `subscription_id` survives. The later row keeps the source identifier and `surviving_subscription_id`. |
| Two product users at one firm share an email. | The earlier `product_user_id` survives. The later row keeps `product_user_source_id` and `surviving_product_user_id`. |
| Two product users at different firms share an email. | The earlier `product_user_id` survives. The later row keeps `product_user_source_id` and `surviving_product_user_id`. The account change is a Type 2 version of `account_id` on that surviving product user, not a second surviving product user. |
| A product user email matches a contact at the same firm. | The contact and the product user both remain. `product_user.contact_id` links them. |
| A converted lead and the customer account. | Both remain. The lead is not a duplicate of the account. |
| Same firm name and different domains, or either side has no domain. | Two accounts. Name alone does not match across systems. |

## Conflicting and ambiguous attributes

| Conflict | Chosen treatment |
|---|---|
| HubSpot firm name and Product firm name differ. | HubSpot wins `firm_name` when a HubSpot company is linked. Product supplies the name only while no HubSpot company is linked. |
| HubSpot domain and Product domain differ. | The rows stay separate accounts. Equal normalized domains are required for a cross-system firm match. |
| HubSpot `amount`, DealHub `quoted_amount`, `total_contract_value`, `booking_amount`, and `recurring_amount` differ. | Each amount stays on its own entity. Pipeline uses opportunity `amount`. Bookings uses `booking_amount`. ARR uses subscription `recurring_amount` and `billing_frequency`. No amount is copied onto another entity. |
| Opportunity `expected_close_date` and contract `start_date` differ. | Both are kept. Close date is a sales expectation. Contract start is the signed term. |
| HubSpot lifecycle stage and canonical `commercial_status` differ. | `commercial_status` and lifecycle events are the analytical record. `hubspot_lifecycle_stage` is retained for reconciliation. |
| Account `owner_name` and opportunity `owner_name` differ. | Both are kept. Pipeline uses the opportunity owner. The account owner is the firm-relationship owner. |
| Subscription `seat_count` and the number of product users differ. | Both are kept. Seats are a commercial quantity. Product users are observed logins. |
| A person exists as a contact and as a product user. | Two entities, linked by email and `contact_id`. |
| A lead and a contact describe one person. | The lead names the contact. The lead remains its own entity. |
| A customer and an account describe one firm. | One entity, `account`. The customer identifier is `account_id`. |

## Traceability

Every mapped source identifier resolves to one canonical primary key by the lookup in "How a canonical identifier is assigned." The source identifier remains stored on the row that received it, including a non-surviving duplicate. Following `surviving_<entity>_id` reaches the surviving canonical identifier.

| Source identifier | Canonical identifier |
|---|---|
| `hubspot_company_id` | `account.account_id` |
| `product_firm_id` | `account.account_id` |
| `hubspot_contact_id` | `contact.contact_id` |
| `hubspot_lead_id` | `lead.lead_id` |
| `hubspot_deal_id` | `opportunity.opportunity_id` |
| `dealhub_quote_id` | `quote.quote_id` |
| `dealhub_contract_id` | `contract.contract_id` |
| `dealhub_subscription_id` | `subscription.subscription_id` |
| `dealhub_booking_id` | `booking.booking_id` |
| `marketing_campaign_id` | `campaign.campaign_id` |
| `marketing_campaign_id` + `performance_date` | `campaign_performance.campaign_performance_id` |
| `marketing_touch_source_id` | `marketing_touch.marketing_touch_id` |
| `hubspot_activity_id` | `activity.activity_id` |
| `product_user_source_id` | `product_user.product_user_id` |
| `product_workflow_id` | `ai_workflow.ai_workflow_id` |
| `product_usage_source_id` | `product_usage.product_usage_id` |
| `product_outcome_source_id` | `product_outcome.product_outcome_id` |

`customer_converted` and `adoption_reached` have no source identifier. They are canonical events derived from the first winning deal and the first product outcome.

## Handoff to DATA-002

DATA-002 specifies physical field types, nullability, and contract files from this mapping. The logical source entities, the attributes those contracts must carry, and the events the sources emit are in the synthetic data strategy in `decisions.md`. This task does not add those contract files.
