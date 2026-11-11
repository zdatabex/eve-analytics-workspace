# Canonical GTM entities

These entities are the shared GTM model for Marketing, Sales, Customer Success, and Product Usage. The company is a fictional AI-native B2B SaaS vendor. The customer is a plaintiff law firm. Relationships match `erd.md`. History and identity rules match `decisions.md`. Source ownership matches `source-mapping.md`.

A canonical primary key is a surrogate. A surrogate stays stable when a source system is replaced, and a non-surviving duplicate can keep its own primary key while it points at the survivor. Where a business key exists, it is the stable business identifier used for matching or for a human-readable document number. The business key is not the primary key because it can be absent, it can change, or it is issued by one source system.

Amounts are observed commercial amounts in US dollars. They are inputs to later pipeline, bookings, and ARR metrics. This model does not store calculated ARR, retention, pipeline coverage, or adoption scores. The metric and mart contract in `metric-contract.md` defines sourced pipeline, influenced pipeline, bookings, ARR annualization, retention, adoption as the 0/1 flag, and customer value. Pipeline coverage and an adoption rate remain undefined.

The business grain of an entity is one instance of that entity. Where slowly changing dimension Type 2 applies, the analytical dimension uses a second grain: one row is one effective-dated version. `decisions.md` defines that row grain. The two grains are different, and both are stated on each Type 2 entity below.

`commercial_status` on the account is the commercial state of the firm. Lifecycle stage lives on events. An account can be a customer while adoption and renewal events continue.

## account

An account is one plaintiff law firm, including a solo practice. It is the customer account. HubSpot companies and Product firms that are the same firm resolve to one account.

Business grain: one instance of an account, which is one law firm.

The account dimension uses a different grain. One row represents one effective-dated version of one account, from effective_start inclusive until effective_end exclusive, with exactly one current row. That row grain is defined in `decisions.md`.

Primary key: `account_id`. The primary key is a surrogate. The same firm is identified by a HubSpot company id and a Product firm id, and either source may arrive first.

Business key: `primary_domain`, the firm's normalized website domain. It is unique among surviving accounts when it is present. It can be absent, and it can change, so it is not the primary key.

Foreign keys:

- `surviving_account_id` references `account.account_id`. A duplicate account identifies zero or one surviving account. A surviving account is identified by zero or many duplicate accounts.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `firm_name` | The firm's display name. | Descriptive. Pipeline and retention slices can label the firm. |
| `primary_domain` | Normalized website domain used to match the same firm across sources. | Identity. A domain change changes which records join to the firm. |
| `state` | The firm's principal US state. | Descriptive firmographic. |
| `segment` | Firm-size band: `solo`, `small`, `mid`, or `large`. | Pipeline and retention. |
| `practice_focus` | The firm's principal plaintiff practice, such as personal injury or mass tort. The catalog is open. | Pipeline and retention. |
| `icp_fit` | Whether the firm fits the ideal customer profile: `in_icp` or `out_of_icp`. | Pipeline. |
| `owner_name` | The sales owner of the firm relationship. | Pipeline. |
| `commercial_status` | Canonical commercial state: `prospect` before `customer_converted`; `customer` after `customer_converted` while any subscription is `pending` or `active`; `former_customer` after `customer_converted` when every subscription is `churned`. A later win returns the account to `customer`. Renewal and expansion leave subscription status `active`. | Retention. It is also the customer state of the account. |
| `hubspot_lifecycle_stage` | The lifecycle value stored in HubSpot. It is retained for reconciliation. | Descriptive. Canonical analysis uses `commercial_status` and lifecycle events. |
| `hubspot_company_id` | HubSpot's identifier for the company. | Identity. |
| `product_firm_id` | The Product system's identifier for the firm. | Identity. |

Uniqueness and referential integrity:

- `account_id` is unique.
- `hubspot_company_id` is unique across all account rows when it is present, including duplicate rows.
- `product_firm_id` is unique across all account rows when it is present, including duplicate rows.
- `primary_domain` is unique among surviving accounts when it is present. A duplicate may keep the same domain.
- `surviving_account_id` references a surviving account, and that account has no survivor of its own. An account does not reference itself.

## contact

A contact is a person known to sales or marketing in relation to a firm: a partner, an intake lead, a marketer, or a billing contact. A contact is not a product login.

Business grain: one instance of a contact, which is one person known to sales or marketing.

The contact dimension uses a different grain. One row represents one effective-dated version of one contact, from effective_start inclusive until effective_end exclusive, with exactly one current row. That row grain is defined in `decisions.md`.

Primary key: `contact_id`. The primary key is a surrogate because the same person can be re-created in HubSpot and because email can change.

Business key: `email_normalized`, the lowercased and trimmed email address. It is unique among surviving contacts when it is present. It can be absent and it can change, so it is not the primary key.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many contacts. A contact belongs to zero or one account.
- `surviving_contact_id` references `contact.contact_id`. A duplicate contact identifies zero or one surviving contact. A surviving contact is identified by zero or many duplicate contacts.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `full_name` | The person's name as known to sales. | Descriptive. |
| `email_normalized` | The match key to a product user and the business key of the contact. | Identity. It links the buying contact to product adoption. |
| `title` | The person's role title at the firm. | Descriptive. |
| `buying_role` | The person's role in a purchase: `champion`, `decision_maker`, `user`, or `billing`. | Pipeline. |
| `hubspot_contact_id` | HubSpot's identifier for the contact. | Identity. |

Uniqueness and referential integrity:

- `contact_id` is unique.
- `hubspot_contact_id` is unique across all contact rows when it is present.
- `email_normalized` is unique among surviving contacts when it is present.
- A contact's current firm is the account on the current dimension row. Earlier firms remain on earlier rows.
- `surviving_contact_id` references a surviving contact. A contact does not reference itself.

## lead

A lead is one sales inquiry. It can exist before a firm or a contact is known. A lead is not a customer and is not rewritten into an account.

Business grain: one instance of a lead, which is one sales inquiry.

Lead status history is stored as lifecycle events. Type 2 is a poor fit because those events already keep qualification history, and pipeline history lives on the opportunity. The lead dimension therefore uses the business grain.

Dimension grain: one row represents one lead.

Primary key: `lead_id`. The primary key is a surrogate. HubSpot's lead id is a source identifier, and a lead has no natural key that survives qualification and conversion.

Business key: none.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many leads. A lead belongs to zero or one account.
- `contact_id` references `contact.contact_id`. A contact has zero or many leads. A lead names zero or one contact.
- `originating_campaign_id` references `campaign.campaign_id`. A campaign originates zero or many leads. A lead has zero or one originating campaign.
- `surviving_lead_id` references `lead.lead_id`. A duplicate lead identifies zero or one surviving lead. A surviving lead is identified by zero or many duplicate leads.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `status` | The inquiry's current status: `new`, `working`, `qualified`, `disqualified`, or `converted`. | Lifecycle. Qualification and conversion choose lead events. |
| `created_at` | When the inquiry was opened. The `lead_created` event uses this time as `occurred_at`. | Lifecycle. |
| `hubspot_lead_id` | HubSpot's identifier for the lead. | Identity. |

Uniqueness and referential integrity:

- `lead_id` is unique.
- `hubspot_lead_id` is unique across all lead rows when it is present.
- `opportunity.lead_id` is the only conversion link. It is unique when present, so a lead converts to one opportunity and an opportunity comes from one lead.
- A lead in `disqualified` has no opportunity. A lead in `converted` has one opportunity.
- `surviving_lead_id` references a surviving lead. A lead does not reference itself.

## opportunity

An opportunity is one sales deal for one law firm. New business, expansion, and renewal are types of opportunity, not separate entities.

Business grain: one instance of an opportunity, which is one sales deal.

The opportunity dimension uses a different grain. One row represents one effective-dated version of one opportunity, from effective_start inclusive until effective_end exclusive, with exactly one current row. That row grain is defined in `decisions.md`.

Primary key: `opportunity_id`. The primary key is a surrogate. HubSpot's deal id is a source identifier, and replacing HubSpot must not change the canonical deal.

Business key: none.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many opportunities. An opportunity belongs to exactly one account.
- `primary_contact_id` references `contact.contact_id`. A contact is the primary contact of zero or many opportunities. An opportunity has zero or one primary contact.
- `lead_id` references `lead.lead_id`. A lead converts to zero or one opportunity. An opportunity comes from zero or one lead.
- `subscription_id` references `subscription.subscription_id`. A subscription is the target of zero or many opportunities. An opportunity targets zero or one subscription. This foreign key is present for `expansion` and `renewal`. It is absent for `new_business`, because that deal creates a subscription rather than targeting an existing one.
- `surviving_opportunity_id` references `opportunity.opportunity_id`. A duplicate opportunity identifies zero or one surviving opportunity. A surviving opportunity is identified by zero or many duplicate opportunities.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `opportunity_name` | The deal name used by sales. | Descriptive. |
| `opportunity_type` | Why the deal exists: `new_business`, `expansion`, or `renewal`. | Pipeline, bookings, and retention. |
| `stage` | The current sales stage: `discovery`, `evaluation`, `proposal`, `negotiation`, `closed_won`, or `closed_lost`. | Pipeline. Stage changes, wins, and losses choose opportunity events. |
| `amount` | The sales-entered deal amount observed in HubSpot. | Pipeline. This is an observed amount, not calculated ARR or bookings. |
| `expected_close_date` | The date sales expects the deal to close. | Pipeline. |
| `owner_name` | The sales owner of the deal. | Pipeline. |
| `forecast_category` | The forecast bucket: `pipeline`, `best_case`, `commit`, `closed`, or `omitted`. | Pipeline. |
| `created_at` | When the deal was opened. The `opportunity_opened` event uses this time as `occurred_at`. | Lifecycle and pipeline. |
| `hubspot_deal_id` | HubSpot's identifier for the deal. | Identity. |

Uniqueness and referential integrity:

- `opportunity_id` is unique.
- `hubspot_deal_id` is unique across all opportunity rows when it is present.
- `lead_id` is unique when it is present.
- The account on the primary contact, when both are present, is the opportunity's account.
- A `new_business` opportunity in `closed_won` has exactly one contract. A `closed_lost` opportunity has zero contracts. An `expansion` or `renewal` opportunity has zero contracts.
- `subscription_id`, when present, belongs to the same account as the opportunity.
- `surviving_opportunity_id` references a surviving opportunity. An opportunity does not reference itself.

## quote

A quote is one commercial proposal for one opportunity. DealHub owns it. The accepted quote of a won new-business deal is the quote the contract references.

Business grain: one instance of a quote, which is one commercial proposal.

The quote dimension uses a different grain. One row represents one effective-dated version of one quote, from effective_start inclusive until effective_end exclusive, with exactly one current row. That row grain is defined in `decisions.md`.

Primary key: `quote_id`. The primary key is a surrogate so the canonical quote survives replacement of the quoting system.

Business key: `quote_number`, the commercial document number. It is unique among quotes. It is not the primary key because the numbering scheme belongs to the commercial system.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many quotes. A quote belongs to exactly one account.
- `opportunity_id` references `opportunity.opportunity_id`. An opportunity has zero or many quotes. A quote belongs to exactly one opportunity.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `quote_number` | The human-readable proposal number. | Identity. |
| `status` | The proposal state: `draft`, `sent`, `accepted`, `rejected`, or `expired`. | Pipeline context for the deal, and the bridge from proposal to contract. |
| `quoted_amount` | The observed amount on the proposal. | Pipeline context. It is not copied into bookings or ARR. |
| `dealhub_quote_id` | DealHub's identifier for the quote. | Identity. |

Uniqueness and referential integrity:

- `quote_id` is unique.
- `quote_number` is unique.
- `dealhub_quote_id` is unique when it is present.
- `account_id` equals the account of `opportunity_id`.
- The quote referenced by a contract is the accepted quote of that contract's opportunity.

## contract

A contract is one signed agreement that grants one or many subscriptions. It is created from a won new-business opportunity. Renewal and expansion extend the subscription and can change this contract's value or end date; they do not create another contract.

Business grain: one instance of a contract, which is one signed agreement.

The contract dimension uses a different grain. One row represents one effective-dated version of one contract, from effective_start inclusive until effective_end exclusive, with exactly one current row. That row grain is defined in `decisions.md`.

Primary key: `contract_id`. The primary key is a surrogate so the canonical agreement survives replacement of DealHub.

Business key: `contract_number`, the signed document number. It is unique among contracts. It is not the primary key because the numbering scheme belongs to the commercial system.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many contracts. A contract belongs to exactly one account.
- `opportunity_id` references `opportunity.opportunity_id`. An opportunity has zero or one contract. A contract belongs to exactly one opportunity.
- `quote_id` references `quote.quote_id`. A quote is accepted as zero or one contract. A contract belongs to exactly one quote.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `contract_number` | The human-readable agreement number. | Identity. |
| `status` | The legal state: `active`, `expired`, or `terminated`. | Retention context for the signed term. |
| `total_contract_value` | The observed total value of the signed agreement. | Bookings context. It is not ARR and it is not the booking amount. |
| `start_date` | The day the agreement starts. | Retention and bookings context. |
| `end_date` | The day the agreement ends. A renewal can move this date. | Retention. |
| `dealhub_contract_id` | DealHub's identifier for the contract. | Identity. |

Uniqueness and referential integrity:

- `contract_id` is unique.
- `contract_number` is unique.
- `dealhub_contract_id` is unique when it is present.
- `opportunity_id` is unique. `quote_id` is unique.
- `account_id` equals the account of the opportunity and the account of the quote.
- The opportunity is a `new_business` opportunity in `closed_won`.

## subscription

A subscription is one recurring commercial entitlement under one contract. It is the entity whose amount, term, and status carry ARR and retention history. Expansion and renewal keep the same subscription. Durable status stays `active` across terms. Each renewal observation records `subscription_renewed`, and each expansion observation records `subscription_expanded`, including when status is unchanged. A change to term, amount, or seats opens a new effective-dated version. A second purchased product is a second subscription.

Business grain: one instance of a subscription, which is one recurring entitlement.

The subscription dimension uses a different grain. One row represents one effective-dated version of one subscription, from effective_start inclusive until effective_end exclusive, with exactly one current row. That row grain is defined in `decisions.md`.

Primary key: `subscription_id`. The primary key is a surrogate. DealHub's subscription id is a source identifier.

Business key: `subscription_number`, the commercial subscription number. It is unique among surviving subscriptions. It is not the primary key because the numbering scheme belongs to DealHub.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many subscriptions. A subscription belongs to exactly one account.
- `contract_id` references `contract.contract_id`. A contract grants one or many subscriptions. A subscription belongs to exactly one contract. `contract_id` is fixed when the subscription is created.
- `surviving_subscription_id` references `subscription.subscription_id`. A duplicate subscription identifies zero or one surviving subscription. A surviving subscription is identified by zero or many duplicate subscriptions.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `subscription_number` | The human-readable subscription number. | Identity. |
| `status` | The durable commercial state: `pending`, `active`, or `churned`. Status stays `active` across renewals and expansions. | ARR and retention. `churned` chooses `subscription_churned`. A renewal or expansion observation chooses its event even when status is unchanged. |
| `plan_code` | The commercial plan sold to the firm. The catalog is open. | ARR and adoption segmentation. |
| `seat_count` | The number of seats on the subscription. | ARR context. It is an observed commercial quantity, not a count of product users. |
| `recurring_amount` | The observed recurring fee for the subscription. | ARR. Later ARR math uses this amount with `billing_frequency`. The formula is later metric work. |
| `billing_frequency` | How often the fee repeats: `monthly`, `quarterly`, or `annual`. | ARR. |
| `term_start` | The first day of the current term. | ARR and retention. |
| `term_end` | The last day of the current term. | Retention and renewal. |
| `dealhub_subscription_id` | DealHub's identifier for the subscription. | Identity. |

Uniqueness and referential integrity:

- `subscription_id` is unique.
- `subscription_number` is unique among surviving subscriptions.
- `dealhub_subscription_id` is unique across all subscription rows when it is present.
- `account_id` equals the account of `contract_id`.
- Account ARR is the later sum of the current recurring amounts on the account's subscriptions. This model stores the subscription inputs, not that sum.
- `surviving_subscription_id` references a surviving subscription. A subscription does not reference itself.

## booking

A booking is one recognized commercial booking. DealHub records it. A reversal or a later commercial event is another booking. New business, expansion, and renewal are booking types. Churn does not create a booking.

Business grain: one instance of a booking, which is one recognized booking.

Fact grain: one row represents one recognized booking. This matches the business grain. Type 2 is a poor fit because the booking is the historical record; changing it would rewrite a recognized economic event.

Primary key: `booking_id`. The primary key is a surrogate so a booking correction can be a new booking without reusing a source document number as the canonical id.

Business key: `booking_number`, the commercial booking number. It is unique among bookings. It is not the primary key because the numbering scheme belongs to DealHub.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many bookings. A booking belongs to exactly one account.
- `opportunity_id` references `opportunity.opportunity_id`. An opportunity has zero or many bookings. A booking belongs to exactly one opportunity.
- `contract_id` references `contract.contract_id`. A contract authorizes zero or many bookings. A booking belongs to exactly one contract.
- `subscription_id` references `subscription.subscription_id`. A subscription has zero or many bookings. A booking belongs to exactly one subscription.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `booking_number` | The human-readable booking number. | Identity. |
| `booking_type` | The commercial motion: `new_business`, `expansion`, or `renewal`. | Bookings. |
| `booking_amount` | The observed recognized booking amount. | Bookings. It is not ARR and it is not the HubSpot deal amount. |
| `booked_at` | When the booking was recognized. This timestamp orders the booking. | Bookings. |
| `dealhub_booking_id` | DealHub's identifier for the booking. | Identity. |

Uniqueness and referential integrity:

- `booking_id` is unique.
- `booking_number` is unique.
- `dealhub_booking_id` is unique when it is present.
- `account_id` equals the account on the opportunity, the contract, and the subscription.
- `booking_type` equals the opportunity's `opportunity_type`.
- A booking is immutable. A correction is a new booking.

## campaign

A campaign is one marketing program. Spend and impressions live on campaign performance, not on the campaign.

Business grain: one instance of a campaign.

Dimension grain: one row represents one campaign. This matches the business grain. Type 2 is a poor fit because delivery history already has its own day grain on `campaign_performance`, and the channel is part of the campaign setup.

Primary key: `campaign_id`. The primary key is a surrogate so a campaign code from the marketing system is not the canonical identifier.

Business key: `campaign_code`. It is unique among campaigns. It is not the primary key because a code can be corrected without changing historical touches and delivery rows that already point at `campaign_id`.

Foreign keys: none.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `campaign_code` | The stable marketing code for the program. | Identity. |
| `campaign_name` | The program name. | Descriptive. |
| `channel` | The program channel: `paid_search`, `paid_social`, `email`, `webinar`, `partner`, or `outbound`. | Pipeline context for which programs create leads. |
| `marketing_campaign_id` | The marketing system's identifier for the campaign. | Identity. |

Uniqueness and referential integrity:

- `campaign_id` is unique.
- `campaign_code` is unique.
- `marketing_campaign_id` is unique when it is present.
- Channel is stable for the life of the campaign. A correction updates this row.

## campaign_performance

A campaign performance row is one campaign's observed delivery on one day: spend, impressions, and clicks.

Business grain: one instance of a campaign's delivery on one day.

Fact grain: one row represents one campaign on one day. This matches the business grain. Type 2 is a poor fit because the day is already the grain. A correction replaces that campaign-day.

Primary key: `campaign_performance_id`. The primary key is a surrogate. The business identity of the row is the campaign plus the day.

Business key: `campaign_id` together with `performance_date`. That pair is unique.

Foreign keys:

- `campaign_id` references `campaign.campaign_id`. A campaign has zero or many campaign performance rows. A campaign performance row belongs to exactly one campaign.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `performance_date` | The calendar day of delivery. | Pipeline context for demand generation. |
| `spend_amount` | The observed spend on that day. | Pipeline context. It is not a return-on-spend metric. |
| `impression_count` | The observed impressions on that day. | Pipeline context. |
| `click_count` | The observed clicks on that day. | Descriptive demand detail. |

Uniqueness and referential integrity:

- `campaign_performance_id` is unique.
- The pair `campaign_id`, `performance_date` is unique.
- The source identifier is that same pair. There is no separate delivery document number.

## marketing_touch

A marketing touch is one attribution of a campaign to a lead, a contact, or an account.

Business grain: one instance of an attribution touch.

Fact grain: one row represents one attribution touch. This matches the business grain. Type 2 is a poor fit because a touch is an event that has already happened.

Primary key: `marketing_touch_id`. The primary key is a surrogate.

Business key: none.

Foreign keys:

- `campaign_id` references `campaign.campaign_id`. A campaign has zero or many marketing touches. A marketing touch belongs to exactly one campaign.
- `account_id` references `account.account_id`. An account has zero or many marketing touches. A marketing touch belongs to zero or one account.
- `contact_id` references `contact.contact_id`. A contact has zero or many marketing touches. A marketing touch belongs to zero or one contact.
- `lead_id` references `lead.lead_id`. A lead has zero or many marketing touches. A marketing touch belongs to zero or one lead.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `occurred_at` | When the touch happened. This timestamp orders the touch. | Pipeline context for which campaign preceded a lead or deal. |
| `marketing_touch_source_id` | The marketing system's identifier for the touch. | Identity. |

Uniqueness and referential integrity:

- `marketing_touch_id` is unique.
- `marketing_touch_source_id` is unique when it is present.
- A marketing touch belongs to exactly one campaign and to at least one of account, contact, or lead.
- When a lead or contact is present and has an account, the touch's account is that account.

## activity

An activity is one sales interaction recorded in HubSpot: a call, an email, or a meeting.

Business grain: one instance of a sales activity.

Fact grain: one row represents one sales activity. This matches the business grain. Type 2 is a poor fit because an activity is an event that has already happened.

Primary key: `activity_id`. The primary key is a surrogate.

Business key: none.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many activities. An activity belongs to zero or one account.
- `contact_id` references `contact.contact_id`. A contact has zero or many activities. An activity belongs to zero or one contact.
- `lead_id` references `lead.lead_id`. A lead has zero or many activities. An activity belongs to zero or one lead.
- `opportunity_id` references `opportunity.opportunity_id`. An opportunity has zero or many activities. An activity belongs to zero or one opportunity.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `activity_type` | The interaction: `call`, `email`, or `meeting`. | Pipeline context for sales effort. |
| `subject` | The short description of the interaction. | Descriptive. |
| `occurred_at` | When the interaction happened. This timestamp orders the activity. | Pipeline context. |
| `hubspot_activity_id` | HubSpot's identifier for the activity. | Identity. |

Uniqueness and referential integrity:

- `activity_id` is unique.
- `hubspot_activity_id` is unique when it is present.
- An activity belongs to at least one of account, contact, lead, or opportunity.
- When a parent that has an account is present, the activity's account is that account.

## product_user

A product user is one product login. The current version belongs to exactly one firm. The same human may also be a contact. The two stay separate because HubSpot and the Product system issue different identifiers and because a user can exist before sales knows the person. The same `email_normalized` at another firm is the same product user. That match records a Type 2 change of `account_id` on the surviving `product_user_id`. It does not create a second surviving product user.

Business grain: one instance of a product user, which is one product login. The firm is the account on the current version, not a second identity.

The product user dimension uses a different grain. One row represents one effective-dated version of one product user, from effective_start inclusive until effective_end exclusive, with exactly one current row. That row grain is defined in `decisions.md`.

Primary key: `product_user_id`. The primary key is a surrogate. The Product system's user id is a source identifier, and email can change.

Business key: `email_normalized`. It is unique among surviving product users across accounts when it is present. It is not the primary key because email can change and because the product login id is the source identifier.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many product users. A product user belongs to exactly one account.
- `contact_id` references `contact.contact_id`. A contact matches zero or one product user. A product user matches zero or one contact.
- `surviving_product_user_id` references `product_user.product_user_id`. A duplicate product user identifies zero or one surviving product user. A surviving product user is identified by zero or many duplicate product users.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `email_normalized` | The login email. It matches another product user across accounts. It matches a contact only when the account is the same. | Identity and adoption. |
| `status` | The login state: `invited`, `active`, or `inactive`. | Adoption. Active users are the adoption denominator. |
| `product_user_source_id` | The Product system's identifier for the user. | Identity. |

Uniqueness and referential integrity:

- `product_user_id` is unique.
- `product_user_source_id` is unique across all product user rows when it is present.
- `email_normalized` is unique among surviving product users across accounts when it is present. A second source login with the same email, including at a different firm, is not a second surviving product user.
- A cross-account match on `email_normalized` records a Type 2 change of `account_id` on the surviving `product_user_id`.
- `contact_id` is unique when it is present.
- The contact, when present, has the same email and the same account.
- `surviving_product_user_id` references a surviving product user. A product user does not reference itself.

## ai_workflow

An AI workflow is one product capability a firm can run, such as case intake, medical chronology, or demand-letter drafting. The workflow catalog is open. Workflows are defined by the product, not by a firm.

Business grain: one instance of an AI workflow.

Dimension grain: one row represents one AI workflow. This matches the business grain. Type 2 is a poor fit because usage history is stored on `product_usage`, and the workflow code is stable.

Primary key: `ai_workflow_id`. The primary key is a surrogate.

Business key: `workflow_code`. It is unique among workflows. It is not the primary key so a code correction does not orphan usage history.

Foreign keys: none.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `workflow_code` | The stable code for the capability. | Adoption segmentation. |
| `workflow_name` | The capability name. | Descriptive. |
| `product_workflow_id` | The Product system's identifier for the workflow. | Identity. |

Uniqueness and referential integrity:

- `ai_workflow_id` is unique.
- `workflow_code` is unique.
- `product_workflow_id` is unique when it is present.

## product_usage

A product usage event is one run of one AI workflow by one product user. This entity is the usage event in the lifecycle. It is not copied onto `lifecycle_event`.

Business grain: one instance of a product usage event.

Fact grain: one row represents one usage of one AI workflow by one product user. This matches the business grain. Type 2 is a poor fit because the usage has already happened.

Primary key: `product_usage_id`. The primary key is a surrogate.

Business key: none.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many product usage events. A product usage event belongs to exactly one account.
- `product_user_id` references `product_user.product_user_id`. A product user performs zero or many product usage events. A product usage event belongs to exactly one product user.
- `ai_workflow_id` references `ai_workflow.ai_workflow_id`. An AI workflow is run as zero or many product usage events. A product usage event belongs to exactly one AI workflow.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `occurred_at` | When the run happened. This timestamp orders the usage. | Adoption. |
| `work_unit_count` | The observed number of runs represented by the event. A single run has a count of one. | Adoption. It is not an adoption score. |
| `product_usage_source_id` | The Product system's identifier for the usage event. | Identity. |

Uniqueness and referential integrity:

- `product_usage_id` is unique.
- `product_usage_source_id` is unique when it is present.
- `account_id` equals the account of `product_user_id`.

## product_outcome

A product outcome is one completed result of one usage event, such as a draft completed, a review accepted, or an export.

Business grain: one instance of a product outcome.

Fact grain: one row represents one outcome of one product usage event. This matches the business grain. Type 2 is a poor fit because the outcome has already happened.

Primary key: `product_outcome_id`. The primary key is a surrogate.

Business key: none.

Foreign keys:

- `product_usage_id` references `product_usage.product_usage_id`. A product usage event yields zero or one product outcome. A product outcome belongs to exactly one product usage event.
- `account_id` references `account.account_id`. An account has zero or many product outcomes. A product outcome belongs to exactly one account.
- `product_user_id` references `product_user.product_user_id`. A product user produces zero or many product outcomes. A product outcome belongs to exactly one product user.
- `ai_workflow_id` references `ai_workflow.ai_workflow_id`. An AI workflow is completed as zero or many product outcomes. A product outcome belongs to exactly one AI workflow.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `occurred_at` | When the outcome was completed. This timestamp orders the outcome. The account's first outcome orders `adoption_reached`. | Adoption. |
| `outcome_type` | The result: `draft_completed`, `review_accepted`, or `exported`. | Adoption quality. |
| `product_outcome_source_id` | The Product system's identifier for the outcome. | Identity. |

Uniqueness and referential integrity:

- `product_outcome_id` is unique.
- `product_outcome_source_id` is unique when it is present.
- `product_usage_id` is unique.
- `account_id`, `product_user_id`, and `ai_workflow_id` equal the same fields on `product_usage_id`.

## lifecycle_event

A lifecycle event is one recorded step in Lead → Opportunity → Customer → Adoption → Renewal. Product usage is represented by `product_usage` and is listed with these events so the lifecycle is complete. It is not stored again in this entity.

Business grain: one instance of a lifecycle event.

Fact grain: one row represents one occurrence of one named lifecycle event. This matches the business grain. Type 2 is a poor fit because the event is the history.

Primary key: `lifecycle_event_id`. The primary key is a surrogate. There is no business key, because an occurrence is identified by the event name and the subject it belongs to.

Business key: none.

Foreign keys:

- `account_id` references `account.account_id`. An account has zero or many lifecycle events. A lifecycle event belongs to zero or one account.
- `lead_id` references `lead.lead_id`. A lead has zero or many lifecycle events. A lifecycle event belongs to zero or one lead.
- `opportunity_id` references `opportunity.opportunity_id`. An opportunity has zero or many lifecycle events. A lifecycle event belongs to zero or one opportunity.
- `subscription_id` references `subscription.subscription_id`. A subscription has zero or many lifecycle events. A lifecycle event belongs to zero or one subscription.

| Attribute | Business definition | Analysis that needs it |
|---|---|---|
| `event_name` | The lifecycle step named in the event catalog. | Lifecycle, pipeline, retention, and adoption. |
| `lifecycle_stage` | The stage the event records: `lead`, `opportunity`, `customer`, `adoption`, or `renewal`. | Lifecycle. |
| `occurred_at` | The timestamp that orders the event. | Lifecycle and every analysis that depends on sequence. |
| `subject_entity` | The entity the event belongs to: `lead`, `opportunity`, `account`, or `subscription`. | Lifecycle. It selects which foreign key is required. |

Uniqueness and referential integrity:

- `lifecycle_event_id` is unique.
- The foreign keys required for each event name are in the catalog below. Other subject foreign keys are absent.
- When `opportunity_id` is present, `account_id` equals that opportunity's account.
- When `subscription_id` is present, `account_id` equals that subscription's account.
- When `lead_id` is present and the lead has an account, `account_id` equals that lead's account.
- `subject_entity` names the entity that owns the event.
- One `lead_created` exists for a lead. One `lead_qualified`, one `lead_disqualified`, and one `lead_converted` exist for a lead when that step happens. Qualification and disqualification do not both happen. Conversion follows qualification and requires an opportunity.
- One `opportunity_opened` exists for an opportunity. Open-stage moves are many `opportunity_stage_changed` rows. The opportunity then has one `opportunity_won` or one `opportunity_lost`.
- One `customer_converted` exists for an account. It is the account's first `opportunity_won`.
- One `adoption_reached` exists for an account under the working assumption in `decisions.md`.
- One `subscription_churned` exists for a subscription. `subscription_renewed` and `subscription_expanded` may each occur many times. Consecutive renewals each add a `subscription_renewed` row while status remains `active`. Consecutive expansions each add a `subscription_expanded` row the same way. The event does not require the status value to change.

## Proposed facts and dimensions

These are logical analytical objects. They are not dbt models. Warehouse names and metric formulas belong to later work. Each Type 2 dimension grain below is the effective-dated grain, which is different from the entity's business grain. Each other grain matches the entity's business grain.

| Analytical object | Role | Grain |
|---|---|---|
| Account dimension | Dimension of `account` | One row represents one effective-dated version of one account, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| Contact dimension | Dimension of `contact` | One row represents one effective-dated version of one contact, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| Lead dimension | Dimension of `lead` | One row represents one lead. |
| Opportunity dimension | Dimension of `opportunity` | One row represents one effective-dated version of one opportunity, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| Quote dimension | Dimension of `quote` | One row represents one effective-dated version of one quote, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| Contract dimension | Dimension of `contract` | One row represents one effective-dated version of one contract, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| Subscription dimension | Dimension of `subscription` | One row represents one effective-dated version of one subscription, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| Campaign dimension | Dimension of `campaign` | One row represents one campaign. |
| Product user dimension | Dimension of `product_user` | One row represents one effective-dated version of one product user, from effective_start inclusive until effective_end exclusive, with exactly one current row. |
| AI workflow dimension | Dimension of `ai_workflow` | One row represents one AI workflow. |
| Booking fact | Fact of `booking` | One row represents one recognized booking. |
| Campaign performance fact | Fact of `campaign_performance` | One row represents one campaign on one day. |
| Marketing touch fact | Fact of `marketing_touch` | One row represents one attribution touch. |
| Activity fact | Fact of `activity` | One row represents one sales activity. |
| Product usage fact | Fact of `product_usage` | One row represents one usage of one AI workflow by one product user. |
| Product outcome fact | Fact of `product_outcome` | One row represents one outcome of one product usage event. |
| Lifecycle event fact | Fact of `lifecycle_event` | One row represents one occurrence of one named lifecycle event. |

Pipeline uses the opportunity dimension and opportunity lifecycle events. Bookings uses the booking fact. ARR uses the subscription dimension's `recurring_amount` and `billing_frequency` over effective dates. Retention uses subscription status history, subscription lifecycle events, and account `commercial_status`. Adoption uses the product usage fact, the product outcome fact, product user status, and `adoption_reached`.

## Business events

The stage and status values that choose an event are the working vocabulary. `decisions.md` marks that vocabulary as an open question for human review before DATA-002. The grain of `adoption_reached` is also a working assumption marked there, because the alternative would change that grain.

`product_usage` represents product usage. The other rows are stored as `lifecycle_event`.

| Event | Grain | Entity | Ordering timestamp | Lifecycle stage | Choosing value |
|---|---|---|---|---|---|
| `lead_created` | One row represents one creation of one lead. | `lead` | `occurred_at`, equal to the lead's `created_at` | `lead` | A lead is created at status `new`. |
| `lead_qualified` | One row represents one qualification of one lead. | `lead` | `occurred_at` | `lead` | Lead status becomes `qualified`. |
| `lead_disqualified` | One row represents one disqualification of one lead. | `lead` | `occurred_at` | `lead` | Lead status becomes `disqualified`. |
| `lead_converted` | One row represents one conversion of one lead to one opportunity. | `lead` | `occurred_at` | `lead` | Lead status becomes `converted`. |
| `opportunity_opened` | One row represents one opening of one opportunity. | `opportunity` | `occurred_at`, equal to the opportunity's `created_at` | `opportunity` | An opportunity is created at stage `discovery`. |
| `opportunity_stage_changed` | One row represents one move of one opportunity between open stages. | `opportunity` | `occurred_at` | `opportunity` | Stage becomes `evaluation`, `proposal`, or `negotiation`. The opening `discovery` stage is `opportunity_opened`, not this event. |
| `opportunity_won` | One row represents one win of one opportunity. | `opportunity` | `occurred_at` | `opportunity` | Stage becomes `closed_won`. |
| `opportunity_lost` | One row represents one loss of one opportunity. | `opportunity` | `occurred_at` | `opportunity` | Stage becomes `closed_lost`. |
| `customer_converted` | One row represents the first win for one account. | `account` | `occurred_at` of that first win | `customer` | The account's first `opportunity_won`. The canonical customer identifier is `account_id`. |
| `adoption_reached` | One row represents the first time one account reaches adoption. | `account` | `occurred_at` of the first `product_outcome` | `adoption` | The account's first `product_outcome`, of any outcome type. |
| `product_usage` | One row represents one usage of one AI workflow by one product user. | `product_usage` | `occurred_at` | `adoption` | Each Product usage observation. |
| `subscription_renewed` | One row represents one renewal of one subscription. | `subscription` | `occurred_at` | `renewal` | Each renewal observation, including when status stays `active`. |
| `subscription_expanded` | One row represents one expansion of one subscription. | `subscription` | `occurred_at` | `renewal` | Each expansion observation, including when status stays `active`. |
| `subscription_churned` | One row represents one churn of one subscription. | `subscription` | `occurred_at` | `renewal` | Subscription status becomes `churned`. |

Required foreign keys on `lifecycle_event`:

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

Lead status `working` does not choose an event. Subscription statuses `pending` and `active` do not by themselves choose a lifecycle event. A renewal observation fires `subscription_renewed`, and an expansion observation fires `subscription_expanded`, on every such observation, including when status stays `active`. Consecutive renewals each fire `subscription_renewed`. Consecutive expansions each fire `subscription_expanded`. Term, amount, and seat changes still open a Type 2 subscription version. `churned` chooses `subscription_churned`. The new-business booking and the subscription's first effective-dated row record the commercial start. Product user status does not choose a lifecycle event; it is history on the product user dimension.

A later win for an account that was a `former_customer` is another `opportunity_won`. It does not create a second `customer_converted`. `commercial_status` returns to `customer` through a new effective-dated account row.
