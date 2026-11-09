"""Component tests for named GTM lifecycle scenarios."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

import duckdb
import pytest
import yaml

from eve_data_generation.cli import main
from eve_data_generation.config import JOURNEY_NAMES, config_from_mapping, load_config
from eve_data_generation.contracts import load_contracts
from eve_data_generation.dataset import build_dataset
from eve_data_generation.errors import GenerationError
from eve_data_generation.loader import load_dataset
from eve_data_generation.paths import CONFIG_DIR
from eve_data_generation.sampling import WINDOW_ERROR, inclusive_dates
from eve_data_generation.writer import write_dataset

CUSTOMER = (
    "new_business_conversion",
    "expansion",
    "renewal",
    "churn",
    "low_adoption",
)
WORKFLOWS = (
    ("case_intake", "Case intake"),
    ("document_collection", "Document collection"),
    ("medical_record_review", "Medical record review"),
    ("document_summarization", "Document summarization"),
    ("demand_letter_generation", "Demand letter generation"),
    ("case_analysis", "Case analysis"),
    ("settlement_preparation", "Settlement preparation"),
)
CONVERTING = (
    ("new", "lead_created"),
    ("working", None),
    ("qualified", "lead_qualified"),
    ("converted", "lead_converted"),
)
FORWARD = ("discovery", "evaluation", "proposal", "negotiation")
FORBIDDEN = {
    "commercial_status",
    "customer_converted",
    "adoption_reached",
    "is_deleted",
    "effective_start",
    "effective_end",
    "is_current",
    "arr",
    "annual_recurring_revenue",
    "annualized_arr",
}


@pytest.fixture(scope="module")
def scenario_config():
    return load_config(CONFIG_DIR / "scenarios-test.yaml")


@pytest.fixture(scope="module")
def scenario_dataset(scenario_config):
    return build_dataset(scenario_config)


def _domain(journey: str, instance: int = 1) -> str:
    slug = journey.replace("_", "-")
    if instance == 1:
        return f"{slug}.example"
    return f"{slug}-{instance}.example"


def _grouped(rows, field):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[field]].append(row)
    for items in grouped.values():
        if "observed_at" in items[0]:
            items.sort(key=lambda item: item["observed_at"])
    return grouped


def _company_ids(dataset, domain):
    return {
        row["hubspot_company_id"]
        for row in dataset.rows["hubspot.company"]
        if row["primary_domain"] == domain
    }


def _won_company(dataset, domain):
    ids = _company_ids(dataset, domain)
    winners = {
        row["hubspot_company_id"]
        for row in dataset.rows["hubspot.deal"]
        if row["hubspot_company_id"] in ids
        and row["opportunity_type"] == "new_business"
        and row["emitted_event"] == "opportunity_won"
    }
    assert len(winners) == 1
    return next(iter(winners))


def _only_company(dataset, domain):
    ids = _company_ids(dataset, domain)
    assert len(ids) == 1
    return next(iter(ids))


def _deals(dataset, company_id):
    grouped = _grouped(dataset.rows["hubspot.deal"], "hubspot_deal_id")
    return {
        deal_id: rows
        for deal_id, rows in grouped.items()
        if rows[0]["hubspot_company_id"] == company_id
    }


def _deal(deals, opportunity_type):
    matches = [rows for rows in deals.values() if rows[-1]["opportunity_type"] == opportunity_type]
    assert len(matches) == 1
    return matches[0]


def _quotes(dataset, deal_id):
    grouped = _grouped(dataset.rows["dealhub.quote"], "dealhub_quote_id")
    matches = [rows for rows in grouped.values() if rows[0]["hubspot_deal_id"] == deal_id]
    assert len(matches) == 1
    return matches[0]


def _subscription(dataset, company_id):
    grouped = _grouped(dataset.rows["dealhub.subscription"], "dealhub_subscription_id")
    matches = [rows for rows in grouped.values() if rows[0]["hubspot_company_id"] == company_id]
    assert len(matches) == 1
    return matches[0]


def _contract(dataset, company_id):
    grouped = _grouped(dataset.rows["dealhub.contract"], "dealhub_contract_id")
    matches = [rows for rows in grouped.values() if rows[0]["hubspot_company_id"] == company_id]
    assert len(matches) == 1
    return matches[0]


def _firm(dataset, domain):
    matches = [row for row in dataset.rows["product.firm"] if row["primary_domain"] == domain]
    assert len(matches) == 1
    return matches[0]


def test_scenario_files_carry_the_catalog():
    development = load_config(CONFIG_DIR / "scenarios.yaml")
    tested = load_config(CONFIG_DIR / "scenarios-test.yaml")
    assert development.seed == 1004
    assert development.start_date.isoformat() == "2024-01-01"
    assert development.end_date.isoformat() == "2025-07-01"
    assert tested.seed == 4004
    development_span = (development.end_date - development.start_date).days
    tested_span = (tested.end_date - tested.start_date).days
    assert tested_span > 180
    assert tested_span < development_span
    for config in (development, tested):
        assert config.journeys == {name: 1 for name in JOURNEY_NAMES}
        assert [(entry.code, entry.name) for entry in config.workflows] == list(WORKFLOWS)
        assert config.schema == "dev_data_004"
        assert config.ingest_lag_days == 1
        assert config.late_event_count == 1
        assert config.expansion_seat_increase == 1
        assert config.expansion_recurring_increase == Decimal("10.00")
        assert config.contract_value_increase == Decimal("100.00")
        assert config.term_days == 180
        assert "prospect" in config.lifecycle_stage_catalog
        assert "customer" in config.lifecycle_stage_catalog
        assert "former_customer" in config.lifecycle_stage_catalog
        assert "sql" in config.lifecycle_stage_catalog
    bounds = tested.integer_ranges["work_unit_count"]
    assert bounds.minimum >= 1
    assert bounds.maximum >= 2
    assert bounds.maximum > bounds.minimum
    for name in ("default.yaml", "test.yaml"):
        payload = yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))
        assert "journeys" not in payload
        assert "schema" not in payload


def test_baseline_command_still_uses_the_baseline_sampler():
    config = load_config(CONFIG_DIR / "test.yaml")
    dataset = build_dataset(config)
    companies = {row["hubspot_company_id"] for row in dataset.rows["hubspot.company"]}
    assert len(companies) == config.account_count


def test_journey_counts_not_the_retained_volume_keys(scenario_config, scenario_dataset):
    dataset = scenario_dataset
    companies = {row["hubspot_company_id"] for row in dataset.rows["hubspot.company"]}
    assert len(companies) == sum(scenario_config.journeys.values()) + scenario_config.journeys["new_business_conversion"]
    assert len(companies) != scenario_config.account_count
    assert len(dataset.rows["marketing.campaign"]) == 1
    assert len(dataset.rows["marketing.campaign"]) != scenario_config.campaign_count
    assert len(dataset.rows["hubspot.activity"]) == 3
    assert len(dataset.rows["hubspot.activity"]) != scenario_config.activity_count
    days = len(inclusive_dates(scenario_config.start_date, scenario_config.end_date))
    assert len(dataset.rows["marketing.campaign_performance"]) == days
    payload = yaml.safe_load((CONFIG_DIR / "scenarios-test.yaml").read_text(encoding="utf-8"))
    payload["expansion_rate"] = 0
    payload["renewal_rate"] = 0
    payload["churn_rate"] = 0
    payload["account_count"] = 2
    altered = build_dataset(config_from_mapping(payload, "scenarios-test.yaml"))
    assert len({row["hubspot_company_id"] for row in altered.rows["hubspot.company"]}) == len(companies)


def test_each_journey_matches_its_sequence(scenario_config, scenario_dataset):
    dataset = scenario_dataset
    leads = _grouped(dataset.rows["hubspot.lead"], "hubspot_lead_id")
    for journey in JOURNEY_NAMES:
        if journey == "new_business_conversion":
            company_id = _won_company(dataset, _domain(journey))
        else:
            company_id = _only_company(dataset, _domain(journey))
        company_rows = _grouped(dataset.rows["hubspot.company"], "hubspot_company_id")[company_id]
        deals = _deals(dataset, company_id)
        new_business = _deal(deals, "new_business")
        lead_rows = leads[new_business[0]["hubspot_lead_id"]]
        assert [(row["status"], row["emitted_event"]) for row in lead_rows] == list(CONVERTING)
        assert lead_rows[0]["observed_at"] == lead_rows[0]["created_at"]
        assert all(row["created_at"] == lead_rows[0]["created_at"] for row in lead_rows)
        converted = lead_rows[-1]
        assert converted["hubspot_deal_id"] == new_business[0]["hubspot_deal_id"]
        assert all(row["hubspot_deal_id"] is None for row in lead_rows[:-1])
        assert new_business[0]["observed_at"] == converted["observed_at"]
        assert new_business[0]["created_at"] == converted["observed_at"]
        assert new_business[0]["stage"] == "discovery"
        assert new_business[0]["emitted_event"] == "opportunity_opened"
        assert all(row["hubspot_lead_id"] == converted["hubspot_lead_id"] for row in new_business)
        assert all(row["hubspot_company_id"] == company_id for row in new_business)
        touches = [
            row
            for row in dataset.rows["marketing.touch"]
            if row["hubspot_company_id"] == company_id
        ]
        assert touches
        assert all(row["hubspot_lead_id"] is None for row in touches)
        assert min(row["occurred_at"] for row in touches) <= lead_rows[0]["created_at"]
        quotes = _quotes(dataset, new_business[0]["hubspot_deal_id"])
        if journey in CUSTOMER:
            assert [row["stage"] for row in new_business] == [*FORWARD, "closed_won"]
            assert [row["status"] for row in quotes] == ["draft", "sent", "accepted"]
            assert company_rows[0]["hubspot_lifecycle_stage"] == "prospect"
            win = next(row for row in new_business if row["emitted_event"] == "opportunity_won")
            assert any(
                row["hubspot_lifecycle_stage"] == "customer" and row["observed_at"] >= win["observed_at"]
                for row in company_rows
            )
            assert quotes[-1]["observed_at"] <= win["observed_at"]
            assert quotes[-1]["quoted_amount"] is not None
            assert quotes[0]["quoted_amount"] is None
            contract = _contract(dataset, company_id)
            assert contract[0]["observed_at"] >= win["observed_at"]
            assert contract[0]["status"] == "active"
            assert contract[0]["dealhub_quote_id"] == quotes[0]["dealhub_quote_id"]
            assert contract[0]["hubspot_deal_id"] == new_business[0]["hubspot_deal_id"]
            subscription = _subscription(dataset, company_id)
            assert subscription[0]["status"] == "pending" and subscription[0]["emitted_event"] is None
            assert subscription[1]["status"] == "active" and subscription[1]["emitted_event"] is None
            assert subscription[0]["term_end"] >= subscription[0]["term_start"]
            firm = _firm(dataset, _domain(journey))
            assert firm["primary_domain"] == _domain(journey)
            bookings = [
                row
                for row in dataset.rows["dealhub.booking"]
                if row["hubspot_deal_id"] == new_business[0]["hubspot_deal_id"]
            ]
            assert len(bookings) == 1
            assert bookings[0]["booking_type"] == "new_business"
            assert bookings[0]["booked_at"] >= win["observed_at"]
            assert bookings[0]["dealhub_contract_id"] == contract[0]["dealhub_contract_id"]
            assert bookings[0]["dealhub_subscription_id"] == subscription[0]["dealhub_subscription_id"]
            assert {row["amount"] for row in new_business} == {new_business[0]["amount"]}
            assert len({
                new_business[0]["amount"],
                quotes[-1]["quoted_amount"],
                contract[0]["total_contract_value"],
                bookings[0]["booking_amount"],
                subscription[0]["recurring_amount"],
            }) == 5
            assert new_business[0]["expected_close_date"] != contract[0]["start_date"]
            assert subscription[0]["seat_count"] != len({
                row["product_user_source_id"]
                for row in dataset.rows["product.user"]
                if row["product_firm_id"] == firm["product_firm_id"]
            })
        elif journey == "lost_opportunity":
            assert [row["stage"] for row in new_business] == [*FORWARD, "closed_lost"]
            assert [row["status"] for row in quotes] == ["draft", "sent", "rejected"]
            lost = next(row for row in new_business if row["emitted_event"] == "opportunity_lost")
            assert quotes[-1]["observed_at"] <= lost["observed_at"]
            assert _absent(dataset, company_id, _domain(journey))
        else:
            assert [row["stage"] for row in new_business] == [
                "discovery",
                "evaluation",
                "proposal",
                "evaluation",
                "negotiation",
            ]
            assert [row["emitted_event"] for row in new_business] == [
                "opportunity_opened",
                *["opportunity_stage_changed"] * 4,
            ]
            assert [row["status"] for row in quotes] == ["draft", "sent", "expired"]
            proposal = next(row["observed_at"] for row in new_business if row["stage"] == "proposal")
            returned = [row["observed_at"] for row in new_business if row["stage"] == "evaluation"][1]
            expired = next(row for row in quotes if row["status"] == "expired")
            assert proposal < expired["observed_at"] < returned
            assert _absent(dataset, company_id, _domain(journey))
        events = {row["emitted_event"] for row in new_business}
        assert not ({"opportunity_won", "opportunity_lost"} <= events)
        assert len([row for row in new_business if row["emitted_event"] == "opportunity_stage_changed"]) == (
            4 if journey == "stage_regression" else 3
        )


def _absent(dataset, company_id, domain) -> bool:
    assert not any(row["hubspot_company_id"] == company_id for row in dataset.rows["dealhub.contract"])
    assert not any(row["hubspot_company_id"] == company_id for row in dataset.rows["dealhub.subscription"])
    assert not any(row["hubspot_company_id"] == company_id for row in dataset.rows["dealhub.booking"])
    assert not any(row["primary_domain"] == domain for row in dataset.rows["product.firm"])
    return True


def test_expansion_renewal_and_churn(scenario_config, scenario_dataset):
    dataset = scenario_dataset
    expansion_id = _only_company(dataset, _domain("expansion"))
    expansion_deals = _deals(dataset, expansion_id)
    expansion = _deal(expansion_deals, "expansion")
    assert [row["stage"] for row in expansion] == [*FORWARD, "closed_won"]
    assert all(row["dealhub_subscription_id"] for row in expansion)
    assert all(row["hubspot_lead_id"] is None for row in expansion)
    expansion_win = next(row for row in expansion if row["emitted_event"] == "opportunity_won")
    assert not any(row["hubspot_deal_id"] == expansion[0]["hubspot_deal_id"] for row in dataset.rows["dealhub.contract"])
    subscription = _subscription(dataset, expansion_id)
    expanded = next(row for row in subscription if row["emitted_event"] == "subscription_expanded")
    previous = subscription[subscription.index(expanded) - 1]
    assert expanded["status"] == "active"
    assert expanded["seat_count"] == previous["seat_count"] + scenario_config.expansion_seat_increase
    assert expanded["recurring_amount"] == previous["recurring_amount"] + scenario_config.expansion_recurring_increase
    assert expanded["plan_code"] == previous["plan_code"]
    assert expanded["billing_frequency"] == previous["billing_frequency"]
    assert subscription[-1]["status"] == "active"
    assert not any(row["emitted_event"] == "subscription_churned" for row in subscription)
    contract = _contract(dataset, expansion_id)
    assert contract[-1]["total_contract_value"] == contract[0]["total_contract_value"] + scenario_config.contract_value_increase
    assert contract[-1]["contract_number"] == contract[0]["contract_number"]
    assert contract[-1]["dealhub_contract_id"] == contract[0]["dealhub_contract_id"]
    expansion_bookings = [
        row for row in dataset.rows["dealhub.booking"] if row["hubspot_deal_id"] == expansion[0]["hubspot_deal_id"]
    ]
    assert len(expansion_bookings) == 1
    assert expansion_bookings[0]["booking_type"] == "expansion"
    assert expansion_bookings[0]["booked_at"] >= expansion_win["observed_at"]
    assert expansion_bookings[0]["dealhub_contract_id"] == contract[0]["dealhub_contract_id"]

    renewal_id = _only_company(dataset, _domain("renewal"))
    renewal = _deal(_deals(dataset, renewal_id), "renewal")
    renewal_win = next(row for row in renewal if row["emitted_event"] == "opportunity_won")
    assert not any(row["hubspot_deal_id"] == renewal[0]["hubspot_deal_id"] for row in dataset.rows["dealhub.contract"])
    renewed_sub = _subscription(dataset, renewal_id)
    renewed = next(row for row in renewed_sub if row["emitted_event"] == "subscription_renewed")
    before = renewed_sub[renewed_sub.index(renewed) - 1]
    assert renewed["term_end"] == before["term_end"] + timedelta(days=scenario_config.term_days)
    assert renewed["seat_count"] == before["seat_count"]
    assert renewed["recurring_amount"] == before["recurring_amount"]
    assert renewed_sub[-1]["status"] == "active"
    renewed_contract = _contract(dataset, renewal_id)
    assert renewed_contract[-1]["end_date"] == renewed_contract[0]["end_date"] + timedelta(days=scenario_config.term_days)
    assert renewed_contract[-1]["end_date"] >= renewed_contract[-1]["start_date"]
    assert renewed_contract[-1]["total_contract_value"] == renewed_contract[0]["total_contract_value"]
    assert renewed_contract[-1]["contract_number"] == renewed_contract[0]["contract_number"]
    renewal_bookings = [
        row for row in dataset.rows["dealhub.booking"] if row["hubspot_deal_id"] == renewal[0]["hubspot_deal_id"]
    ]
    assert len(renewal_bookings) == 1
    assert renewal_bookings[0]["booking_type"] == "renewal"
    assert renewal_bookings[0]["booked_at"] >= renewal_win["observed_at"]

    churn_id = _only_company(dataset, _domain("churn"))
    churned = _subscription(dataset, churn_id)
    churn = next(row for row in churned if row["emitted_event"] == "subscription_churned")
    assert churn["status"] == "churned"
    assert churned[-1]["emitted_event"] == "subscription_churned"
    assert not any(
        row["dealhub_subscription_id"] == churn["dealhub_subscription_id"] and row["booked_at"] >= churn["observed_at"]
        for row in dataset.rows["dealhub.booking"]
    )
    terminated = _contract(dataset, churn_id)
    assert terminated[-1]["status"] == "terminated"
    assert terminated[-1]["observed_at"] >= churn["observed_at"]
    company_rows = _grouped(dataset.rows["hubspot.company"], "hubspot_company_id")[churn_id]
    assert any(
        row["hubspot_lifecycle_stage"] == "former_customer" and row["observed_at"] >= churn["observed_at"]
        for row in company_rows
    )
    active = next(row for row in churned if row["status"] == "active" and row["emitted_event"] is None)
    firm = _firm(dataset, _domain("churn"))
    usages = sorted(
        (row for row in dataset.rows["product.usage"] if row["product_firm_id"] == firm["product_firm_id"]),
        key=lambda row: row["occurred_at"],
    )
    assert len(usages) == 2
    assert usages[0]["work_unit_count"] == scenario_config.integer_ranges["work_unit_count"].maximum
    assert usages[1]["work_unit_count"] == scenario_config.integer_ranges["work_unit_count"].minimum
    assert usages[0]["work_unit_count"] > usages[1]["work_unit_count"]
    assert active["observed_at"] < usages[0]["occurred_at"] < usages[1]["occurred_at"] < churn["observed_at"]
    assert not any(row["product_firm_id"] == firm["product_firm_id"] for row in dataset.rows["product.outcome"])
    users = _grouped(dataset.rows["product.user"], "product_user_source_id")
    churn_users = [rows for rows in users.values() if rows[0]["product_firm_id"] == firm["product_firm_id"]]
    assert len(churn_users) == 1
    assert [row["status"] for row in churn_users[0]] == ["active", "inactive"]
    assert churn_users[0][-1]["observed_at"] > usages[1]["occurred_at"]


def test_product_adoption_and_activities(scenario_dataset):
    dataset = scenario_dataset
    workflows = {row["product_workflow_id"]: row["workflow_code"] for row in dataset.rows["product.ai_workflow"]}
    assert set(workflows.values()) == {code for code, _name in WORKFLOWS}
    company_id = _won_company(dataset, _domain("new_business_conversion"))
    firm = _firm(dataset, _domain("new_business_conversion"))
    usages = [
        row for row in dataset.rows["product.usage"] if row["product_firm_id"] == firm["product_firm_id"]
    ]
    outcomes = [
        row for row in dataset.rows["product.outcome"] if row["product_firm_id"] == firm["product_firm_id"]
    ]
    by_code = {workflows[row["product_workflow_id"]]: row for row in usages}
    assert set(by_code) == {code for code, _outcome in (
        ("case_intake", None),
        ("document_collection", None),
        ("medical_record_review", None),
        ("document_summarization", "exported"),
        ("demand_letter_generation", "draft_completed"),
        ("settlement_preparation", "review_accepted"),
    )}
    assert "case_analysis" not in by_code
    config = load_config(CONFIG_DIR / "scenarios-test.yaml")
    assert by_code["document_collection"]["work_unit_count"] == config.integer_ranges["work_unit_count"].maximum
    outcome_by_usage = {row["product_usage_source_id"]: row for row in outcomes}
    assert by_code["case_intake"]["product_usage_source_id"] not in outcome_by_usage
    assert outcome_by_usage[by_code["document_summarization"]["product_usage_source_id"]]["outcome_type"] == "exported"
    assert outcome_by_usage[by_code["demand_letter_generation"]["product_usage_source_id"]]["outcome_type"] == "draft_completed"
    assert outcome_by_usage[by_code["settlement_preparation"]["product_usage_source_id"]]["outcome_type"] == "review_accepted"
    win = next(
        row["observed_at"]
        for row in dataset.rows["hubspot.deal"]
        if row["hubspot_company_id"] == company_id and row["emitted_event"] == "opportunity_won"
    )
    users = [
        row
        for row in dataset.rows["product.user"]
        if row["product_firm_id"] == firm["product_firm_id"]
    ]
    assert users
    assert min(row["observed_at"] for row in users) <= min(row["occurred_at"] for row in usages)
    assert all(row["occurred_at"] >= win for row in usages)
    deal = _deal(_deals(dataset, company_id), "new_business")
    activities = [
        row for row in dataset.rows["hubspot.activity"] if row["hubspot_deal_id"] == deal[0]["hubspot_deal_id"]
    ]
    assert sorted(row["activity_type"] for row in activities) == ["call", "email", "meeting"]
    assert all(row["hubspot_company_id"] == company_id for row in activities)
    assert all(deal[0]["created_at"] < row["occurred_at"] <= deal[-1]["observed_at"] for row in activities)
    low_firm = _firm(dataset, _domain("low_adoption"))
    low_usage = [row for row in dataset.rows["product.usage"] if row["product_firm_id"] == low_firm["product_firm_id"]]
    assert len(low_usage) == 1
    assert workflows[low_usage[0]["product_workflow_id"]] == "case_analysis"
    assert not any(row["product_firm_id"] == low_firm["product_firm_id"] for row in dataset.rows["product.outcome"])
    low_company = _only_company(dataset, _domain("low_adoption"))
    low_deals = _deals(dataset, low_company)
    assert set(rows[-1]["opportunity_type"] for rows in low_deals.values()) == {"new_business"}
    assert _subscription(dataset, low_company)[-1]["status"] == "active"
    assert {row["outcome_type"] for row in dataset.rows["product.outcome"]} == {
        "draft_completed",
        "review_accepted",
        "exported",
    }
    assert any(row["work_unit_count"] > 1 for row in dataset.rows["product.usage"])
    contacts = [
        row for row in dataset.rows["hubspot.contact"] if row["hubspot_company_id"] == company_id
    ]
    assert len({row["hubspot_contact_id"] for row in contacts}) == 2
    assert len({row["email_normalized"] for row in contacts}) == 1
    assert contacts[0]["email_normalized"]


def test_edge_cases_and_source_shape(scenario_config, scenario_dataset):
    dataset = scenario_dataset
    domain = _domain("new_business_conversion")
    ids = _company_ids(dataset, domain)
    assert len(ids) == 2
    journey_id = _won_company(dataset, domain)
    twin_id = next(iter(ids - {journey_id}))
    twin_rows = _grouped(dataset.rows["hubspot.company"], "hubspot_company_id")[twin_id]
    assert len(twin_rows) == 1
    assert twin_rows[0]["hubspot_lifecycle_stage"] == "sql"
    assert not any(
        row["hubspot_company_id"] == twin_id and row["emitted_event"] == "opportunity_won"
        for row in dataset.rows["hubspot.deal"]
    )
    twin_leads = [
        rows
        for rows in _grouped(dataset.rows["hubspot.lead"], "hubspot_lead_id").values()
        if rows[0]["hubspot_company_id"] == twin_id
    ]
    assert len(twin_leads) == 1
    assert [(row["status"], row["emitted_event"]) for row in twin_leads[0]] == [
        ("new", "lead_created"),
        ("disqualified", "lead_disqualified"),
    ]
    assert all(row["hubspot_deal_id"] is None for row in twin_leads[0])
    firm = _firm(dataset, domain)
    assert firm["primary_domain"] == domain
    contracts = load_contracts()
    for contract in contracts.values():
        if "observed_at" not in contract.observation_key:
            continue
        identifier = contract.observation_key[0]
        for rows in _grouped(dataset.rows[contract.id], identifier).values():
            stamps = [row["observed_at"] for row in rows]
            assert stamps == sorted(set(stamps))
    late = []
    for rows in dataset.rows.values():
        for row in rows:
            business = _business_timestamp(row)
            if business is None:
                continue
            if row["ingested_at"] != business:
                assert row["ingested_at"] == business + timedelta(days=scenario_config.ingest_lag_days)
                late.append(row)
    assert len(late) == scenario_config.late_event_count
    for row in dataset.rows["hubspot.deal"]:
        assert row["forecast_category"] == scenario_config.forecast_by_stage[row["stage"]]
    for rows in dataset.rows.values():
        for row in rows:
            assert not set(row) & FORBIDDEN
            assert not any(name.startswith("surviving_") for name in row)
    assert dataset.delivery_id == f"dlv_{scenario_config.seed}"
    for row in dataset.rows["dealhub.booking"]:
        assert "recurring_amount" not in row
        assert "billing_frequency" not in row
    for row in dataset.rows["dealhub.subscription"]:
        assert "booking_amount" not in row
        assert "booking_type" not in row


def _business_timestamp(row):
    for name in ("observed_at", "occurred_at", "booked_at"):
        if isinstance(row.get(name), datetime):
            return row[name]
    if isinstance(row.get("performance_date"), datetime):
        return None
    performance_date = row.get("performance_date")
    if performance_date is not None and not isinstance(performance_date, datetime):
        return datetime.combine(performance_date, time.min)
    return None


def test_timestamps_are_reproducible_and_the_manifest_has_no_clock(scenario_config, tmp_path):
    contracts = load_contracts()
    first = tmp_path / "one"
    second = tmp_path / "two"
    write_dataset(build_dataset(scenario_config), contracts, first)
    write_dataset(build_dataset(scenario_config), contracts, second)
    files = sorted(path.name for path in first.iterdir())
    assert files == sorted(path.name for path in second.iterdir())
    for name in files:
        assert (first / name).read_bytes() == (second / name).read_bytes()
    manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest) == {
        "configuration_file",
        "delivery_id",
        "end_date",
        "entities",
        "seed",
        "start_date",
    }
    assert "T" not in manifest["start_date"]
    assert manifest["delivery_id"] == "dlv_4004"


def test_short_window_uses_the_date_range_error():
    payload = yaml.safe_load((CONFIG_DIR / "scenarios-test.yaml").read_text(encoding="utf-8"))
    payload["end_date"] = "2024-01-20"
    config = config_from_mapping(payload, "scenarios-test.yaml")
    with pytest.raises(GenerationError, match=WINDOW_ERROR):
        build_dataset(config)


def test_scenario_load_uses_dev_data_004(scenario_config, scenario_dataset, tmp_path):
    directory = tmp_path / "dataset"
    contracts = load_contracts()
    write_dataset(scenario_dataset, contracts, directory)
    database = tmp_path / "warehouse" / "scenarios.duckdb"
    load_dataset(directory, database, scenario_config.schema)
    load_dataset(directory, database, scenario_config.schema)
    connection = duckdb.connect(str(database))
    schemas = {row[0] for row in connection.execute("SELECT schema_name FROM information_schema.schemata").fetchall()}
    assert "dev_data_004" in schemas
    assert "dev_data_003" not in schemas
    catalog = connection.execute("SELECT current_catalog()").fetchone()[0]
    table = f'"{catalog}"."dev_data_004"."src_hubspot_company"'
    count = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    assert count == len(scenario_dataset.rows["hubspot.company"])
    connection.execute(f"DELETE FROM {table}")
    connection.close()
    load_dataset(directory, database, scenario_config.schema)
    connection = duckdb.connect(str(database))
    restored = connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    connection.close()
    assert restored == count


def test_cli_generate_and_load_scenario_schema(tmp_path, monkeypatch):
    output = tmp_path / "generated"
    database = tmp_path / "cli.duckdb"
    config = str(CONFIG_DIR / "scenarios-test.yaml")
    assert main(["generate", "--config", config, "--output", str(output)]) == 0
    assert (output / "manifest.json").exists()
    monkeypatch.setenv("EVE_DATA_GENERATION_DUCKDB_PATH", str(database))
    assert main(["load", "--config", config, "--dataset-dir", str(output)]) == 0
    connection = duckdb.connect(str(database))
    schemas = {row[0] for row in connection.execute("SELECT schema_name FROM information_schema.schemata").fetchall()}
    connection.close()
    assert "dev_data_004" in schemas
    assert "dev_data_003" not in schemas


def test_development_scenario_generates():
    dataset = build_dataset(load_config(CONFIG_DIR / "scenarios.yaml"))
    assert dataset.delivery_id == "dlv_1004"
    assert {row["primary_domain"] for row in dataset.rows["product.firm"]}
