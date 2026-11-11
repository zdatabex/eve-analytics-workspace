---
name: dbt-development
description: Guidelines for developing and maintaining dbt models, transformations, incremental strategies, and tests.
---

# dbt Development

## Responsibilities

- Implement staging, intermediate, and mart models.
- Maintain transformation logic and dependencies.
- Implement incremental processing where appropriate.
- Document models and enforce data quality.
- Maintain consistent dimensional modeling conventions.

## Principles

- Follow the established project model structure.
- Prefer reusable and maintainable transformations.
- Preserve explicit model grain and keys.
- Keep business logic in the warehouse transformation layer.
- Avoid duplicate models and redundant transformations.
- Use appropriate incremental strategies.
- Optimize for performance and maintainability.
- Keep analytics consumers dependent on governed models.

## Staging

A specification may name grains, columns, and business rules. It adopts this structure instead of choosing another one.

- One directory per source: `models/staging/<source>/`. No ticket directory under it.
- One model file: `stg_<source>__<entity>.sql`.
- One YAML file with that same basename beside the SQL. Do not use a shared `schema.yml` or `_models.yml` for several models. Source declarations stay in `_<source>__sources.yml`.
- SQL uses a `raw_data` CTE that reads `{{ source() }}`, then a `renamed` CTE, then `select * from renamed`.
- Column order in `renamed`: primary key, foreign keys, strings, numerics, bools, dates and timestamps, then `source_system`, `delivery_id`, `ingested_at`.
- Tests go in that model's YAML: `unique`, `not_null`, `accepted_values`, and `relationships`.
- A singular test is only for a rule those generic tests cannot express. A pass-through model does not get a singular test that compares every column to the source.

## Documentation

- For staging, follow the Staging section. Other models keep their YAML beside the SQL.
- Document model purpose, grain, and important columns.
- Define primary key and relationship tests.
- Document materialization and incremental behavior.

## Validation

- Run relevant dbt tests.
- Validate model dependencies.
- Check generated SQL and query performance.
- Verify incremental behavior and historical correctness.
