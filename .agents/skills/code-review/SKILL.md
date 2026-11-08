---
name: code-review
description: Reviews implementation quality, architecture, data correctness, testing, security, and compliance with task requirements.
---

# Code Review

## Responsibilities

- Review changes against task specifications.
- Validate implementation against acceptance criteria.
- Identify correctness and maintainability issues.
- Assess component boundaries and downstream impact.
- Evaluate test coverage and documentation.

## Review Areas

### Requirements
- Does the implementation satisfy the specification?
- Are all acceptance criteria addressed?
- Are constraints and approval requirements respected?

### Architecture
- Are component ownership boundaries respected?
- Are shared contracts used appropriately?
- Are dependencies and downstream impacts understood?
- Is unnecessary coupling introduced?

### Data Correctness
- Is model grain preserved?
- Are keys and relationships correct?
- Are transformations and business rules accurate?
- Are data quality expectations tested?

### Engineering Quality
- Is the implementation maintainable and reusable?
- Is error handling appropriate?
- Are performance implications considered?
- Are security and sensitive data handled appropriately?

### Testing
- Are relevant tests included?
- Are edge cases addressed?
- Have appropriate validation steps been executed?

## Review Output

Report findings with:

- Severity
- Affected file and location
- Description of the issue
- Potential impact
- Recommended resolution

Distinguish blocking issues from suggestions.

Do not silently modify the implementation being reviewed.
