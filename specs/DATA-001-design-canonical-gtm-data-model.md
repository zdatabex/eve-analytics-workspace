---
id: DATA-001
title: Design Canonical GTM Data Model
type: design
agent: data-engineer
skills:
  - data-modeling
  - data-generation
priority: critical
components: []
dependencies: []
requires_approval: true
allowed_paths:
  - docs/data-model/
excluded_paths:
  - contracts/
  - data-generation/
  - data/
  - warehouse/
  - analytics/
  - orchestration/
  - infrastructure/
  - agent-platform/
  - tests/
  - docs/architecture/
  - docs/development/
  - specs/
contracts:
  changes_required: false
  affected_contracts: []
testing:
  component_tests: false
  integration_tests: false
  end_to_end_tests: false
environment:
  isolated_schema: false
  schema_prefix: dev
delivery:
  pull_request_required: true
  human_approval_required: true
  deployment_required: false
---

## Objective

Design the canonical go-to-market data model for a fictional AI-native B2B SaaS company that sells to plaintiff law firms. The model gives Marketing, Sales, Customer Success, and Product Usage one shared set of entities, relationships, identifiers, grains, and lifecycle events.

The work product is design documentation in `docs/data-model/`. Human approval of that design is the gate for DATA-002.

## Business context

GitHub issue #2 (`DATA-001 — Design Canonical GTM Data Model`) is the first child of epic #1 (`DATA-000 — Build GTM Data Foundation`). The epic builds a synthetic GTM foundation for later transformations, metrics, and analytics. This task designs the canonical model that foundation will follow.

The company is fictional. Use the business description in the issue and the parent epic. Record an assumption wherever source behavior or commercial process is unspecified. Keep Eve's real internal systems, fields, and metrics out of the design.

The customer is a plaintiff law firm. People participate as contacts and product users of a firm. The lifecycle the model must represent is:

Lead → Opportunity → Customer → Adoption → Renewal

The model must be sufficient for later analysis of pipeline, bookings, ARR, customer retention, and product adoption. This task documents the entities, events, and grains those analyses need. Metric definitions, semantic models, and dashboards belong to later work.

The parent epic names the source systems this design must reconcile:

| Source | Concepts the mapping must account for |
|---|---|
| HubSpot | Companies, contacts, leads, deals, activities |
| DealHub | Quotes, contracts, subscriptions, bookings |
| Marketing | Campaigns, spend, impressions, attribution |
| Product | Firms, users, AI workflows, usage, outcomes |

Apollo and Clay may arrive later as enrichment sources. Record them in the decisions document as future sources, separate from the current source mapping.

`contracts/` documents component ownership and does not yet define GTM entities. This task leaves that directory unchanged. DATA-002 writes the source schemas and data contracts from the approved model.

Shared architecture places contracts between components, data generation on the source side of those contracts, and dbt and analytics downstream. This design describes the canonical model those later layers will follow. It lives in `docs/data-model/` so the canonical model stays independent of any one source layout and of warehouse model names.

## Scope

The implementation writes the design artifacts listed under Deliverables. It covers:

1. Core business entities for the GTM lifecycle.
2. Relationships and cardinality.
3. Primary keys, business keys, and foreign keys.
4. Grain of each proposed fact and dimension.
5. Source-system ownership of entities and attributes.
6. Source-specific identifiers and canonical identifiers.
7. Identity resolution and deduplication requirements.
8. Historical tracking, including where slowly changing dimension Type 2 is appropriate.
9. Proposed analytical facts and dimensions.
10. Business events required for lifecycle analysis.
11. A logical source schema for synthetic generation: source entities, source identifiers, attributes required for canonical mapping, relationships, and the lifecycle events those sources emit. Physical field types, nullability, and contract files stay with DATA-002.

`components` is empty. The files in scope are design documents under `docs/data-model/`, and `docs` is not a component in `workspace.yaml`. Integration tests are required when a specification lists more than one component. This specification lists none, so `testing.integration_tests` is false.

Later issues own the work in the table below. This specification stops at the design documents.

| Issue | Owns |
|---|---|
| DATA-002 | Source schema files, field names, data types, nullability, ingestion metadata, and data contracts |
| DATA-003 | Synthetic data generators and generated datasets |
| DATA-004 | GTM lifecycle scenario implementations |
| DATA-005 | Validation of generated data |
| Later warehouse work | dbt staging models, intermediate models, and marts, owned by `analytics-engineer` |
| Later analytics work | Hex and Omni assets, owned by `analyst` |

Orchestration workflows, infrastructure, and deployment are outside this task.

The source proposal in `decisions.md` names source entities, source identifiers, attributes required for canonical mapping, relationships, and the lifecycle events those sources emit. Physical field types, nullability, and contract files begin in DATA-002.

## Deliverables

Create these four files. They are the complete file set for the implementation.

### `docs/data-model/erd.md`

- A Mermaid entity-relationship diagram of the canonical entities.
- Every relationship labeled with explicit cardinality.
- The same cardinality restated in prose next to the diagram.
- A short note that walks the diagram along Lead → Opportunity → Customer → Adoption → Renewal.
- Canonical entities only. Source tables stay in `source-mapping.md`.

### `docs/data-model/entities.md`

- One section per canonical entity with business meaning, grain, primary key, business key, foreign keys, and attributes.
- Each attribute has a business definition. State when an attribute is required for pipeline, bookings, ARR, retention, or adoption.
- Relationship cardinality for each foreign key, matching the diagram.
- Proposed facts and dimensions. Each grain is a sentence of the form "one row represents ...". The entity section states the business grain: one instance of the entity. A fact or dimension grain stays consistent with that entity. Where Type 2 applies, the dimension row grain is the effective-dated grain defined in `decisions.md`, and the entity section still states the business grain. Those are different grains, and both are required.
- Business events, each with name, grain, the entity it belongs to, the timestamp that orders it, and the lifecycle stage it records. In `entities.md` or `decisions.md`, list the canonical stage and status values that choose each event, or mark that vocabulary as an open question for human review before DATA-002.
- Uniqueness and referential integrity expectations for each entity, stated so a later contract or test can enforce them.

The event list must be able to represent lead creation and qualification, opportunity open, stage change, win, and loss, customer conversion, product adoption and usage, and renewal, expansion, and churn. The design names the events and the entities that carry them. `entities.md` or `decisions.md` lists the canonical stage and status values that choose an event, or marks that list as an open question.

### `docs/data-model/source-mapping.md`

- For HubSpot, DealHub, Marketing, and Product: source concepts, source identifiers, the canonical entity each concept maps to, and the system that owns each canonical attribute.
- Rules that assign a canonical identifier from source identifiers, including which source wins when two systems describe the same firm, contact, lead, opportunity, subscription, or product user.
- Attributes that conflict or are ambiguous across sources, and either the chosen treatment or an open question.
- Traceability from each source identifier to the canonical identifier.
- A handoff note: DATA-002 specifies physical field types, nullability, and contract files from this mapping.

### `docs/data-model/decisions.md`

- Historical tracking strategy. For each entity whose changes affect pipeline, bookings, ARR, retention, or adoption, name the approach. Where slowly changing dimension Type 2 is the approach, define the dimension row grain as the effective-dated grain: effective start, effective end, and the current row. The entity section in `entities.md` still states the business grain. Where another approach is used, explain why Type 2 is a poor fit.
- Identity resolution and deduplication. Cover law firm versus contact versus product user, and lead versus customer. State match keys, the surviving canonical identifier, and the duplicate cases the model expects. A non-surviving duplicate keeps its source identifier and a link to the surviving canonical identifier.
- Synthetic data strategy. Propose the logical source schema a later generator needs so it can emit referentially consistent records for the canonical model. Name source entities, source identifiers, attributes required for canonical mapping, relationships, and the lifecycle events those sources must be able to emit. Physical field types, nullability, and contract files stay with DATA-002. Identify configurable seed, volume, and distribution as generator inputs for DATA-003. Proposed source records carry observed attributes and events. Revenue metrics and other business calculations stay out of those source records.
- Assumptions, constraints, limitations, and open questions. Mark any unresolved choice that would change grain, identity, or revenue history for human review before DATA-002 starts.
- A statement that this task leaves `contracts/` unchanged. Recommendations for a future shared contract are written here and implemented, if approved, by DATA-002.

## Constraints

- Stay inside `allowed_paths`.
- `contracts.changes_required` is false. DATA-002 is the issue that adds contract files.
- Follow the data-modeling principles: explicit grain, stable business identifiers where a business key exists, source structures separate from the canonical model, one canonical entity per business concept, and source lineage preserved on every mapped identifier.
- The canonical model must remain usable when a source system is added or replaced. Source-specific fields stay in the source mapping.
- Keep HubSpot, DealHub, Marketing, and Product as separate sources in the mapping.
- Preserve history where a changed attribute would change the result of pipeline, bookings, ARR, retention, or adoption analysis.
- Design for B2B SaaS sold to plaintiff law firms. A firm is the customer account. Contacts and product users are people related to a firm.
- Describe both the operational source records and the analytical facts and dimensions. Warehouse models that implement the analytical layer are later work owned by `analytics-engineer`.
- Prefer the smallest entity set that can represent the lifecycle and the analytical questions in Business context.
- The synthetic data proposal follows data-generation principles: referential integrity across related source records, reproducible generation through a configurable seed, configurable volume and distribution, and source records that expose lifecycle events.
- One owning agent, `data-engineer`, writes the design.
- Human approval is required. `decisions.md` presents significant unresolved modeling decisions for review before DATA-002 starts.
- An isolated warehouse schema is not required. Deployment is not required.

## Acceptance criteria

- [ ] `docs/data-model/erd.md`, `docs/data-model/entities.md`, `docs/data-model/source-mapping.md`, and `docs/data-model/decisions.md` exist.
- [ ] Those four files are the only files the implementation adds or edits.
- [ ] Core entities and relationships are documented, and every relationship has explicit cardinality that matches between the Mermaid diagram and the entity text.
- [ ] Every canonical entity defines a primary key and its foreign keys. Each foreign key references a documented primary key.
- [ ] Each entity states its business key where one exists, and the design records why the primary key is that business key or a surrogate.
- [ ] Source ownership is documented for HubSpot, DealHub, Marketing, and Product, including source identifiers and the canonical identifier they resolve to.
- [ ] The identity strategy documents how a firm, contact, lead, opportunity, customer, and product user are reconciled across those systems, including deduplication. A non-surviving duplicate keeps its source identifier and a link to the surviving canonical identifier.
- [ ] Grain is explicit for every proposed fact and dimension, and that grain stays consistent with the entity it describes. The entity section states the business grain. Where Type 2 applies, `decisions.md` states the dimension row grain as the effective-dated grain (effective start, effective end, and the current row). Those two statements describe different grains, and both are required.
- [ ] Historical tracking requirements are identified. Entities that need Type 2 history name that approach and its effective-dating grain. Other entities state why history is unnecessary or why a different approach is used.
- [ ] Business events required for Lead → Opportunity → Customer → Adoption → Renewal are identified, including events that can support pipeline, bookings, ARR, retention, and product adoption. The design lists the canonical stage and status values that choose each event, or marks that vocabulary as an open question.
- [ ] The `decisions.md` proposal names source entities, source identifiers, attributes required for canonical mapping, relationships, and the lifecycle events those sources emit. The proposal is sufficient for a later generator to emit referentially consistent records for the canonical model. Physical field types, nullability, and contract files stay with DATA-002.
- [ ] Conflicting or ambiguous source attributes are listed, each with an assumption or an open question.
- [ ] Assumptions, limitations, and unresolved questions are in `decisions.md`. Unresolved choices that would change identity, grain, or revenue history are marked for human review. An unresolved stage and status vocabulary is marked as an open question.
- [ ] Every canonical entity named in the source map and the event list appears in the diagram and in `entities.md`. Cardinality and keys agree across the four files. Business grain and, where Type 2 applies, the effective-dated row grain are both stated and stay consistent with each other.
- [ ] `contracts/`, `data-generation/`, `warehouse/`, `analytics/`, and `orchestration/` are unchanged.

## Execution notes

Implement this specification only after it has merged and the issue label is `status:ready`. Use an `impl` worktree. Write the four design documents. Leave this specification file unchanged unless a human changes the approved requirements.

Read the data-modeling skill before choosing entities, keys, grain, and mappings. Read the data-generation skill as a constraint on the synthetic data proposal. Generator code, scenario code, contract files, and dbt models sit outside `allowed_paths`.

Review the four documents together before opening the implementation pull request. Check that cardinality, keys, source identifiers, and events agree, and that the business grain and any Type 2 effective-dated row grain stay consistent with each other.

Where the fictional process does not force a choice, record an assumption or an open question. The approval gate for this design is `delivery.human_approval_required`. DATA-002 starts after a human approves the design.

Validation of this task is a review of the four documents against the acceptance criteria. `testing.component_tests`, `testing.integration_tests`, and `testing.end_to_end_tests` are false. `environment.isolated_schema` is false. `delivery.deployment_required` is false.
