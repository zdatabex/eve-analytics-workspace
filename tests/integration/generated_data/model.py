"""Shared types for the DATA-005 generated-data suite.

The suite parses contracts itself. It does not import eve_data_generation.validate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from pathlib import Path
import re

import yaml


CHECKS = (
    "schema_compliance",
    "primary_key_uniqueness",
    "foreign_keys",
    "completeness",
    "lifecycle_transitions",
    "temporal_consistency",
    "bookings_contracts_subscriptions",
    "product_usage",
    "reproducibility",
    "distributions_and_edge_cases",
    "load_readback",
)

CHECK_TITLES = {
    "schema_compliance": "Schema compliance",
    "primary_key_uniqueness": "Primary key uniqueness",
    "foreign_keys": "Foreign key relationships",
    "completeness": "Required field completeness",
    "lifecycle_transitions": "Lifecycle transitions",
    "temporal_consistency": "Temporal consistency",
    "bookings_contracts_subscriptions": "Bookings, contracts, and subscriptions",
    "product_usage": "Product usage relationships",
    "reproducibility": "Reproducibility",
    "distributions_and_edge_cases": "Distributions and edge cases",
    "load_readback": "Load read-back",
}

JOURNEYS = (
    "new_business_conversion",
    "expansion",
    "renewal",
    "churn",
    "lost_opportunity",
    "stage_regression",
    "low_adoption",
)

CUSTOMER_JOURNEYS = (
    "new_business_conversion",
    "expansion",
    "renewal",
    "churn",
    "low_adoption",
)

EXPECTED_WORKFLOWS = (
    ("case_intake", "Case intake"),
    ("document_collection", "Document collection"),
    ("medical_record_review", "Medical record review"),
    ("document_summarization", "Document summarization"),
    ("demand_letter_generation", "Demand letter generation"),
    ("case_analysis", "Case analysis"),
    ("settlement_preparation", "Settlement preparation"),
)

NB_USAGE = (
    ("case_intake", None),
    ("document_collection", None),
    ("medical_record_review", None),
    ("document_summarization", "exported"),
    ("demand_letter_generation", "draft_completed"),
    ("settlement_preparation", "review_accepted"),
)

FORWARD_WON = ("discovery", "evaluation", "proposal", "negotiation", "closed_won")
FORWARD_LOST = ("discovery", "evaluation", "proposal", "negotiation", "closed_lost")
REGRESSION_STAGES = ("discovery", "evaluation", "proposal", "evaluation", "negotiation")
CONVERTING_LEAD = (
    ("new", "lead_created"),
    ("working", None),
    ("qualified", "lead_qualified"),
    ("converted", "lead_converted"),
)

DOCUMENT_FIELDS = {
    "dealhub.quote": ("dealhub_quote_id", "quote_number"),
    "dealhub.contract": ("dealhub_contract_id", "contract_number"),
    "dealhub.subscription": ("dealhub_subscription_id", "subscription_number"),
    "dealhub.booking": ("dealhub_booking_id", "booking_number"),
    "marketing.campaign": ("marketing_campaign_id", "campaign_code"),
    "product.ai_workflow": ("product_workflow_id", "workflow_code"),
}

NO_EVENT_ENTITIES = {
    "dealhub.quote",
    "dealhub.contract",
    "dealhub.booking",
    "hubspot.activity",
    "marketing.touch",
    "marketing.campaign",
    "marketing.campaign_performance",
    "product.firm",
    "product.user",
    "product.ai_workflow",
    "product.usage",
    "product.outcome",
}

INTEGER_MINIMUMS = {
    "seat_count": 0,
    "work_unit_count": 1,
    "impression_count": 0,
    "click_count": 0,
}

MANIFEST_KEYS = {
    "configuration_file",
    "delivery_id",
    "end_date",
    "entities",
    "seed",
    "start_date",
}

DEVELOPMENT_START = date(2024, 1, 1)
DEVELOPMENT_END = date(2025, 7, 1)
CANONICAL_STAGES = {"prospect", "customer", "former_customer"}
ACTIVITY_PARENTS = (
    "hubspot_company_id",
    "hubspot_contact_id",
    "hubspot_lead_id",
    "hubspot_deal_id",
)
TOUCH_PARENTS = ("hubspot_contact_id", "hubspot_lead_id", "hubspot_company_id")
HUBSPOT_ID_FIELDS = {
    "hubspot_company_id",
    "hubspot_contact_id",
    "hubspot_lead_id",
    "hubspot_deal_id",
    "hubspot_activity_id",
}
DEALHUB_ID_FIELDS = {
    "dealhub_quote_id",
    "dealhub_contract_id",
    "dealhub_subscription_id",
    "dealhub_booking_id",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DECIMAL_RE = re.compile(r"^(0|[1-9]\d*)(\.\d{1,2})?$")
LEAD_EVENTS = ("lead_created", "lead_qualified", "lead_disqualified", "lead_converted")
DEAL_EVENTS = (
    "opportunity_opened",
    "opportunity_stage_changed",
    "opportunity_won",
    "opportunity_lost",
)
SUBSCRIPTION_EVENTS = (
    "subscription_renewed",
    "subscription_expanded",
    "subscription_churned",
)


@dataclass(frozen=True)
class Defect:
    config_path: str
    seed: str
    generate_command: str
    check: str
    contract: str
    rule: str
    entity: str
    observation_key: str
    field: str
    actual: str

    def sort_key(self) -> tuple:
        return (
            self.check,
            self.config_path,
            self.entity,
            self.observation_key,
            self.field,
            self.rule,
            self.actual,
        )

    def one_line(self) -> str:
        return (
            f"{self.check} {self.entity} {self.observation_key} "
            f"{self.field}={self.actual} | {self.rule}"
        )


@dataclass
class FieldSpec:
    name: str
    type: str
    nullable: bool
    allowed_values: tuple[str, ...] | None


@dataclass
class RelationshipSpec:
    field: str
    contract_id: str
    reference_field: str
    required: bool


@dataclass
class ContractSpec:
    id: str
    path: str
    source_system: str
    source_entity: str
    history: str
    source_identifier: tuple[str, ...]
    observation_key: tuple[str, ...]
    fields: tuple[FieldSpec, ...]
    ingestion: tuple[FieldSpec, ...]
    relationships: tuple[RelationshipSpec, ...]

    @property
    def columns(self) -> tuple[FieldSpec, ...]:
        return self.fields + self.ingestion

    @property
    def names(self) -> set[str]:
        return {item.name for item in self.columns}

    @property
    def file_name(self) -> str:
        return f"{self.source_system}_{self.source_entity}.jsonl"

    @property
    def table_name(self) -> str:
        return f"src_{self.source_system}_{self.source_entity}"


@dataclass
class DatasetRun:
    path: str
    population: str
    expected_seed: int
    load_schema: str
    generate_command: str
    config: dict | None = None
    seed: str = ""
    start: str = ""
    end: str = ""
    delivery_id: str = ""
    directory: Path | None = None
    warehouse: Path | None = None
    generated: bool = False
    rows: dict[str, list[dict]] = field(default_factory=dict)
    row_counts: dict[str, str] = field(default_factory=dict)
    manifest: dict | None = None
    reproducible: bool = False
    distribution: dict = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    journeys: list[tuple[str, str, str]] = field(default_factory=list)


def repo_config(path: str) -> str:
    return path


def generate_command(path: str) -> str:
    return (
        "python3 -m eve_data_generation generate "
        f"--config {path} --output <temp directory>"
    )


def load_contracts(root: Path) -> dict[str, ContractSpec]:
    contracts = {}
    for path in sorted(root.glob("*/*.yaml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        contract = ContractSpec(
            id=document["id"],
            path=f"contracts/source/{path.parent.name}/{path.name}",
            source_system=document["source_system"],
            source_entity=document["source_entity"],
            history=document["history"],
            source_identifier=tuple(document["source_identifier"]),
            observation_key=tuple(document["observation_key"]),
            fields=tuple(_field(item) for item in document["fields"]),
            ingestion=tuple(_field(item) for item in document["ingestion"]),
            relationships=tuple(
                _relationship(item) for item in document.get("relationships") or []
            ),
        )
        contracts[contract.id] = contract
    return contracts


def _field(payload: dict) -> FieldSpec:
    allowed = payload.get("allowed_values")
    return FieldSpec(
        name=payload["name"],
        type=payload["type"],
        nullable=bool(payload["nullable"]),
        allowed_values=tuple(str(item) for item in allowed) if allowed else None,
    )


def _relationship(payload: dict) -> RelationshipSpec:
    system, entity, reference = payload["references"].split(".")
    return RelationshipSpec(
        field=payload["field"],
        contract_id=f"{system}.{entity}",
        reference_field=reference,
        required=bool(payload["required"]),
    )


def as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        parsed = parse_date(value)
        return parsed
    return None


def as_decimal(value) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def parse_date(value) -> date | None:
    if not isinstance(value, str) or DATE_RE.fullmatch(value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_timestamp(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    if value.endswith("Z"):
        text = value[:-1] + "+00:00"
    elif value.endswith("+00:00"):
        text = value
    else:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    offset = parsed.utcoffset()
    if offset != timedelta(0):
        return None
    return parsed.astimezone(timezone.utc).replace(tzinfo=None)


def parse_decimal(value) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, str):
        return None
    if DECIMAL_RE.fullmatch(value) is None:
        return None
    parsed = Decimal(value)
    if parsed < 0:
        return None
    return parsed


def observation_key(contract: ContractSpec, row: dict) -> str:
    parts = []
    for name in contract.observation_key:
        parts.append(f"{name}={row.get(name)!s}")
    return ", ".join(parts)


def ordered_rows(rows: list[dict]) -> list[dict]:
    def sort_key(row: dict):
        if "observed_at" in row:
            parsed = parse_timestamp(row.get("observed_at"))
            if parsed is not None:
                return parsed
        return datetime.min

    return sorted(rows, key=sort_key)


def group_rows(rows: list[dict], name: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row.get(name)), []).append(row)
    for key in grouped:
        grouped[key] = ordered_rows(grouped[key])
    return grouped


def in_effect(grouped: dict[str, list[dict]], identifier, moment: datetime | None) -> dict | None:
    if identifier is None or moment is None:
        return None
    chosen = None
    chosen_at = None
    for row in grouped.get(str(identifier), []):
        observed = parse_timestamp(row.get("observed_at"))
        if observed is None or observed > moment:
            continue
        if chosen_at is None or observed >= chosen_at:
            chosen = row
            chosen_at = observed
    return chosen


def identifier_set(rows: list[dict], name: str) -> set[str]:
    return {str(row[name]) for row in rows if row.get(name) is not None}


def share_count(population: int, rate: Decimal) -> int:
    if population <= 0 or rate <= 0:
        return 0
    if rate >= 1:
        return population
    chosen = int((Decimal(population) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if chosen < 1:
        chosen = 1
    if population > 1 and chosen > population - 1:
        chosen = population - 1
    return chosen


def allocate(count: int, weights: dict[str, int]) -> dict[str, int]:
    total = sum(weights.values())
    raw = {key: (Decimal(count) * Decimal(weight)) / Decimal(total) for key, weight in weights.items()}
    floors = {key: int(raw[key].to_integral_value(rounding=ROUND_FLOOR)) for key in weights}
    remainder = count - sum(floors.values())
    ranked = sorted(weights, key=lambda key: (-(raw[key] - Decimal(floors[key])), key))
    for key in ranked[:remainder]:
        floors[key] += 1
    return floors


def format_number(value) -> str:
    if isinstance(value, Decimal):
        text = format(value, "f")
    else:
        text = str(value)
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def months_at_least(start: date, end: date, months: int) -> bool:
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(start.day, _month_days(year, month))
    return end >= date(year, month, day)


def _month_days(year: int, month: int) -> int:
    if month == 12:
        nxt = date(year + 1, 1, 1)
    else:
        nxt = date(year, month + 1, 1)
    return (nxt - date(year, month, 1)).days


def window_contains_timestamp(moment: datetime, start: date, end: date) -> bool:
    opened = datetime.combine(start, time.min)
    closed = datetime.combine(end, time.max)
    return opened <= moment <= closed


def business_timestamp(contract: ContractSpec, row: dict) -> datetime | None:
    if contract.id == "marketing.campaign_performance":
        day = parse_date(row.get("performance_date"))
        if day is None:
            return None
        return datetime.combine(day, time.min)
    if contract.history == "current":
        return None
    for name in ("observed_at", "occurred_at", "booked_at"):
        if row.get(name) is not None:
            return parse_timestamp(row.get(name))
    return None


def latest(rows: list[dict]) -> dict:
    return ordered_rows(rows)[-1]


def add_defect(bucket: list[Defect], run: DatasetRun, check: str, rule: str, **kwargs) -> None:
    bucket.append(
        Defect(
            config_path=run.path,
            seed=run.seed or str(run.expected_seed),
            generate_command=run.generate_command,
            check=check,
            contract=kwargs.get("contract", "n/a"),
            rule=rule,
            entity=kwargs.get("entity", "n/a"),
            observation_key=kwargs.get("key", "n/a"),
            field=kwargs.get("field", "n/a"),
            actual=str(kwargs.get("actual", "")),
        )
    )
