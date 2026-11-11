# Local Development

Git, Bash, and Python 3.11 or newer. No Docker and no credentials.

## Data

From `data-generation/`, the config file chooses the dataset. `config/default.yaml` loads `dev_data_003`. For the scenario dataset, use `config/scenarios.yaml` and `../data/warehouse/dev_data_004` ([details](../../data-generation/README.md)).

```bash
python3 -m pip install -e ".[dev]"
```

```bash
python3 -m eve_data_generation generate --config config/default.yaml --output ../data/generated
python3 -m eve_data_generation load --config config/default.yaml --dataset-dir ../data/generated --warehouse ../data/warehouse/dev_data_003
```

## dbt

From `warehouse/dbt/`, this uses `dev_data_003`; set `EVE_DBT_DUCKDB_PATH` for `dev_data_004` ([details](../../warehouse/dbt/README.md)).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/dbt deps
.venv/bin/dbt debug --profiles-dir .
.venv/bin/dbt parse --profiles-dir .
.venv/bin/dbt build --profiles-dir . --select date_spine
```

## Tests

Run the component tests, then the integration suite.

```bash
# from data-generation/
python3 -m pytest tests
```

```bash
# from the repository root
python3 -m pytest tests/integration/generated_data
```

## Not on a laptop

- Hex has no laptop runtime.
- Omni has no laptop runtime.
- Orchestration has no laptop runtime.
- Infrastructure has no laptop runtime.
- `tests/e2e/` has no laptop runtime.

The dispatcher and worktrees are in [agent-workflow.md](agent-workflow.md) and the [root README](../../README.md).
