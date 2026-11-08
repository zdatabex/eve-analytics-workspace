---
name: data-modeling
description: Defines canonical data models, entities, relationships, grains, and source schemas. Use when designing or modifying data structures and data contracts.
---

# Data Modeling

## Responsibilities

- Define canonical entities and their relationships.
- Establish model grain and business keys.
- Define source schemas and mappings to canonical entities.
- Identify source system ownership and authoritative attributes.
- Document assumptions and business rules.

## Principles

- Establish explicit and consistent model grain.
- Prefer stable business identifiers where available.
- Separate source-specific structures from canonical models.
- Avoid unnecessary duplication of business entities.
- Preserve source lineage and traceability.
- Consider historical changes and lifecycle events.
- Use shared contracts for interfaces between components.

## Deliverables

- Entity and relationship definitions.
- Canonical data model documentation.
- Source-to-canonical mappings.
- Schema definitions and data contracts.

## Validation

- Validate primary and foreign key relationships.
- Check uniqueness and referential integrity.
- Verify model grain.
- Identify ambiguous or conflicting source attributes.
