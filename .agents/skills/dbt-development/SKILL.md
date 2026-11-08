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

## Documentation

- Maintain schema.yml alongside relevant models.
- Document model purpose, grain, and important columns.
- Define primary key and relationship tests.
- Document materialization and incremental behavior.

## Validation

- Run relevant dbt tests.
- Validate model dependencies.
- Check generated SQL and query performance.
- Verify incremental behavior and historical correctness.
