"""Generation configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import yaml

from eve_data_generation.errors import ConfigError
from eve_data_generation.sampling import WINDOW_ERROR, available_seconds

CANONICAL_LIFECYCLE = frozenset({"prospect", "customer", "former_customer"})

COUNT_KEYS = (
    "account_count",
    "contacts_per_account",
    "lead_count",
    "campaign_count",
    "activity_count",
    "touch_count",
    "product_users_per_customer",
    "usage_events_per_user",
)

RATE_KEYS = (
    "opportunity_win_rate",
    "renewal_rate",
    "expansion_rate",
    "churn_rate",
    "outcome_rate",
    "domain_match_rate",
    "null_company_domain_rate",
    "duplicate_contact_email_rate",
    "orphan_lead_rate",
    "null_deal_amount_rate",
    "single_parent_activity_rate",
    "null_performance_measure_rate",
    "clicks_exceed_impressions_rate",
    "null_user_email_rate",
    "company_change_rate",
)

AMOUNT_KEYS = (
    "hubspot_amount",
    "quoted_amount",
    "total_contract_value",
    "booking_amount_new_business",
    "booking_amount_expansion",
    "booking_amount_renewal",
    "recurring_amount",
    "spend_amount",
)

INTEGER_KEYS = (
    "seat_count",
    "impression_count",
    "click_excess",
    "work_unit_count",
)

TOP_LEVEL = frozenset(
    {
        "seed",
        "start_date",
        "end_date",
        *COUNT_KEYS,
        *RATE_KEYS,
        "stage_mix",
        "lead_status_mix",
        "channel_mix",
        "lifecycle_stage_catalog",
        "owner_names",
        "practice_focuses",
        "plan_codes",
        "workflows",
        "states",
        "firm_prefixes",
        "hubspot_firm_suffixes",
        "product_firm_suffixes",
        "person_names",
        "titles",
        "campaign_names",
        "activity_subjects",
        "opportunity_name_template",
        "forecast_by_stage",
        "amount_ranges",
        "integer_ranges",
        "term_days",
    }
)


@dataclass(frozen=True)
class Bounds:
    minimum: Decimal
    maximum: Decimal


@dataclass(frozen=True)
class IntegerBounds:
    minimum: int
    maximum: int


@dataclass(frozen=True)
class WorkflowCatalogEntry:
    code: str
    name: str


@dataclass(frozen=True)
class Config:
    config_file: str
    seed: int
    start_date: date
    end_date: date
    account_count: int
    contacts_per_account: int
    lead_count: int
    campaign_count: int
    activity_count: int
    touch_count: int
    product_users_per_customer: int
    usage_events_per_user: int
    opportunity_win_rate: Decimal
    renewal_rate: Decimal
    expansion_rate: Decimal
    churn_rate: Decimal
    outcome_rate: Decimal
    domain_match_rate: Decimal
    null_company_domain_rate: Decimal
    duplicate_contact_email_rate: Decimal
    orphan_lead_rate: Decimal
    null_deal_amount_rate: Decimal
    single_parent_activity_rate: Decimal
    null_performance_measure_rate: Decimal
    clicks_exceed_impressions_rate: Decimal
    null_user_email_rate: Decimal
    company_change_rate: Decimal
    stage_mix: dict[str, int]
    lead_status_mix: dict[str, int]
    channel_mix: dict[str, int]
    lifecycle_stage_catalog: tuple[str, ...]
    owner_names: tuple[str, ...]
    practice_focuses: tuple[str, ...]
    plan_codes: tuple[str, ...]
    workflows: tuple[WorkflowCatalogEntry, ...]
    states: tuple[str, ...]
    firm_prefixes: tuple[str, ...]
    hubspot_firm_suffixes: tuple[str, ...]
    product_firm_suffixes: tuple[str, ...]
    person_names: tuple[str, ...]
    titles: tuple[str, ...]
    campaign_names: tuple[str, ...]
    activity_subjects: dict[str, tuple[str, ...]]
    opportunity_name_template: str
    forecast_by_stage: dict[str, str]
    amount_ranges: dict[str, Bounds]
    integer_ranges: dict[str, IntegerBounds]
    term_days: int

    @property
    def delivery_id(self) -> str:
        return f"dlv_{self.seed}"


def _date(value: object, key: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ConfigError(f"{key} must be an ISO-8601 date")


def _decimal(value: object, key: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ConfigError(f"{key} must be a number")
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise ConfigError(f"{key} must be a number") from exc


def _rate(value: object, key: str) -> Decimal:
    rate = _decimal(value, key)
    if rate < 0 or rate > 1:
        raise ConfigError(f"{key} must be between 0 and 1")
    return rate


def _count(value: object, key: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{key} must be a non-negative integer")
    if value < 0:
        raise ConfigError(f"{key} must be a non-negative integer")
    return value


def _positive_weights(value: object, key: str) -> dict[str, int]:
    if not isinstance(value, dict) or not value:
        raise ConfigError(f"{key} must be a non-empty map of weights")
    weights = {}
    for name, weight in value.items():
        if isinstance(weight, bool) or not isinstance(weight, int) or weight <= 0:
            raise ConfigError(f"{key}.{name} must be a positive integer")
        weights[str(name)] = weight
    return weights


def _strings(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ConfigError(f"{key} must be a non-empty list of strings")
    items = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(f"{key} must contain non-empty strings")
        items.append(item.strip())
    return tuple(items)


def _bounds(payload: object, key: str) -> Bounds:
    if not isinstance(payload, dict) or set(payload) != {"min", "max"}:
        raise ConfigError(f"{key} must define min and max")
    low = _decimal(payload["min"], f"{key}.min")
    high = _decimal(payload["max"], f"{key}.max")
    if low < 0 or high < low:
        raise ConfigError(f"{key} must be a non-negative min <= max")
    if high - low < Decimal("0.01"):
        raise ConfigError(f"{key} must span at least one cent")
    return Bounds(low, high)


def _integer_bounds(payload: object, key: str) -> IntegerBounds:
    if not isinstance(payload, dict) or set(payload) != {"min", "max"}:
        raise ConfigError(f"{key} must define min and max")
    low = payload["min"]
    high = payload["max"]
    if isinstance(low, bool) or isinstance(high, bool):
        raise ConfigError(f"{key} bounds must be integers")
    if not isinstance(low, int) or not isinstance(high, int) or low < 0 or high < low:
        raise ConfigError(f"{key} must be a non-negative min <= max")
    return IntegerBounds(low, high)


def config_from_mapping(payload: dict, config_file: str) -> Config:
    if not isinstance(payload, dict):
        raise ConfigError("configuration must be a mapping")
    unknown = set(payload) - TOP_LEVEL
    missing = TOP_LEVEL - set(payload)
    if unknown:
        raise ConfigError(f"unknown configuration keys: {', '.join(sorted(unknown))}")
    if missing:
        raise ConfigError(f"missing configuration keys: {', '.join(sorted(missing))}")

    stage_mix = _positive_weights(payload["stage_mix"], "stage_mix")
    if "closed_won" not in stage_mix:
        raise ConfigError("stage_mix must include closed_won")
    win_rate = _rate(payload["opportunity_win_rate"], "opportunity_win_rate")
    ratio = Decimal(stage_mix["closed_won"]) / Decimal(sum(stage_mix.values()))
    if ratio != win_rate:
        raise ConfigError(
            "stage_mix closed_won weight divided by the total weight "
            "must equal opportunity_win_rate"
        )

    lifecycle = _strings(payload["lifecycle_stage_catalog"], "lifecycle_stage_catalog")
    if not any(value not in CANONICAL_LIFECYCLE for value in lifecycle):
        raise ConfigError(
            "lifecycle_stage_catalog must include a value other than "
            "prospect, customer, and former_customer"
        )
    if len(lifecycle) < 2:
        raise ConfigError("lifecycle_stage_catalog must contain at least two values")

    workflows_raw = payload["workflows"]
    if not isinstance(workflows_raw, list) or not workflows_raw:
        raise ConfigError("workflows must be a non-empty catalog")
    workflows = []
    seen_codes = set()
    for entry in workflows_raw:
        if not isinstance(entry, dict) or set(entry) != {"code", "name"}:
            raise ConfigError("each workflow needs code and name")
        code = entry["code"]
        name = entry["name"]
        if not isinstance(code, str) or not code.strip():
            raise ConfigError("workflow code must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError("workflow name must be a non-empty string")
        if code in seen_codes:
            raise ConfigError(f"duplicate workflow code {code}")
        seen_codes.add(code)
        workflows.append(WorkflowCatalogEntry(code.strip(), name.strip()))

    subjects_raw = payload["activity_subjects"]
    if not isinstance(subjects_raw, dict) or not subjects_raw:
        raise ConfigError("activity_subjects must map activity types to phrases")
    subjects = {}
    for activity_type, phrases in subjects_raw.items():
        subjects[str(activity_type)] = _strings(phrases, f"activity_subjects.{activity_type}")

    forecast = payload["forecast_by_stage"]
    if not isinstance(forecast, dict) or not forecast:
        raise ConfigError("forecast_by_stage must map stages to forecast categories")
    forecast_by_stage = {str(key): str(value) for key, value in forecast.items()}

    template = payload["opportunity_name_template"]
    if not isinstance(template, str) or "{firm_name}" not in template or "{opportunity_type}" not in template:
        raise ConfigError(
            "opportunity_name_template must include {firm_name} and {opportunity_type}"
        )

    start = _date(payload["start_date"], "start_date")
    end = _date(payload["end_date"], "end_date")
    if end < start:
        raise ConfigError(WINDOW_ERROR)

    amount_payload = payload["amount_ranges"]
    integer_payload = payload["integer_ranges"]
    if not isinstance(amount_payload, dict) or set(amount_payload) != set(AMOUNT_KEYS):
        raise ConfigError("amount_ranges must define the commercial amount ranges")
    if not isinstance(integer_payload, dict) or set(integer_payload) != set(INTEGER_KEYS):
        raise ConfigError("integer_ranges must define seat, impression, click, and work-unit ranges")

    seed = payload["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ConfigError("seed must be an integer")

    term_days = payload["term_days"]
    if isinstance(term_days, bool) or not isinstance(term_days, int) or term_days < 1:
        raise ConfigError("term_days must be a positive integer")
    integer_ranges = {
        key: _integer_bounds(payload["integer_ranges"][key], f"integer_ranges.{key}")
        for key in INTEGER_KEYS
    }
    if integer_ranges["work_unit_count"].minimum < 1:
        raise ConfigError("integer_ranges.work_unit_count min must be at least 1")
    if integer_ranges["click_excess"].minimum < 1:
        raise ConfigError("integer_ranges.click_excess min must be at least 1")

    values = {key: _count(payload[key], key) for key in COUNT_KEYS}
    rates = {key: _rate(payload[key], key) for key in RATE_KEYS}
    return Config(
        config_file=config_file,
        seed=seed,
        start_date=start,
        end_date=end,
        lifecycle_stage_catalog=lifecycle,
        owner_names=_strings(payload["owner_names"], "owner_names"),
        practice_focuses=_strings(payload["practice_focuses"], "practice_focuses"),
        plan_codes=_strings(payload["plan_codes"], "plan_codes"),
        workflows=tuple(workflows),
        states=_strings(payload["states"], "states"),
        firm_prefixes=_strings(payload["firm_prefixes"], "firm_prefixes"),
        hubspot_firm_suffixes=_strings(payload["hubspot_firm_suffixes"], "hubspot_firm_suffixes"),
        product_firm_suffixes=_strings(payload["product_firm_suffixes"], "product_firm_suffixes"),
        person_names=_strings(payload["person_names"], "person_names"),
        titles=_strings(payload["titles"], "titles"),
        campaign_names=_strings(payload["campaign_names"], "campaign_names"),
        activity_subjects=subjects,
        opportunity_name_template=template,
        forecast_by_stage=forecast_by_stage,
        amount_ranges={key: _bounds(amount_payload[key], f"amount_ranges.{key}") for key in AMOUNT_KEYS},
        integer_ranges=integer_ranges,
        term_days=term_days,
        stage_mix=stage_mix,
        lead_status_mix=_positive_weights(payload["lead_status_mix"], "lead_status_mix"),
        channel_mix=_positive_weights(payload["channel_mix"], "channel_mix"),
        **values,
        **rates,
    )


def load_config(path: Path | str) -> Config:
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return config_from_mapping(payload, config_path.name)


def minimum_timestamps(config: Config) -> int:
    contacts = config.account_count * config.contacts_per_account
    return (
        config.account_count
        + contacts
        + config.lead_count
        + config.activity_count
        + config.touch_count
        + config.campaign_count
        + len(config.workflows)
        + 1
    )


def ensure_window(config: Config) -> None:
    if available_seconds(config.start_date, config.end_date) < minimum_timestamps(config):
        from eve_data_generation.errors import GenerationError

        raise GenerationError(WINDOW_ERROR)
