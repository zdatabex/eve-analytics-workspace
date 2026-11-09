"""Component tests for DATA-003 synthetic generators."""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest
import yaml

from eve_data_generation.cli import main
from eve_data_generation.config import config_from_mapping, load_config
from eve_data_generation.contracts import load_contracts
from eve_data_generation.dataset import build_dataset
from eve_data_generation.errors import ConfigError, GenerationError
from eve_data_generation.loader import load_dataset, warehouse_path
from eve_data_generation.paths import CONFIG_DIR, DATA_GENERATION_ROOT
from eve_data_generation.sampling import WINDOW_ERROR, allocate, inclusive_dates, share_count
from eve_data_generation.writer import write_dataset

FORBIDDEN = {
    "commercial_status",
    "effective_start",
    "effective_end",
    "is_current",
    "customer_converted",
    "adoption_reached",
    "surviving_account_id",
}

LEAD_EVENTS = {"lead_created", "lead_qualified", "lead_disqualified", "lead_converted"}
DEAL_EVENTS = {
    "opportunity_opened",
    "opportunity_stage_changed",
    "opportunity_won",
    "opportunity_lost",
}
SUBSCRIPTION_EVENTS = {"subscription_renewed", "subscription_expanded", "subscription_churned"}
CANONICAL_LIFECYCLE = {"prospect", "customer", "former_customer"}


@pytest.fixture(scope="module")
def contracts():
    return load_contracts()


@pytest.fixture(scope="module")
def config():
    return load_config(CONFIG_DIR / "test.yaml")


@pytest.fixture(scope="module")
def dataset(config):
    return build_dataset(config)


def _counts(values, expected):
    observed = Counter(values)
    return {key: observed[key] for key in expected}


def _latest(rows, identifier):
    grouped = {}
    for row in rows:
        grouped.setdefault(row[identifier], []).append(row)
    return {key: max(items, key=lambda item: item["observed_at"]) for key, items in grouped.items()}


def _parents(row):
    return [
        name
        for name in ("hubspot_company_id", "hubspot_contact_id", "hubspot_lead_id", "hubspot_deal_id")
        if row[name] is not None
    ]


def test_share_and_allocation_rules():
    assert share_count(90, Decimal("0.05")) == 5
    assert share_count(8, Decimal("0.125")) == 1
    assert share_count(4, Decimal("0.5")) == 2
    assert share_count(0, Decimal("0.5")) == 0
    assert share_count(4, Decimal("0")) == 0
    assert share_count(4, Decimal("1")) == 4
    weights = {"discovery": 1, "evaluation": 1, "proposal": 1, "negotiation": 1, "closed_won": 8, "closed_lost": 4}
    assert allocate(8, weights)["closed_won"] == 4
    assert allocate(8, weights)["closed_lost"] == 2


def test_default_window_is_at_least_18_months():
    config = load_config(CONFIG_DIR / "default.yaml")
    months = (config.end_date.year - config.start_date.year) * 12 + (
        config.end_date.month - config.start_date.month
    )
    assert months >= 18
    assert config.end_date >= date(config.start_date.year + 1, config.start_date.month, config.start_date.day)
    limit = config.start_date
    year = limit.year + (limit.month - 1 + 18) // 12
    month = (limit.month - 1 + 18) % 12 + 1
    assert config.end_date >= date(year, month, min(limit.day, 28))
    assert config.activity_count >= 2
    assert config.touch_count >= 1
    assert config.seed != load_config(CONFIG_DIR / "test.yaml").seed


def test_rejects_win_rate_that_disagrees_with_stage_mix():
    payload = yaml.safe_load((CONFIG_DIR / "test.yaml").read_text(encoding="utf-8"))
    payload["opportunity_win_rate"] = 0.2
    with pytest.raises(ConfigError, match="opportunity_win_rate"):
        config_from_mapping(payload, "bad.yaml")


def test_short_window_fails(config):
    short = replace(
        config,
        account_count=100000,
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 1),
        config_file="short.yaml",
    )
    with pytest.raises(GenerationError, match=WINDOW_ERROR):
        build_dataset(short)


def test_does_not_read_the_wall_clock(config):
    package = Path(__file__).resolve().parents[1] / "src" / "eve_data_generation"
    forbidden = ("datetime.now", "datetime.utcnow", "date.today", "time.time(", "time.time_ns")
    for path in sorted(package.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} reads the wall clock"
    build_dataset(config)


def test_alternate_population_replaces_the_baseline(config):
    dataset = build_dataset(config, population=lambda world: None)
    assert dataset.rows["marketing.campaign"] == []
    assert dataset.rows["hubspot.company"] == []


def test_exact_volumes(dataset, config):
    companies = {row["hubspot_company_id"] for row in dataset.rows["hubspot.company"]}
    contacts = {row["hubspot_contact_id"] for row in dataset.rows["hubspot.contact"]}
    leads = _latest(dataset.rows["hubspot.lead"], "hubspot_lead_id")
    campaigns = dataset.rows["marketing.campaign"]
    assert len(companies) == config.account_count
    assert len(contacts) == config.account_count * config.contacts_per_account
    assert len(leads) == config.lead_count
    assert len(campaigns) == config.campaign_count
    assert len(dataset.rows["hubspot.activity"]) == config.activity_count
    assert len(dataset.rows["marketing.touch"]) == config.touch_count
    lead_allocation = allocate(config.lead_count, config.lead_status_mix)
    assert _counts((lead["status"] for lead in leads.values()), lead_allocation) == lead_allocation
    new_business = [
        row
        for row in _latest(dataset.rows["hubspot.deal"], "hubspot_deal_id").values()
        if row["opportunity_type"] == "new_business"
    ]
    assert len(new_business) == lead_allocation["converted"]
    stage_allocation = allocate(len(new_business), config.stage_mix)
    assert _counts((row["stage"] for row in new_business), stage_allocation) == stage_allocation
    wins = [row for row in new_business if row["stage"] == "closed_won"]
    subscriptions = {row["dealhub_subscription_id"] for row in dataset.rows["dealhub.subscription"]}
    assert len(subscriptions) == len(wins)
    renewed = {
        row["dealhub_subscription_id"]
        for row in dataset.rows["dealhub.subscription"]
        if row["emitted_event"] == "subscription_renewed"
    }
    expanded = {
        row["dealhub_subscription_id"]
        for row in dataset.rows["dealhub.subscription"]
        if row["emitted_event"] == "subscription_expanded"
    }
    churned = {
        row["dealhub_subscription_id"]
        for row in dataset.rows["dealhub.subscription"]
        if row["emitted_event"] == "subscription_churned"
    }
    assert len(renewed) == share_count(len(subscriptions), config.renewal_rate)
    assert len(expanded) == share_count(len(subscriptions), config.expansion_rate)
    assert len(churned) == share_count(len(subscriptions), config.churn_rate)
    firms = dataset.rows["product.firm"]
    users = dataset.rows["product.user"]
    usages = dataset.rows["product.usage"]
    assert len(firms) == len(wins)
    assert len(users) == len(firms) * config.product_users_per_customer
    assert len(usages) == len(users) * config.usage_events_per_user
    assert len(dataset.rows["product.outcome"]) == share_count(len(usages), config.outcome_rate)
    days = len(inclusive_dates(config.start_date, config.end_date))
    performance = dataset.rows["marketing.campaign_performance"]
    assert len(performance) == config.campaign_count * days
    assert sum(row["spend_amount"] is None for row in performance) == share_count(
        len(performance), config.null_performance_measure_rate
    )
    assert sum(
        row["click_count"] is not None
        and row["impression_count"] is not None
        and row["click_count"] > row["impression_count"]
        for row in performance
    ) == share_count(len(performance), config.clicks_exceed_impressions_rate)


def test_every_entity_and_event(dataset, contracts):
    assert set(dataset.rows) == set(contracts)
    assert all(dataset.rows[contract_id] for contract_id in contracts)
    systems = {contract.source_system for contract in contracts.values()}
    assert systems == {"hubspot", "dealhub", "marketing", "product"}
    assert not any(name.startswith("apollo") or name.startswith("clay") for name in dataset.rows)
    lead_events = {row["emitted_event"] for row in dataset.rows["hubspot.lead"] if row["emitted_event"]}
    deal_events = {row["emitted_event"] for row in dataset.rows["hubspot.deal"] if row["emitted_event"]}
    subscription_events = {
        row["emitted_event"] for row in dataset.rows["dealhub.subscription"] if row["emitted_event"]
    }
    assert lead_events == LEAD_EVENTS
    assert deal_events == DEAL_EVENTS
    assert subscription_events == SUBSCRIPTION_EVENTS
    pre = [row for row in dataset.rows["hubspot.activity"] if row["hubspot_deal_id"] is None]
    post = [row for row in dataset.rows["hubspot.activity"] if row["hubspot_deal_id"] is not None]
    assert pre and post
    assert len(pre) == len(dataset.rows["hubspot.activity"]) // 2


def test_contract_shape(dataset, config, contracts):
    for contract in contracts.values():
        expected = [field.name for field in contract.columns]
        for row in dataset.rows[contract.id]:
            assert list(row) != expected or set(row) == set(expected)
            assert set(row) == set(expected)
            assert not set(row) & FORBIDDEN
            for field in contract.columns:
                value = row[field.name]
                if value is None:
                    assert field.nullable
                    continue
                if field.type in {"string", "enum"}:
                    assert isinstance(value, str) and value
                elif field.type == "decimal":
                    assert isinstance(value, Decimal) and value >= 0
                elif field.type == "integer":
                    assert isinstance(value, int) and not isinstance(value, bool)
                elif field.type == "date":
                    assert config.start_date <= value <= config.end_date
                elif field.type == "timestamp":
                    assert datetime_in_window(value, config)
            assert row["source_system"] == contract.source_system
            assert row["delivery_id"] == config.delivery_id
            assert datetime_in_window(row["ingested_at"], config)


def datetime_in_window(value, config):
    start = f"{config.start_date.isoformat()}T00:00:00"
    end = f"{config.end_date.isoformat()}T23:59:59"
    rendered = value.strftime("%Y-%m-%dT%H:%M:%S")
    return start <= rendered <= end


def test_conformance_cases(dataset, config):
    companies = dataset.rows["hubspot.company"]
    assert any(row["primary_domain"] is None for row in companies)
    assert any(row["hubspot_lifecycle_stage"] not in CANONICAL_LIFECYCLE for row in companies)
    counts = Counter(row["hubspot_company_id"] for row in companies)
    assert sum(count > 1 for count in counts.values()) == share_count(
        config.account_count, config.company_change_rate
    )
    emails = [row["email_normalized"] for row in dataset.rows["hubspot.contact"]]
    assert max(Counter(emails).values()) >= 2
    orphans = [
        row
        for row in _latest(dataset.rows["hubspot.lead"], "hubspot_lead_id").values()
        if row["hubspot_company_id"] is None and row["hubspot_contact_id"] is None
    ]
    assert orphans
    assert all(row["status"] != "converted" for row in orphans)
    assert any(row["amount"] is None for row in dataset.rows["hubspot.deal"])
    single = [row for row in dataset.rows["hubspot.activity"] if len(_parents(row)) == 1]
    assert len(single) == share_count(config.activity_count, config.single_parent_activity_rate)
    assert any(row["status"] == "active" and row["emitted_event"] in {"subscription_renewed", "subscription_expanded"} for row in dataset.rows["dealhub.subscription"])
    churn_ids = {
        row["dealhub_subscription_id"]
        for row in dataset.rows["dealhub.subscription"]
        if row["emitted_event"] == "subscription_churned"
    }
    assert churn_ids
    company_domains = {row["primary_domain"] for row in companies if row["primary_domain"]}
    matched = [row for row in dataset.rows["product.firm"] if row["primary_domain"] in company_domains]
    unmatched = [row for row in dataset.rows["product.firm"] if row["primary_domain"] not in company_domains]
    assert matched and unmatched
    for firm in matched:
        same_domain = [row for row in companies if row["primary_domain"] == firm["primary_domain"]]
        assert same_domain
        assert any(row["firm_name"] != firm["firm_name"] for row in same_domain)
    assert any(row["email_normalized"] is None for row in dataset.rows["product.user"])
    for row in dataset.rows["dealhub.subscription"]:
        assert row["seat_count"] != config.product_users_per_customer


def test_amounts_are_independent(dataset, config):
    ranges = config.amount_ranges
    checks = {
        "hubspot.deal": ("amount", ranges["hubspot_amount"]),
        "dealhub.quote": ("quoted_amount", ranges["quoted_amount"]),
        "dealhub.contract": ("total_contract_value", ranges["total_contract_value"]),
        "dealhub.subscription": ("recurring_amount", ranges["recurring_amount"]),
        "marketing.campaign_performance": ("spend_amount", ranges["spend_amount"]),
    }
    for contract_id, (field, bounds) in checks.items():
        for row in dataset.rows[contract_id]:
            value = row[field]
            if value is not None:
                assert bounds.minimum <= value <= bounds.maximum
    booking_ranges = {
        "new_business": ranges["booking_amount_new_business"],
        "expansion": ranges["booking_amount_expansion"],
        "renewal": ranges["booking_amount_renewal"],
    }
    for row in dataset.rows["dealhub.booking"]:
        bounds = booking_ranges[row["booking_type"]]
        assert bounds.minimum <= row["booking_amount"] <= bounds.maximum
    deal_amounts = {
        row["hubspot_deal_id"]: row["amount"]
        for row in dataset.rows["hubspot.deal"]
        if row["amount"] is not None
    }
    for booking in dataset.rows["dealhub.booking"]:
        amount = deal_amounts.get(booking["hubspot_deal_id"])
        if amount is not None:
            assert amount != booking["booking_amount"]


def test_referential_integrity_and_commercial_chain(dataset):
    deals = _latest(dataset.rows["hubspot.deal"], "hubspot_deal_id")
    contracts_by_deal = {}
    for row in dataset.rows["dealhub.contract"]:
        contracts_by_deal.setdefault(row["hubspot_deal_id"], set()).add(row["dealhub_contract_id"])
    for deal in deals.values():
        if deal["stage"] == "closed_won" and deal["opportunity_type"] == "new_business":
            assert len(contracts_by_deal[deal["hubspot_deal_id"]]) == 1
        if deal["opportunity_type"] in {"expansion", "renewal"}:
            assert deal["hubspot_deal_id"] not in contracts_by_deal
    numbers = {}
    for contract_id, identifier, number in (
        ("dealhub.quote", "dealhub_quote_id", "quote_number"),
        ("dealhub.contract", "dealhub_contract_id", "contract_number"),
        ("dealhub.subscription", "dealhub_subscription_id", "subscription_number"),
        ("dealhub.booking", "dealhub_booking_id", "booking_number"),
        ("marketing.campaign", "marketing_campaign_id", "campaign_code"),
        ("product.ai_workflow", "product_workflow_id", "workflow_code"),
    ):
        seen = {}
        for row in dataset.rows[contract_id]:
            seen.setdefault(row[identifier], set()).add(row[number])
        assert all(len(values) == 1 for values in seen.values())
        assert len({next(iter(values)) for values in seen.values()}) == len(seen)
        numbers[(contract_id, number)] = seen
    for row in dataset.rows["hubspot.company"]:
        assert row["hubspot_company_id"].isdigit()
    for row in dataset.rows["dealhub.quote"]:
        assert row["dealhub_quote_id"].startswith("qte_")
    for row in dataset.rows["product.firm"]:
        assert row["product_firm_id"].startswith("frm_")
    for row in dataset.rows["marketing.touch"]:
        assert row["marketing_touch_source_id"].startswith("tch_")


def test_opening_timestamps(dataset):
    for rows in _group(dataset.rows["hubspot.lead"], "hubspot_lead_id").values():
        opening = min(rows, key=lambda row: row["observed_at"])
        assert opening["observed_at"] == opening["created_at"]
        assert all(row["observed_at"] >= row["created_at"] for row in rows)
    for rows in _group(dataset.rows["hubspot.deal"], "hubspot_deal_id").values():
        opening = min(rows, key=lambda row: row["observed_at"])
        assert opening["observed_at"] == opening["created_at"]
        assert opening["emitted_event"] == "opportunity_opened"


def _group(rows, identifier):
    grouped = {}
    for row in rows:
        grouped.setdefault(row[identifier], []).append(row)
    return grouped


def test_reproducible_bytes(config, contracts, tmp_path):
    first = tmp_path / "one"
    second = tmp_path / "two"
    write_dataset(build_dataset(config), contracts, first)
    write_dataset(build_dataset(config), contracts, second)
    files = sorted(path.name for path in first.iterdir())
    assert files == sorted(path.name for path in second.iterdir())
    assert "manifest.json" in files
    for name in files:
        assert (first / name).read_bytes() == (second / name).read_bytes()
    other = replace(config, seed=config.seed + 1, config_file=config.config_file)
    third = tmp_path / "three"
    write_dataset(build_dataset(other), contracts, third)
    assert (first / "hubspot_lead.jsonl").read_bytes() != (third / "hubspot_lead.jsonl").read_bytes()


def test_jsonl_and_manifest(config, contracts, tmp_path):
    directory = tmp_path / "dataset"
    write_dataset(build_dataset(config), contracts, directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {
        "configuration_file",
        "delivery_id",
        "end_date",
        "entities",
        "seed",
        "start_date",
    }
    assert manifest["seed"] == config.seed
    assert manifest["configuration_file"] == "test.yaml"
    assert manifest["delivery_id"] == f"dlv_{config.seed}"
    assert "T" not in manifest["start_date"]
    sample = (directory / "hubspot_company.jsonl").read_text(encoding="utf-8")
    assert sample.endswith("\n")
    row = json.loads(sample.splitlines()[0])
    assert list(row) == sorted(row)
    deal = json.loads((directory / "hubspot_deal.jsonl").read_text(encoding="utf-8").splitlines()[0])
    if deal["amount"] is not None:
        assert isinstance(deal["amount"], str)
        assert Decimal(deal["amount"]).as_tuple().exponent == -2
    activity = (directory / "hubspot_activity.jsonl").read_text(encoding="utf-8")
    assert activity.endswith("\n")


def test_loader_replaces_rows_and_preserves_decimals(config, contracts, tmp_path, monkeypatch):
    directory = tmp_path / "dataset"
    write_dataset(build_dataset(config), contracts, directory)
    database = tmp_path / "warehouse" / "dev_data_003"
    monkeypatch.delenv("EVE_DATA_GENERATION_DUCKDB_PATH", raising=False)
    assert warehouse_path() .name == "dev_data_003"
    monkeypatch.setenv("EVE_DATA_GENERATION_DUCKDB_PATH", "")
    assert warehouse_path() == warehouse_path(None)
    load_dataset(directory, database)
    load_dataset(directory, database)
    connection = duckdb.connect(str(database))
    catalog = connection.execute("SELECT current_catalog()").fetchone()[0]
    company_table = f'"{catalog}"."dev_data_003"."src_hubspot_company"'
    quote_table = f'"{catalog}"."dev_data_003"."src_dealhub_quote"'
    schemas = {row[0] for row in connection.execute("SELECT schema_name FROM information_schema.schemata").fetchall()}
    assert "dev_data_003" in schemas
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'dev_data_003'"
        ).fetchall()
    }
    assert tables == {contract.table_name for contract in contracts.values()}
    columns = [
        row[0]
        for row in connection.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'dev_data_003' AND table_name = 'src_hubspot_company'
            ORDER BY ordinal_position
            """
        ).fetchall()
    ]
    assert columns == [field.name for field in contracts["hubspot.company"].columns]
    company_count = connection.execute(f"SELECT count(*) FROM {company_table}").fetchone()[0]
    assert company_count == len(build_dataset(config).rows["hubspot.company"])
    null_domains = connection.execute(
        f"SELECT count(*) FROM {company_table} WHERE primary_domain IS NULL"
    ).fetchone()[0]
    assert null_domains >= 1
    amount = connection.execute(
        f"SELECT quoted_amount FROM {quote_table} WHERE quoted_amount IS NOT NULL LIMIT 1"
    ).fetchone()[0]
    assert isinstance(amount, Decimal)
    assert amount == amount.quantize(Decimal("0.01"))
    connection.execute(f"DELETE FROM {company_table}")
    connection.close()
    load_dataset(directory, database)
    connection = duckdb.connect(str(database))
    restored = connection.execute(f"SELECT count(*) FROM {company_table}").fetchone()[0]
    connection.close()
    assert restored == company_count


def test_cli_generate_and_load(tmp_path, monkeypatch):
    output = tmp_path / "generated"
    database = tmp_path / "cli.duckdb"
    assert main(["generate", "--config", str(CONFIG_DIR / "test.yaml"), "--output", str(output)]) == 0
    assert (output / "manifest.json").exists()
    monkeypatch.setenv("EVE_DATA_GENERATION_DUCKDB_PATH", str(database))
    assert main(["load", "--config", str(CONFIG_DIR / "test.yaml"), "--dataset-dir", str(output)]) == 0
    assert database.exists()


def test_output_is_gitignored():
    text = (DATA_GENERATION_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "output/" in text
    example = (DATA_GENERATION_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "EVE_DATA_GENERATION_DUCKDB_PATH=" in example
    assert "secret" not in example.lower()
    assert not list(DATA_GENERATION_ROOT.joinpath("output").glob("*.jsonl"))
