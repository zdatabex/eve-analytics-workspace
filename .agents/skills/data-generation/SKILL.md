---
name: data-generation
description: Guidelines for generating synthetic data, source records, business scenarios, and lifecycle events. Use when implementing or modifying data generators.
---

# Data Generation

## Responsibilities

- Generate realistic synthetic source data.
- Represent business entities and their relationships.
- Simulate source system behavior and lifecycle events.
- Support reproducible development and testing scenarios.
- Generate data that exercises transformation and quality rules.

## Principles

- Generate data consistent with source schemas and contracts.
- Preserve referential integrity across related records.
- Support deterministic generation through configurable seeds.
- Make data volume and distribution configurable.
- Represent realistic business scenarios and edge cases.
- Support incremental generation and updates where required.
- Avoid embedding business transformation logic in generators.

## Deliverables

- Reusable data generators.
- Configurable generation parameters.
- Representative datasets and scenarios.
- Generator documentation.

## Validation

- Validate generated records against source schemas.
- Check referential integrity.
- Verify expected record volumes and distributions.
- Confirm reproducibility.
- Test edge cases and lifecycle scenarios.
