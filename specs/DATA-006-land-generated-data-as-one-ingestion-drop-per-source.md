---
id: DATA-006
title: Land generated data as one ingestion drop per source
type: implementation
agent: data-engineer
skills:
  - data-generation
  - data-modeling
  - data-quality
priority: medium
components:
  - data-generation
dependencies:
  - DATA-005
requires_approval: true
allowed_paths:
  - data-generation/
  - .gitignore
  - tests/integration/generated_data/
excluded_paths:
  - contracts/
  - warehouse/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - tests/e2e/
  - tests/integration/README.md
  - docs/
  - specs/
contracts:
  changes_required: false
  affected_contracts: []
testing:
  component_tests: true
  integration_tests: true
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

Land each generator run as one ingestion drop per source system, and load those drops into one raw schema per source.

`generate` writes the JSON Lines directories. `load` creates the DuckDB file. `data/generated/` and `data/warehouse/` stay absent until those commands create them.

## Business context

GitHub issue #18 (`DATA-006 — Land generated data as one ingestion drop per source`) depends on DATA-005. DATA-005 is the validation suite for the synthetic datasets. The baseline sampler and the named journeys are already in `data-generation/`. The physical source schemas are the contract files under `contracts/source/`.

The company is a fictional AI-native B2B SaaS vendor. The customer is a plaintiff law firm. The lifecycle the sources support is Lead → Opportunity → Customer → Adoption → Renewal. This task changes where a finished run is written and how that run is loaded. It does not define pipeline, bookings, ARR, retention, or adoption metrics, and it does not derive `customer_converted` or `adoption_reached`.

Today one generate run writes a flat directory, `data-generation/output/<dataset>/<source_system>_<source_entity>.jsonl`, plus one `manifest.json`. The loader reads that directory into one DuckDB schema, `dev_data_003` or `dev_data_004`, with tables named `src_<source_system>_<source_entity>`. The default warehouse file is `data-generation/output/warehouse/dev_data_003`. The configuration key `schema` selects that DuckDB schema.

This task replaces that landing layout. One generate run still has one `delivery_id`. Each source system gets its own drop directory and its own manifest. `load` places each drop in schema `raw_<source_system>` inside the dataset warehouse file. The configuration key `schema` selects that file.

`contracts/source/` remains normative for field names, types, nullability, keys, relationships, timestamps, status values, lifecycle signals, and ingestion metadata. Where this specification summarizes a contract rule, the merged YAML file wins.

## Scope

The implementation changes the writer, the loader, their paths, the component tests, the generator usage documentation, and the generated-data validation suite. It covers:

1. `generate` writes `<output>/<source_system>/<source_entity>.jsonl` and one `manifest.json` per source. Sources stay `hubspot`, `dealhub`, `marketing`, and `product`. `generate` creates those directories. It writes no DuckDB file.
2. Each manifest shares `delivery_id`, seed, and the date window, and lists that source's row counts.
3. `--output ../data/generated`, run from `data-generation/`, fills `data/generated/<source>/`. The default run uses `data-generation/output/<dataset>/<source>/`.
4. `load` reads that drop and creates the DuckDB file. The baseline file is `data/warehouse/dev_data_003`. The scenario file is `data/warehouse/dev_data_004`. `load` creates `data/warehouse/` when that path is selected.
5. Inside each file, `load` creates schema `raw_<source_system>` and table `<source_entity>`, for example `raw_hubspot.company`. A load replaces that source's tables.
6. The configuration `schema` value selects the warehouse file. DuckDB schema names are `raw_<source_system>` in both files.
7. `data-generation` tests and `data-generation/README.md` describe `generate` and `load` as those two steps.
8. `tests/integration/generated_data/` asserts that same layout. `python3 -m pytest tests/integration/generated_data` passes. The suite README names `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`. A passing run rewrites `DATA-005-report.md`, and the committed file matches that rewrite.

`components` lists `data-generation` only. `tests/` is not a component in `workspace.yaml`. `testing.integration_tests` is true because this change alters the landing contract the existing suite asserts. The rule that more than one component requires integration tests still holds. It does not forbid the flag for a single component. The root `.gitignore` change that keeps `data/warehouse/` untracked is repository hygiene for this component's output. It is not a second component.

The baseline sampler and the named journeys stay. `generate` owns the JSON Lines layout. `load` owns the DuckDB schemas.

Later issues own the work in the table below.

| Issue | Owns |
|---|---|
| DATA-001 | Canonical model. Merged. This task consumes it and does not change it. |
| DATA-002 | Source contracts. Merged. This task reads `contracts/source/` and does not change it. |
| DATA-003 | Baseline generators, `config/default.yaml`, `config/test.yaml`, and the sampler. Merged. This task keeps that sampler and changes the writer and loader. |
| DATA-004 | Named GTM lifecycle journeys and `config/scenarios.yaml` and `config/scenarios-test.yaml`. Merged. This task keeps those journeys. |
| DATA-005 | The validation suite under `tests/integration/generated_data/`. Merged. This task points that suite at the landing layout below. Population, key, relationship, lifecycle, temporal, commercial, usage, and journey checks stay. |
| DATA-006 | Per-source JSON Lines drops, per-source manifests, raw schemas, the dataset warehouse files, component tests, the generated-data validation suite, and generator usage documentation. |
| Later warehouse work | dbt sources, staging, intermediate models, and marts, owned by `analytics-engineer`. |
| Later analytics work | Hex and Omni assets, owned by `analyst`. |

Orchestration workflows, infrastructure provisioning, and deployment are outside this task.

## Deliverables

The implementation adds and updates files under `data-generation/`, and updates the warehouse rule in the root `.gitignore`.

- The writer and loader, so `generate` and `load` follow the layout in this specification.
- Component tests under `data-generation/tests/` for paths, manifests, raw schemas, and replacement on reload.
- `data-generation/README.md`, documenting `generate` and `load` as the two steps below.
- The comment in `data-generation/.env.example`, so the empty placeholder describes the warehouse file selected by this specification.
- The root `.gitignore` rule that ignores every file under `data/warehouse/`.
- `tests/integration/generated_data/`, pointed at the drop paths, one manifest per source, schemas `raw_<source_system>`, tables `<source_entity>`, and warehouse file selection from `schema`.
- `tests/integration/generated_data/README.md`, naming `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004`.
- `tests/integration/generated_data/DATA-005-report.md`, rewritten by a passing `python3 -m pytest tests/integration/generated_data`.

`data-generation/.gitignore` already ignores `data-generation/output/`. Generated datasets under that directory stay untracked. `config/default.yaml`, `config/test.yaml`, `config/scenarios.yaml`, and `config/scenarios-test.yaml` stay as they are. Scenario files keep `schema: dev_data_004`. Baseline files keep `schema` absent.

## Drops

One `generate` run is one delivery. `delivery_id` remains `dlv_<seed>`. HubSpot, DealHub, Marketing, and Product each receive one drop from that delivery. The four drops share that `delivery_id`. Apollo and Clay stay absent.

The output directory contains only these source directories:

```text
<output>/
  hubspot/
  dealhub/
  marketing/
  product/
```

Each source directory contains one `<source_entity>.jsonl` file for every contract entity of that source, plus `manifest.json`. An entity with no rows is an empty file. A non-empty file ends with a newline. `generate` creates the source directories. The directory contains no DuckDB file and no `warehouse/` directory.

The writer and the loader discover entities from `contracts/source/`. The table is the inventory at specification time. The merged YAML wins where this specification summarizes a contract.

| Source | `source_entity` files | Raw table |
|---|---|---|
| `hubspot` | `company`, `contact`, `lead`, `deal`, `activity` | `raw_hubspot.<source_entity>` |
| `dealhub` | `quote`, `contract`, `subscription`, `booking` | `raw_dealhub.<source_entity>` |
| `marketing` | `campaign`, `campaign_performance`, `touch` | `raw_marketing.<source_entity>` |
| `product` | `firm`, `user`, `ai_workflow`, `usage`, `outcome` | `raw_product.<source_entity>` |

Examples: `hubspot/company.jsonl` loads into `raw_hubspot.company`. `marketing/campaign_performance.jsonl` loads into `raw_marketing.campaign_performance`. `product/ai_workflow.jsonl` loads into `raw_product.ai_workflow`.

### Paths

The default output directory is `data-generation/output/<config stem>/`, resolved from the package location. `config/test.yaml` writes `data-generation/output/test/<source>/`. `config/default.yaml` writes `data-generation/output/default/<source>/`. `config/scenarios.yaml` writes `data-generation/output/scenarios/<source>/`. `config/scenarios-test.yaml` writes `data-generation/output/scenarios-test/<source>/`. The working directory does not move this default.

`--output` is the parent of the four source directories. It does not insert another dataset directory. From `data-generation/`, `--output ../data/generated` writes `data/generated/hubspot/`, `data/generated/dealhub/`, `data/generated/marketing/`, and `data/generated/product/`. A second generate to the same `--output` replaces those files. `generate` removes every other child of the selected output directory, including the retired flat `<source_system>_<source_entity>.jsonl` files and a dataset-level `manifest.json`. After the command, that directory contains only `hubspot/`, `dealhub/`, `marketing/`, and `product/`.

`generate` writes only under the selected output directory. A run whose output is `data/generated` creates `data/generated/`. It leaves `data/warehouse/` absent.

### JSON Lines

Serialization stays the serialization DATA-003 already requires.

- Decimal amounts are JSON strings with two fraction digits.
- Integers are JSON integers.
- Dates and timestamps are JSON strings. Timestamps use a `Z` suffix.
- Nulls are JSON null.
- Object keys are sorted.
- Rows are ordered by the contract `observation_key`.
- Each row's keys are that entity's contract `fields` followed by the ingestion fields `source_system`, `delivery_id`, and `ingested_at`. The row has no other key.
- `source_system` equals the source directory.
- Every row in the run uses the run's `delivery_id`.

### Manifests

Each source directory has one `manifest.json`. The four files share `configuration_file`, `delivery_id`, `seed`, `start_date`, and `end_date`. `delivery_id` is `dlv_<seed>` and equals `delivery_id` on every row. `start_date` and `end_date` are the inclusive configured window, written as ISO-8601 dates. The manifest has no wall-clock timestamp and no time component on those dates.

The keys are exactly:

| Key | Value |
|---|---|
| `configuration_file` | The configuration file name. |
| `delivery_id` | `dlv_<seed>`. |
| `seed` | The configured seed. |
| `start_date` | The configured window start. |
| `end_date` | The configured window end. |
| `entities` | That source's row counts, keyed by `source_entity`. |

`entities` lists every `source_entity` of that source and no entity from another source. The count is the number of JSON Lines rows in `<source_entity>.jsonl`, and it is `0` when the file is empty. Manifest keys are sorted. The file ends with a newline. The same seed, the same configuration, and the same generator version produce the same bytes for every JSON Lines file and every manifest.

## Warehouse load

`load` reads the dataset directory `generate` wrote. `--dataset-dir` selects that directory and defaults to the same path as `generate` for the configuration file. The directory's children are `hubspot/`, `dealhub/`, `marketing/`, and `product/`. `load` reads `<source_system>/<source_entity>.jsonl`. A missing entity file fails the load.

`load` creates the DuckDB file and the parent directory of that file. The engine remains DuckDB. This task adds no Python dependency.

The warehouse file is selected in this order:

1. `--warehouse`, when the command passes it.
2. `EVE_DATA_GENERATION_DUCKDB_PATH`, when that variable is set to a non-empty value.
3. `<repository>/data/warehouse/<name>`. `<name>` is the configuration `schema` value. When `schema` is absent, `<name>` is `dev_data_003`.

The repository path does not depend on the working directory. `data-generation/.env.example` keeps `EVE_DATA_GENERATION_DUCKDB_PATH=` as an empty placeholder and contains no credentials. The package does not load a dotenv file. The comment in that example names the default files below.

| Configuration | `schema` key | Default warehouse file |
|---|---|---|
| `config/default.yaml` | absent | `data/warehouse/dev_data_003` |
| `config/test.yaml` | absent | `data/warehouse/dev_data_003` |
| `config/scenarios.yaml` | `dev_data_004` | `data/warehouse/dev_data_004` |
| `config/scenarios-test.yaml` | `dev_data_004` | `data/warehouse/dev_data_004` |

`schema` remains a lowercase identifier. The configuration parser still accepts the committed files. The value is the warehouse file name. It is not a DuckDB schema. A baseline load that uses the default file creates `data/warehouse/dev_data_003` and leaves `data/warehouse/dev_data_004` untouched. A scenario load that uses the default file creates `data/warehouse/dev_data_004` and leaves `data/warehouse/dev_data_003` untouched. The retired default `data-generation/output/warehouse/dev_data_003` is no longer the target.

Inside the selected file, `load` creates these schemas and one table per contract entity:

| Schema | Tables |
|---|---|
| `raw_hubspot` | `company`, `contact`, `lead`, `deal`, `activity` |
| `raw_dealhub` | `quote`, `contract`, `subscription`, `booking` |
| `raw_marketing` | `campaign`, `campaign_performance`, `touch` |
| `raw_product` | `firm`, `user`, `ai_workflow`, `usage`, `outcome` |

Both warehouse files use these schema and table names. Neither file contains a schema named `dev_data_003` or `dev_data_004`. Neither file contains a table named `src_<source_system>_<source_entity>`.

Columns are the contract `fields` followed by `source_system`, `delivery_id`, and `ingested_at`. Warehouse types stay text for `string` and `enum`, `DECIMAL(18,2)` for `decimal`, `BIGINT` for `integer`, `DATE` for `date`, and `TIMESTAMP` for `timestamp`. Required columns reject nulls. Optional columns keep nulls. A decimal loaded from JSON equals that decimal at two fraction digits.

One `load` command loads every source directory and replaces every entity table in those raw schemas. After the load, each table's row count equals that entity's JSON Lines count. A second load of the same drop leaves those counts unchanged. A load that follows a deletion of rows from `raw_hubspot.company` restores that table to the drop. The previous default of one shared schema named `dev_data_003` or `dev_data_004` is the layout this task retires.

`load` creates `data/warehouse/` only when the selected file is under that directory. It does not create `data/generated/`.

## Records that stay

The baseline sampler, the scenario population, seeds, windows, journey counts, volumes, rates, and catalogs stay. `build_dataset` still calls `baseline_population` when `journeys` is absent and the scenario population when `journeys` is present. The commands stay:

```bash
python3 -m eve_data_generation generate --config <file>
python3 -m eve_data_generation load --config <file>
```

`config/default.yaml` and `config/test.yaml` still generate the baseline population. `config/scenarios.yaml` and `config/scenarios-test.yaml` still generate the named journeys. Contract fields on each row stay the merged contract fields plus the ingestion envelope. Canonical surrogate keys, `surviving_*` links, effective-dating columns, `commercial_status`, `customer_converted`, `adoption_reached`, and metric fields stay absent.

The same seed, configuration, and generator version still produce the same source identifiers, relationships, business attributes, ingestion values, and row order. The seed remains the only source of randomness. The generator does not read the wall clock.

## Documentation

`data-generation/README.md` documents `generate` and `load` as two steps, in that order.

The generate step documents the default directory, `--output ../data/generated`, the four source directories, the `<source_entity>.jsonl` names, the manifest fields, and that this step writes no DuckDB file.

The load step documents `--dataset-dir`, `--warehouse`, `EVE_DATA_GENERATION_DUCKDB_PATH`, the file-selection order, `data/warehouse/dev_data_003`, `data/warehouse/dev_data_004`, schemas `raw_<source_system>`, tables `<source_entity>`, and replacement on reload. The scenario section states that `schema: dev_data_004` selects `data/warehouse/dev_data_004` and that the raw schema names match the baseline file.

The output-layout section shows:

```text
data-generation/output/<dataset>/<source_system>/<source_entity>.jsonl
data-generation/output/<dataset>/<source_system>/manifest.json
data/generated/<source_system>/<source_entity>.jsonl
data/warehouse/dev_data_003
data/warehouse/dev_data_004
```

The README states that `data/generated/` and `data/warehouse/` are created by the commands and are not committed. Journey names, journey behavior, and the business assumptions already in the README stay. Sentences that call `dev_data_003` or `dev_data_004` a DuckDB schema, that name tables `src_<source_system>_<source_entity>`, or that place one `manifest.json` on the dataset directory, are updated to this layout.

## Tests

Component tests run from `data-generation`:

```bash
python3 -m pytest tests
```

The tests cover:

- Default paths `data-generation/output/<config stem>/<source_system>/<source_entity>.jsonl` and one manifest in each source directory.
- `--output` aimed at `data/generated`, or at a temporary directory standing in for it, writes `<output>/<source_system>/` and does not insert a dataset stem.
- The four manifests share `configuration_file`, `delivery_id`, `seed`, `start_date`, and `end_date`. Each `entities` map lists only that source's `source_entity` values, and the counts match the files.
- `generate` writes no DuckDB file and does not create `data/warehouse/`.
- A baseline load's default file is `<repository>/data/warehouse/dev_data_003`. A scenario load's default file is `<repository>/data/warehouse/dev_data_004`.
- The loaded file has `raw_hubspot.company` and the other raw tables in this specification, preserves nulls and exact decimals, and has no schema named `dev_data_003` or `dev_data_004`.
- A second load of the same drop replaces table contents. The row count stays equal to the JSON Lines count.
- A scenario load that uses its own warehouse file leaves the baseline warehouse file unchanged, and both files use the same raw schema names.
- Reproducibility of the source directories and manifests, plus the existing population, contract, and journey checks.

Tests that open DuckDB pass `--warehouse` or `EVE_DATA_GENERATION_DUCKDB_PATH` with a temporary file, except a test that resolves the default path and creates it. A test that creates `data/generated/` or `data/warehouse/` deletes that directory before it finishes. After `python3 -m pytest tests`, the worktree contains neither directory.

`data-generation/output/` stays ignored. The root `.gitignore` ignores `data/generated/` and `data/warehouse/`. The test that reads ignore rules asserts both.

## Validation suite

`tests/integration/generated_data/` is in this task. The suite still generates the four committed configurations through the existing generate and load commands, checks the published population and contract rules, and writes `DATA-005-report.md`. It still passes `--output`, `--dataset-dir`, and `--warehouse` under a temporary directory. It still parses `contracts/source/` itself and does not call `eve_data_generation.validate`. It adds no Python dependency. Population, key, relationship, lifecycle, temporal, commercial, usage, and journey checks stay. `ASSUMPTIONS.md` stays. `tests/integration/README.md` stays. In-memory population-rule fixtures keep their row checks. They do not require a DuckDB schema named `dev_data_003` or `dev_data_004`.

The landing assertions follow this specification:

- The output directory's children are `hubspot/`, `dealhub/`, `marketing/`, and `product/`. Each source directory holds `<source_entity>.jsonl` and `manifest.json`. Flat `<source_system>_<source_entity>.jsonl` files and a dataset-level `manifest.json` are absent. Apollo and Clay files stay absent.
- Each source manifest has the keys in the Manifests section. The four manifests share `configuration_file`, `delivery_id`, `seed`, `start_date`, and `end_date`. `entities` is keyed by that source's `source_entity`, and the counts match that source's files. The suite resolves a contract file as `<source_system>/<source_entity>.jsonl`. `model.py` `file_name` follows that path.
- Two generations of the same configuration produce the same bytes for every JSON Lines file and every source manifest, including files nested under the source directories.
- The load writes schema `raw_<source_system>` and table `<source_entity>`. `model.py` `table_name` is `<source_entity>`. Columns and values still match the JSON Lines, including nulls and exact decimals. The temporary file has no schema named `dev_data_003` or `dev_data_004` and no table named `src_<source_system>_<source_entity>`. It does not create `dev_data_005`.
- The configuration `schema` value selects the warehouse file: `dev_data_003` when `schema` is absent, and `dev_data_004` when `schema` is `dev_data_004`. The suite still passes `--warehouse`, so the pytest run loads a temporary file. A baseline file still has no `schema` key. A scenario file still has `schema: dev_data_004`. Those checks name the warehouse file. They do not require a DuckDB schema of that name.
- A second load of `test.yaml` into the same temporary file replaces the raw tables.
- The suite does not write `data-generation/output/` or `data/generated/`, and it does not create or replace `data/warehouse/dev_data_003` or `data/warehouse/dev_data_004`. The retired path `data-generation/output/warehouse/dev_data_003` is not the warehouse file the suite watches.

`tests/integration/generated_data/README.md` states that the suite leaves `data/warehouse/dev_data_003` and `data/warehouse/dev_data_004` in place, and that it does not write `data-generation/output/`.

From the repository root, with `data-generation` installed editable and its `dev` extra:

```bash
python3 -m pytest tests/integration/generated_data
```

That command exits zero. It rewrites `tests/integration/generated_data/DATA-005-report.md`. The committed file matches that rewrite. The report has no wall-clock timestamp. Each dataset section records `Warehouse file: dev_data_003` or `Warehouse file: dev_data_004`, the file the configuration `schema` value selects. Entity rows stay labeled by contract id. The counts are the counts the unchanged sampler and journeys produce.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. Read `contracts/source/` and do not edit it. Contract fields stay unchanged.
- One owning agent, `data-engineer`, changes the writer, the loader, the component tests, the README, the env example comment, the root warehouse ignore rule, and `tests/integration/generated_data/`.
- Follow the data-generation skill. Keep source generation free of canonical transformation. Keep the baseline sampler and the named journeys. Keep volumes, rates, and catalogs in the existing YAML files.
- Follow the data-modeling skill for landing grain. One raw schema is one source system. One table is one source entity. The table grain is that entity's contract grain. Source identifiers stay source identifiers.
- Follow the data-quality skill for the component tests. Failures name the path, the manifest field, or the table. A reload check compares counts with the drop. Tests do not drop rows to make a count match.
- The root `.gitignore` change ignores `data/warehouse/` as a directory. `/data/generated/` is already ignored. No other ignore rule changes.
- Do not commit files under `data/generated/` or `data/warehouse/`. Do not add either directory to the repository.
- Update `tests/integration/generated_data/` so its landing checks match this specification. Leave `ASSUMPTIONS.md` and `tests/integration/README.md` unchanged. Do not edit `tests/e2e/`.
- Do not add dbt sources. Do not edit `warehouse/`, `analytics/`, `orchestration/`, `infrastructure/`, `docs/`, `agent-platform/`, or `specs/`. `contracts/` stays unchanged.
- Do not generate Apollo or Clay records.
- Human approval is required. `delivery.deployment_required` is false.
- `environment.isolated_schema` is true. Isolation is the warehouse file. Baseline rows land in `data/warehouse/dev_data_003`. Scenario rows land in `data/warehouse/dev_data_004`. `environment.schema_prefix` stays `dev` because those file names keep that prefix. The schemas inside each file are `raw_<source_system>`.
- `testing.component_tests` is true. `testing.integration_tests` is true because the landing contract the existing suite asserts has changed. `testing.end_to_end_tests` is false. `components` stays `data-generation`.

## Acceptance criteria

- [ ] The implementation changes files only under `data-generation/`, `tests/integration/generated_data/`, and the root `.gitignore` warehouse rule. `config/default.yaml`, `config/test.yaml`, `config/scenarios.yaml`, and `config/scenarios-test.yaml` are unchanged. `ASSUMPTIONS.md` is unchanged.
- [ ] `data/generated/` and `data/warehouse/` are absent until the commands run, and neither directory is committed.
- [ ] `generate` writes `hubspot/`, `dealhub/`, `marketing/`, and `product/`, one `<source_entity>.jsonl` per contract entity, and one `manifest.json` per source. It writes no DuckDB file.
- [ ] The default directory is `data-generation/output/<config stem>/<source_system>/`. `--output ../data/generated` from `data-generation/` fills `data/generated/<source_system>/`.
- [ ] The four manifests share one `delivery_id`, seed, and date window, and each lists only that source's row counts. The manifest has no wall-clock timestamp. Two generations with the same seed and configuration produce identical drop bytes.
- [ ] `load` creates `data/warehouse/dev_data_003` for a baseline configuration and `data/warehouse/dev_data_004` for a scenario configuration. The scenario file uses the same raw schema names and does not modify the baseline file.
- [ ] Each warehouse file contains `raw_hubspot.company` and the other `raw_<source_system>.<source_entity>` tables in this specification. Columns are the contract fields plus the ingestion envelope. Nulls and exact decimals survive the load.
- [ ] A second load of the same drop replaces table contents. The row count equals the JSON Lines count.
- [ ] Contract fields are unchanged. `contracts/` is unchanged. dbt sources are not added.
- [ ] The baseline sampler and the named journeys still run for their existing configuration files. `python3 -m pytest tests` from `data-generation` passes.
- [ ] `data-generation/README.md` documents `generate` and `load` as the two steps, the drop layout, the manifests, the warehouse files, and the raw schema and table names.
- [ ] `python3 -m pytest tests/integration/generated_data` from the repository root exits zero. The suite reads `<source_system>/<source_entity>.jsonl` and one manifest per source, keys each manifest `entities` map by that source's `source_entity`, loads `raw_<source_system>.<source_entity>`, and treats `schema` as the warehouse file name `dev_data_003` or `dev_data_004`.
- [ ] That run rewrites `tests/integration/generated_data/DATA-005-report.md`, and the committed file matches the rewrite. Each dataset section records `Warehouse file: dev_data_003` or `Warehouse file: dev_data_004`. The suite README names those two files as the warehouse files the run leaves in place. The run does not create or replace `data/generated/`, `data/warehouse/dev_data_003`, `data/warehouse/dev_data_004`, or `data-generation/output/`.
- [ ] `tests/e2e/`, `tests/integration/README.md`, `warehouse/`, `analytics/`, `orchestration/`, `infrastructure/`, `docs/`, `contracts/`, and `specs/` are unchanged.

## Execution notes

Implement this specification only after it has merged and the issue label is `status:ready`. Use an `impl` worktree. Leave this specification unchanged unless a human changes the approved requirements.

Read the data-generation skill before changing the writer, the loader, and the output layout. Read the data-modeling skill before treating a raw table as anything other than the source entity. Read the data-quality skill before writing the path, manifest, schema, and reload tests.

Read `specs/DATA-003-implement-synthetic-data-generators.md` and `specs/DATA-004-implement-gtm-lifecycle-scenarios.md` for the sampler, the journeys, the JSON Lines encoding, and the population hook. Read `specs/DATA-005-validate-generated-data.md` for the checks that stay. Read `data-generation/README.md`, `data-generation/src/eve_data_generation/writer.py`, `loader.py`, `cli.py`, and `paths.py` before changing them. Read `tests/integration/generated_data/model.py`, `quality.py`, `validate_generated.py`, `README.md`, and `DATA-005-report.md` before pointing the suite at the new layout. Keep `baseline_population` and the scenario population. Change the writer layout and the loader's file selection and schema names. Update the component tests and the suite checks that expect a flat directory, one manifest at the dataset root, `src_*` tables, a DuckDB schema named `dev_data_003` or `dev_data_004`, or the warehouse path `data-generation/output/warehouse/dev_data_003`.

`generate` owns the JSON Lines layout. `load` owns the DuckDB schemas. The suite asserts that layout. Do not edit `contracts/`. Do not add dbt sources. Do not edit `tests/e2e/` or `tests/integration/README.md`.

Component tests and `python3 -m pytest tests/integration/generated_data` run locally. They do not require a remote warehouse. No end-to-end test or deployment is required for this task.

Validation of this task is `python3 -m pytest tests` from `data-generation` and `python3 -m pytest tests/integration/generated_data` from the repository root, plus a review of the acceptance criteria. Human approval is required before merge.
