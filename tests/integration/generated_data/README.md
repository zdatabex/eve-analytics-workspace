# Generated data validation

This suite validates the four committed synthetic datasets against `contracts/source/` and the generation behavior published for those datasets. It does not change the generator, the contracts, or the canonical model.

## Run

From the repository root, with `data-generation` installed editable and its `dev` extra:

```bash
python3 -m pip install -e "data-generation[dev]"
python3 -m pytest tests/integration/generated_data
```

The suite calls the existing generate and load commands. It passes `--output`, `--dataset-dir`, and `--warehouse`, all under a temporary directory, and deletes those files when the run finishes. It does not write `data-generation/output/` and it does not replace `data-generation/output/warehouse/dev_data_003`.

```bash
python3 -m eve_data_generation generate --config data-generation/config/<file>.yaml --output <temp directory>
python3 -m eve_data_generation load --config data-generation/config/<file>.yaml --dataset-dir <temp directory> --warehouse <temp duckdb file>
```

The four configurations are `data-generation/config/default.yaml`, `test.yaml`, `scenarios.yaml`, and `scenarios-test.yaml`. Each run is checked twice for identical file bytes. A second load of `test.yaml` into the same temporary warehouse must replace the tables.

PyYAML, DuckDB, and pytest are the dependencies already declared by `data-generation`. The suite parses the contract YAML itself. It does not import `eve_data_generation.validate`.

## Oracle

A contract check reads the merged files under `contracts/source/` and `contracts/source/README.md`. Field names, types, nullability, keys, relationships, and allowed values come from those YAML files. Where the DATA-005 specification summarizes a contract rule, the merged YAML wins.

A generation check reads the rules restated in `specs/DATA-005-validate-generated-data.md` from DATA-003, DATA-004, and `data-generation/README.md`. The generator's own validator is not a source of truth. A row the contract allows is valid here even when a stricter generator check would reject it. Identifier shape is the stated case: any non-empty source identifier is accepted.

`ASSUMPTIONS.md` records the assumptions those checks use. `DATA-005-report.md` is the data-quality report. A fresh run rewrites that report and the committed file must match. Neither file contains a wall-clock timestamp.

## Defects and recommendations

A defect is a failed check. The report records the configuration path, seed, generate command, check name, contract file and rule or the generation rule, entity, `observation_key`, field, and actual value. `pytest` exits non-zero when any defect exists. The report is still written. A failing suite does not authorize an edit under `data-generation/`, `contracts/`, or `docs/`.

A recommendation is a contract-legal pattern worth a later generator change. Recommendations do not fail the suite. The recorded cases are a difference between `duplicate_contact_email_rate` or `domain_match_rate` and the observed count, and an identifier whose shape is narrower than the contract. Legal nulls, duplicate emails, duplicate domains, clicks above impressions, an open lifecycle stage, and late ingestion stay in the dataset and are not defects.

The intentional edge cases in the specification are recorded as present. They are not dropped and they are not reported as defects.
