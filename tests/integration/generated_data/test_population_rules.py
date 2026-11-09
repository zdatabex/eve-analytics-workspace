"""Negative checks for the DATA-005 journey inventory and new-business usage rules."""

from __future__ import annotations

from model import FORWARD_LOST, REGRESSION_STAGES, DatasetRun
from population import _new_business_specific, _scenarios


ENTITIES = (
    "hubspot.company",
    "hubspot.contact",
    "hubspot.lead",
    "hubspot.deal",
    "hubspot.activity",
    "dealhub.quote",
    "dealhub.contract",
    "dealhub.subscription",
    "dealhub.booking",
    "marketing.touch",
    "marketing.campaign",
    "marketing.campaign_performance",
    "product.firm",
    "product.user",
    "product.ai_workflow",
    "product.usage",
    "product.outcome",
)

NB_CODES = (
    "case_intake",
    "document_collection",
    "medical_record_review",
    "document_summarization",
    "demand_letter_generation",
    "settlement_preparation",
)

NB_OUTCOMES = {
    "document_summarization": "exported",
    "demand_letter_generation": "draft_completed",
    "settlement_preparation": "review_accepted",
}


def test_duplicate_workflow_usage_is_a_defect_and_skips_the_single_row_checks():
    defects = _usage_defects({"document_collection": 2}, units={"document_collection": 1}, outcomes={})
    assert [item.field for item in defects] == ["workflow_code"]
    assert defects[0].observation_key == "workflow_code=document_collection"
    assert defects[0].actual == "2"


def test_duplicate_outcome_workflow_does_not_check_outcome_on_those_rows():
    defects = _usage_defects(
        {"document_summarization": 2},
        outcomes={"document_summarization": "other"},
    )
    assert [item.field for item in defects] == ["workflow_code"]
    assert defects[0].observation_key == "workflow_code=document_summarization"
    assert defects[0].actual == "2"


def test_single_document_collection_must_use_the_configured_maximum():
    defects = _usage_defects({}, units={"document_collection": 1}, maximum=4)
    assert [item.field for item in defects] == ["work_unit_count"]
    assert defects[0].actual == "1"


def test_single_workflow_row_must_carry_the_required_outcome():
    defects = _usage_defects({}, outcomes={"document_summarization": "draft_completed"})
    assert [item.field for item in defects] == ["outcome_type"]
    assert defects[0].actual == "['draft_completed']"


def test_one_of_each_new_business_workflow_passes():
    assert _usage_defects({}) == []


def test_journey_inventory_counts_every_company_of_a_type():
    run, defects = _scenario(_journey_rows(extra_expansion=True))
    observed = {name: count for name, _expected, count in run.journeys}
    assert observed["expansion"] == "2"
    assert observed["new_business_conversion"] == "1"
    assert observed["domain twin"] == "1"
    assert [item.actual for item in defects if item.field == "expansion"] == ["2"]


def test_company_outside_the_journeys_and_domain_twin_is_a_defect():
    rows = _journey_rows()
    rows["hubspot.company"].append(_company("co-extra", "extra.example", "prospect"))
    _run, defects = _scenario(rows)
    outsiders = [item for item in defects if item.field == "hubspot_company_id"]
    assert [item.actual for item in outsiders] == ["co-extra"]
    assert outsiders[0].rule == "Every company is one of the seven journey companies or the domain twin."


def test_domain_twin_with_a_won_expansion_fails_merged_accounts():
    rows = _journey_rows()
    rows["hubspot.deal"].append(_won("x-twin", "co-twin", "expansion"))
    run, defects = _scenario(rows)
    assert dict(run.edges)["Merged accounts"] == "missing"
    merged = [item for item in defects if item.field == "primary_domain" and item.actual == "opportunity_won"]
    assert len(merged) == 1
    assert "has no won deal" in merged[0].rule


def test_domain_twin_without_a_won_deal_satisfies_merged_accounts():
    run, _defects = _scenario(_journey_rows())
    assert dict(run.edges)["Merged accounts"] == "present"
    assert {name: count for name, _expected, count in run.journeys} == {
        name: "1" for name in (
            "new_business_conversion",
            "expansion",
            "renewal",
            "churn",
            "lost_opportunity",
            "stage_regression",
            "low_adoption",
            "domain twin",
        )
    }


def _scenario(rows: dict[str, list[dict]]) -> tuple[DatasetRun, list]:
    run = _run(rows)
    defects = []
    _scenarios(run, defects, [])
    return run, defects


def _usage_defects(copies: dict[str, int], units: dict[str, int] | None = None, outcomes: dict[str, str] | None = None, maximum: int = 4) -> list:
    units = units or {}
    outcome_overrides = outcomes or {}
    workflows = []
    usages = []
    outcome_rows = []
    for code in NB_CODES:
        workflow_id = f"w-{code}"
        workflows.append({"product_workflow_id": workflow_id, "workflow_code": code})
        count = copies.get(code, 1)
        for index in range(count):
            usage_id = f"u-{code}-{index}"
            usages.append({
                "product_usage_source_id": usage_id,
                "product_firm_id": "firm-1",
                "product_workflow_id": workflow_id,
                "work_unit_count": units.get(code, maximum if code == "document_collection" else 1),
                "occurred_at": "2024-02-01T00:00:00Z",
            })
            if code not in NB_OUTCOMES and code not in outcome_overrides:
                continue
            outcome_rows.append({
                "product_outcome_source_id": f"o-{usage_id}",
                "product_usage_source_id": usage_id,
                "outcome_type": outcome_overrides.get(code, NB_OUTCOMES.get(code)),
            })
    rows = _blank_rows()
    rows["hubspot.company"] = [_company("co-nb", "nb.example", "customer")]
    rows["hubspot.deal"] = [_won("d-nb", "co-nb", "new_business")]
    rows["hubspot.activity"] = [
        _activity(activity_type) for activity_type in ("call", "email", "meeting")
    ]
    rows["product.firm"] = [{"product_firm_id": "firm-1", "primary_domain": "nb.example"}]
    rows["product.ai_workflow"] = workflows
    rows["product.usage"] = usages
    rows["product.outcome"] = outcome_rows
    run = _run(rows, {"integer_ranges": {"work_unit_count": {"min": 1, "max": maximum}}})
    deals = {}
    for row in rows["hubspot.deal"]:
        deals.setdefault(row["hubspot_deal_id"], []).append(row)
    by_company = {"co-nb": ["d-nb"]}
    defects = []
    _new_business_specific(
        run, defects, {"new_business_conversion": "co-nb"}, {}, deals, by_company,
        {workflow_id: code for code, workflow_id in ((row["workflow_code"], row["product_workflow_id"]) for row in workflows)},
        run.config,
    )
    return defects


def _journey_rows(extra_expansion: bool = False) -> dict[str, list[dict]]:
    rows = _blank_rows()
    companies = [
        _company("co-nb", "shared.example", "customer"),
        _company("co-twin", "shared.example", "sql"),
        _company("co-exp", "expansion.example", "customer"),
        _company("co-ren", "renewal.example", "customer"),
        _company("co-churn", "churn.example", "customer"),
        _company("co-low", "low.example", "customer"),
        _company("co-lost", "lost.example", "prospect"),
        _company("co-reg", "regression.example", "prospect"),
    ]
    deals = [
        _won("d-nb", "co-nb", "new_business"),
        _won("d-exp", "co-exp", "new_business"),
        _won("x-exp", "co-exp", "expansion"),
        _won("d-ren", "co-ren", "new_business"),
        _won("r-ren", "co-ren", "renewal"),
        _won("d-churn", "co-churn", "new_business"),
        _won("d-low", "co-low", "new_business"),
        *_stages("d-lost", "co-lost", FORWARD_LOST),
        *_stages("d-reg", "co-reg", REGRESSION_STAGES),
    ]
    if extra_expansion:
        companies.append(_company("co-exp-2", "expansion-2.example", "customer"))
        deals.extend([
            _won("d-exp-2", "co-exp-2", "new_business"),
            _won("x-exp-2", "co-exp-2", "expansion"),
        ])
    rows["hubspot.company"] = companies
    rows["hubspot.deal"] = deals
    rows["dealhub.contract"] = [{
        "dealhub_contract_id": "c-churn",
        "hubspot_deal_id": "d-churn",
        "observed_at": "2024-06-01T00:00:00Z",
        "status": "active",
    }]
    rows["dealhub.subscription"] = [{
        "dealhub_subscription_id": "s-churn",
        "dealhub_contract_id": "c-churn",
        "status": "churned",
        "emitted_event": None,
        "observed_at": "2024-06-02T00:00:00Z",
    }]
    rows["product.firm"] = [{"product_firm_id": "firm-nb", "primary_domain": "shared.example"}]
    return rows


def _run(rows: dict[str, list[dict]], config: dict | None = None) -> DatasetRun:
    return DatasetRun(
        path="data-generation/config/scenarios.yaml",
        population="scenario",
        expected_seed=1,
        load_schema="dev_data_004",
        generate_command=(
            "python3 -m eve_data_generation generate "
            "--config data-generation/config/scenarios.yaml --output <temp directory>"
        ),
        config=config or {},
        seed="1",
        rows=rows,
        generated=True,
    )


def _blank_rows() -> dict[str, list[dict]]:
    return {entity: [] for entity in ENTITIES}


def _company(company_id: str, domain: str, stage: str) -> dict:
    return {
        "hubspot_company_id": company_id,
        "primary_domain": domain,
        "hubspot_lifecycle_stage": stage,
        "observed_at": "2024-06-01T00:00:00Z",
    }


def _won(deal_id: str, company_id: str, opportunity_type: str) -> dict:
    return {
        "hubspot_deal_id": deal_id,
        "hubspot_company_id": company_id,
        "emitted_event": "opportunity_won",
        "opportunity_type": opportunity_type,
        "stage": "closed_won",
        "observed_at": "2024-06-01T00:00:00Z",
        "created_at": "2024-01-02T00:00:00Z",
    }


def _stages(deal_id: str, company_id: str, stages: tuple[str, ...]) -> list[dict]:
    rows = []
    for index, stage in enumerate(stages, start=1):
        rows.append({
            "hubspot_deal_id": deal_id,
            "hubspot_company_id": company_id,
            "stage": stage,
            "emitted_event": "opportunity_lost" if stage == "closed_lost" else "opportunity_stage_changed",
            "observed_at": f"2024-01-{index:02d}T00:00:00Z",
        })
    return rows


def _activity(activity_type: str) -> dict:
    return {
        "activity_type": activity_type,
        "hubspot_company_id": "co-nb",
        "hubspot_deal_id": "d-nb",
        "occurred_at": "2024-02-01T00:00:00Z",
    }
