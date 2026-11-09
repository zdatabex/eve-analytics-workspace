# data-generation

Reproducible synthetic source data for the HubSpot, DealHub, Marketing, and Product contracts. One run writes JSON Lines and loads them into the isolated DuckDB schema `dev_data_003`.

The Python dependency for the warehouse is `duckdb`. The loader creates the schema and one table per source entity. It does not provision a remote warehouse.

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

`--output` overrides the dataset directory. The default directory is `output/<config stem>/`, so `config/test.yaml` writes `output/test/` and `config/default.yaml` writes `output/default/`.

`config/default.yaml` is the development dataset. Its window is 2024-01-01 through 2025-07-01, eighteen months, with seed `1003`. `config/test.yaml` is the shorter dataset the component tests generate and load.

Each source entity is one JSON Lines file named `<source_system>_<source_entity>.jsonl`. Decimal amounts are strings with two fraction digits. Integers are JSON integers. Dates and timestamps are strings. Timestamps use a `Z` suffix. Nulls are JSON null. Object keys are sorted. Rows are ordered by `observation_key`. A non-empty file ends with a newline. An entity with no rows is an empty file.

`manifest.json` records `configuration_file`, `delivery_id`, `end_date`, `entities`, `seed`, and `start_date`. `delivery_id` is `dlv_<seed>`. The manifest has no wall-clock timestamp. The configured seed is the only source of randomness. The same seed, configuration, and generator version produce the same file bytes.

If the inclusive date window cannot hold the ordered timestamps, generation fails with `date range cannot hold the ordered timestamps`.

## Load

```bash
python3 -m eve_data_generation load --config config/test.yaml
```

`--dataset-dir` selects the JSON Lines directory. It defaults to the same `output/<config stem>/` path as generate. `--warehouse` selects the DuckDB file.

The loader reads `EVE_DATA_GENERATION_DUCKDB_PATH`. When that variable is unset or empty, the target is `output/warehouse/dev_data_003`. `data-generation/.env.example` contains that variable as an empty placeholder and no credentials. This package does not load a dotenv file. Export the variable in the shell when a different file is required.

The schema name is `dev_data_003`. Table names are `src_<source_system>_<source_entity>`, for example `src_hubspot_company` and `src_marketing_campaign_performance`. Columns are the contract fields followed by `source_system`, `delivery_id`, and `ingested_at`. A load replaces each table. A second load of the same dataset does not append rows.

The DuckDB file name can match the schema name. The loader qualifies every table as `<catalog>.dev_data_003.<table>` so those two names stay distinct.

## Test

From this directory:

```bash
python3 -m pytest tests
```

The component tests generate `config/test.yaml`, check volumes, rates, contract shape, referential integrity, reproducibility, and the date window, and read the loaded rows back from `dev_data_003`.

## Output layout

`output/` is gitignored. Generated datasets and the local warehouse file are not committed.

```text
output/
  test/
    hubspot_company.jsonl
    ...
    manifest.json
  default/
  warehouse/
    dev_data_003
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

`build_dataset(config, population=None)` builds the dataset. The default population is the baseline sampler in `eve_data_generation.population`. Pass a callable `population(world)` to replace that sampler. The callable may use the HubSpot, DealHub, Marketing, and Product generators on `world`. An empty population still validates: every contract key is present and may be an empty list. This package ships the baseline sampler only.
