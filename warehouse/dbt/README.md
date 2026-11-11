# Eve Analytics dbt

This DuckDB project declares the raw source interface and shared warehouse
utilities. It does not transform source entities or define business metrics.

## Setup

The baseline warehouse is `data/warehouse/dev_data_003`. The scenario warehouse
is `data/warehouse/dev_data_004`. Generate and load either file with the
commands documented in `data-generation/README.md`; generated DuckDB files are
local artifacts and must not be committed.

From `warehouse/dbt/`, dbt defaults to the baseline file and an isolated schema
named `dev_data_007_001`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export EVE_DBT_SCHEMA=dev_data_007_001
.venv/bin/dbt debug --profiles-dir .
```

Set `EVE_DBT_DUCKDB_PATH` to select another warehouse file. Paths are resolved
from the directory where dbt runs.

```bash
export EVE_DBT_DUCKDB_PATH=../../data/warehouse/dev_data_004
```

The raw schemas are `raw_hubspot`, `raw_dealhub`, `raw_marketing`, and
`raw_product`. The four files under `models/sources/` declare only the tables
landed by DATA-006 and do not add freshness guarantees.

## Validate

Run the foundation checks from `warehouse/dbt/`:

```bash
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt compile --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select date_spine
.venv/bin/dbt test --profiles-dir . --select path:tests
.venv/bin/dbt show --profiles-dir . --select date_spine --limit 5
```

These commands use the selected DuckDB file and isolated target schema. The
date spine build and its key tests are the only model build required for this
foundation.

## Shared utilities

`date_spine` has one row per calendar date from 2024-01-01 through 2025-07-01,
inclusive. `date_day` is its unique, non-null key. Override the range only for a
specific run:

```bash
.venv/bin/dbt build --profiles-dir . --select date_spine \
  --vars '{date_spine_start_date: 2024-01-01, date_spine_end_date: 2025-07-01}'
```

`generate_surrogate_key(fields)` returns a deterministic, null-safe MD5 key.
The ordered SQL expressions are length-prefixed, so null, empty strings, and
field boundaries remain distinct.

```sql
{{ generate_surrogate_key(['source_system', 'source_identifier']) }}
```

`effective_date(relation, entity_key, observed_at, tracked_columns)` returns all
input columns plus `effective_start`, `effective_end`, and `is_current`.
Consecutive unchanged observations are collapsed. `effective_start` is
inclusive, `effective_end` is exclusive, and the one current row for each
surviving input entity has a null `effective_end`.

```sql
{{ effective_date(
    ref('stg_account_observations'),
    ['account_id'],
    'observed_at',
    ['commercial_status', 'owner_name', 'segment']
) }}
```

## Model ownership

Later warehouse issues add models only in an issue-owned child directory under
`models/staging/`, `models/intermediate/`, or `models/marts/`. They do not edit
`dbt_project.yml` or the four source YAML files. A future shared-project or raw
source change requires a separately scoped task.
