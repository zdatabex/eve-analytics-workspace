---
id: DATA-008-005
title: Standardize staging model quality
type: implementation
agent: analytics-engineer
skills:
  - dbt-development
  - using-dbt-for-analytics-engineering
  - data-modeling
priority: high
components:
  - dbt
dependencies:
  - DATA-008-001
  - DATA-008-002
  - DATA-008-003
  - DATA-008-004
requires_approval: true
allowed_paths:
  - warehouse/dbt/models/staging/hubspot/
  - warehouse/dbt/models/staging/dealhub/
  - warehouse/dbt/models/staging/marketing/
  - warehouse/dbt/models/staging/product/
  - warehouse/dbt/tests/staging/
  - warehouse/dbt/tests/data_008_001/
  - warehouse/dbt/tests/dealhub/
  - warehouse/dbt/tests/marketing/
excluded_paths:
  - contracts/
  - data-generation/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - docs/
  - specs/
  - tests/
  - data/
  - warehouse/dbt/dbt_project.yml
  - warehouse/dbt/profiles.yml
  - warehouse/dbt/packages.yml
  - warehouse/dbt/package-lock.yml
  - warehouse/dbt/README.md
  - warehouse/dbt/macros/
  - warehouse/dbt/models/utilities/
  - warehouse/dbt/models/intermediate/
  - warehouse/dbt/models/marts/
  - warehouse/dbt/models/staging/hubspot/_hubspot__sources.yml
  - warehouse/dbt/models/staging/dealhub/_dealhub__sources.yml
  - warehouse/dbt/models/staging/marketing/_marketing__sources.yml
  - warehouse/dbt/models/staging/product/_product__sources.yml
  - warehouse/dbt/tests/test_effective_date.sql
  - warehouse/dbt/tests/test_generate_surrogate_key.sql
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

Bring the HubSpot, DealHub, Marketing, and Product staging models onto one staging layout, with discoverable documentation and a test set that keeps the current contract rules.

Model names, column names, and staged values stay as they are. Column order changes only where a model does not already follow the order in this specification. The models remain pass-through views of one source table each.

## Business context

GitHub issue #47 (`DATA-008-005 — Standardize staging model quality`) depends on DATA-008-001, DATA-008-002, DATA-008-003, and DATA-008-004. Those issues staged the four GTM source systems. The staged interfaces disagree on directory layout, YAML layout, SQL shape, and which checks are custom tests.

Later warehouse models will `ref()` these relations. They need one way to find a model, its grain, and its columns. This task does not add business logic, metrics, canonical identity, or another source system.

The binding source contracts are `contracts/source/hubspot/`, `contracts/source/dealhub/`, `contracts/source/marketing/`, and `contracts/source/product/`. This task reads them and does not edit them. The development warehouses are `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`.

## Scope

The implementation adopts the staging layout below for every existing staging model. It does not add a model, a source, or a package.

- One directory per source: `warehouse/dbt/models/staging/<source>/`. No ticket directory under it. Move the HubSpot models out of `models/staging/hubspot/data_008_001/` and remove that directory.
- One SQL file: `stg_<source>__<entity>.sql`.
- One YAML file with that same basename beside the SQL. Remove the shared files `models/staging/hubspot/data_008_001/schema.yml`, `models/staging/dealhub/schema.yml`, `models/staging/product/schema.yml`, and `models/staging/marketing/_marketing__models.yml`.
- Source declarations stay in `_hubspot__sources.yml`, `_dealhub__sources.yml`, `_marketing__sources.yml`, and `_product__sources.yml`.

Each model is a view through the project default in `dbt_project.yml`. The SQL does not set `materialized` and does not set a tag. Remove `config(materialized='view', tags=['marketing_staging'])` from the Marketing models. Nothing outside those models and the Marketing reconciliation tests selects `tag:marketing_staging`.

SQL for every model is:

```sql
with raw_data as (

    select * from {{ source('<source>', '<entity>') }}

),

renamed as (

    select
        <columns in the order below>
    from raw_data

)

select * from renamed
```

`renamed` lists the current columns by name. It does not cast, rename, filter, join, aggregate, or deduplicate. A null stays null. An empty string stays an empty string. `amount` null stays null and is not stored as zero. The model does not call `source()` for any other table and does not `ref()` another model.

Column order inside `renamed` is the grain key, foreign keys that are not part of the grain, other strings (including enums), numerics, dates and timestamps that are not part of the grain, then `source_system`, `delivery_id`, `ingested_at`. A date or timestamp that is part of the grain stays in the grain key. None of these models has a boolean. Same-system foreign keys come before identifiers that point at another source system. The lists below are that order. Names in the lists are the only output columns.

### Grain

| Model | Source | History | Grain | Unique key |
|---|---|---|---|---|
| `stg_hubspot__company` | `source('hubspot', 'company')` | observation | One observation of one HubSpot company | `hubspot_company_id`, `observed_at` |
| `stg_hubspot__contact` | `source('hubspot', 'contact')` | observation | One observation of one HubSpot contact | `hubspot_contact_id`, `observed_at` |
| `stg_hubspot__lead` | `source('hubspot', 'lead')` | observation | One observation of one HubSpot lead | `hubspot_lead_id`, `observed_at` |
| `stg_hubspot__deal` | `source('hubspot', 'deal')` | observation | One observation of one HubSpot deal | `hubspot_deal_id`, `observed_at` |
| `stg_hubspot__activity` | `source('hubspot', 'activity')` | immutable | One HubSpot activity | `hubspot_activity_id` |
| `stg_dealhub__quote` | `source('dealhub', 'quote')` | observation | One observation of one DealHub quote | `dealhub_quote_id`, `observed_at` |
| `stg_dealhub__contract` | `source('dealhub', 'contract')` | observation | One observation of one DealHub contract | `dealhub_contract_id`, `observed_at` |
| `stg_dealhub__subscription` | `source('dealhub', 'subscription')` | observation | One observation of one DealHub subscription | `dealhub_subscription_id`, `observed_at` |
| `stg_dealhub__booking` | `source('dealhub', 'booking')` | immutable | One recognized booking | `dealhub_booking_id` |
| `stg_marketing__campaign` | `source('marketing', 'campaign')` | current | One marketing campaign | `marketing_campaign_id` |
| `stg_marketing__campaign_performance` | `source('marketing', 'campaign_performance')` | immutable | One campaign on one day | `marketing_campaign_id`, `performance_date` |
| `stg_marketing__touch` | `source('marketing', 'touch')` | immutable | One attribution touch | `marketing_touch_source_id` |
| `stg_product__firm` | `source('product', 'firm')` | current | One Product firm | `product_firm_id` |
| `stg_product__user` | `source('product', 'user')` | observation | One observation of one product user | `product_user_source_id`, `observed_at` |
| `stg_product__ai_workflow` | `source('product', 'ai_workflow')` | current | One AI workflow | `product_workflow_id` |
| `stg_product__usage` | `source('product', 'usage')` | immutable | One usage of one AI workflow by one product user | `product_usage_source_id` |
| `stg_product__outcome` | `source('product', 'outcome')` | immutable | One outcome of one product usage event | `product_outcome_source_id` |

A repeated source identifier on an observation model is another observation when `observed_at` differs. The models keep every landed row.

### Columns

`stg_hubspot__company`: `hubspot_company_id`, `observed_at`, `firm_name`, `primary_domain`, `state`, `segment`, `practice_focus`, `icp_fit`, `owner_name`, `hubspot_lifecycle_stage`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__contact`: `hubspot_contact_id`, `observed_at`, `hubspot_company_id`, `full_name`, `email_normalized`, `title`, `buying_role`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__lead`: `hubspot_lead_id`, `observed_at`, `hubspot_company_id`, `hubspot_contact_id`, `hubspot_deal_id`, `marketing_campaign_id`, `status`, `emitted_event`, `created_at`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__deal`: `hubspot_deal_id`, `observed_at`, `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, `dealhub_subscription_id`, `opportunity_name`, `opportunity_type`, `stage`, `owner_name`, `forecast_category`, `emitted_event`, `amount`, `expected_close_date`, `created_at`, `source_system`, `delivery_id`, `ingested_at`.

`stg_hubspot__activity`: `hubspot_activity_id`, `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, `hubspot_deal_id`, `activity_type`, `subject`, `occurred_at`, `source_system`, `delivery_id`, `ingested_at`.

`stg_dealhub__quote`: `dealhub_quote_id`, `observed_at`, `hubspot_deal_id`, `hubspot_company_id`, `quote_number`, `status`, `quoted_amount`, `source_system`, `delivery_id`, `ingested_at`.

`stg_dealhub__contract`: `dealhub_contract_id`, `observed_at`, `dealhub_quote_id`, `hubspot_deal_id`, `hubspot_company_id`, `contract_number`, `status`, `total_contract_value`, `start_date`, `end_date`, `source_system`, `delivery_id`, `ingested_at`.

`stg_dealhub__subscription`: `dealhub_subscription_id`, `observed_at`, `dealhub_contract_id`, `hubspot_company_id`, `subscription_number`, `status`, `plan_code`, `billing_frequency`, `emitted_event`, `seat_count`, `recurring_amount`, `term_start`, `term_end`, `source_system`, `delivery_id`, `ingested_at`.

`stg_dealhub__booking`: `dealhub_booking_id`, `dealhub_contract_id`, `dealhub_subscription_id`, `hubspot_company_id`, `hubspot_deal_id`, `booking_number`, `booking_type`, `booking_amount`, `booked_at`, `source_system`, `delivery_id`, `ingested_at`.

`stg_marketing__campaign`: `marketing_campaign_id`, `campaign_code`, `campaign_name`, `channel`, `source_system`, `delivery_id`, `ingested_at`.

`stg_marketing__campaign_performance`: `marketing_campaign_id`, `performance_date`, `spend_amount`, `impression_count`, `click_count`, `source_system`, `delivery_id`, `ingested_at`.

`stg_marketing__touch`: `marketing_touch_source_id`, `marketing_campaign_id`, `hubspot_contact_id`, `hubspot_lead_id`, `hubspot_company_id`, `occurred_at`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__firm`: `product_firm_id`, `firm_name`, `primary_domain`, `state`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__user`: `product_user_source_id`, `observed_at`, `product_firm_id`, `email_normalized`, `status`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__ai_workflow`: `product_workflow_id`, `workflow_code`, `workflow_name`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__usage`: `product_usage_source_id`, `product_user_source_id`, `product_firm_id`, `product_workflow_id`, `work_unit_count`, `occurred_at`, `source_system`, `delivery_id`, `ingested_at`.

`stg_product__outcome`: `product_outcome_source_id`, `product_usage_source_id`, `product_user_source_id`, `product_firm_id`, `product_workflow_id`, `outcome_type`, `occurred_at`, `source_system`, `delivery_id`, `ingested_at`.

### Documentation

Each model YAML documents that one model and every column. Keep the current descriptions when the YAML files are split. A description that only repeats the column name does not satisfy this section. Use the contract field description for that column when the current text only repeats the name.

Each model description states the purpose, the grain, the history class, the `source()` relation, that downstream models `ref()` this relation, that `renamed` selects landed columns with no expression, and that reconciliation exceptions are none. Keep the current distinctions between source attributes and later canonical attributes. In particular:

- `hubspot_lifecycle_stage` is the HubSpot label. It is not canonical `commercial_status`.
- `amount`, `quoted_amount`, `total_contract_value`, `recurring_amount`, `booking_amount`, and `spend_amount` stay on the source that stored them. They are not ARR, and a null amount is not zero.
- `emitted_event` is the source signal on that row. It is not a lifecycle-event entity.
- `marketing_campaign_id` on a HubSpot lead, `dealhub_subscription_id` on a HubSpot deal, and HubSpot identifiers on DealHub and Marketing rows stay unresolved. Staging does not look them up.
- `source_system`, `delivery_id`, and `ingested_at` are delivery metadata. They are not part of the grain key. Late `ingested_at` is valid.
- Product descriptions still say that the model does not resolve canonical identity, derive adoption, or calculate a metric.

This specification is the record of the layout applied by the change. The model YAML is the discoverable documentation. Do not add a document under `docs/` or a section to `warehouse/dbt/README.md`.

### Tests in the model YAML

Tests live in that model's YAML. The tests are `unique`, `not_null`, `accepted_values`, and `relationships`, plus the installed generic tests below where those four cannot express the current rule. Do not add a dbt package. `dbt_utils` is already installed.

Keep the current generic tests, with these alignments:

- Grain uniqueness is `unique` when the unique key is one column. It is `dbt_utils.unique_combination_of_columns` when the unique key has more than one column. `unique` on one column of an observation key would reject a later observation of the same source identifier.
- `not_null` stays on every column the current YAML marks `not_null`. That set is the contract fields with `nullable: false`, including `source_system`, `delivery_id`, and `ingested_at`.
- `dbt_utils.not_empty_string` stays on string columns that do not have `accepted_values`. Set `trim_whitespace: false` on every such test. The contract rejects an empty string. HubSpot's current tests omit the argument and use the package default `true`. `false` is the same predicate DealHub, Marketing, and Product already use. Do not change staged values.
- Drop `not_empty_string` from a column that has `accepted_values`. The accepted list already rejects `''`.
- `accepted_values` stays on the current enum columns, with the current lists. Nullable enums keep null outside the list. `source_system` accepts only that model's source name: `hubspot`, `dealhub`, `marketing`, or `product`.
- These non-grain `unique` tests stay, because the contract requires them and they are not the grain key: `stg_marketing__campaign.campaign_code`, `stg_dealhub__booking.booking_number`, `stg_product__ai_workflow.workflow_code`, and `stg_product__outcome.product_usage_source_id`.
- `relationships` stays on the current same-system parents. Do not add a relationship to another source system. There is no `relationships` test on `stg_hubspot__lead.marketing_campaign_id`, `stg_hubspot__deal.dealhub_subscription_id`, any HubSpot identifier stored on DealHub or Marketing, or a Product firm matched by `primary_domain`.

Same-system relationships that stay:

| Column | Parent |
|---|---|
| `stg_hubspot__contact.hubspot_company_id` | `stg_hubspot__company.hubspot_company_id` |
| `stg_hubspot__lead.hubspot_company_id` | `stg_hubspot__company.hubspot_company_id` |
| `stg_hubspot__lead.hubspot_contact_id` | `stg_hubspot__contact.hubspot_contact_id` |
| `stg_hubspot__lead.hubspot_deal_id` | `stg_hubspot__deal.hubspot_deal_id` |
| `stg_hubspot__deal.hubspot_company_id` | `stg_hubspot__company.hubspot_company_id` |
| `stg_hubspot__deal.hubspot_contact_id` | `stg_hubspot__contact.hubspot_contact_id` |
| `stg_hubspot__deal.hubspot_lead_id` | `stg_hubspot__lead.hubspot_lead_id` |
| `stg_hubspot__activity.hubspot_company_id` | `stg_hubspot__company.hubspot_company_id` |
| `stg_hubspot__activity.hubspot_contact_id` | `stg_hubspot__contact.hubspot_contact_id` |
| `stg_hubspot__activity.hubspot_lead_id` | `stg_hubspot__lead.hubspot_lead_id` |
| `stg_hubspot__activity.hubspot_deal_id` | `stg_hubspot__deal.hubspot_deal_id` |
| `stg_dealhub__contract.dealhub_quote_id` | `stg_dealhub__quote.dealhub_quote_id` |
| `stg_dealhub__subscription.dealhub_contract_id` | `stg_dealhub__contract.dealhub_contract_id` |
| `stg_dealhub__booking.dealhub_contract_id` | `stg_dealhub__contract.dealhub_contract_id` |
| `stg_dealhub__booking.dealhub_subscription_id` | `stg_dealhub__subscription.dealhub_subscription_id` |
| `stg_marketing__campaign_performance.marketing_campaign_id` | `stg_marketing__campaign.marketing_campaign_id` |
| `stg_marketing__touch.marketing_campaign_id` | `stg_marketing__campaign.marketing_campaign_id` |
| `stg_product__user.product_firm_id` | `stg_product__firm.product_firm_id` |
| `stg_product__usage.product_user_source_id` | `stg_product__user.product_user_source_id` |
| `stg_product__usage.product_firm_id` | `stg_product__firm.product_firm_id` |
| `stg_product__usage.product_workflow_id` | `stg_product__ai_workflow.product_workflow_id` |
| `stg_product__outcome.product_usage_source_id` | `stg_product__usage.product_usage_source_id` |
| `stg_product__outcome.product_user_source_id` | `stg_product__user.product_user_source_id` |
| `stg_product__outcome.product_firm_id` | `stg_product__firm.product_firm_id` |
| `stg_product__outcome.product_workflow_id` | `stg_product__ai_workflow.product_workflow_id` |

`dbt_utils.expression_is_true` and `dbt_utils.accepted_range` stay where they already are, with the current predicate text. Copy the predicate. Do not tighten or loosen it. Add a `description` on each of those tests that states the rule in one sentence. The current predicates are:

- Company `primary_domain`, when present, is lowercase and trimmed and contains neither a scheme nor a path. The Product firm domain predicate stays the current Product expression, including the checks for `\`, `@`, and whitespace. Do not make the two domain predicates the same.
- Contact `email_normalized`, when present, equals its lowercase trimmed form. The Product user email predicate stays the current Product expression.
- Lead `observed_at` is at or after `created_at`. Lead `status` and `emitted_event` stay paired as they are now, including `working` with a null event and `new` allowed by that predicate. `hubspot_deal_id` is present only on `lead_converted`.
- Deal `observed_at` is at or after `created_at`. `amount` is null or greater than or equal to zero. `new_business` has null `dealhub_subscription_id`. `expansion` and `renewal` have a non-empty `dealhub_subscription_id`. Existence of that subscription is not tested.
- Activity has at least one of `hubspot_company_id`, `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_deal_id`.
- Quote `quoted_amount` is greater than or equal to zero when present, and a null `quoted_amount` is allowed when `status` is `draft`.
- Contract `end_date` is at or after `start_date`. `total_contract_value` is greater than or equal to zero.
- Subscription `term_end` is at or after `term_start`. `seat_count` and `recurring_amount` are greater than or equal to zero.
- Booking `booking_amount` is greater than or equal to zero.
- Touch has at least one of `hubspot_contact_id`, `hubspot_lead_id`, and `hubspot_company_id`.
- Campaign performance `spend_amount`, `impression_count`, and `click_count` are greater than or equal to zero when present. Null stays null. Do not add an integer test those columns do not already have.
- Usage `work_unit_count` is a whole number greater than or equal to 1.

Move the subscription status and `emitted_event` pairing from `dealhub_subscription_event_pairing.sql` onto `stg_dealhub__subscription` as one `dbt_utils.expression_is_true`. The expression is the current positive predicate: `pending` has a null event, `active` has a null event or `subscription_renewed` or `subscription_expanded`, and `churned` has `subscription_churned`. `accepted_values` cannot express that pair. Delete the singular file after the YAML test exists.

### Singular tests

A singular test remains only for a rule that `unique`, `not_null`, `accepted_values`, `relationships`, `not_empty_string`, `accepted_range`, and `expression_is_true` cannot express. A pass-through model does not get a singular test that compares every staged column to the source.

Delete these every-column reconciliation tests:

- `warehouse/dbt/tests/data_008_001/reconcile_hubspot_staging.sql`
- `warehouse/dbt/tests/dealhub/reconcile_dealhub_staging.sql`
- `warehouse/dbt/tests/marketing/test_stg_marketing__campaign_matches_source.sql`
- `warehouse/dbt/tests/marketing/test_stg_marketing__campaign_performance_matches_source.sql`
- `warehouse/dbt/tests/marketing/test_stg_marketing__touch_matches_source.sql`
- `warehouse/dbt/tests/staging/product/stg_product__firm_reconciles_to_source.sql`
- `warehouse/dbt/tests/staging/product/stg_product__user_reconciles_to_source.sql`
- `warehouse/dbt/tests/staging/product/stg_product__ai_workflow_reconciles_to_source.sql`
- `warehouse/dbt/tests/staging/product/stg_product__usage_reconciles_to_source.sql`
- `warehouse/dbt/tests/staging/product/stg_product__outcome_reconciles_to_source.sql`

Do not replace them with `dbt_utils.equality`, `dbt_utils.equal_rowcount`, or another singular column compare. Contract alignment stays in force because `renamed` selects each column with no expression, the YAML column list is the list in this specification, and the generic tests still enforce the grain, required fields, enums, ranges, and same-system relationships. The reconciliation exception list stays empty in the model description. A filter, join, cast, or rename would violate this specification. Validation confirms the column set and a sample of values against the source. That confirmation is a `dbt show` check, not a permanent singular test.

Singular tests live under `warehouse/dbt/tests/staging/<source>/`. Move the files below without changing their SQL, other than a leading comment. The comment states the rule and that the generic tests cannot express it. Keep the current violation names. `ref()` model names stay the same.

| File | Why it stays |
|---|---|
| `tests/staging/hubspot/hubspot_lead_history.sql` | Compares observations of one `hubspot_lead_id`: `created_at` is stable, one `lead_created` row is `status` `new` at `created_at`, `qualified`, `disqualified`, and `converted` each occur at most once, a lead is not both `qualified` and `disqualified`, and `lead_converted` is at or after `lead_qualified`. |
| `tests/staging/hubspot/hubspot_deal_history.sql` | Compares observations of one deal: `created_at` and `hubspot_company_id` are stable, `hubspot_lead_id` does not change within the deal, one `opportunity_opened` row is `discovery` at `created_at`, a stage change carries the matching `emitted_event`, won and lost occur at most once and not together, and one lead belongs to one deal. |
| `tests/staging/hubspot/hubspot_deal_contact_company.sql` | The contact observation in effect at the deal `observed_at` has the same `hubspot_company_id` as the deal. `relationships` does not choose an as-of row. |
| `tests/staging/hubspot/hubspot_activity_parent_company.sql` | When the activity names a company, an in-effect deal, contact, or lead observation that has a company must match it. A deal requires an in-effect observation. A contact or lead constrains the activity only when that observation has a company. |
| `tests/staging/dealhub/dealhub_document_number_stability.sql` | One quote, contract, or subscription identifier has one document number across observations, and one document number belongs to one identifier. `unique` on the number would fail repeated observations. Booking stays out of this test because `booking_number` already has `unique`. |
| `tests/staging/dealhub/dealhub_relationship_rules.sql` | One quote is cited by one contract, one `hubspot_deal_id` is cited by one contract, one subscription keeps one `dealhub_contract_id`, and the company identifier agrees across the quote and citing contract, the contract and subscription, the contract and booking, and the subscription and booking. `relationships` checks existence only. |
| `tests/staging/dealhub/dealhub_booking_on_or_after_churn.sql` | `subscription_churned` occurs at most once per subscription, and no booking of that subscription has `booked_at` on or after that observation's `observed_at`. `ingested_at` stays out of the comparison. |
| `tests/staging/product/stg_product__usage_firm_matches_user_in_effect.sql` | The user observation in effect at the usage `occurred_at` has the usage `product_firm_id`. No in-effect observation fails the test. The test does not add `effective_start`, `effective_end`, or `is_current`. |
| `tests/staging/product/stg_product__outcome_agrees_with_cited_usage.sql` | The outcome's user, firm, workflow, and `occurred_at` agree with the cited usage. `occurred_at` on the outcome is at or after the usage. `relationships` does not compare those attributes. |

Remove the empty directories `warehouse/dbt/tests/data_008_001/`, `warehouse/dbt/tests/dealhub/`, and `warehouse/dbt/tests/marketing/` after the moves and deletions.

A failing test stays failing. The implementation does not drop the row, rewrite the value, or edit a contract to obtain a green test.

## Deliverables

- Seventeen staging SQL files in `warehouse/dbt/models/staging/<source>/`, each with the `raw_data` and `renamed` shape and the column order in this specification.
- Seventeen model YAML files, one beside each SQL file, documenting the model, every column, and the generic tests in this specification.
- The nine singular tests listed above under `warehouse/dbt/tests/staging/<source>/`.
- Removal of the ticket directory, the shared staging YAML files, the every-column reconciliation tests, `dealhub_subscription_event_pairing.sql`, and the Marketing `config` blocks.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read the source contracts and leave them unchanged.
- Leave the four `_sources.yml` files, `dbt_project.yml`, `profiles.yml`, `packages.yml`, `package-lock.yml`, `warehouse/dbt/README.md`, macros, utilities, intermediate models, and marts unchanged.
- The repository has no SQL formatter or linter configuration. Do not add one. The SQL shape and column order in this specification are the format.
- Do not add a dbt package, a canonical column, an effective-dating column, a metric, a cross-source join, or a lifecycle-event model.
- Do not change a model name or a column name. Column order is the result-shape change this specification allows. No model under `models/intermediate/` or `models/marts/` references these models. A rename, removal, or retype of a column is outside this task.
- Use an isolated schema named `dev_data_008_005`, set with `EVE_DBT_SCHEMA`. Do not build into a raw schema or the shared `dev_dbt` schema.
- Validate against `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Do not commit either file, dbt artifacts, or a virtualenv.
- `testing.integration_tests` is false because `components` lists only `dbt`.
- No deployment and no production warehouse change.

## Acceptance criteria

- [ ] The implementation changes only staging model SQL, per-model YAML, and staging tests inside `allowed_paths`. The four source YAML files, shared dbt project files, `contracts/`, and `docs/` are unchanged.
- [ ] HubSpot, DealHub, Marketing, and Product models live in `models/staging/<source>/` as `stg_<source>__<entity>.sql`, with one YAML file of the same basename beside each SQL file. `models/staging/hubspot/data_008_001/` is gone. No shared `schema.yml` or `_models.yml` remains for these models.
- [ ] Every model uses `raw_data`, then `renamed`, then `select * from renamed`. `raw_data` reads only that model's `source()`. `renamed` selects the columns listed for that model, in that order, with no expression. There is no model `config` block.
- [ ] Each model is a view. Grain, history, unique key, column names, and values match this specification. Nulls and amounts pass through. The models do not filter, deduplicate, or rewrite landed rows.
- [ ] Every model and every column has a description in its YAML. The description states the source meaning. The model description states grain, history, source, pass-through behavior, and an empty reconciliation-exception list.
- [ ] Generic tests in each model YAML are the grain test, `not_null`, `not_empty_string` with `trim_whitespace: false` on strings that are not enums, `accepted_values`, the same-system `relationships` listed above, and the current `expression_is_true` and `accepted_range` predicates. The subscription status and event pairing is an `expression_is_true` test. `dealhub_subscription_event_pairing.sql` is gone.
- [ ] The nine singular tests remain, under `tests/staging/<source>/`, with their current rules. Each file's leading comment states why the generic tests cannot express the rule. The every-column reconciliation tests are gone and are not replaced by another column-compare test.
- [ ] `tests/data_008_001/`, `tests/dealhub/`, and `tests/marketing/` are gone.
- [ ] From `warehouse/dbt/`, with `EVE_DBT_SCHEMA=dev_data_008_005`, `dbt parse` succeeds and `dbt build --select path:models/staging path:tests/staging` succeeds against `data/warehouse/dev_data_003` and against `data/warehouse/dev_data_004`.
- [ ] `dbt show` for each staged model returns rows from the baseline warehouse. For each model, the staged column set matches the source column set, and a limited sample of values matches the source aside from column order.
- [ ] No file under `data/warehouse/` is committed.

## Execution notes

Implement this specification only after it has merged and issue #47 is `status:ready`. Use an `impl` worktree and schema `dev_data_008_005`. Do not merge or deploy without human approval.

Before editing a model, read its current YAML description and its contract file. Confirm column names from the current SQL and from `dbt show --limit 5` on `source()`. Keep the current descriptions and the current `expression_is_true` and `accepted_range` text.

Search the repository for `ref('stg_hubspot__`, `ref('stg_dealhub__`, `ref('stg_marketing__`, and `ref('stg_product__` before changing column order. The expected referencers are these staging tests. If a model outside `allowed_paths` selects one of these relations, stop.

Validation runs from `warehouse/dbt/` against each warehouse file:

```bash
export EVE_DBT_SCHEMA=dev_data_008_005
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_003
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select path:models/staging path:tests/staging
.venv/bin/dbt show --profiles-dir . --select stg_hubspot__company --limit 5
```

Repeat `dbt show --limit 5` for each of the seventeen models. Repeat the build and a limited `dbt show` with `EVE_DBT_DUCKDB_PATH` pointed at `data/warehouse/dev_data_004`. If a warehouse file is absent, create it through the merged DATA-006 generate and load path, and do not commit it.

For each model, compare the `dbt show` column names with the source column names, and compare a limited sample of values. A difference other than column order is a stop. Do not make a test pass by dropping rows or by changing a contract.
