# data-generation

Reproducible synthetic source data for the HubSpot, DealHub, Marketing, and Product contracts. `generate` writes one JSON Lines drop per source system. `load` places each drop in schema `raw_<source_system>` inside the dataset warehouse file.

The Python dependency for the warehouse is `duckdb`. The loader creates one raw schema per source and one table per source entity. It does not provision a remote warehouse. `generate` writes no DuckDB file.

## Install

From this directory:

```bash
python3 -m pip install -e ".[dev]"
```

Python 3.11 or newer is required. Runtime dependencies are PyYAML and DuckDB. The `dev` extra installs pytest.

## Generate

```bash
python3 -m eve_data_generation generate --config config/test.yaml
```

The default directory is `output/<config stem>/`, resolved from the package location. `config/test.yaml` writes `output/test/<source>/`. `config/default.yaml` writes `output/default/<source>/`. `config/scenarios.yaml` writes `output/scenarios/<source>/`. `config/scenarios-test.yaml` writes `output/scenarios-test/<source>/`. The working directory does not move this default.

`--output` is the parent of the four source directories. It does not insert another dataset directory. From this directory, `--output ../data/generated` writes `data/generated/hubspot/`, `data/generated/dealhub/`, `data/generated/marketing/`, and `data/generated/product/`. A second generate to the same directory replaces those files and removes every other child.

`config/default.yaml` is the development dataset. Its window is 2024-01-01 through 2025-07-01, eighteen months, with seed `1003`. `config/test.yaml` is the shorter dataset the component tests generate and load.

The source directories are `hubspot/`, `dealhub/`, `marketing/`, and `product/`. Each one holds one JSON Lines file named `<source_entity>.jsonl` for every contract entity of that source. Examples are `hubspot/company.jsonl` and `marketing/campaign_performance.jsonl`. Decimal amounts are strings with two fraction digits. Integers are JSON integers. Dates and timestamps are strings. Timestamps use a `Z` suffix. Nulls are JSON null. Object keys are sorted. Rows are ordered by `observation_key`. A non-empty file ends with a newline. An entity with no rows is an empty file. This step writes no DuckDB file.

Each source directory has one `manifest.json`. The four files share `configuration_file`, `delivery_id`, `seed`, `start_date`, and `end_date`. `entities` lists that source's row counts, keyed by `source_entity`. `delivery_id` is `dlv_<seed>`. The manifest has no wall-clock timestamp and no time component on the dates. The configured seed is the only source of randomness. The same seed, configuration, and generator version produce the same file bytes.

If the inclusive date window cannot hold the ordered timestamps, generation fails with `date range cannot hold the ordered timestamps`.

## Load

```bash
python3 -m eve_data_generation load --config config/test.yaml
```

`--dataset-dir` selects the drop directory `generate` wrote. It defaults to the same path as generate for the configuration file. `--warehouse` selects the DuckDB file.

The warehouse file is selected in this order:

1. `--warehouse`, when the command passes it.
2. `EVE_DATA_GENERATION_DUCKDB_PATH`, when that variable is set to a non-empty value.
3. `<repository>/data/warehouse/<name>`. `<name>` is the configuration `schema` value. When `schema` is absent, `<name>` is `dev_data_003`.

A baseline configuration loads `data/warehouse/dev_data_003`. A scenario configuration with `schema: dev_data_004` loads `data/warehouse/dev_data_004`. `data-generation/.env.example` keeps `EVE_DATA_GENERATION_DUCKDB_PATH=` as an empty placeholder and contains no credentials. This package does not load a dotenv file. Export the variable in the shell when a different file is required.

Inside the selected file, `load` creates schema `raw_<source_system>` and table `<source_entity>`. Examples are `raw_hubspot.company` and `raw_marketing.campaign_performance`. Both warehouse files use these schema and table names. Columns are the contract fields followed by `source_system`, `delivery_id`, and `ingested_at`. One load replaces every entity table. A second load of the same drop does not append rows. A baseline load leaves `data/warehouse/dev_data_004` untouched. A scenario load leaves `data/warehouse/dev_data_003` untouched.

## Test

From this directory:

```bash
python3 -m pytest tests
```

The component tests generate `config/test.yaml`, check volumes, rates, contract shape, referential integrity, reproducibility, and the date window, and read the loaded rows back from `raw_<source_system>.<source_entity>`.

## Output layout

`output/` is gitignored. `data/generated/` and `data/warehouse/` are created by the commands and are not committed.

```text
data-generation/output/<dataset>/<source_system>/<source_entity>.jsonl
data-generation/output/<dataset>/<source_system>/manifest.json
data/generated/<source_system>/<source_entity>.jsonl
data/warehouse/dev_data_003
data/warehouse/dev_data_004
```

## Configuration

Business volumes, rates, date bounds, and catalogs live in the YAML file. The package reads them from that file.

Count keys are exact distinct-entity targets:

| Key | Parent |
|---|---|
| `account_count` | Distinct HubSpot companies. |
| `contacts_per_account` | Distinct contacts on each company. Contact count is `account_count` times this value. |
| `lead_count` | Distinct HubSpot leads. |
| `campaign_count` | Distinct campaigns. |
| `activity_count` | Exact total of HubSpot activities. |
| `touch_count` | Exact total of marketing touches. |
| `product_users_per_customer` | Distinct product users on each Product firm. |
| `usage_events_per_user` | Usage rows for each product user. |

Rate keys are seeded shares of a parent population. `share_count` multiplies the population by the rate and rounds half up. A rate of 0 selects none. A rate of 1 selects all. A rate strictly between 0 and 1, on a population larger than 1, selects at least one parent and leaves at least one out. `stage_mix`, `lead_status_mix`, and `channel_mix` are relative weights allocated by largest remainder. `stage_mix` `closed_won` divided by the total weight must equal `opportunity_win_rate`. A file that disagrees is rejected.

| Key | Parent the rate applies to |
|---|---|
| `opportunity_win_rate` | New-business deals. The latest stage is `closed_won` for this share. It must match `stage_mix`. |
| `stage_mix` | Latest stage of each new-business deal. |
| `lead_status_mix` | Latest status of each lead. |
| `renewal_rate` | Subscriptions that receive `subscription_renewed` while status stays `active`. |
| `expansion_rate` | Subscriptions that receive `subscription_expanded` while status stays `active`. |
| `churn_rate` | Subscriptions that end `churned` with `subscription_churned`. |
| `channel_mix` | Channel of each campaign. |
| `outcome_rate` | Usage rows cited by one outcome. |
| `domain_match_rate` | Product firms whose `primary_domain` copies the linked HubSpot company. |
| `null_company_domain_rate` | Companies whose `primary_domain` is null. |
| `duplicate_contact_email_rate` | Contacts that share `email_normalized` with another contact. |
| `orphan_lead_rate` | Leads with a null company and a null contact. An orphan is not `converted`. |
| `null_deal_amount_rate` | Deals whose `amount` is null. |
| `single_parent_activity_rate` | Activities, out of `activity_count`, with exactly one parent. |
| `null_performance_measure_rate` | Campaign-day performance rows whose `spend_amount` is null. |
| `clicks_exceed_impressions_rate` | Campaign-day performance rows whose `click_count` exceeds `impression_count`. |
| `null_user_email_rate` | Product users whose email is null. |
| `company_change_rate` | Companies that receive a second observation at a later `observed_at`. |

`lifecycle_stage_catalog` is the open list of `hubspot_lifecycle_stage` values. It includes at least one value other than `prospect`, `customer`, and `former_customer`. The remaining catalogs are `owner_names`, `practice_focuses`, `plan_codes`, `workflows`, `states`, firm and person names, `activity_subjects`, `opportunity_name_template`, and `forecast_by_stage`.

`amount_ranges` and `integer_ranges` bound the drawn amounts and integers. Amount fields are drawn independently, so HubSpot `amount`, `quoted_amount`, `total_contract_value`, `booking_amount`, `recurring_amount`, and `spend_amount` are not copies of one another. `term_days` is the contract term used when a renewal extends `end_date`.

Quote, contract, subscription, and booking counts follow wins, expansions, renewals, and churn. They are not separate volume targets.

## Identifiers

HubSpot identifiers are numeric strings beginning at `10000001`. DealHub identifiers use `qte_`, `ctr_`, `sub_`, and `bkg_`. Document numbers use `Q-`, `C-`, `S-`, and `B-`. Marketing identifiers use `cmp_` and `tch_`. Campaign codes use `CMP-`. Product identifiers use `wf_`, `frm_`, `usr_`, `usg_`, and `out_`. `workflow_code` comes from the YAML workflow catalog. Document numbers stay stable across observations of one source identifier and are unique across identifiers of that entity.

## Population extension

`build_dataset(config, population=None)` builds the dataset. The default population is the baseline sampler in `eve_data_generation.population`. Pass a callable `population(world)` to replace that sampler. The callable may use the HubSpot, DealHub, Marketing, and Product generators on `world`. An empty population still validates: every contract key is present and may be an empty list. When the loaded configuration contains `journeys`, and the caller does not pass a population, `build_dataset` selects the scenario population below. `config/default.yaml` and `config/test.yaml` have no `journeys` key and keep the baseline sampler.

## GTM lifecycle scenarios

`config/scenarios.yaml` is the development journey dataset. Its seed is `1004` and its window is 2024-01-01 through 2025-07-01. `config/scenarios-test.yaml` is the dataset the scenario component tests generate and load. Its seed is `4004`. Its window is longer than 180 days and shorter than the development window, so a renewal can add `term_days` to `term_end` and `end_date` and still land inside the window. Both files set every journey count to 1. `term_days` is 180.

Generate and load use the same commands as the baseline sampler:

```bash
python3 -m eve_data_generation generate --config config/scenarios.yaml
python3 -m eve_data_generation generate --config config/scenarios-test.yaml
python3 -m eve_data_generation load --config config/scenarios-test.yaml
```

From this directory, the component tests are:

```bash
python3 -m pytest tests
```

`schema: dev_data_004` selects the warehouse file `data/warehouse/dev_data_004`. The raw schema names match the baseline file. A scenario load replaces table contents on reload and does not modify `data/warehouse/dev_data_003`. Baseline loads use `data/warehouse/dev_data_003`. Generated files under `output/` are not committed.

### Journeys

Each count is a positive integer. Each instance has its own HubSpot company, non-null `primary_domain`, contacts, leads, and deals. Customer journeys do not share a subscription or a contract. A customer journey is one whose company has a new-business win: `new_business_conversion`, `expansion`, `renewal`, `churn`, and `low_adoption`. `lost_opportunity` and `stage_regression` are not customer journeys.

| Journey | What it emits |
|---|---|
| `new_business_conversion` | Converting lead, won new-business deal, accepted quote history, contract, pending-then-active subscription, new-business booking, call, email, meeting, and product usage with outcomes. Two contacts share one email. |
| `expansion` | Its own new-business win, then a won expansion deal, `subscription_expanded`, a higher `total_contract_value` on the same contract, and an expansion booking. |
| `renewal` | Its own new-business win, then a won renewal deal, `subscription_renewed`, a later `end_date` on the same contract, and a renewal booking. |
| `churn` | Its own new-business win, falling `work_unit_count`, `subscription_churned`, a terminated contract, `former_customer`, and an inactive product user. No booking at or after churn. |
| `lost_opportunity` | Converting lead and a lost deal. The quote ends `rejected`. No contract, subscription, booking, or product firm. |
| `stage_regression` | Converting lead and an open deal that moves `proposal` back to `evaluation`. The quote ends `expired`. No contract, subscription, booking, or product firm. |
| `low_adoption` | Its own new-business win and one `case_analysis` usage with no outcome. |

The domain twin is an extra company, not an eighth journey. It copies the `new_business_conversion` domain, uses a different `hubspot_company_id`, has no won deal, and has one lead that ends `disqualified`.

Journey counts and the sequences in this file decide companies, contacts, leads, deals, quotes, contracts, subscriptions, bookings, activities, touches, firms, users, usage, and outcomes. The retained count and rate keys still have to pass the baseline vocabulary and window checks. The scenario population does not use `account_count`, `contacts_per_account`, `lead_count`, `campaign_count`, `activity_count`, `touch_count`, `product_users_per_customer`, `usage_events_per_user`, or the rate keys to decide journey size or journey outcomes.

### Scenario keys

| Key | Committed value | Behavior |
|---|---|---|
| `journeys` | 1 for each of the seven names | Selects this population. |
| `schema` | `dev_data_004` | Warehouse file name. Selects `data/warehouse/dev_data_004`. Absent on baseline files, which use `data/warehouse/dev_data_003`. |
| `ingest_lag_days` | 1 | Days added to `ingested_at` on a late immutable row. |
| `late_event_count` | 1 | How many immutable rows arrive late. |
| `expansion_seat_increase` | 1 | Seats added on `subscription_expanded`. |
| `expansion_recurring_increase` | `10.00` | Added to `recurring_amount` on expansion. |
| `contract_value_increase` | `100.00` | Added to `total_contract_value` on the expansion amendment. |

Amount ranges, integer ranges, `term_days`, and catalogs are read from the same file. The scenario does not encode real prices, win rates, or customer economics. Deal `amount`, `quoted_amount`, `total_contract_value`, `booking_amount`, and `recurring_amount` are drawn separately. `expected_close_date` and contract `start_date` are chosen independently. `seat_count` is not the number of product users.

`ingested_at` defaults to the business timestamp. `late_event_count` immutable rows set it exactly `ingest_lag_days` later. That later timestamp stays inside the window and does not move `created_at`, `observed_at`, `occurred_at`, or `booked_at`.

### Business assumptions

- A canceled subscription is `status` `churned` and `emitted_event` `subscription_churned`. The subscription vocabulary has no `canceled` value. The related contract ends `terminated`. Churn does not create a booking.
- A soft-deleted record remains in the extract. Product-user removal is a later `inactive` observation. A lead that will not proceed ends `disqualified`. A quote that will not be signed ends `expired` or `rejected`. The contracts have no delete flag, and observation history is kept.
- A merged account is two HubSpot companies with the same `primary_domain` and different source identifiers. The source row does not name a survivor. One Product firm uses that domain.
- A workflow start is a product usage row. Processing volume is `work_unit_count`. A completion is an outcome of `draft_completed` or `exported`. A human review is an outcome of `review_accepted`. A run that does not complete is a usage row with no outcome. The usage contract has no failure status.
- Customer health is not a generated score. A healthy journey is the new-business company with an active subscription, an active product user, sales activities, and an outcome. A declining journey is the churn company: falling `work_unit_count`, then `subscription_churned`, a terminated contract, `former_customer`, and an `inactive` user. Low adoption is a won company with usage and no outcome.
- `hubspot_lifecycle_stage` values `prospect`, `customer`, and `former_customer` are unconstrained source labels. They are not canonical `commercial_status`.
- Bookings and subscription fees answer different questions. Bookings are immutable booking rows. Subscription fees are `recurring_amount` and `billing_frequency`. This task does not annualize those fees.
- The domain twin and the duplicate contacts are intentional source duplicates. Identity resolution remains downstream.

