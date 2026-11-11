---
id: DATA-008-006
title: Improve staging model documentation
type: implementation
agent: analytics-engineer
skills:
  - dbt-development
  - using-dbt-for-analytics-engineering
  - data-modeling
  - data-generation
priority: medium
components:
  - dbt
dependencies:
  - DATA-008-005
requires_approval: true
allowed_paths:
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__company.yml
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__contact.yml
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__lead.yml
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__deal.yml
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__activity.yml
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__quote.yml
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__contract.yml
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__subscription.yml
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__booking.yml
  - warehouse/dbt/models/staging/marketing/stg_marketing__campaign.yml
  - warehouse/dbt/models/staging/marketing/stg_marketing__campaign_performance.yml
  - warehouse/dbt/models/staging/marketing/stg_marketing__touch.yml
  - warehouse/dbt/models/staging/product/stg_product__firm.yml
  - warehouse/dbt/models/staging/product/stg_product__user.yml
  - warehouse/dbt/models/staging/product/stg_product__ai_workflow.yml
  - warehouse/dbt/models/staging/product/stg_product__usage.yml
  - warehouse/dbt/models/staging/product/stg_product__outcome.yml
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
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__company.sql
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__contact.sql
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__lead.sql
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__deal.sql
  - warehouse/dbt/models/staging/hubspot/stg_hubspot__activity.sql
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__quote.sql
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__contract.sql
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__subscription.sql
  - warehouse/dbt/models/staging/dealhub/stg_dealhub__booking.sql
  - warehouse/dbt/models/staging/marketing/stg_marketing__campaign.sql
  - warehouse/dbt/models/staging/marketing/stg_marketing__campaign_performance.sql
  - warehouse/dbt/models/staging/marketing/stg_marketing__touch.sql
  - warehouse/dbt/models/staging/product/stg_product__firm.sql
  - warehouse/dbt/models/staging/product/stg_product__user.sql
  - warehouse/dbt/models/staging/product/stg_product__ai_workflow.sql
  - warehouse/dbt/models/staging/product/stg_product__usage.sql
  - warehouse/dbt/models/staging/product/stg_product__outcome.sql
  - warehouse/dbt/tests/
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

Rewrite the HubSpot, DealHub, Marketing, and Product staging descriptions so a person can tell what each row and each field means, in few words.

The descriptions follow the Documentation section of `dbt-development`. Model SQL, tests, grains, and column sets stay as DATA-008-005 left them.

## Business context

GitHub issue #50 (`DATA-008-006 — Improve staging model documentation`) depends on DATA-008-005. That work merged the seventeen staging models as one YAML file beside each SQL file. The descriptions still recite grain, keys, history class, `source()` and `ref()`, reconciliation, canonical identity, and test predicates. A reader has to dig for the business meaning, and later prompts spend tokens on text that does not help them use the row.

The binding meanings are the merged source contracts in `contracts/source/` and the logical ownership in `docs/data-model/source-mapping.md`. This task reads both and edits neither. Staged behavior is the pass-through already in the SQL: one source table, landed values, nulls left null. Generators under `data-generation/` already produce that shape. This task does not change them and does not describe a transformation the model does not perform.

Warehouse staging documentation belongs with the other DATA-008 staging work. The implementation agent is `analytics-engineer`.

On the merged DATA-008-005 YAML, the seventeen model `description` values plus their column `description` values total 40,050 characters. Test `description` values are a separate 1,824 characters and stay as written.

## Scope

The implementation rewrites description text in the seventeen YAML files under `allowed_paths`. It does not add a model, a column, a test, a package, a docs block, or a page under `docs/`.

Staging layout stays the `dbt-development` Staging section. One directory per source. One `stg_<source>__<entity>.sql`. One YAML file with that same basename. Source declarations stay in the four `_sources.yml` files. SQL stays `raw_data`, then `renamed`, then `select * from renamed`. This task does not choose another layout.

### Who the description is for

Write each description for a person using the model. The Documentation section of `dbt-development` is the description shape.

A model description is at most three short sentences: what one row is, the behavior that would surprise the reader when there is one, and where related numbers live when they are on another staged model. `stg_marketing__campaign` uses the three sentences already given for that case:

`One marketing campaign per row. A channel change replaces the previous channel. Daily spend and results are on campaign performance.`

A column description is one sentence a person would say. It says what the column means. When a closed list helps, it names the values in the ordinary words below.

Model and column descriptions leave out grain, keys, history class, canonical identity, `source()` and `ref()` mechanics, reconciliation, and the phrase "not on this model." They do not repeat the model's sentence. They do not restate `not_null`, `unique`, an empty-string check, an identifier-shape rule, or "not a canonical key."

### What one row is

The first sentence says what one row is. A later sentence is only the surprise or the other home of a number, and only when that cell has one.

| Model | One row | Surprise | Related numbers on another model |
|---|---|---|---|
| `stg_hubspot__company` | One HubSpot company as HubSpot recorded it at one time | A later recording of the same company is another row | Deal amount, contract value, and booking amount live on the HubSpot deal and the DealHub models |
| `stg_hubspot__contact` | One HubSpot contact as HubSpot recorded that person at one time | A later recording of the same contact is another row | |
| `stg_hubspot__lead` | One HubSpot lead as HubSpot recorded its status at one time | A later status is another row | |
| `stg_hubspot__deal` | One HubSpot deal as HubSpot recorded it at one time | A later recording of the same deal is another row even when the stage stays the same | Booking amount lives on DealHub bookings, and the repeating charge lives on the DealHub subscription |
| `stg_hubspot__activity` | One HubSpot call, email, or meeting | The activity is kept as recorded and can name a firm, a contact, a lead, a deal, or more than one of those | |
| `stg_dealhub__quote` | One DealHub quote as DealHub recorded it at one time | A later status or quoted price is another row | Contract value lives on the DealHub contract |
| `stg_dealhub__contract` | One DealHub contract as DealHub recorded it at one time | A later change to status, value, or dates is another row | The repeating charge lives on the DealHub subscription |
| `stg_dealhub__subscription` | One DealHub subscription as DealHub recorded it at one time | A renewal or an expansion can be recorded while the subscription stays active | Booking amount lives on DealHub bookings |
| `stg_dealhub__booking` | One booking DealHub recognized | The booking is kept as recorded | Deal amount and the repeating charge stay on the HubSpot deal and the DealHub subscription |
| `stg_marketing__campaign` | The three sentences quoted above | | |
| `stg_marketing__campaign_performance` | One marketing campaign on one calendar day | A correction replaces that day's spend, impressions, and clicks | |
| `stg_marketing__touch` | One attribution touch Marketing recorded | The touch is kept as recorded and can name a contact, a lead, a firm, or more than one | |
| `stg_product__firm` | One firm as Product currently stores that tenant | A correction replaces the firm record | |
| `stg_product__user` | One product login as Product recorded it at one time | A later status, firm, or email change is another row | |
| `stg_product__ai_workflow` | One AI workflow as Product currently stores it | A correction replaces that workflow | |
| `stg_product__usage` | One use of one AI workflow by one product login | The use is kept as recorded | Results of that use live on the product outcome row |
| `stg_product__outcome` | One result of one product use | The result is kept as recorded | |

Each filled cell is one sentence. `stg_marketing__campaign` is only the three quoted sentences.

### Shared words

Use these words in every model that mentions the figure or the thing:

| Words | Use for |
|---|---|
| firm | The organization. HubSpot's row is a company. Product's row is a firm. |
| contact | The HubSpot person. |
| product login | The Product user. |
| deal amount | HubSpot `amount` |
| quoted price | DealHub `quoted_amount` |
| contract value | DealHub `total_contract_value` |
| repeating charge | DealHub `recurring_amount` |
| booking amount | DealHub `booking_amount` |
| spend | Marketing `spend_amount` |

Amounts are US dollars. The repeating charge is the fee stored for the billing period. Descriptions do not annualize it.

The same email, the same web address, and the same firm name can appear on more than one source record. Say that on the column that holds the value.

`ingested_at` uses one sentence on every model: `When this delivery was accepted, which can be later than the business time on the row.`

`delivery_id` uses one sentence on every model: `The delivery batch this row arrived in, shared with the other rows in that batch.`

`source_system` uses one sentence that names the sending system for that model: HubSpot, DealHub, Marketing, or Product.

### Column sentences

Every column keeps one description. The sentence starts from the contract field's meaning and the value the staged model actually returns. A distinction below shares that sentence.

Closed values use these words:

| Column | Words |
|---|---|
| `segment` | solo, small, mid, or large |
| `icp_fit` | in the ideal customer profile, or outside it |
| `buying_role` | champion, decision maker, user, or billing |
| lead `status` | new, working, qualified, disqualified, or converted |
| deal `stage` | discovery, evaluation, proposal, negotiation, closed won, or closed lost |
| `opportunity_type` and `booking_type` | new business, expansion, or renewal |
| `forecast_category` | pipeline, best case, commit, closed, or omitted |
| quote `status` | draft, sent, accepted, rejected, or expired |
| contract `status` | active, expired, or terminated |
| subscription `status` | pending, active, or churned |
| `billing_frequency` | monthly, quarterly, or annual |
| product user `status` | invited, active, or inactive |
| `outcome_type` | draft completed, review accepted, or exported |
| `activity_type` | call, email, or meeting |
| `channel` | paid search, paid social, email, webinar, partner, or outbound |
| lead `emitted_event` | created, qualified, disqualified, or converted |
| deal `emitted_event` | opened, stage changed, won, or lost |
| subscription `emitted_event` | renewed, expanded, or churned |

These distinctions stay in the column sentence that owns them:

- `hubspot_lifecycle_stage` is HubSpot's own lifecycle label, and those words are not limited to prospect, customer, or former customer.
- The firm-relationship owner on the HubSpot company and the deal owner are different people.
- `expected_close_date` and the contract start date are different days.
- `created_at` stays the time the lead or deal was created. `observed_at` is when that recording was taken. `occurred_at`, `booked_at`, `performance_date`, and the term dates are the other times, each named for the event it marks.
- A campaign id on a HubSpot lead, a subscription id on a HubSpot deal, and a HubSpot id stored on a DealHub or Marketing row is that other system's id.
- `dealhub_subscription_id` on a HubSpot deal is the subscription an expansion or renewal targets. New business leaves it blank.
- A lead's `hubspot_deal_id` is present only on the converted observation and blank otherwise.
- Lead `emitted_event` is blank while the lead is working. Deal `emitted_event` is blank when the stage did not change on that recording. Subscription `emitted_event` is blank while pending, and blank on an active subscription that is not a renewal or expansion.
- A blank deal amount, quoted price, spend, impression count, or click count stays blank. A draft quote may leave the quoted price blank.
- Clicks on a campaign day can exceed impressions.
- The same email can appear on more than one HubSpot contact and on more than one product login. A product login is not a HubSpot contact and is not a billed seat.
- A Product firm's name and web address can differ from the HubSpot company for the same firm.
- `work_unit_count` counts work on that use. `seat_count` counts seats billed on the subscription. `impression_count` and `click_count` count those delivery events for the campaign day.
- `plan_code`, `practice_focus`, `workflow_name`, `state`, and the name and subject columns keep the source's own wording.

An identifier sentence names whose id it is and which record it points at. A document number sentence (`quote_number`, `contract_number`, `subscription_number`, `booking_number`, `campaign_code`, `workflow_code`) names the business number a person would read on that record.

### Length

After the rewrite, the sum of the characters in the seventeen model `description` values and their column `description` values is at most 20,025, half of the 40,050-character baseline. Count the parsed strings. The sentence rules above still hold when the text is under that cap. Cutting a distinction in the tables above to make the cap is a miss.

## Deliverables

- Rewritten model and column descriptions in the seventeen YAML files listed under `allowed_paths`.
- The same tests, test descriptions, SQL, column names, and column order DATA-008-005 merged.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/` and leave it unchanged.
- Leave SQL, source YAML, tests, test `description` values, `dbt_project.yml`, `profiles.yml`, `packages.yml`, `package-lock.yml`, `warehouse/dbt/README.md`, macros, utilities, intermediate models, and marts unchanged.
- Leave `data-generation/` unchanged. Descriptions match the records those generators already produce and the pass-through the SQL already performs.
- Leave `docs/` unchanged. The model YAML is the staging documentation.
- Do not add a dbt package, a `{% docs %}` block, a shared `schema.yml`, or a second description field.
- Do not change a model name, a column name, a type, a test, or a staged value.
- Use an isolated schema named `dev_data_008_006`, set with `EVE_DBT_SCHEMA`. Do not build into a raw schema or the shared `dev_dbt` schema.
- Validate against `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. Do not commit either file, dbt artifacts, or a virtualenv.
- `testing.integration_tests` is false because `components` lists only `dbt`.
- No deployment and no production warehouse change.

## Acceptance criteria

- [ ] The implementation changes only the seventeen YAML files in `allowed_paths`, and within those files only model and column `description` text.
- [ ] Each model description is at most three short sentences and follows the row table in this specification. `stg_marketing__campaign` is the three Documentation sentences quoted above.
- [ ] Each column description is one sentence, uses the shared words and closed-list words in this specification, and still carries the distinctions listed under Column sentences.
- [ ] The descriptions leave out grain, keys, history class, canonical identity, `source()` and `ref()` mechanics, reconciliation, and the phrase "not on this model." They do not restate a nullability, uniqueness, or expression test, and they do more than repeat the model or column name.
- [ ] Parsed model and column description text totals at most 20,025 characters. Test `description` text is unchanged.
- [ ] Staged SQL, column sets, tests, and values are unchanged. The models still pass through landed rows, including null amounts.
- [ ] From `warehouse/dbt/`, with `EVE_DBT_SCHEMA=dev_data_008_006`, `dbt parse` succeeds and `dbt docs generate` succeeds.
- [ ] `dbt build --select path:models/staging path:tests/staging` succeeds against `data/warehouse/dev_data_003` and against `data/warehouse/dev_data_004`.
- [ ] `contracts/`, `data-generation/`, `docs/`, and the paths under `excluded_paths` are unchanged. No warehouse file is committed.

## Execution notes

Implement this specification only after it has merged and issue #50 is `status:ready`. Use an `impl` worktree and schema `dev_data_008_006`. Do not merge or deploy without human approval.

Before editing a description, read the Documentation section of `dbt-development`, the model's current YAML, and that entity's contract file. Write for a person using the row. Then remove wording that does not help that person decide what the value means. Keep the distinctions in this specification.

Count characters from the parsed YAML, summing each model `description` and each column `description`. Do that on the merged baseline before editing, and again after. The baseline on the DATA-008-005 merge is 40,050. The revised total is at most 20,025. Leave every `data_tests` block, including its `description`, as it is.

Validation runs from `warehouse/dbt/` against each warehouse file:

```bash
export EVE_DBT_SCHEMA=dev_data_008_006
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_003
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt docs generate --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select path:models/staging path:tests/staging
```

Repeat the build with `EVE_DBT_DUCKDB_PATH` pointed at `data/warehouse/dev_data_004`. If a warehouse file is absent, create it through the merged DATA-006 generate and load path, and do not commit it.

A description that disagrees with the contract or with the staged column is a stop. Do not make it agree by changing SQL, a test, or a contract.
