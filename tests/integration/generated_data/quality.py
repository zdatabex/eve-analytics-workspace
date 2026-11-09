"""Contract, lifecycle, temporal, commercial, and usage checks."""

from __future__ import annotations

from datetime import timedelta

from model import (
    ACTIVITY_PARENTS,
    DEALHUB_ID_FIELDS,
    DOCUMENT_FIELDS,
    HUBSPOT_ID_FIELDS,
    INTEGER_MINIMUMS,
    MANIFEST_KEYS,
    NO_EVENT_ENTITIES,
    TOUCH_PARENTS,
    ContractSpec,
    DatasetRun,
    Defect,
    add_defect,
    as_date,
    business_timestamp,
    group_rows,
    identifier_set,
    in_effect,
    months_at_least,
    observation_key,
    ordered_rows,
    parse_date,
    parse_decimal,
    parse_timestamp,
    window_contains_timestamp,
)


def check_configuration(run: DatasetRun, defects: list[Defect], development_days: int) -> None:
    config = run.config or {}
    rule = "A committed configuration matches the DATA-005 dataset table."
    start = as_date(config.get("start_date"))
    end = as_date(config.get("end_date"))
    if config.get("seed") != run.expected_seed:
        add_defect(
            defects, run, "schema_compliance", rule,
            field="seed", actual=config.get("seed"),
        )
    if run.path.endswith("scenarios-test.yaml"):
        if start is None or end is None or (end - start).days <= 180 or (end - start).days >= development_days:
            add_defect(
                defects, run, "schema_compliance",
                "scenarios-test.yaml is longer than 180 days and shorter than the scenario development window.",
                field="window",
                actual=f"{config.get('start_date')} through {config.get('end_date')}",
            )
    else:
        expected = _expected_window(run.path)
        if start is None or end is None or start.isoformat() != expected[0] or end.isoformat() != expected[1]:
            add_defect(
                defects, run, "schema_compliance", rule,
                field="window",
                actual=f"{config.get('start_date')} through {config.get('end_date')}",
            )
    if run.path.endswith("default.yaml") and start and end and not months_at_least(start, end, 18):
        add_defect(
            defects, run, "schema_compliance",
            "default.yaml spans at least 18 months.",
            field="window", actual=f"{start} through {end}",
        )
    if run.population == "baseline":
        if "journeys" in config or "schema" in config:
            add_defect(
                defects, run, "schema_compliance",
                "A baseline file has no journeys key and no schema key. The load schema is dev_data_003.",
                field="schema", actual=sorted(key for key in ("journeys", "schema") if key in config),
            )
        if int(config.get("activity_count") or 0) < 2 or int(config.get("touch_count") or 0) < 1:
            add_defect(
                defects, run, "schema_compliance",
                "Both committed baseline files set activity_count to at least 2 and touch_count to at least 1.",
                field="activity_count",
                actual=f"activity_count={config.get('activity_count')} touch_count={config.get('touch_count')}",
            )
        return
    journeys = config.get("journeys") or {}
    expected_names = {
        "new_business_conversion", "expansion", "renewal", "churn",
        "lost_opportunity", "stage_regression", "low_adoption",
    }
    if set(journeys) != expected_names or any(journeys.get(name) != 1 for name in expected_names):
        add_defect(
            defects, run, "schema_compliance",
            "The two scenario files set every journey count to 1.",
            field="journeys", actual=journeys,
        )
    if config.get("schema") != "dev_data_004":
        add_defect(
            defects, run, "schema_compliance", rule,
            field="schema", actual=config.get("schema"),
        )
    for name, expected in (
        ("late_event_count", 1),
        ("ingest_lag_days", 1),
        ("term_days", 180),
        ("expansion_seat_increase", 1),
    ):
        if config.get(name) != expected:
            add_defect(
                defects, run, "schema_compliance",
                "Committed scenario files set late_event_count and ingest_lag_days to 1, term_days to 180, and expansion_seat_increase to 1.",
                field=name, actual=config.get(name),
            )
    for name, expected in (
        ("expansion_recurring_increase", "10.00"),
        ("contract_value_increase", "100.00"),
    ):
        if str(config.get(name)) != expected:
            add_defect(
                defects, run, "schema_compliance",
                "Committed scenario files set expansion_recurring_increase to 10.00 and contract_value_increase to 100.00.",
                field=name, actual=config.get(name),
            )
    catalog = list(config.get("lifecycle_stage_catalog") or [])
    missing = [item for item in ("prospect", "customer", "former_customer", "sql") if item not in catalog]
    if missing:
        add_defect(
            defects, run, "schema_compliance",
            "The committed lifecycle catalog includes prospect, customer, former_customer, and sql.",
            field="lifecycle_stage_catalog", actual=catalog,
        )
    workflows = tuple(
        (item.get("code"), item.get("name")) for item in config.get("workflows") or []
    )
    from model import EXPECTED_WORKFLOWS
    if set(workflows) != set(EXPECTED_WORKFLOWS) or len(workflows) != len(EXPECTED_WORKFLOWS):
        add_defect(
            defects, run, "schema_compliance",
            "The workflow catalog on both scenario files is exactly the seven codes in the DATA-005 specification.",
            field="workflows", actual=list(workflows),
        )
    bounds = (config.get("integer_ranges") or {}).get("work_unit_count") or {}
    maximum = bounds.get("max")
    minimum = bounds.get("min")
    if not isinstance(maximum, int) or not isinstance(minimum, int) or maximum < 2 or maximum <= minimum:
        add_defect(
            defects, run, "schema_compliance",
            "The configured work_unit_count maximum is at least 2 and greater than the minimum.",
            field="work_unit_count", actual=bounds,
        )


def _expected_window(path: str) -> tuple[str, str]:
    if path.endswith("test.yaml"):
        return ("2024-03-01", "2024-04-14")
    return ("2024-01-01", "2025-07-01")


def check_schema(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated or run.directory is None:
        return
    present = sorted(path.name for path in run.directory.iterdir() if path.is_file())
    expected_files = {contract.file_name for contract in contracts.values()} | {"manifest.json"}
    for name in present:
        if name.startswith("apollo") or name.startswith("clay") or name not in expected_files:
            add_defect(
                defects, run, "schema_compliance",
                "Apollo and Clay files are absent. Every dataset file is a source entity or manifest.json.",
                field="file", actual=name,
            )
    for contract in contracts.values():
        path = run.directory / contract.file_name
        if not path.exists():
            add_defect(
                defects, run, "schema_compliance",
                "Each dataset has one JSON Lines file named <source_system>_<source_entity>.jsonl.",
                contract=contract.path, entity=contract.id, field="file", actual="missing",
            )
            continue
        rows = run.rows.get(contract.id, [])
        if not rows:
            add_defect(
                defects, run, "schema_compliance",
                "Every committed dataset contains at least one row of every entity.",
                contract=contract.path, entity=contract.id, field="rows", actual=0,
            )
        for row in rows:
            _check_row_schema(run, contract, row, defects)
    _check_manifest(run, contracts, defects)
    _check_contract_shape(run, contracts, defects)
    _shape_recommendations(run, contracts)


def _check_contract_shape(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    user = contracts["product.user"]
    firm = contracts["product.firm"]
    if "hubspot_contact_id" in user.names:
        add_defect(
            defects, run, "schema_compliance",
            "A product user has no contact identifier.",
            contract=user.path, entity=user.id, field="hubspot_contact_id", actual="present on the contract",
        )
    if "hubspot_company_id" in firm.names:
        add_defect(
            defects, run, "schema_compliance",
            "The Product firm contract has no hubspot_company_id.",
            contract=firm.path, entity=firm.id, field="hubspot_company_id", actual="present on the contract",
        )


def _check_row_schema(run, contract: ContractSpec, row: dict, defects: list[Defect]) -> None:
    keys = set(row)
    expected = contract.names
    key_text = observation_key(contract, row)
    for name in sorted(keys - expected):
        add_defect(
            defects, run, "schema_compliance",
            "A row's keys are exactly that entity's fields plus its ingestion fields.",
            contract=contract.path, entity=contract.id, key=key_text, field=name, actual="extra column",
        )
    for name in sorted(expected - keys):
        add_defect(
            defects, run, "schema_compliance",
            "A row's keys are exactly that entity's fields plus its ingestion fields.",
            contract=contract.path, entity=contract.id, key=key_text, field=name, actual="missing column",
        )
    for column in contract.columns:
        if column.name not in row:
            continue
        value = row[column.name]
        _check_value(run, contract, row, column, value, defects)
    if row.get("source_system") != contract.source_system:
        add_defect(
            defects, run, "schema_compliance",
            "source_system equals the contract's source_system.",
            contract=contract.path, entity=contract.id, key=key_text,
            field="source_system", actual=row.get("source_system"),
        )


def _check_value(run, contract, row, column, value, defects) -> None:
    key_text = observation_key(contract, row)
    if value is None:
        return
    if value == "":
        add_defect(
            defects, run, "schema_compliance",
            "A missing optional value is null, not an empty string. A required string is non-empty.",
            contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual="empty string",
        )
        return
    if column.type in {"string", "enum"}:
        if not isinstance(value, str):
            add_defect(
                defects, run, "schema_compliance",
                "A string value is JSON text.",
                contract=contract.path, entity=contract.id, key=key_text,
                field=column.name, actual=type(value).__name__,
            )
            return
        if column.type == "enum" and column.allowed_values is not None and value not in column.allowed_values:
            add_defect(
                defects, run, "schema_compliance",
                "An enum value is one of that field's allowed_values.",
                contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
            )
        if column.name == "email_normalized" and value != value.strip().lower():
            add_defect(
                defects, run, "schema_compliance",
                "email_normalized, when present, is lowercase and trimmed.",
                contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
            )
        if column.name == "primary_domain" and not _valid_domain(value):
            add_defect(
                defects, run, "schema_compliance",
                "primary_domain, when present, is a lowercase host with no scheme and no path.",
                contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
            )
        return
    if column.type == "decimal":
        if parse_decimal(value) is None:
            add_defect(
                defects, run, "schema_compliance",
                "A decimal is a non-negative base-10 amount with at most two fraction digits, carried as a JSON string.",
                contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
            )
        return
    if column.type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            add_defect(
                defects, run, "schema_compliance",
                "An integer is a JSON integer.",
                contract=contract.path, entity=contract.id, key=key_text,
                field=column.name, actual=value,
            )
            return
        minimum = INTEGER_MINIMUMS.get(column.name)
        if minimum is not None and value < minimum:
            add_defect(
                defects, run, "schema_compliance",
                "seat_count is at least 0. work_unit_count is at least 1. impression_count and click_count, when present, are at least 0.",
                contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
            )
        return
    if column.type == "date" and parse_date(value) is None:
        add_defect(
            defects, run, "schema_compliance",
            "A date is an ISO-8601 calendar date. Dates have no time.",
            contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
        )
    if column.type == "timestamp" and parse_timestamp(value) is None:
        add_defect(
            defects, run, "schema_compliance",
            "A timestamp is an ISO-8601 UTC timestamp.",
            contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
        )


def _valid_domain(value: str) -> bool:
    if value != value.strip().lower() or not value:
        return False
    if "://" in value or "/" in value or "\\" in value or "@" in value:
        return False
    if any(character.isspace() for character in value):
        return False
    return True


def _check_manifest(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    manifest = run.manifest
    rule = "manifest.json records the seed, the configuration file name, start_date, end_date, delivery_id, and the row count of each entity."
    if not isinstance(manifest, dict):
        add_defect(defects, run, "schema_compliance", rule, entity="manifest", field="manifest.json", actual="missing")
        return
    extra = sorted(set(manifest) - MANIFEST_KEYS)
    missing = sorted(MANIFEST_KEYS - set(manifest))
    if extra or missing:
        add_defect(
            defects, run, "schema_compliance",
            "The manifest has no wall-clock timestamp. Its keys are the seed, configuration file name, window, delivery_id, and entity counts.",
            entity="manifest", field="keys", actual={"extra": extra, "missing": missing},
        )
    if manifest.get("configuration_file") != run.path.rsplit("/", 1)[-1]:
        add_defect(
            defects, run, "schema_compliance", rule,
            entity="manifest", field="configuration_file", actual=manifest.get("configuration_file"),
        )
    if manifest.get("seed") != run.expected_seed:
        add_defect(
            defects, run, "schema_compliance", rule,
            entity="manifest", field="seed", actual=manifest.get("seed"),
        )
    delivery = f"dlv_{run.expected_seed}"
    if manifest.get("delivery_id") != delivery:
        add_defect(
            defects, run, "schema_compliance",
            "One run uses one delivery_id, dlv_<seed>.",
            entity="manifest", field="delivery_id", actual=manifest.get("delivery_id"),
        )
    start = as_date((run.config or {}).get("start_date"))
    end = as_date((run.config or {}).get("end_date"))
    if manifest.get("start_date") != (start.isoformat() if start else None):
        add_defect(
            defects, run, "schema_compliance", rule,
            entity="manifest", field="start_date", actual=manifest.get("start_date"),
        )
    if manifest.get("end_date") != (end.isoformat() if end else None):
        add_defect(
            defects, run, "schema_compliance", rule,
            entity="manifest", field="end_date", actual=manifest.get("end_date"),
        )
    entities = manifest.get("entities")
    if not isinstance(entities, dict):
        add_defect(defects, run, "schema_compliance", rule, entity="manifest", field="entities", actual=entities)
        return
    expected_ids = set(contracts)
    if set(entities) != expected_ids:
        add_defect(
            defects, run, "schema_compliance", rule,
            entity="manifest", field="entities",
            actual={"missing": sorted(expected_ids - set(entities)), "extra": sorted(set(entities) - expected_ids)},
        )
    for contract_id, count in entities.items():
        actual = len(run.rows.get(contract_id, []))
        if count != actual:
            add_defect(
                defects, run, "schema_compliance",
                "Manifest entity counts match the files.",
                entity=contract_id, field="entities", actual=f"manifest={count} file={actual}",
            )
    deliveries = {
        row.get("delivery_id")
        for rows in run.rows.values()
        for row in rows
    }
    if deliveries != {delivery}:
        add_defect(
            defects, run, "schema_compliance",
            "One run uses one delivery_id, shared by the manifest and every row.",
            entity="manifest", field="delivery_id", actual=sorted(str(item) for item in deliveries),
        )


def _shape_recommendations(run: DatasetRun, contracts: dict[str, ContractSpec]) -> None:
    mismatches = []
    for contract in contracts.values():
        for row in run.rows.get(contract.id, []):
            for name, value in row.items():
                if not isinstance(value, str) or not value:
                    continue
                if name in HUBSPOT_ID_FIELDS and not value.isdigit():
                    mismatches.append(f"{contract.id}.{name}={value}")
                if name in DEALHUB_ID_FIELDS and not value.startswith(("qte_", "ctr_", "sub_", "bkg_")):
                    mismatches.append(f"{contract.id}.{name}={value}")
    run.distribution.setdefault("shape_mismatches", mismatches)


def check_keys(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated:
        return
    rule = (
        "The row key is the contract observation_key and is unique inside the entity. "
        "A repeated source identifier on an observation entity is not a duplicate primary key. "
        "Current entities and immutable entities whose observation_key is the source identifier have one row per source identifier. "
        "Campaign performance is unique on marketing_campaign_id plus performance_date. "
        "One generate run does not emit a replay or two current rows for one source identifier."
    )
    for contract in contracts.values():
        seen = {}
        for row in run.rows.get(contract.id, []):
            key = tuple(row.get(name) for name in contract.observation_key)
            rendered = observation_key(contract, row)
            if key in seen:
                add_defect(
                    defects, run, "primary_key_uniqueness", rule,
                    contract=contract.path, entity=contract.id, key=rendered,
                    field="observation_key", actual="duplicate",
                )
            seen[key] = rendered
    for contract_id, (identifier, document) in DOCUMENT_FIELDS.items():
        contract = contracts[contract_id]
        by_source: dict[str, set] = {}
        owners: dict[str, set] = {}
        for row in run.rows.get(contract_id, []):
            source = row.get(identifier)
            number = row.get(document)
            by_source.setdefault(str(source), set()).add(number)
            owners.setdefault(str(number), set()).add(str(source))
        for source, numbers in by_source.items():
            if len(numbers) != 1:
                add_defect(
                    defects, run, "primary_key_uniqueness",
                    f"{document} is stable across observations of one source identifier.",
                    contract=contract.path, entity=contract_id, key=f"{identifier}={source}",
                    field=document, actual=sorted(str(item) for item in numbers),
                )
        for number, sources in owners.items():
            if len(sources) > 1:
                add_defect(
                    defects, run, "primary_key_uniqueness",
                    f"{document} is unique across source identifiers of that entity.",
                    contract=contract.path, entity=contract_id, field=document, actual=f"{number} on {sorted(sources)}",
                )


def check_completeness(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated:
        return
    for contract in contracts.values():
        for row in run.rows.get(contract.id, []):
            key_text = observation_key(contract, row)
            for column in contract.columns:
                value = row.get(column.name, None)
                if column.name not in row:
                    continue
                if not column.nullable and value is None:
                    add_defect(
                        defects, run, "completeness",
                        "A field with nullable: false is present and non-null.",
                        contract=contract.path, entity=contract.id, key=key_text,
                        field=column.name, actual=None,
                    )
                if column.type == "string" and not column.nullable and isinstance(value, str) and value.strip() == "":
                    add_defect(
                        defects, run, "completeness",
                        "Required strings are non-empty.",
                        contract=contract.path, entity=contract.id, key=key_text,
                        field=column.name, actual=value,
                    )
                if value == "":
                    add_defect(
                        defects, run, "completeness",
                        "A null optional field meets the completeness rule. Null is not an empty string.",
                        contract=contract.path, entity=contract.id, key=key_text,
                        field=column.name, actual="empty string",
                    )


def check_foreign_keys(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated:
        return
    indexes = {
        contract_id: group_rows(rows, contracts[contract_id].source_identifier[0])
        for contract_id, rows in run.rows.items()
        if contracts[contract_id].source_identifier
    }
    id_sets = {
        contract.id: identifier_set(run.rows.get(contract.id, []), contract.source_identifier[0])
        for contract in contracts.values()
        if len(contract.source_identifier) == 1
    }
    for contract in contracts.values():
        for relationship in contract.relationships:
            parent_ids = id_sets.get(relationship.contract_id, set())
            for row in run.rows.get(contract.id, []):
                value = row.get(relationship.field)
                key_text = observation_key(contract, row)
                if value is None:
                    if relationship.required:
                        add_defect(
                            defects, run, "foreign_keys",
                            "A required relationship is present.",
                            contract=contract.path, entity=contract.id, key=key_text,
                            field=relationship.field, actual=None,
                        )
                    continue
                if str(value) not in parent_ids:
                    add_defect(
                        defects, run, "foreign_keys",
                        "A relationship value, when present, equals a source identifier emitted in the same dataset.",
                        contract=contract.path, entity=contract.id, key=key_text,
                        field=relationship.field, actual=value,
                    )
    _conditional_parents(run, contracts, indexes, defects)
    _company_agreement(run, contracts, indexes, defects)
    _cardinality(run, indexes, defects)
    leads = id_sets.get("hubspot.lead", set())
    companies = id_sets.get("hubspot.company", set())
    overlap = sorted(leads & companies)
    if overlap:
        add_defect(
            defects, run, "foreign_keys",
            "A lead and a company remain different source records. Conversion cites hubspot_deal_id and does not turn the lead into a company.",
            entity="hubspot.lead", field="hubspot_lead_id", actual=overlap[:10],
        )


def _conditional_parents(run, contracts, indexes, defects) -> None:
    for row in run.rows.get("hubspot.lead", []):
        key_text = observation_key(contracts["hubspot.lead"], row)
        converted = row.get("emitted_event") == "lead_converted"
        if converted and not row.get("hubspot_deal_id"):
            add_defect(
                defects, run, "foreign_keys",
                "A lead's hubspot_deal_id is present when emitted_event is lead_converted, and null on every other observation of that lead.",
                contract=contracts["hubspot.lead"].path, entity="hubspot.lead", key=key_text,
                field="hubspot_deal_id", actual=None,
            )
        if not converted and row.get("hubspot_deal_id") is not None:
            add_defect(
                defects, run, "foreign_keys",
                "A lead's hubspot_deal_id is present when emitted_event is lead_converted, and null on every other observation of that lead.",
                contract=contracts["hubspot.lead"].path, entity="hubspot.lead", key=key_text,
                field="hubspot_deal_id", actual=row.get("hubspot_deal_id"),
            )
    subscriptions = indexes.get("dealhub.subscription", {})
    for row in run.rows.get("hubspot.deal", []):
        key_text = observation_key(contracts["hubspot.deal"], row)
        kind = row.get("opportunity_type")
        subscription_id = row.get("dealhub_subscription_id")
        if kind == "new_business" and subscription_id is not None:
            add_defect(
                defects, run, "foreign_keys",
                "A deal observation with opportunity_type new_business has a null dealhub_subscription_id.",
                contract=contracts["hubspot.deal"].path, entity="hubspot.deal", key=key_text,
                field="dealhub_subscription_id", actual=subscription_id,
            )
        if kind in {"expansion", "renewal"}:
            if not subscription_id:
                add_defect(
                    defects, run, "foreign_keys",
                    "An observation with expansion or renewal has dealhub_subscription_id, and that subscription's hubspot_company_id equals the deal's.",
                    contract=contracts["hubspot.deal"].path, entity="hubspot.deal", key=key_text,
                    field="dealhub_subscription_id", actual=None,
                )
            else:
                sub_rows = subscriptions.get(str(subscription_id), [])
                companies = {item.get("hubspot_company_id") for item in sub_rows}
                if row.get("hubspot_company_id") not in companies:
                    add_defect(
                        defects, run, "foreign_keys",
                        "An observation with expansion or renewal has dealhub_subscription_id, and that subscription's hubspot_company_id equals the deal's.",
                        contract=contracts["hubspot.deal"].path, entity="hubspot.deal", key=key_text,
                        field="hubspot_company_id", actual=f"deal={row.get('hubspot_company_id')} subscription={sorted(str(item) for item in companies)}",
                    )
    for row in run.rows.get("marketing.touch", []):
        if not any(row.get(name) for name in TOUCH_PARENTS):
            add_defect(
                defects, run, "foreign_keys",
                "A touch has marketing_campaign_id and at least one of hubspot_contact_id, hubspot_lead_id, and hubspot_company_id.",
                contract=contracts["marketing.touch"].path, entity="marketing.touch",
                key=observation_key(contracts["marketing.touch"], row), field="parents", actual=None,
            )
    for row in run.rows.get("hubspot.activity", []):
        if not any(row.get(name) for name in ACTIVITY_PARENTS):
            add_defect(
                defects, run, "foreign_keys",
                "An activity has at least one of hubspot_company_id, hubspot_contact_id, hubspot_lead_id, and hubspot_deal_id.",
                contract=contracts["hubspot.activity"].path, entity="hubspot.activity",
                key=observation_key(contracts["hubspot.activity"], row), field="parents", actual=None,
            )


def _company_agreement(run, contracts, indexes, defects) -> None:
    deals = indexes.get("hubspot.deal", {})
    contacts = indexes.get("hubspot.contact", {})
    leads = indexes.get("hubspot.lead", {})
    quotes = indexes.get("dealhub.quote", {})
    contracts_by_id = indexes.get("dealhub.contract", {})
    subscriptions = indexes.get("dealhub.subscription", {})
    for row in run.rows.get("hubspot.deal", []):
        contact_id = row.get("hubspot_contact_id")
        if not contact_id:
            continue
        moment = parse_timestamp(row.get("observed_at"))
        contact = in_effect(contacts, contact_id, moment)
        key_text = observation_key(contracts["hubspot.deal"], row)
        if contact is None or contact.get("hubspot_company_id") != row.get("hubspot_company_id"):
            add_defect(
                defects, run, "foreign_keys",
                "When a deal observation includes hubspot_contact_id, the contact observation in effect at the deal's observed_at has the same hubspot_company_id.",
                contract=contracts["hubspot.deal"].path, entity="hubspot.deal", key=key_text,
                field="hubspot_company_id",
                actual=None if contact is None else contact.get("hubspot_company_id"),
            )
    _activity_touch_agreement(run, contracts, deals, contacts, leads, defects)
    for row in run.rows.get("dealhub.quote", []):
        moment = parse_timestamp(row.get("observed_at"))
        deal = in_effect(deals, row.get("hubspot_deal_id"), moment)
        if deal is None or deal.get("hubspot_company_id") != row.get("hubspot_company_id"):
            add_defect(
                defects, run, "foreign_keys",
                "A quote's hubspot_company_id equals the company on the deal observation in effect at the quote's observed_at.",
                contract=contracts["dealhub.quote"].path, entity="dealhub.quote",
                key=observation_key(contracts["dealhub.quote"], row), field="hubspot_company_id",
                actual=None if deal is None else deal.get("hubspot_company_id"),
            )
    for row in run.rows.get("dealhub.contract", []):
        moment = parse_timestamp(row.get("observed_at"))
        deal = in_effect(deals, row.get("hubspot_deal_id"), moment)
        quote = in_effect(quotes, row.get("dealhub_quote_id"), moment)
        key_text = observation_key(contracts["dealhub.contract"], row)
        if deal is None or deal.get("hubspot_company_id") != row.get("hubspot_company_id"):
            add_defect(
                defects, run, "foreign_keys",
                "A contract's company matches the cited deal and the cited quote.",
                contract=contracts["dealhub.contract"].path, entity="dealhub.contract", key=key_text,
                field="hubspot_deal_id", actual=None if deal is None else deal.get("hubspot_company_id"),
            )
        if quote is None or quote.get("hubspot_company_id") != row.get("hubspot_company_id"):
            add_defect(
                defects, run, "foreign_keys",
                "A contract's company matches the cited deal and the cited quote.",
                contract=contracts["dealhub.contract"].path, entity="dealhub.contract", key=key_text,
                field="dealhub_quote_id", actual=None if quote is None else quote.get("hubspot_company_id"),
            )
    for source, rows in subscriptions.items():
        contract_ids = {row.get("dealhub_contract_id") for row in rows}
        if len(contract_ids) != 1:
            add_defect(
                defects, run, "foreign_keys",
                "dealhub_contract_id is stable across that subscription's observations.",
                contract=contracts["dealhub.subscription"].path, entity="dealhub.subscription",
                key=f"dealhub_subscription_id={source}", field="dealhub_contract_id",
                actual=sorted(str(item) for item in contract_ids),
            )
        for row in rows:
            moment = parse_timestamp(row.get("observed_at"))
            parent = in_effect(contracts_by_id, row.get("dealhub_contract_id"), moment)
            if parent is None or parent.get("hubspot_company_id") != row.get("hubspot_company_id"):
                add_defect(
                    defects, run, "foreign_keys",
                    "A subscription's hubspot_company_id matches the cited contract.",
                    contract=contracts["dealhub.subscription"].path, entity="dealhub.subscription",
                    key=observation_key(contracts["dealhub.subscription"], row),
                    field="hubspot_company_id",
                    actual=None if parent is None else parent.get("hubspot_company_id"),
                )
    for row in run.rows.get("dealhub.booking", []):
        moment = parse_timestamp(row.get("booked_at"))
        key_text = observation_key(contracts["dealhub.booking"], row)
        parents = {
            "hubspot_deal_id": in_effect(deals, row.get("hubspot_deal_id"), moment),
            "dealhub_contract_id": in_effect(contracts_by_id, row.get("dealhub_contract_id"), moment),
            "dealhub_subscription_id": in_effect(subscriptions, row.get("dealhub_subscription_id"), moment),
        }
        for field_name, parent in parents.items():
            if parent is None or parent.get("hubspot_company_id") != row.get("hubspot_company_id"):
                add_defect(
                    defects, run, "foreign_keys",
                    "A booking's company matches the cited deal, contract, and subscription. All four booking parents are present.",
                    contract=contracts["dealhub.booking"].path, entity="dealhub.booking", key=key_text,
                    field=field_name, actual=None if parent is None else parent.get("hubspot_company_id"),
                )
        if not all(row.get(name) for name in ("hubspot_company_id", "hubspot_deal_id", "dealhub_contract_id", "dealhub_subscription_id")):
            add_defect(
                defects, run, "foreign_keys",
                "A booking's company matches the cited deal, contract, and subscription. All four booking parents are present.",
                contract=contracts["dealhub.booking"].path, entity="dealhub.booking", key=key_text,
                field="parents", actual="missing",
            )


def _activity_touch_agreement(run, contracts, deals, contacts, leads, defects) -> None:
    for entity, moment_field in (("hubspot.activity", "occurred_at"), ("marketing.touch", "occurred_at")):
        contract = contracts[entity]
        for row in run.rows.get(entity, []):
            moment = parse_timestamp(row.get(moment_field))
            key_text = observation_key(contract, row)
            if entity == "hubspot.activity" and row.get("hubspot_deal_id"):
                deal = in_effect(deals, row.get("hubspot_deal_id"), moment)
                if deal is None:
                    add_defect(
                        defects, run, "foreign_keys",
                        "An activity that cites a deal fails when no observation of that deal is in effect at occurred_at.",
                        contract=contract.path, entity=entity, key=key_text,
                        field="hubspot_deal_id", actual=row.get("hubspot_deal_id"),
                    )
            if not row.get("hubspot_company_id"):
                continue
            parents = []
            if row.get("hubspot_deal_id"):
                parents.append(("deal", in_effect(deals, row.get("hubspot_deal_id"), moment), True))
            if row.get("hubspot_contact_id"):
                parents.append(("contact", in_effect(contacts, row.get("hubspot_contact_id"), moment), False))
            if row.get("hubspot_lead_id"):
                parents.append(("lead", in_effect(leads, row.get("hubspot_lead_id"), moment), False))
            for label, parent, always_company in parents:
                if parent is None:
                    add_defect(
                        defects, run, "foreign_keys",
                        "When an activity or a touch includes hubspot_company_id and another parent that has a company, the company identifiers agree, using the parent observation in effect at occurred_at.",
                        contract=contract.path, entity=entity, key=key_text,
                        field=label, actual="no observation in effect",
                    )
                    continue
                parent_company = parent.get("hubspot_company_id")
                if parent_company is None and not always_company:
                    continue
                if parent_company != row.get("hubspot_company_id"):
                    add_defect(
                        defects, run, "foreign_keys",
                        "When an activity or a touch includes hubspot_company_id and another parent that has a company, the company identifiers agree, using the parent observation in effect at occurred_at.",
                        contract=contract.path, entity=entity, key=key_text,
                        field="hubspot_company_id", actual=f"{label}={parent_company}",
                    )


def _cardinality(run, indexes, defects) -> None:
    deals = indexes.get("hubspot.deal", {})
    leads = indexes.get("hubspot.lead", {})
    contracts_by_id = indexes.get("dealhub.contract", {})
    lead_deals: dict[str, set] = {}
    for deal_id, rows in deals.items():
        cited = {row.get("hubspot_lead_id") for row in rows if row.get("hubspot_lead_id")}
        for lead_id in cited:
            lead_deals.setdefault(str(lead_id), set()).add(deal_id)
    for lead_id, deal_ids in lead_deals.items():
        if len(deal_ids) > 1:
            add_defect(
                defects, run, "foreign_keys",
                "At most one deal cites a given lead.",
                entity="hubspot.deal", key=f"hubspot_lead_id={lead_id}",
                field="hubspot_deal_id", actual=sorted(deal_ids),
            )
    for lead_id, rows in leads.items():
        cited = {row.get("hubspot_deal_id") for row in rows if row.get("hubspot_deal_id")}
        if len(cited) > 1:
            add_defect(
                defects, run, "foreign_keys",
                "A lead cites at most one deal.",
                entity="hubspot.lead", key=f"hubspot_lead_id={lead_id}",
                field="hubspot_deal_id", actual=sorted(cited),
            )
    quote_contracts: dict[str, set] = {}
    deal_contracts: dict[str, set] = {}
    for contract_id, rows in contracts_by_id.items():
        quotes = {row.get("dealhub_quote_id") for row in rows if row.get("dealhub_quote_id")}
        deals_cited = {row.get("hubspot_deal_id") for row in rows if row.get("hubspot_deal_id")}
        for quote_id in quotes:
            quote_contracts.setdefault(str(quote_id), set()).add(contract_id)
        for deal_id in deals_cited:
            deal_contracts.setdefault(str(deal_id), set()).add(contract_id)
    for quote_id, contract_ids in quote_contracts.items():
        if len(contract_ids) > 1:
            add_defect(
                defects, run, "foreign_keys",
                "At most one contract cites a given quote.",
                entity="dealhub.contract", key=f"dealhub_quote_id={quote_id}",
                field="dealhub_contract_id", actual=sorted(contract_ids),
            )
    for deal_id, contract_ids in deal_contracts.items():
        if len(contract_ids) > 1:
            add_defect(
                defects, run, "foreign_keys",
                "At most one contract cites a given deal.",
                entity="dealhub.contract", key=f"hubspot_deal_id={deal_id}",
                field="dealhub_contract_id", actual=sorted(contract_ids),
            )


def check_lifecycle(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated:
        return
    for contract_id in sorted(NO_EVENT_ENTITIES):
        contract = contracts[contract_id]
        if "emitted_event" in contract.names:
            add_defect(
                defects, run, "lifecycle_transitions",
                "Quotes, contracts, bookings, activities, touches, campaign rows, campaign-day rows, firms, users, workflows, usage, and outcomes do not carry an emitted_event column.",
                contract=contract.path, entity=contract_id, field="emitted_event", actual="present",
            )
    _lead_lifecycle(run, contracts, defects)
    _deal_lifecycle(run, contracts, defects)
    _subscription_lifecycle(run, contracts, defects)


def _lead_lifecycle(run, contracts, defects) -> None:
    contract = contracts["hubspot.lead"]
    for lead_id, rows in group_rows(run.rows.get("hubspot.lead", []), "hubspot_lead_id").items():
        first = rows[0]
        key_text = f"hubspot_lead_id={lead_id}"
        if first.get("status") != "new" or first.get("emitted_event") != "lead_created" or first.get("observed_at") != first.get("created_at"):
            add_defect(
                defects, run, "lifecycle_transitions",
                "The first lead observation has status new, emitted_event lead_created, and observed_at equal to created_at.",
                contract=contract.path, entity=contract.id, key=key_text, field="status",
                actual=f"status={first.get('status')} event={first.get('emitted_event')}",
            )
        if len({row.get("created_at") for row in rows}) != 1:
            add_defect(
                defects, run, "lifecycle_transitions",
                "created_at is stable. Exactly one lead_created exists.",
                contract=contract.path, entity=contract.id, key=key_text, field="created_at", actual="varies",
            )
        events = [row.get("emitted_event") for row in rows]
        if events.count("lead_created") != 1:
            add_defect(
                defects, run, "lifecycle_transitions",
                "Exactly one lead_created exists.",
                contract=contract.path, entity=contract.id, key=key_text, field="emitted_event", actual=events.count("lead_created"),
            )
        for event in ("lead_qualified", "lead_disqualified", "lead_converted"):
            if events.count(event) > 1:
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "lead_qualified, lead_disqualified, and lead_converted each occur at most once.",
                    contract=contract.path, entity=contract.id, key=key_text, field="emitted_event", actual=event,
                )
        if "lead_qualified" in events and "lead_disqualified" in events:
            add_defect(
                defects, run, "lifecycle_transitions",
                "qualified and disqualified do not both occur.",
                contract=contract.path, entity=contract.id, key=key_text, field="emitted_event", actual="both",
            )
        qualified_at = next((parse_timestamp(row.get("observed_at")) for row in rows if row.get("emitted_event") == "lead_qualified"), None)
        converted_at = next((parse_timestamp(row.get("observed_at")) for row in rows if row.get("emitted_event") == "lead_converted"), None)
        if converted_at is not None and (qualified_at is None or qualified_at >= converted_at):
            add_defect(
                defects, run, "lifecycle_transitions",
                "lead_converted is preceded by lead_qualified at an earlier observed_at.",
                contract=contract.path, entity=contract.id, key=key_text, field="emitted_event", actual="lead_converted",
            )
        for row in rows:
            status = row.get("status")
            event = row.get("emitted_event")
            expected = {
                "qualified": "lead_qualified",
                "disqualified": "lead_disqualified",
                "converted": "lead_converted",
            }.get(status)
            if expected and event != expected:
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "status qualified, disqualified, and converted use lead_qualified, lead_disqualified, and lead_converted.",
                    contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                    field="emitted_event", actual=event,
                )
            if status == "working" and event is not None:
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "status working has a null emitted_event.",
                    contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                    field="emitted_event", actual=event,
                )
            if status == "disqualified" and row.get("hubspot_deal_id") is not None:
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "A disqualified lead has no hubspot_deal_id.",
                    contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                    field="hubspot_deal_id", actual=row.get("hubspot_deal_id"),
                )
            if row.get("hubspot_company_id") is None and row.get("hubspot_contact_id") is None and status == "converted":
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "A lead with a null company and a null contact is not converted.",
                    contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                    field="status", actual="converted",
                )


def _deal_lifecycle(run, contracts, defects) -> None:
    contract = contracts["hubspot.deal"]
    for deal_id, rows in group_rows(run.rows.get("hubspot.deal", []), "hubspot_deal_id").items():
        first = rows[0]
        key_text = f"hubspot_deal_id={deal_id}"
        if (
            first.get("stage") != "discovery"
            or first.get("emitted_event") != "opportunity_opened"
            or first.get("observed_at") != first.get("created_at")
            or first.get("emitted_event") == "opportunity_stage_changed"
        ):
            add_defect(
                defects, run, "lifecycle_transitions",
                "The first deal observation has stage discovery, emitted_event opportunity_opened, and observed_at equal to created_at. That opening is not opportunity_stage_changed.",
                contract=contract.path, entity=contract.id, key=key_text, field="stage",
                actual=f"stage={first.get('stage')} event={first.get('emitted_event')}",
            )
        events = [row.get("emitted_event") for row in rows]
        if events.count("opportunity_opened") != 1:
            add_defect(
                defects, run, "lifecycle_transitions",
                "Exactly one opportunity_opened exists.",
                contract=contract.path, entity=contract.id, key=key_text, field="emitted_event",
                actual=events.count("opportunity_opened"),
            )
        if len({row.get("created_at") for row in rows}) != 1 or len({row.get("hubspot_company_id") for row in rows}) != 1:
            add_defect(
                defects, run, "lifecycle_transitions",
                "created_at and hubspot_company_id are stable.",
                contract=contract.path, entity=contract.id, key=key_text, field="created_at", actual="varies",
            )
        present_leads = {row.get("hubspot_lead_id") for row in rows if row.get("hubspot_lead_id")}
        if len(present_leads) > 1:
            add_defect(
                defects, run, "lifecycle_transitions",
                "hubspot_lead_id on a deal is stable when it is present. A deal comes from at most one lead.",
                contract=contract.path, entity=contract.id, key=key_text, field="hubspot_lead_id",
                actual=sorted(present_leads),
            )
        previous = None
        for row in rows:
            if previous is not None and row.get("stage") == previous.get("stage") and row.get("emitted_event") is not None:
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "An observation whose stage equals the previous observation has a null emitted_event.",
                    contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                    field="emitted_event", actual=row.get("emitted_event"),
                )
            if previous is not None and row.get("stage") != previous.get("stage") and row.get("stage") in {"evaluation", "proposal", "negotiation"}:
                if row.get("emitted_event") != "opportunity_stage_changed":
                    add_defect(
                        defects, run, "lifecycle_transitions",
                        "An observation whose stage differs from the previous observation and is evaluation, proposal, or negotiation has emitted_event opportunity_stage_changed.",
                        contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                        field="emitted_event", actual=row.get("emitted_event"),
                    )
            if row.get("stage") == "closed_won" and row.get("emitted_event") != "opportunity_won":
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "An observation whose stage is closed_won has emitted_event opportunity_won.",
                    contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                    field="emitted_event", actual=row.get("emitted_event"),
                )
            if row.get("stage") == "closed_lost" and row.get("emitted_event") != "opportunity_lost":
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "An observation whose stage is closed_lost has emitted_event opportunity_lost.",
                    contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                    field="emitted_event", actual=row.get("emitted_event"),
                )
            previous = row
        won = events.count("opportunity_won")
        lost = events.count("opportunity_lost")
        if won > 1 or lost > 1 or (won and lost):
            add_defect(
                defects, run, "lifecycle_transitions",
                "opportunity_won and opportunity_lost each occur at most once. A deal does not have both.",
                contract=contract.path, entity=contract.id, key=key_text, field="emitted_event",
                actual=f"won={won} lost={lost}",
            )


def _subscription_lifecycle(run, contracts, defects) -> None:
    contract = contracts["dealhub.subscription"]
    bookings = run.rows.get("dealhub.booking", [])
    for subscription_id, rows in group_rows(run.rows.get("dealhub.subscription", []), "dealhub_subscription_id").items():
        churns = [row for row in rows if row.get("emitted_event") == "subscription_churned"]
        if len(churns) > 1:
            add_defect(
                defects, run, "lifecycle_transitions",
                "subscription_churned occurs at most once.",
                contract=contract.path, entity=contract.id, key=f"dealhub_subscription_id={subscription_id}",
                field="emitted_event", actual=len(churns),
            )
        for row in rows:
            event = row.get("emitted_event")
            status = row.get("status")
            key_text = observation_key(contract, row)
            if event in {"subscription_renewed", "subscription_expanded"} and status != "active":
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "subscription_renewed and subscription_expanded have status active.",
                    contract=contract.path, entity=contract.id, key=key_text, field="status", actual=status,
                )
            if status == "pending" and event is not None:
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "status pending has a null emitted_event.",
                    contract=contract.path, entity=contract.id, key=key_text, field="emitted_event", actual=event,
                )
            if status == "active" and event not in {None, "subscription_renewed", "subscription_expanded"}:
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "status active has a null emitted_event unless the observation is a renewal or an expansion.",
                    contract=contract.path, entity=contract.id, key=key_text, field="emitted_event", actual=event,
                )
            if event == "subscription_churned" and status != "churned":
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "subscription_churned has status churned, and a churned observation has emitted_event subscription_churned.",
                    contract=contract.path, entity=contract.id, key=key_text, field="status", actual=status,
                )
            if status == "churned" and event != "subscription_churned":
                add_defect(
                    defects, run, "lifecycle_transitions",
                    "A churned observation has emitted_event subscription_churned.",
                    contract=contract.path, entity=contract.id, key=key_text, field="emitted_event", actual=event,
                )
        if churns:
            churn_at = parse_timestamp(churns[0].get("observed_at"))
            for booking in bookings:
                if booking.get("dealhub_subscription_id") != subscription_id or churn_at is None:
                    continue
                booked_at = parse_timestamp(booking.get("booked_at"))
                if booked_at is not None and booked_at >= churn_at:
                    add_defect(
                        defects, run, "lifecycle_transitions",
                        "No booking for that subscription has booked_at at or after the churn observed_at.",
                        contract=contract.path, entity=contract.id,
                        key=observation_key(contracts["dealhub.booking"], booking),
                        field="booked_at", actual=booking.get("booked_at"),
                    )


def check_temporal(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated:
        return
    start = as_date((run.config or {}).get("start_date"))
    end = as_date((run.config or {}).get("end_date"))
    if start is None or end is None:
        return
    mismatches = []
    for contract in contracts.values():
        grouped = group_rows(run.rows.get(contract.id, []), contract.source_identifier[0]) if contract.history == "observation" else {}
        if contract.history == "observation":
            for source, rows in grouped.items():
                seen = set()
                for row in rows:
                    observed = parse_timestamp(row.get("observed_at"))
                    if observed is None:
                        continue
                    if observed in seen:
                        add_defect(
                            defects, run, "temporal_consistency",
                            "For one source identifier on an observation entity, observed_at values are unique, so the ordered observations strictly increase.",
                            contract=contract.path, entity=contract.id, key=f"{contract.source_identifier[0]}={source}",
                            field="observed_at", actual=row.get("observed_at"),
                        )
                    seen.add(observed)
        for row in run.rows.get(contract.id, []):
            key_text = observation_key(contract, row)
            created = parse_timestamp(row.get("created_at")) if row.get("created_at") is not None else None
            observed = parse_timestamp(row.get("observed_at")) if row.get("observed_at") is not None else None
            if created is not None and observed is not None and observed < created:
                add_defect(
                    defects, run, "temporal_consistency",
                    "observed_at is at or after created_at where both exist.",
                    contract=contract.path, entity=contract.id, key=key_text, field="observed_at", actual=row.get("observed_at"),
                )
            if contract.id == "dealhub.contract":
                start_day = parse_date(row.get("start_date"))
                end_day = parse_date(row.get("end_date"))
                if start_day and end_day and end_day < start_day:
                    add_defect(
                        defects, run, "temporal_consistency",
                        "end_date is on or after start_date on every contract observation.",
                        contract=contract.path, entity=contract.id, key=key_text, field="end_date", actual=row.get("end_date"),
                    )
            if contract.id == "dealhub.subscription":
                term_start = parse_date(row.get("term_start"))
                term_end = parse_date(row.get("term_end"))
                if term_start and term_end and term_end < term_start:
                    add_defect(
                        defects, run, "temporal_consistency",
                        "term_end is on or after term_start on every subscription observation.",
                        contract=contract.path, entity=contract.id, key=key_text, field="term_end", actual=row.get("term_end"),
                    )
            for column in contract.columns:
                value = row.get(column.name)
                if value is None:
                    continue
                if column.type == "date":
                    day = parse_date(value)
                    if day is not None and not (start <= day <= end):
                        add_defect(
                            defects, run, "temporal_consistency",
                            "Each business date falls inside the inclusive configured window.",
                            contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
                        )
                if column.type == "timestamp":
                    moment = parse_timestamp(value)
                    if moment is not None and not window_contains_timestamp(moment, start, end):
                        add_defect(
                            defects, run, "temporal_consistency",
                            "Each business timestamp and each ingested_at falls inside the inclusive configured window.",
                            contract=contract.path, entity=contract.id, key=key_text, field=column.name, actual=value,
                        )
            business = business_timestamp(contract, row)
            ingested = parse_timestamp(row.get("ingested_at"))
            if business is not None and ingested is not None and ingested < business:
                add_defect(
                    defects, run, "temporal_consistency",
                    "Where a row has a business timestamp, ingested_at is at or after it. A campaign-day business timestamp is performance_date at 00:00:00 UTC.",
                    contract=contract.path, entity=contract.id, key=key_text, field="ingested_at", actual=row.get("ingested_at"),
                )
            if business is not None and ingested is not None and ingested != business:
                mismatches.append((contract, row, business, ingested))
    usages = {row.get("product_usage_source_id"): row for row in run.rows.get("product.usage", [])}
    for row in run.rows.get("product.outcome", []):
        usage = usages.get(row.get("product_usage_source_id"))
        if usage is None:
            continue
        outcome_at = parse_timestamp(row.get("occurred_at"))
        usage_at = parse_timestamp(usage.get("occurred_at"))
        if outcome_at is not None and usage_at is not None and outcome_at < usage_at:
            add_defect(
                defects, run, "temporal_consistency",
                "An outcome's occurred_at is at or after the cited usage occurred_at.",
                contract=contracts["product.outcome"].path, entity="product.outcome",
                key=observation_key(contracts["product.outcome"], row), field="occurred_at", actual=row.get("occurred_at"),
            )
    if run.population != "scenario":
        return
    lag = (run.config or {}).get("ingest_lag_days")
    late_count = (run.config or {}).get("late_event_count")
    rule = (
        "On a scenario dataset, every row that has a business timestamp has ingested_at equal to that timestamp, "
        "except late_event_count immutable rows, which may be campaign-day rows and are exactly ingest_lag_days later."
    )
    if len(mismatches) != late_count:
        add_defect(
            defects, run, "temporal_consistency", rule,
            field="ingested_at", actual=f"{len(mismatches)} rows differ from the business timestamp",
        )
    for contract, row, business, ingested in mismatches:
        if contract.history != "immutable" or not isinstance(lag, int) or ingested != business + timedelta(days=lag):
            add_defect(
                defects, run, "temporal_consistency", rule,
                contract=contract.path, entity=contract.id, key=observation_key(contract, row),
                field="ingested_at", actual=row.get("ingested_at"),
            )


def check_commercial(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated:
        return
    deals = group_rows(run.rows.get("hubspot.deal", []), "hubspot_deal_id")
    quotes = group_rows(run.rows.get("dealhub.quote", []), "dealhub_quote_id")
    contract_rows = group_rows(run.rows.get("dealhub.contract", []), "dealhub_contract_id")
    subscriptions = group_rows(run.rows.get("dealhub.subscription", []), "dealhub_subscription_id")
    bookings = run.rows.get("dealhub.booking", [])
    contracts_by_deal: dict[str, set] = {}
    for contract_id, rows in contract_rows.items():
        for deal_id in {row.get("hubspot_deal_id") for row in rows}:
            contracts_by_deal.setdefault(str(deal_id), set()).add(contract_id)
    for deal_id, rows in deals.items():
        wins = [row for row in rows if row.get("emitted_event") == "opportunity_won"]
        cited = contracts_by_deal.get(deal_id, set())
        if len(wins) != 1:
            if cited:
                add_defect(
                    defects, run, "bookings_contracts_subscriptions",
                    "Contract creation follows the winning observation. A deal without that win has no contract.",
                    contract=contracts["dealhub.contract"].path, entity="dealhub.contract",
                    key=f"hubspot_deal_id={deal_id}", field="hubspot_deal_id", actual=sorted(cited),
                )
            continue
        win = wins[0]
        if win.get("stage") == "closed_won" and win.get("opportunity_type") == "new_business":
            _new_business_win(run, contracts, deal_id, win, cited, quotes, contract_rows, subscriptions, bookings, defects)
        elif cited:
            add_defect(
                defects, run, "bookings_contracts_subscriptions",
                "A deal whose winning observation is expansion or renewal has no contract.",
                contract=contracts["dealhub.contract"].path, entity="dealhub.contract",
                key=f"hubspot_deal_id={deal_id}", field="opportunity_type", actual=win.get("opportunity_type"),
            )
    for booking in bookings:
        amount = parse_decimal(booking.get("booking_amount"))
        if amount is None:
            continue
        moment = parse_timestamp(booking.get("booked_at"))
        deal = in_effect(deals, booking.get("hubspot_deal_id"), moment)
        key_text = observation_key(contracts["dealhub.booking"], booking)
        if deal is None:
            add_defect(
                defects, run, "bookings_contracts_subscriptions",
                "booked_at has a deal observation in effect, and booking_type equals opportunity_type on that observation.",
                contract=contracts["dealhub.booking"].path, entity="dealhub.booking", key=key_text,
                field="booked_at", actual=booking.get("booked_at"),
            )
        elif booking.get("booking_type") != deal.get("opportunity_type"):
            add_defect(
                defects, run, "bookings_contracts_subscriptions",
                "booking_type equals opportunity_type on the deal observation in effect at booked_at.",
                contract=contracts["dealhub.booking"].path, entity="dealhub.booking", key=key_text,
                field="booking_type", actual=f"{booking.get('booking_type')} != {deal.get('opportunity_type')}",
            )
    for subscription_id, rows in subscriptions.items():
        churns = [row for row in rows if row.get("emitted_event") == "subscription_churned"]
        if not churns:
            continue
        churn_at = parse_timestamp(churns[0].get("observed_at"))
        earlier = [
            booking for booking in bookings
            if booking.get("dealhub_subscription_id") == subscription_id
            and booking.get("booking_type") == "new_business"
            and churn_at is not None
            and parse_timestamp(booking.get("booked_at")) is not None
            and parse_timestamp(booking.get("booked_at")) < churn_at
        ]
        if not earlier:
            add_defect(
                defects, run, "bookings_contracts_subscriptions",
                "The earlier new-business booking remains. Churn does not create a booking.",
                entity="dealhub.subscription", key=f"dealhub_subscription_id={subscription_id}",
                field="booking_type", actual="no earlier new_business booking",
            )


def _new_business_win(run, contracts, deal_id, win, cited, quotes, contract_rows, subscriptions, bookings, defects) -> None:
    if len(cited) != 1:
        add_defect(
            defects, run, "bookings_contracts_subscriptions",
            "A new-business win has exactly one contract, and the contract's hubspot_deal_id is that deal.",
            contract=contracts["dealhub.contract"].path, entity="dealhub.contract",
            key=f"hubspot_deal_id={deal_id}", field="dealhub_contract_id", actual=sorted(cited),
        )
        return
    contract_id = next(iter(cited))
    observations = contract_rows[contract_id]
    first = observations[0]
    moment = parse_timestamp(first.get("observed_at"))
    quote = in_effect(quotes, first.get("dealhub_quote_id"), moment)
    if (
        quote is None
        or quote.get("status") != "accepted"
        or quote.get("quoted_amount") is None
        or quote.get("hubspot_deal_id") != deal_id
    ):
        add_defect(
            defects, run, "bookings_contracts_subscriptions",
            "The quote observation in effect at the contract's first observed_at has status accepted, a non-null quoted_amount, and the same hubspot_deal_id.",
            contract=contracts["dealhub.quote"].path, entity="dealhub.quote",
            key=f"dealhub_contract_id={contract_id}", field="status",
            actual=None if quote is None else quote.get("status"),
        )
    subs = {
        subscription_id
        for subscription_id, rows in subscriptions.items()
        if any(row.get("dealhub_contract_id") == contract_id for row in rows)
    }
    if not subs:
        add_defect(
            defects, run, "bookings_contracts_subscriptions",
            "A new-business win has at least one subscription on its contract.",
            entity="dealhub.subscription", key=f"dealhub_contract_id={contract_id}",
            field="dealhub_subscription_id", actual=0,
        )
    matched = [
        booking for booking in bookings
        if booking.get("hubspot_deal_id") == deal_id and booking.get("booking_type") == "new_business"
    ]
    if len(matched) != 1:
        add_defect(
            defects, run, "bookings_contracts_subscriptions",
            "A new-business win has exactly one booking with booking_type new_business on that deal.",
            entity="dealhub.booking", key=f"hubspot_deal_id={deal_id}",
            field="booking_type", actual=len(matched),
        )
        return
    booking = matched[0]
    if booking.get("dealhub_contract_id") != contract_id or booking.get("dealhub_subscription_id") not in subs:
        add_defect(
            defects, run, "bookings_contracts_subscriptions",
            "The booking cites that deal, that contract, and a subscription of that contract.",
            contract=contracts["dealhub.booking"].path, entity="dealhub.booking",
            key=observation_key(contracts["dealhub.booking"], booking),
            field="dealhub_contract_id", actual=booking.get("dealhub_contract_id"),
        )


def check_usage(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    if not run.generated:
        return
    usage_contract = contracts["product.usage"]
    if any(column.type == "decimal" for column in usage_contract.fields) or "emitted_event" in usage_contract.names:
        add_defect(
            defects, run, "product_usage",
            "Usage has no commercial amount and is not a lifecycle-event payload.",
            contract=usage_contract.path, entity=usage_contract.id, field="fields", actual="commercial or emitted_event column",
        )
    users = group_rows(run.rows.get("product.user", []), "product_user_source_id")
    for row in run.rows.get("product.usage", []):
        moment = parse_timestamp(row.get("occurred_at"))
        user = in_effect(users, row.get("product_user_source_id"), moment)
        if user is None or user.get("product_firm_id") != row.get("product_firm_id"):
            add_defect(
                defects, run, "product_usage",
                "product_firm_id is the firm on the user observation in effect at occurred_at.",
                contract=usage_contract.path, entity=usage_contract.id,
                key=observation_key(usage_contract, row), field="product_firm_id",
                actual=None if user is None else user.get("product_firm_id"),
            )
    seen = set()
    usages = {row.get("product_usage_source_id"): row for row in run.rows.get("product.usage", [])}
    for row in run.rows.get("product.outcome", []):
        usage_id = row.get("product_usage_source_id")
        key_text = observation_key(contracts["product.outcome"], row)
        if usage_id in seen:
            add_defect(
                defects, run, "product_usage",
                "At most one outcome cites a usage. product_usage_source_id is unique among outcomes.",
                contract=contracts["product.outcome"].path, entity="product.outcome", key=key_text,
                field="product_usage_source_id", actual=usage_id,
            )
        seen.add(usage_id)
        usage = usages.get(usage_id)
        if usage is None:
            continue
        for field_name in ("product_user_source_id", "product_firm_id", "product_workflow_id"):
            if row.get(field_name) != usage.get(field_name):
                add_defect(
                    defects, run, "product_usage",
                    "The outcome's user, firm, and workflow equal the usage.",
                    contract=contracts["product.outcome"].path, entity="product.outcome", key=key_text,
                    field=field_name, actual=row.get(field_name),
                )
        outcome_at = parse_timestamp(row.get("occurred_at"))
        usage_at = parse_timestamp(usage.get("occurred_at"))
        if outcome_at is not None and usage_at is not None and outcome_at < usage_at:
            add_defect(
                defects, run, "product_usage",
                "The outcome occurred_at is at or after the usage.",
                contract=contracts["product.outcome"].path, entity="product.outcome", key=key_text,
                field="occurred_at", actual=row.get("occurred_at"),
            )
