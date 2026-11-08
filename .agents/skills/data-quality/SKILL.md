---
name: data-quality
description: Guidelines for data validation, integrity, reconciliation, and automated quality testing across platform components.
---

# Data Quality

## Responsibilities

- Define and validate data quality expectations.
- Detect missing, duplicate, invalid, and inconsistent records.
- Validate relationships and referential integrity.
- Reconcile source and transformed data.
- Implement automated quality checks.

## Quality Dimensions

- Completeness
- Uniqueness
- Validity
- Consistency
- Referential integrity
- Timeliness
- Accuracy

## Principles

- Define explicit and measurable expectations.
- Validate data at appropriate component boundaries.
- Test business rules, not just technical constraints.
- Make failures observable and actionable.
- Distinguish expected exceptions from actual defects.
- Avoid silently discarding invalid records.
- Preserve traceability to source records.

## Validation

- Test required fields and accepted values.
- Check uniqueness and relationship constraints.
- Reconcile source and destination record counts.
- Validate aggregation and transformation results.
- Test late-arriving and updated records.
- Document known limitations and exceptions.
