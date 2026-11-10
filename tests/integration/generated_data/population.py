"""Baseline distributions, edge cases, and scenario journey checks."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from model import (
    CANONICAL_STAGES,
    CONVERTING_LEAD,
    CUSTOMER_JOURNEYS,
    DEAL_EVENTS,
    FORWARD_LOST,
    FORWARD_WON,
    JOURNEYS,
    LEAD_EVENTS,
    NB_USAGE,
    REGRESSION_STAGES,
    SUBSCRIPTION_EVENTS,
    DatasetRun,
    Defect,
    add_defect,
    allocate,
    as_date,
    as_decimal,
    format_number,
    group_rows,
    latest,
    parse_date,
    parse_timestamp,
    share_count,
)


def check_population(run: DatasetRun, defects: list[Defect], recommendations: list[tuple[str, str]]) -> None:
    if not run.generated or not run.config:
        _blank_edges(run)
        return
    if run.population == "baseline":
        _baseline(run, defects, recommendations)
        return
    _scenarios(run, defects, recommendations)


def _blank_edges(run: DatasetRun) -> None:
    if run.population == "baseline":
        run.edges = [(name, "missing") for name in BASELINE_EDGE_NAMES]
    else:
        run.edges = [(name, "missing") for name in SCENARIO_EDGE_NAMES]
        run.journeys = [(name, "1", "0") for name in (*JOURNEYS, "domain twin")]


BASELINE_EDGE_NAMES = (
    "company with a null primary_domain",
    "two contacts with the same email and different contact ids",
    "lead with a null company and a null contact",
    "deal with a null amount",
    "activity with exactly one parent",
    "activity with a null deal and activity that cites a deal",
    "campaign-day row with a null spend_amount",
    "campaign-day row whose clicks exceed impressions",
    "one product firm domain matching a company and one that does not",
    "product user with a null email",
    "active subscription renewal or expansion",
    "churned subscription with no booking at or after churn",
    "lifecycle stage outside prospect, customer, and former_customer",
    "two observations of one company",
)

SCENARIO_EDGE_NAMES = (
    "Duplicate contacts",
    "Merged accounts",
    "Repeated stage changes",
    "Late-arriving events",
    "Contract amendments",
    "Canceled subscriptions",
    "Soft-deleted records",
    "Low or declining adoption",
)


def _baseline(run: DatasetRun, defects: list[Defect], recommendations: list[tuple[str, str]]) -> None:
    config = run.config
    companies = group_rows(run.rows["hubspot.company"], "hubspot_company_id")
    contacts = group_rows(run.rows["hubspot.contact"], "hubspot_contact_id")
    leads = group_rows(run.rows["hubspot.lead"], "hubspot_lead_id")
    deals = group_rows(run.rows["hubspot.deal"], "hubspot_deal_id")
    subscriptions = group_rows(run.rows["dealhub.subscription"], "dealhub_subscription_id")
    firms = run.rows["product.firm"]
    users = group_rows(run.rows["product.user"], "product_user_source_id")
    activities = run.rows["hubspot.activity"]
    touches = run.rows["marketing.touch"]
    campaigns = run.rows["marketing.campaign"]
    days = run.rows["marketing.campaign_performance"]
    usages = run.rows["product.usage"]
    outcomes = run.rows["product.outcome"]
    new_business = {
        deal_id: rows for deal_id, rows in deals.items()
        if rows and rows[0].get("opportunity_type") == "new_business"
    }
    won_companies = set()
    for rows in new_business.values():
        wins = [row for row in rows if row.get("emitted_event") == "opportunity_won" and row.get("opportunity_type") == "new_business"]
        if wins:
            won_companies.add(wins[0].get("hubspot_company_id"))
    inclusive = (as_date(config["end_date"]) - as_date(config["start_date"])).days + 1
    counts = [
        ("HubSpot companies", config["account_count"], len(companies)),
        ("Contacts", config["account_count"] * config["contacts_per_account"], len(contacts)),
        ("Leads", config["lead_count"], len(leads)),
        ("Campaigns", config["campaign_count"], len(campaigns)),
        ("Activities", config["activity_count"], len(activities)),
        ("Touches", config["touch_count"], len(touches)),
        ("Product firms", len(won_companies), len(firms)),
        ("Product users", len(won_companies) * config["product_users_per_customer"], len(users)),
        ("Usage rows", len(won_companies) * config["product_users_per_customer"] * config["usage_events_per_user"], len(usages)),
        ("Campaign-day rows", config["campaign_count"] * inclusive, len(days)),
    ]
    for label, expected, observed in counts:
        if expected != observed:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                f"The observed {label} count equals the committed configuration target.",
                field=label, actual=f"expected={expected} observed={observed}",
            )
    lead_weights = {str(key): int(value) for key, value in config["lead_status_mix"].items()}
    stage_weights = {str(key): int(value) for key, value in config["stage_mix"].items()}
    channel_weights = {str(key): int(value) for key, value in config["channel_mix"].items()}
    lead_alloc = allocate(int(config["lead_count"]), lead_weights)
    converted = lead_alloc.get("converted", 0)
    stage_alloc = allocate(converted, stage_weights)
    channel_alloc = allocate(int(config["campaign_count"]), channel_weights)
    if len(new_business) != converted:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "The number of new-business deals equals the allocated converted lead count.",
            field="new_business_deals", actual=f"expected={converted} observed={len(new_business)}",
        )
    ratio = Decimal(stage_weights.get("closed_won", 0)) / Decimal(sum(stage_weights.values()))
    if ratio != as_decimal(config["opportunity_win_rate"]):
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "The closed_won weight divided by the total stage_mix weight equals opportunity_win_rate.",
            field="opportunity_win_rate", actual=f"ratio={format_number(ratio)} configured={config['opportunity_win_rate']}",
        )
    observed_leads = _latest_counts(leads, "status")
    observed_stages = _latest_counts(new_business, "stage")
    observed_channels = defaultdict(int)
    for row in campaigns:
        observed_channels[row.get("channel")] += 1
    _compare_alloc(run, defects, "lead status", lead_alloc, observed_leads)
    _compare_alloc(run, defects, "new-business stage", stage_alloc, observed_stages)
    _compare_alloc(run, defects, "campaign channel", channel_alloc, observed_channels)
    rate_rows = []
    rate_specs = [
        ("renewal_rate", "Subscriptions", len(subscriptions), _renewed(subscriptions), True),
        ("expansion_rate", "Subscriptions", len(subscriptions), _expanded(subscriptions), True),
        ("churn_rate", "Subscriptions", len(subscriptions), _churned(subscriptions), True),
        ("outcome_rate", "Usage rows", len(usages), len({row.get("product_usage_source_id") for row in outcomes}), True),
        ("null_company_domain_rate", "Companies", len(companies), sum(1 for rows in companies.values() if latest(rows).get("primary_domain") is None), True),
        ("orphan_lead_rate", "Leads", len(leads), sum(1 for rows in leads.values() if latest(rows).get("hubspot_company_id") is None and latest(rows).get("hubspot_contact_id") is None), True),
        ("null_deal_amount_rate", "Deals", len(deals), sum(1 for rows in deals.values() if latest(rows).get("amount") is None), True),
        ("single_parent_activity_rate", "Activities", len(activities), sum(1 for row in activities if _parent_count(row) == 1), True),
        ("null_performance_measure_rate", "Campaign-day rows", len(days), sum(1 for row in days if row.get("spend_amount") is None), True),
        ("clicks_exceed_impressions_rate", "Campaign-day rows", len(days), sum(1 for row in days if _clicks_exceed(row)), True),
        ("null_user_email_rate", "Product users", len(users), sum(1 for rows in users.values() if latest(rows).get("email_normalized") is None), True),
        ("company_change_rate", "Companies", len(companies), sum(1 for rows in companies.values() if len(rows) > 1), True),
    ]
    for name, population, size, observed, fails in rate_specs:
        expected = share_count(size, as_decimal(config[name]))
        rate_rows.append((name, population, str(size), str(expected), str(observed), "yes" if fails else "no"))
        if fails and expected != observed:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                f"{name} observed count equals share_count of the stated population.",
                field=name, actual=f"share_count={expected} observed={observed}",
            )
    duplicate_observed = _duplicate_contacts(contacts)
    duplicate_expected = share_count(len(contacts), as_decimal(config["duplicate_contact_email_rate"]))
    domain_observed = _domain_matches(firms, companies)
    domain_expected = share_count(len(firms), as_decimal(config["domain_match_rate"]))
    rate_rows.append(("duplicate_contact_email_rate", "Contacts", str(len(contacts)), str(duplicate_expected), str(duplicate_observed), "no"))
    rate_rows.append(("domain_match_rate", "Product firms", str(len(firms)), str(domain_expected), str(domain_observed), "no"))
    if duplicate_expected != duplicate_observed:
        recommendations.append((
            run.path,
            f"duplicate_contact_email_rate share_count is {duplicate_expected} and {duplicate_observed} contacts share an email. "
            "Duplicate contacts are produced by copying one source email onto the selected recipients, so the contacts that share an email include that source when the source was not selected.",
        ))
    if domain_expected != domain_observed:
        recommendations.append((
            run.path,
            f"domain_match_rate share_count is {domain_expected} and {domain_observed} product firms match a HubSpot company on primary_domain. "
            "A customer firm whose company has a null domain cannot match on primary_domain.",
        ))
    if int(config["activity_count"]) >= 2:
        null_deals = sum(1 for row in activities if row.get("hubspot_deal_id") is None)
        expected_null = int(config["activity_count"]) // 2
        if null_deals != expected_null or (len(activities) - null_deals) != len(activities) - expected_null:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "When activity_count is at least 2, the activities with a null hubspot_deal_id number activity_count // 2, and the other activities cite a deal.",
                field="hubspot_deal_id", actual=f"null={null_deals} expected={expected_null}",
            )
    events = {
        "lead": {row.get("emitted_event") for row in run.rows["hubspot.lead"]},
        "deal": {row.get("emitted_event") for row in run.rows["hubspot.deal"]},
        "subscription": {row.get("emitted_event") for row in run.rows["dealhub.subscription"]},
    }
    event_rows = []
    for label, names, present in (
        ("lead", LEAD_EVENTS, events["lead"]),
        ("deal", DEAL_EVENTS, events["deal"]),
        ("subscription", SUBSCRIPTION_EVENTS, events["subscription"]),
    ):
        for name in names:
            status = "present" if name in present else "missing"
            event_rows.append((name, status))
            if status == "missing":
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "Every baseline dataset contains at least one of each lead, deal, and subscription emitted_event value.",
                    field="emitted_event", actual=name,
                )
    company_domains = {row.get("primary_domain") for row in run.rows["hubspot.company"] if row.get("primary_domain")}
    firm_match = any(row.get("primary_domain") in company_domains for row in firms)
    firm_miss = any(row.get("primary_domain") not in company_domains for row in firms)
    edges = {
        "company with a null primary_domain": any(latest(rows).get("primary_domain") is None for rows in companies.values()),
        "two contacts with the same email and different contact ids": duplicate_observed >= 2,
        "lead with a null company and a null contact": any(latest(rows).get("hubspot_company_id") is None and latest(rows).get("hubspot_contact_id") is None for rows in leads.values()),
        "deal with a null amount": any(latest(rows).get("amount") is None for rows in deals.values()),
        "activity with exactly one parent": any(_parent_count(row) == 1 for row in activities),
        "activity with a null deal and activity that cites a deal": any(row.get("hubspot_deal_id") is None for row in activities) and any(row.get("hubspot_deal_id") for row in activities),
        "campaign-day row with a null spend_amount": any(row.get("spend_amount") is None for row in days),
        "campaign-day row whose clicks exceed impressions": any(_clicks_exceed(row) for row in days),
        "one product firm domain matching a company and one that does not": firm_match and firm_miss,
        "product user with a null email": any(latest(rows).get("email_normalized") is None for rows in users.values()),
        "active subscription renewal or expansion": any(row.get("status") == "active" and row.get("emitted_event") in {"subscription_renewed", "subscription_expanded"} for row in run.rows["dealhub.subscription"]),
        "churned subscription with no booking at or after churn": _churn_without_later_booking(subscriptions, run.rows["dealhub.booking"]),
        "lifecycle stage outside prospect, customer, and former_customer": any(row.get("hubspot_lifecycle_stage") not in CANONICAL_STAGES for row in run.rows["hubspot.company"]),
        "two observations of one company": any(len(rows) > 1 for rows in companies.values()),
    }
    run.edges = [(name, "present" if edges[name] else "missing") for name in BASELINE_EDGE_NAMES]
    for name, status in run.edges:
        if status == "missing":
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Both baseline datasets contain each specified edge case at least once.",
                field=name, actual="missing",
            )
    shape = run.distribution.get("shape_mismatches", [])
    run.distribution = {
        "counts": [(label, str(expected), str(observed)) for label, expected, observed in counts],
        "rates": rate_rows,
        "mixes": [
            ("Lead status", _mix_rows(lead_weights, lead_alloc, observed_leads)),
            ("New-business stage", _mix_rows(stage_weights, stage_alloc, observed_stages)),
            ("Campaign channel", _mix_rows(channel_weights, channel_alloc, observed_channels)),
        ],
        "events": event_rows,
        "shape_mismatches": shape,
    }
    if shape:
        recommendations.append((
            run.path,
            f"{len(shape)} source identifiers do not match the expected HubSpot numeric or DealHub prefixed shape. "
            f"Example: {shape[0]}. The contract accepts any non-empty string. eve_data_generation.validate is not the oracle.",
        ))


def _scenarios(run: DatasetRun, defects: list[Defect], recommendations: list[tuple[str, str]]) -> None:
    try:
        members, outsiders = _identify(run, defects)
    except Exception as exc:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "Both scenario files contain one of each journey and the domain twin.",
            field="journeys", actual=f"{type(exc).__name__}: {exc}",
        )
        _blank_edges(run)
        return
    names = (*JOURNEYS, "domain twin")
    run.journeys = [(name, "1", str(len(members[name]))) for name in names]
    for name, _expected, observed in run.journeys:
        if observed != "1":
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Both scenario datasets contain one instance of each journey and the domain twin.",
                field=name, actual=observed,
            )
    for company_id in outsiders:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "Every company is one of the seven journey companies or the domain twin.",
            entity="hubspot.company", key=f"hubspot_company_id={company_id}",
            field="hubspot_company_id", actual=company_id,
        )
    flags = {name: False for name in SCENARIO_EDGE_NAMES}
    if all(len(members[name]) == 1 for name in names):
        found = {name: members[name][0] for name in names}
        flags = _scenario_details(run, defects, found)
    run.edges = [(name, "present" if flags[name] else "missing") for name in SCENARIO_EDGE_NAMES]
    for name, status in run.edges:
        if status == "missing":
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Both scenario datasets contain the scenario edge-case rows.",
                field=name, actual="missing",
            )
    shape = run.distribution.get("shape_mismatches", [])
    run.distribution = {"shape_mismatches": shape}
    if shape:
        recommendations.append((
            run.path,
            f"{len(shape)} source identifiers do not match the expected HubSpot numeric or DealHub prefixed shape. "
            f"Example: {shape[0]}. The contract accepts any non-empty string. eve_data_generation.validate is not the oracle.",
        ))


def _identify(run: DatasetRun, defects: list[Defect]) -> tuple[dict[str, list[str]], list[str]]:
    companies = group_rows(run.rows["hubspot.company"], "hubspot_company_id")
    deals = group_rows(run.rows["hubspot.deal"], "hubspot_deal_id")
    by_company = defaultdict(list)
    for deal_id, rows in deals.items():
        by_company[rows[0].get("hubspot_company_id")].append(deal_id)
    def won_type(deal_id):
        wins = [row for row in deals[deal_id] if row.get("emitted_event") == "opportunity_won"]
        if len(wins) != 1:
            return None
        return wins[0].get("opportunity_type")
    customers = []
    for company_id in companies:
        if any(won_type(deal_id) == "new_business" for deal_id in by_company.get(company_id, [])):
            customers.append(company_id)
    domains = defaultdict(list)
    for company_id, rows in companies.items():
        domain = latest(rows).get("primary_domain")
        if domain:
            domains[domain].append(company_id)
    members: dict[str, list[str]] = {name: [] for name in (*JOURNEYS, "domain twin")}
    customer_ids = set(customers)
    for owners in domains.values():
        if len(owners) != 2:
            continue
        left, right = owners
        if left in customer_ids and right not in customer_ids:
            members["new_business_conversion"].append(left)
            members["domain twin"].append(right)
        elif right in customer_ids and left not in customer_ids:
            members["new_business_conversion"].append(right)
            members["domain twin"].append(left)
    nb_ids = set(members["new_business_conversion"])
    twin_ids = set(members["domain twin"])
    for company_id in customers:
        if company_id in nb_ids:
            continue
        types = {won_type(deal_id) for deal_id in by_company.get(company_id, [])}
        subscription_status = _customer_subscription_status(run, company_id, by_company, deals)
        if "expansion" in types:
            members["expansion"].append(company_id)
        elif "renewal" in types:
            members["renewal"].append(company_id)
        elif subscription_status == "churned":
            members["churn"].append(company_id)
        else:
            members["low_adoption"].append(company_id)
    for company_id in companies:
        if company_id in customer_ids or company_id in twin_ids:
            continue
        sequences = [tuple(row.get("stage") for row in deals[deal_id]) for deal_id in by_company.get(company_id, [])]
        if any(sequence == FORWARD_LOST for sequence in sequences):
            members["lost_opportunity"].append(company_id)
        elif any(sequence == REGRESSION_STAGES for sequence in sequences):
            members["stage_regression"].append(company_id)
    assigned = {company_id for grouped in members.values() for company_id in grouped}
    outsiders = [company_id for company_id in companies if company_id not in assigned]
    journey_domains = []
    for name in JOURNEYS:
        for company_id in members[name]:
            domain = latest(companies[company_id]).get("primary_domain")
            journey_domains.append(domain)
            if not domain:
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "Each journey company has its own non-null primary_domain.",
                    entity="hubspot.company", key=f"hubspot_company_id={company_id}", field="primary_domain", actual=None,
                )
    if len(journey_domains) != len(set(journey_domains)):
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "Journey companies do not share a primary_domain. The domain twin is the company that copies the new-business domain.",
            field="primary_domain", actual=journey_domains,
        )
    return members, outsiders


def _customer_subscription_status(run, company_id, by_company, deals) -> str | None:
    for deal_id in by_company.get(company_id, []):
        wins = [row for row in deals[deal_id] if row.get("emitted_event") == "opportunity_won" and row.get("opportunity_type") == "new_business"]
        if not wins:
            continue
        contract_ids = {
            row.get("dealhub_contract_id")
            for row in run.rows["dealhub.contract"]
            if row.get("hubspot_deal_id") == deal_id
        }
        subs = group_rows(
            [row for row in run.rows["dealhub.subscription"] if row.get("dealhub_contract_id") in contract_ids],
            "dealhub_subscription_id",
        )
        if not subs:
            return None
        return latest(next(iter(subs.values()))).get("status")
    return None


def _scenario_details(run: DatasetRun, defects: list[Defect], found: dict[str, str]) -> dict[str, bool]:
    companies = group_rows(run.rows["hubspot.company"], "hubspot_company_id")
    deals = group_rows(run.rows["hubspot.deal"], "hubspot_deal_id")
    contacts = group_rows(run.rows["hubspot.contact"], "hubspot_contact_id")
    leads = group_rows(run.rows["hubspot.lead"], "hubspot_lead_id")
    quotes = group_rows(run.rows["dealhub.quote"], "dealhub_quote_id")
    contracts = group_rows(run.rows["dealhub.contract"], "dealhub_contract_id")
    subscriptions = group_rows(run.rows["dealhub.subscription"], "dealhub_subscription_id")
    workflows = {row.get("product_workflow_id"): row for row in run.rows["product.ai_workflow"]}
    code_by_id = {workflow_id: row.get("workflow_code") for workflow_id, row in workflows.items()}
    config = run.config
    flags = {name: True for name in SCENARIO_EDGE_NAMES}
    by_company = defaultdict(list)
    for deal_id, rows in deals.items():
        by_company[rows[0].get("hubspot_company_id")].append(deal_id)
    _shared_resources(run, defects, found, by_company, deals, contracts, subscriptions)
    _converting_leads(run, defects, leads, deals)
    _forward_deals(run, defects, found, deals, by_company, config)
    nb = found["new_business_conversion"]
    twin = found["domain twin"]
    if not _duplicate_contact_case(contacts, nb):
        flags["Duplicate contacts"] = False
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "The two contacts on the new_business_conversion company share email_normalized and keep different hubspot_contact_id values.",
            entity="hubspot.contact", key=f"hubspot_company_id={nb}", field="email_normalized", actual="not a shared pair",
        )
    nb_domain = latest(companies[nb]).get("primary_domain")
    twin_domain = latest(companies[twin]).get("primary_domain")
    firm = _firm_for_domain(run, nb_domain)
    twin_won = any(
        row.get("emitted_event") == "opportunity_won"
        for deal_id in by_company.get(twin, [])
        for row in deals[deal_id]
    )
    if twin_domain != nb_domain or firm is None or latest(companies[twin]).get("hubspot_lifecycle_stage") != "sql" or twin_won:
        flags["Merged accounts"] = False
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "One extra company copies the new-business primary_domain, uses a different hubspot_company_id, has no won deal, and uses sql. The Product firm uses the same domain.",
            entity="hubspot.company", key=f"hubspot_company_id={twin}", field="primary_domain",
            actual="opportunity_won" if twin_won else twin_domain,
        )
    if not _regression_and_forward(deals, found, by_company):
        flags["Repeated stage changes"] = False
    if not _late_case(run):
        flags["Late-arriving events"] = False
    if not _amendments(run, found, by_company, deals, contracts, subscriptions, config):
        flags["Contract amendments"] = False
    if not _canceled(run, found, by_company, deals, contracts, subscriptions):
        flags["Canceled subscriptions"] = False
    if not _soft_deleted(run, found, leads, quotes, by_company, deals):
        flags["Soft-deleted records"] = False
    if not _adoption_case(run, found, by_company, deals, code_by_id, config):
        flags["Low or declining adoption"] = False
    _customer_sequences(run, defects, found, companies, contacts, leads, deals, quotes, contracts, subscriptions, by_company, code_by_id, config, firm)
    return flags


def _shared_resources(run, defects, found, by_company, deals, contracts, subscriptions) -> None:
    seen_contracts = {}
    seen_subscriptions = {}
    for name in CUSTOMER_JOURNEYS:
        company_id = found[name]
        deal_id = _new_business_deal(by_company, deals, company_id)
        contract_ids = {
            row.get("dealhub_contract_id")
            for row in run.rows["dealhub.contract"]
            if row.get("hubspot_deal_id") == deal_id
        }
        sub_ids = {
            row.get("dealhub_subscription_id")
            for row in run.rows["dealhub.subscription"]
            if row.get("dealhub_contract_id") in contract_ids
        }
        for contract_id in contract_ids:
            if contract_id in seen_contracts:
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "Journey companies do not share a subscription or a contract.",
                    field="dealhub_contract_id", actual=contract_id,
                )
            seen_contracts[contract_id] = name
        for sub_id in sub_ids:
            if sub_id in seen_subscriptions:
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "Journey companies do not share a subscription or a contract.",
                    field="dealhub_subscription_id", actual=sub_id,
                )
            seen_subscriptions[sub_id] = name


def _converting_leads(run, defects, leads, deals) -> None:
    for lead_id, rows in leads.items():
        if not any(row.get("emitted_event") == "lead_converted" for row in rows):
            continue
        sequence = tuple((row.get("status"), row.get("emitted_event")) for row in rows)
        if sequence != CONVERTING_LEAD:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Converting scenario leads use new/lead_created, working/null, qualified/lead_qualified, then converted/lead_converted.",
                entity="hubspot.lead", key=f"hubspot_lead_id={lead_id}", field="status", actual=list(sequence),
            )
        converted = next(row for row in rows if row.get("emitted_event") == "lead_converted")
        deal_id = converted.get("hubspot_deal_id")
        deal_rows = deals.get(str(deal_id), [])
        if not deal_rows or deal_rows[0].get("observed_at") != converted.get("observed_at") or deal_rows[0].get("stage") != "discovery" or deal_rows[0].get("emitted_event") != "opportunity_opened":
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "hubspot_deal_id is set only on lead_converted. That deal opens at the same timestamp with discovery and opportunity_opened.",
                entity="hubspot.deal", key=f"hubspot_lead_id={lead_id}", field="observed_at",
                actual=None if not deal_rows else deal_rows[0].get("observed_at"),
            )


def _forward_deals(run, defects, found, deals, by_company, config) -> None:
    regression_company = found["stage_regression"]
    regression_ids = set(by_company.get(regression_company, []))
    forecast = config.get("forecast_by_stage") or {}
    for deal_id, rows in deals.items():
        stages = tuple(row.get("stage") for row in rows)
        expected = REGRESSION_STAGES if deal_id in regression_ids else None
        if expected is None:
            expected = FORWARD_LOST if stages and stages[-1] == "closed_lost" else FORWARD_WON
        if stages != expected:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Won and lost deals follow discovery, evaluation, proposal, negotiation, and closed_won or closed_lost. The regression deal returns from proposal to evaluation.",
                entity="hubspot.deal", key=f"hubspot_deal_id={deal_id}", field="stage", actual=list(stages),
            )
        for row in rows:
            if row.get("forecast_category") != forecast.get(row.get("stage")):
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "forecast_category comes from forecast_by_stage for that stage.",
                    entity="hubspot.deal", key=f"hubspot_deal_id={deal_id}", field="forecast_category",
                    actual=row.get("forecast_category"),
                )


def _customer_sequences(run, defects, found, companies, contacts, leads, deals, quotes, contracts, subscriptions, by_company, code_by_id, config, nb_firm) -> None:
    for name in CUSTOMER_JOURNEYS:
        company_id = found[name]
        deal_id = _new_business_deal(by_company, deals, company_id)
        deal_rows = deals[deal_id]
        win = next(row for row in deal_rows if row.get("emitted_event") == "opportunity_won")
        quote_id = _quote_for_deal(run, deal_id)
        quote_rows = quotes.get(str(quote_id), [])
        statuses = tuple(row.get("status") for row in quote_rows)
        if statuses != ("draft", "sent", "accepted"):
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Customer journey quote observations are draft, sent, then accepted.",
                entity="dealhub.quote", key=f"hubspot_deal_id={deal_id}", field="status", actual=list(statuses),
            )
        _quote_amounts(run, defects, quote_rows)
        accepted = next((row for row in quote_rows if row.get("status") == "accepted"), None)
        if accepted is None or parse_timestamp(accepted.get("observed_at")) > parse_timestamp(win.get("observed_at")):
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "The accepted observation is at or before the winning deal observation.",
                entity="dealhub.quote", key=f"hubspot_deal_id={deal_id}", field="observed_at", actual=None if accepted is None else accepted.get("observed_at"),
            )
        contract_id = next((row.get("dealhub_contract_id") for row in run.rows["dealhub.contract"] if row.get("hubspot_deal_id") == deal_id), None)
        contract_rows = contracts.get(str(contract_id), [])
        if not contract_rows or parse_timestamp(contract_rows[0].get("observed_at")) < parse_timestamp(win.get("observed_at")) or contract_rows[0].get("dealhub_quote_id") != quote_id:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "The contract's first observed_at is at or after the win, and the contract cites that quote.",
                entity="dealhub.contract", key=f"hubspot_deal_id={deal_id}", field="observed_at",
                actual=None if not contract_rows else contract_rows[0].get("observed_at"),
            )
        sub_rows = [
            row for row in run.rows["dealhub.subscription"]
            if row.get("dealhub_contract_id") == contract_id
        ]
        sub_grouped = group_rows(sub_rows, "dealhub_subscription_id")
        if len(sub_grouped) != 1:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "A customer journey has one subscription. The first observation is pending with a null emitted_event, and the next is active with a null emitted_event.",
                entity="dealhub.subscription", key=f"dealhub_contract_id={contract_id}", field="dealhub_subscription_id", actual=len(sub_grouped),
            )
        else:
            observations = next(iter(sub_grouped.values()))
            if len(observations) < 2 or observations[0].get("status") != "pending" or observations[0].get("emitted_event") is not None or observations[1].get("status") != "active" or observations[1].get("emitted_event") is not None:
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "The subscription's first observation is pending with a null emitted_event. The next is active with a null emitted_event.",
                    entity="dealhub.subscription", key=f"dealhub_subscription_id={observations[0].get('dealhub_subscription_id')}",
                    field="status", actual=[(row.get("status"), row.get("emitted_event")) for row in observations[:2]],
                )
            for field_name in ("subscription_number", "plan_code", "billing_frequency"):
                if len({row.get(field_name) for row in observations}) != 1:
                    add_defect(
                        defects, run, "distributions_and_edge_cases",
                        "subscription_number, plan_code, and billing_frequency stay stable.",
                        entity="dealhub.subscription", field=field_name, actual="varies",
                    )
        company_rows = companies[company_id]
        if company_rows[0].get("hubspot_lifecycle_stage") != "prospect":
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "The company opens at hubspot_lifecycle_stage prospect.",
                entity="hubspot.company", key=f"hubspot_company_id={company_id}", field="hubspot_lifecycle_stage",
                actual=company_rows[0].get("hubspot_lifecycle_stage"),
            )
        customer_rows = [row for row in company_rows if row.get("hubspot_lifecycle_stage") == "customer"]
        if not customer_rows or parse_timestamp(customer_rows[0].get("observed_at")) < parse_timestamp(win.get("observed_at")):
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "The company has a later observation customer at or after the new-business win.",
                entity="hubspot.company", key=f"hubspot_company_id={company_id}", field="hubspot_lifecycle_stage", actual="missing",
            )
        domain = latest(company_rows).get("primary_domain")
        matched = [row for row in run.rows["product.firm"] if row.get("primary_domain") == domain]
        if len(matched) != 1:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Each customer company has one Product firm with the same primary_domain.",
                entity="product.firm", key=f"hubspot_company_id={company_id}", field="primary_domain", actual=len(matched),
            )
            continue
        firm_id = matched[0].get("product_firm_id")
        firm_usages = [row for row in run.rows["product.usage"] if row.get("product_firm_id") == firm_id]
        if firm_usages:
            first_usage = min(parse_timestamp(row.get("occurred_at")) for row in firm_usages)
            user_times = [
                parse_timestamp(row.get("observed_at"))
                for row in run.rows["product.user"]
                if row.get("product_firm_id") == firm_id and parse_timestamp(row.get("observed_at")) is not None
            ]
            if not user_times or min(user_times) > first_usage or first_usage < parse_timestamp(win.get("observed_at")):
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "The first product-user observation is at or before that firm's first usage. Usage occurred_at is at or after the new-business win.",
                    entity="product.usage", key=f"product_firm_id={firm_id}", field="occurred_at", actual="out of order",
                )
        for row in run.rows["product.outcome"]:
            if row.get("product_usage_source_id") in {item.get("product_usage_source_id") for item in firm_usages} and row.get("product_firm_id") != firm_id:
                add_defect(
                    defects, run, "distributions_and_edge_cases",
                    "Usage and outcomes cite that firm.",
                    entity="product.outcome", field="product_firm_id", actual=row.get("product_firm_id"),
                )
    _new_business_specific(run, defects, found, contacts, deals, by_company, code_by_id, config)
    _expansion_specific(run, defects, found, by_company, deals, contracts, subscriptions, config)
    _renewal_specific(run, defects, found, by_company, deals, contracts, subscriptions, config)
    _churn_specific(run, defects, found, companies, by_company, deals, contracts, subscriptions, code_by_id, config)
    _low_specific(run, defects, found, by_company, deals, code_by_id)
    _lost_specific(run, defects, found, by_company, deals, quotes)
    _regression_specific(run, defects, found, by_company, deals, quotes)
    _touches(run, defects, leads)


def _new_business_specific(run, defects, found, contacts, deals, by_company, code_by_id, config) -> None:
    company_id = found["new_business_conversion"]
    deal_id = _new_business_deal(by_company, deals, company_id)
    types = {_deal_won_type(deals[item]) for item in by_company.get(company_id, [])}
    if types != {"new_business"}:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "new_business_conversion has no expansion deal, no renewal deal, and no churn.",
            entity="hubspot.deal", key=f"hubspot_company_id={company_id}", field="opportunity_type", actual=sorted(str(item) for item in types),
        )
    if _subscription_events(run, deal_id) & {"subscription_churned"}:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "new_business_conversion has no churn.",
            entity="dealhub.subscription", key=f"hubspot_deal_id={deal_id}", field="emitted_event", actual="subscription_churned",
        )
    activities = [row for row in run.rows["hubspot.activity"] if row.get("hubspot_deal_id") == deal_id]
    counted = defaultdict(int)
    win = next(row for row in deals[deal_id] if row.get("emitted_event") == "opportunity_won")
    created = parse_timestamp(deals[deal_id][0].get("created_at"))
    won_at = parse_timestamp(win.get("observed_at"))
    for row in activities:
        occurred = parse_timestamp(row.get("occurred_at"))
        if row.get("hubspot_company_id") != company_id or occurred is None or occurred <= created or occurred > won_at:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Each new-business activity cites the deal and the company. occurred_at is after the deal's created_at and at or before the winning observed_at.",
                entity="hubspot.activity", field="occurred_at", actual=row.get("occurred_at"),
            )
        counted[row.get("activity_type")] += 1
    if counted != {"call": 1, "email": 1, "meeting": 1}:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "new_business_conversion includes one call, one email, and one meeting.",
            entity="hubspot.activity", key=f"hubspot_deal_id={deal_id}", field="activity_type", actual=dict(counted),
        )
    firm_id = _firm_for_domain(run, latest(group_rows(run.rows["hubspot.company"], "hubspot_company_id")[company_id]).get("primary_domain"))
    usages = [row for row in run.rows["product.usage"] if firm_id and row.get("product_firm_id") == firm_id]
    by_code = defaultdict(list)
    for row in usages:
        by_code[code_by_id.get(row.get("product_workflow_id"))].append(row)
    outcomes = group_rows(run.rows["product.outcome"], "product_outcome_source_id")
    outcome_by_usage = defaultdict(list)
    for row in run.rows["product.outcome"]:
        outcome_by_usage[row.get("product_usage_source_id")].append(row.get("outcome_type"))
    if set(by_code) != {code for code, _outcome in NB_USAGE}:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "The new-business firm has one usage for each workflow code except case_analysis.",
            entity="product.usage", field="workflow_code", actual=sorted(str(code) for code in by_code),
        )
    maximum = (config.get("integer_ranges") or {}).get("work_unit_count", {}).get("max")
    for code, outcome in NB_USAGE:
        rows = by_code.get(code, [])
        if len(rows) != 1:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "The new-business firm has one usage for each workflow code except case_analysis.",
                entity="product.usage", key=f"workflow_code={code}", field="workflow_code", actual=len(rows),
            )
            continue
        if code == "document_collection" and rows[0].get("work_unit_count") != maximum:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "document_collection work_unit_count equals the configured maximum, which is at least 2.",
                entity="product.usage", field="work_unit_count", actual=rows[0].get("work_unit_count"),
            )
        if outcome is not None and outcome_by_usage.get(rows[0].get("product_usage_source_id")) != [outcome]:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "The new-business outcomes are exported, draft_completed, and review_accepted on the specified workflows.",
                entity="product.outcome", field="outcome_type", actual=outcome_by_usage.get(rows[0].get("product_usage_source_id")),
            )


def _expansion_specific(run, defects, found, by_company, deals, contracts, subscriptions, config) -> None:
    company_id = found["expansion"]
    deal_id = _typed_deal(by_company, deals, company_id, "expansion")
    sub_rows = _subscription_rows(run, _new_business_deal(by_company, deals, company_id))
    expanded = [row for row in sub_rows if row.get("emitted_event") == "subscription_expanded"]
    position = sub_rows.index(expanded[0]) if len(expanded) == 1 else -1
    if len(expanded) != 1 or expanded[0].get("status") != "active" or position < 1:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "expansion keeps that subscription active and emits subscription_expanded.",
            entity="dealhub.subscription", field="emitted_event", actual=len(expanded),
        )
        return
    previous = sub_rows[position - 1]
    if expanded[0].get("seat_count") != previous.get("seat_count") + config["expansion_seat_increase"]:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "expansion raises seat_count by expansion_seat_increase.",
            entity="dealhub.subscription", field="seat_count", actual=expanded[0].get("seat_count"),
        )
    if Decimal(str(expanded[0].get("recurring_amount"))) != Decimal(str(previous.get("recurring_amount"))) + Decimal(str(config["expansion_recurring_increase"])):
        add_defect(
            defects, run, "distributions_and_edge_cases",
            "expansion raises recurring_amount by expansion_recurring_increase.",
            entity="dealhub.subscription", field="recurring_amount", actual=expanded[0].get("recurring_amount"),
        )
    if any(row.get("emitted_event") == "subscription_churned" for row in sub_rows):
        add_defect(defects, run, "distributions_and_edge_cases", "expansion does not churn.", entity="dealhub.subscription", field="emitted_event", actual="subscription_churned")
    if _contracts_for_deal(run, deal_id):
        add_defect(defects, run, "distributions_and_edge_cases", "expansion does not create a contract.", entity="dealhub.contract", key=f"hubspot_deal_id={deal_id}", field="dealhub_contract_id", actual="present")
    bookings = [row for row in run.rows["dealhub.booking"] if row.get("hubspot_deal_id") == deal_id and row.get("booking_type") == "expansion"]
    if len(bookings) != 1:
        add_defect(defects, run, "distributions_and_edge_cases", "expansion adds one expansion booking on the expansion deal.", entity="dealhub.booking", field="booking_type", actual=len(bookings))


def _renewal_specific(run, defects, found, by_company, deals, contracts, subscriptions, config) -> None:
    company_id = found["renewal"]
    deal_id = _typed_deal(by_company, deals, company_id, "renewal")
    sub_rows = _subscription_rows(run, _new_business_deal(by_company, deals, company_id))
    renewed = [row for row in sub_rows if row.get("emitted_event") == "subscription_renewed"]
    position = sub_rows.index(renewed[0]) if len(renewed) == 1 else -1
    if len(renewed) != 1 or renewed[0].get("status") != "active" or position < 1:
        add_defect(defects, run, "distributions_and_edge_cases", "renewal keeps that subscription active and emits subscription_renewed.", entity="dealhub.subscription", field="emitted_event", actual=len(renewed))
        return
    previous = sub_rows[position - 1]
    if renewed[0].get("seat_count") != previous.get("seat_count") or Decimal(str(renewed[0].get("recurring_amount"))) != Decimal(str(previous.get("recurring_amount"))):
        add_defect(defects, run, "distributions_and_edge_cases", "renewal leaves seat_count and recurring_amount unchanged.", entity="dealhub.subscription", field="seat_count", actual=renewed[0].get("seat_count"))
    if parse_date(renewed[0].get("term_end")) != parse_date(previous.get("term_end")) + timedelta(days=int(config["term_days"])):
        add_defect(defects, run, "distributions_and_edge_cases", "renewal moves term_end later by term_days.", entity="dealhub.subscription", field="term_end", actual=renewed[0].get("term_end"))
    if any(row.get("emitted_event") == "subscription_churned" for row in sub_rows):
        add_defect(defects, run, "distributions_and_edge_cases", "renewal does not churn.", entity="dealhub.subscription", field="emitted_event", actual="subscription_churned")
    if _contracts_for_deal(run, deal_id):
        add_defect(defects, run, "distributions_and_edge_cases", "renewal does not create a contract.", entity="dealhub.contract", field="dealhub_contract_id", actual="present")
    bookings = [row for row in run.rows["dealhub.booking"] if row.get("hubspot_deal_id") == deal_id and row.get("booking_type") == "renewal"]
    if len(bookings) != 1:
        add_defect(defects, run, "distributions_and_edge_cases", "renewal adds one renewal booking on the renewal deal.", entity="dealhub.booking", field="booking_type", actual=len(bookings))
    contract_rows = _contract_rows_for_company_deal(run, _new_business_deal(by_company, deals, company_id))
    if len(contract_rows) < 2 or Decimal(str(contract_rows[-1].get("total_contract_value"))) != Decimal(str(contract_rows[0].get("total_contract_value"))):
        add_defect(defects, run, "distributions_and_edge_cases", "renewal keeps total_contract_value the same.", entity="dealhub.contract", field="total_contract_value", actual=None if not contract_rows else contract_rows[-1].get("total_contract_value"))
    if len(contract_rows) < 2 or parse_date(contract_rows[-1].get("end_date")) != parse_date(contract_rows[0].get("end_date")) + timedelta(days=int(config["term_days"])):
        add_defect(defects, run, "distributions_and_edge_cases", "renewal moves the contract end_date later by term_days.", entity="dealhub.contract", field="end_date", actual=None if not contract_rows else contract_rows[-1].get("end_date"))


def _churn_specific(run, defects, found, companies, by_company, deals, contracts, subscriptions, code_by_id, config) -> None:
    company_id = found["churn"]
    deal_id = _new_business_deal(by_company, deals, company_id)
    sub_rows = _subscription_rows(run, deal_id)
    churns = [row for row in sub_rows if row.get("emitted_event") == "subscription_churned"]
    active = next((row for row in sub_rows if row.get("status") == "active"), None)
    domain = latest(companies[company_id]).get("primary_domain")
    firm_id = _firm_for_domain(run, domain)
    usages = sorted(
        [row for row in run.rows["product.usage"] if row.get("product_firm_id") == firm_id],
        key=lambda row: parse_timestamp(row.get("occurred_at")) or 0,
    )
    bounds = (config.get("integer_ranges") or {}).get("work_unit_count") or {}
    outcome_ids = {row.get("product_usage_source_id") for row in run.rows["product.outcome"]}
    if len(usages) != 2 or any(row.get("product_usage_source_id") in outcome_ids for row in usages):
        add_defect(defects, run, "distributions_and_edge_cases", "churn has exactly two usage rows and no outcome.", entity="product.usage", field="product_usage_source_id", actual=len(usages))
    elif usages[0].get("work_unit_count") != bounds.get("max") or usages[1].get("work_unit_count") != bounds.get("min") or bounds.get("max", 0) <= bounds.get("min", 0):
        add_defect(defects, run, "distributions_and_edge_cases", "The earlier churn work_unit_count is the configured maximum and the later one is the configured minimum. The maximum is greater.", entity="product.usage", field="work_unit_count", actual=[row.get("work_unit_count") for row in usages])
    if len(usages) == 2 and active is not None and churns:
        active_at = parse_timestamp(active.get("observed_at"))
        churn_at = parse_timestamp(churns[0].get("observed_at"))
        for row in usages:
            occurred = parse_timestamp(row.get("occurred_at"))
            if occurred is None or active_at is None or churn_at is None or occurred <= active_at or occurred >= churn_at:
                add_defect(defects, run, "distributions_and_edge_cases", "Both churn usage occurred_at values are after the first active subscription observation and before churn.", entity="product.usage", field="occurred_at", actual=row.get("occurred_at"))
    contract_rows = _contract_rows_for_company_deal(run, deal_id)
    if not contract_rows or contract_rows[-1].get("status") != "terminated":
        add_defect(defects, run, "distributions_and_edge_cases", "The churn contract's later observation is terminated. There is no canceled status.", entity="dealhub.contract", field="status", actual=None if not contract_rows else contract_rows[-1].get("status"))
    former = [row for row in companies[company_id] if row.get("hubspot_lifecycle_stage") == "former_customer"]
    if not churns or not former or parse_timestamp(former[0].get("observed_at")) < parse_timestamp(churns[0].get("observed_at")):
        add_defect(defects, run, "distributions_and_edge_cases", "The churn company has former_customer at or after churn.", entity="hubspot.company", field="hubspot_lifecycle_stage", actual="missing")
    if churns and len(usages) == 2:
        later = parse_timestamp(usages[1].get("occurred_at"))
        inactive = [
            row for row in run.rows["product.user"]
            if row.get("product_firm_id") == firm_id and row.get("status") == "inactive" and parse_timestamp(row.get("observed_at")) and parse_timestamp(row.get("observed_at")) > later
        ]
        if not inactive:
            add_defect(defects, run, "distributions_and_edge_cases", "One product user on the churn firm has a later inactive observation after the later usage.", entity="product.user", field="status", actual="missing")


def _low_specific(run, defects, found, by_company, deals, code_by_id) -> None:
    company_id = found["low_adoption"]
    deal_id = _new_business_deal(by_company, deals, company_id)
    domain = latest(group_rows(run.rows["hubspot.company"], "hubspot_company_id")[company_id]).get("primary_domain")
    firm_id = _firm_for_domain(run, domain)
    usages = [row for row in run.rows["product.usage"] if row.get("product_firm_id") == firm_id]
    outcomes = {row.get("product_usage_source_id") for row in run.rows["product.outcome"]}
    types = {_deal_won_type(deals[item]) for item in by_company.get(company_id, [])}
    events = _subscription_events(run, deal_id)
    if len(usages) != 1 or code_by_id.get(usages[0].get("product_workflow_id")) != "case_analysis" or usages[0].get("product_usage_source_id") in outcomes:
        add_defect(defects, run, "distributions_and_edge_cases", "low_adoption has one case_analysis usage and no outcome.", entity="product.usage", field="workflow_code", actual=len(usages))
    if types != {"new_business"} or events & {"subscription_expanded", "subscription_renewed", "subscription_churned"}:
        add_defect(defects, run, "distributions_and_edge_cases", "low_adoption has an active subscription and no expansion, renewal, or churn.", entity="dealhub.subscription", field="emitted_event", actual=sorted(events))
    sub_rows = _subscription_rows(run, deal_id)
    if not sub_rows or latest(sub_rows).get("status") != "active":
        add_defect(defects, run, "distributions_and_edge_cases", "low_adoption has an active subscription.", entity="dealhub.subscription", field="status", actual=None if not sub_rows else latest(sub_rows).get("status"))


def _lost_specific(run, defects, found, by_company, deals, quotes) -> None:
    company_id = found["lost_opportunity"]
    deal_ids = by_company.get(company_id, [])
    if len(deal_ids) != 1:
        add_defect(defects, run, "distributions_and_edge_cases", "lost_opportunity ends closed_lost and has no contract, subscription, booking, or Product firm.", entity="hubspot.deal", field="hubspot_deal_id", actual=len(deal_ids))
        return
    deal_id = deal_ids[0]
    rows = deals[deal_id]
    if rows[-1].get("stage") != "closed_lost":
        add_defect(defects, run, "distributions_and_edge_cases", "lost_opportunity ends closed_lost.", entity="hubspot.deal", field="stage", actual=rows[-1].get("stage"))
    quote_rows = _quotes_for_deal(run, deal_id)
    if tuple(row.get("status") for row in quote_rows) != ("draft", "sent", "rejected"):
        add_defect(defects, run, "distributions_and_edge_cases", "The lost quote is draft, sent, then rejected.", entity="dealhub.quote", field="status", actual=[row.get("status") for row in quote_rows])
    _quote_amounts(run, defects, quote_rows)
    lost = next((row for row in rows if row.get("emitted_event") == "opportunity_lost"), None)
    rejected = next((row for row in quote_rows if row.get("status") == "rejected"), None)
    if lost is None or rejected is None or parse_timestamp(rejected.get("observed_at")) > parse_timestamp(lost.get("observed_at")):
        add_defect(defects, run, "distributions_and_edge_cases", "The rejected observation is at or before opportunity_lost.", entity="dealhub.quote", field="observed_at", actual=None if rejected is None else rejected.get("observed_at"))
    _no_commercial(run, defects, company_id, deal_id, "lost_opportunity")


def _regression_specific(run, defects, found, by_company, deals, quotes) -> None:
    company_id = found["stage_regression"]
    deal_ids = by_company.get(company_id, [])
    if len(deal_ids) != 1:
        add_defect(defects, run, "distributions_and_edge_cases", "stage_regression never reaches closed_won or closed_lost.", entity="hubspot.deal", field="hubspot_deal_id", actual=len(deal_ids))
        return
    deal_id = deal_ids[0]
    rows = deals[deal_id]
    if tuple(row.get("stage") for row in rows) != REGRESSION_STAGES or rows[-1].get("stage") != "negotiation":
        add_defect(defects, run, "distributions_and_edge_cases", "After the opening observation the regression stages are evaluation, proposal, evaluation, negotiation. The latest stage is negotiation.", entity="hubspot.deal", field="stage", actual=[row.get("stage") for row in rows])
    if any(row.get("stage") in {"closed_won", "closed_lost"} for row in rows):
        add_defect(defects, run, "distributions_and_edge_cases", "stage_regression never reaches closed_won or closed_lost.", entity="hubspot.deal", field="stage", actual=rows[-1].get("stage"))
    quote_rows = _quotes_for_deal(run, deal_id)
    if tuple(row.get("status") for row in quote_rows) != ("draft", "sent", "expired"):
        add_defect(defects, run, "distributions_and_edge_cases", "The regression quote is draft, sent, then expired.", entity="dealhub.quote", field="status", actual=[row.get("status") for row in quote_rows])
    _quote_amounts(run, defects, quote_rows)
    proposal = next((row for row in rows if row.get("stage") == "proposal"), None)
    returned = None
    seen_proposal = False
    for row in rows:
        if row.get("stage") == "proposal":
            seen_proposal = True
        elif seen_proposal and row.get("stage") == "evaluation":
            returned = row
            break
    expired = next((row for row in quote_rows if row.get("status") == "expired"), None)
    if proposal is None or returned is None or expired is None or not (
        parse_timestamp(proposal.get("observed_at")) < parse_timestamp(expired.get("observed_at")) < parse_timestamp(returned.get("observed_at"))
    ):
        add_defect(defects, run, "distributions_and_edge_cases", "The expired observation is after the first proposal and before the return to evaluation.", entity="dealhub.quote", field="observed_at", actual=None if expired is None else expired.get("observed_at"))
    _no_commercial(run, defects, company_id, deal_id, "stage_regression")


def _touches(run, defects, leads) -> None:
    for lead_id, rows in leads.items():
        converted = [row for row in rows if row.get("emitted_event") == "lead_converted"]
        if not converted:
            continue
        created = parse_timestamp(rows[0].get("created_at"))
        company_id = converted[0].get("hubspot_company_id")
        matched = [
            row for row in run.rows["marketing.touch"]
            if row.get("hubspot_company_id") == company_id
            and row.get("marketing_campaign_id")
            and row.get("hubspot_lead_id") is None
            and parse_timestamp(row.get("occurred_at")) is not None
            and parse_timestamp(row.get("occurred_at")) <= created
        ]
        if not matched:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "Each converting lead's company has at least one touch with occurred_at at or before that lead's created_at. The touch cites the campaign and the company and does not cite the lead.",
                entity="marketing.touch", key=f"hubspot_lead_id={lead_id}", field="occurred_at", actual="missing",
            )


def _quote_amounts(run, defects, quote_rows) -> None:
    for row in quote_rows:
        if row.get("status") == "draft":
            continue
        if row.get("status") in {"sent", "accepted", "rejected", "expired"} and row.get("quoted_amount") is None:
            add_defect(
                defects, run, "distributions_and_edge_cases",
                "quoted_amount may be null on draft and is present on sent, accepted, rejected, and expired.",
                entity="dealhub.quote", field="quoted_amount", actual=None,
            )


def _no_commercial(run, defects, company_id, deal_id, label) -> None:
    domain = latest(group_rows(run.rows["hubspot.company"], "hubspot_company_id")[company_id]).get("primary_domain")
    has_contract = bool(_contracts_for_deal(run, deal_id))
    has_sub = bool(_subscription_rows(run, deal_id))
    has_booking = any(row.get("hubspot_deal_id") == deal_id for row in run.rows["dealhub.booking"])
    has_firm = any(row.get("primary_domain") == domain for row in run.rows["product.firm"])
    if has_contract or has_sub or has_booking or has_firm:
        add_defect(
            defects, run, "distributions_and_edge_cases",
            f"{label} has no contract, subscription, booking, or Product firm.",
            entity="hubspot.deal", key=f"hubspot_deal_id={deal_id}", field="hubspot_deal_id", actual="commercial rows present",
        )


def _duplicate_contact_case(contacts, company_id) -> bool:
    rows = [latest(group) for group in contacts.values() if latest(group).get("hubspot_company_id") == company_id]
    if len(rows) != 2:
        return False
    emails = {row.get("email_normalized") for row in rows}
    ids = {row.get("hubspot_contact_id") for row in rows}
    return len(emails) == 1 and None not in emails and len(ids) == 2


def _firm_for_domain(run, domain):
    matched = [row.get("product_firm_id") for row in run.rows["product.firm"] if row.get("primary_domain") == domain]
    if len(matched) != 1:
        return None
    return matched[0]


def _late_case(run) -> bool:
    if run.config.get("late_event_count") != 1 or run.config.get("ingest_lag_days") != 1:
        return False
    immutable = {
        "hubspot.activity",
        "dealhub.booking",
        "marketing.touch",
        "marketing.campaign_performance",
        "product.usage",
        "product.outcome",
    }
    mismatches = []
    for entity, rows in run.rows.items():
        for row in rows:
            business = _row_business(entity, row)
            ingested = parse_timestamp(row.get("ingested_at"))
            if business is None or ingested is None or ingested == business:
                continue
            mismatches.append((entity, business, ingested))
    if len(mismatches) != 1:
        return False
    entity, business, ingested = mismatches[0]
    return entity in immutable and ingested == business + timedelta(days=1)


def _row_business(entity, row):
    if entity == "marketing.campaign_performance":
        day = parse_date(row.get("performance_date"))
        if day is None:
            return None
        return datetime.combine(day, time.min)
    if entity in {"marketing.campaign", "product.firm", "product.ai_workflow"}:
        return None
    for name in ("observed_at", "occurred_at", "booked_at"):
        if row.get(name) is not None:
            return parse_timestamp(row.get(name))
    return None


def _regression_and_forward(deals, found, by_company) -> bool:
    regression_ids = set(by_company.get(found["stage_regression"], []))
    for deal_id, rows in deals.items():
        changed = sum(1 for row in rows if row.get("emitted_event") == "opportunity_stage_changed")
        stages = tuple(row.get("stage") for row in rows)
        if deal_id in regression_ids:
            if stages != REGRESSION_STAGES:
                return False
        elif changed != 3:
            return False
    return True


def _amendments(run, found, by_company, deals, contracts, subscriptions, config) -> bool:
    expansion_deal = _new_business_deal(by_company, deals, found["expansion"])
    renewal_deal = _new_business_deal(by_company, deals, found["renewal"])
    expansion_contracts = _contract_rows_for_company_deal(run, expansion_deal)
    renewal_contracts = _contract_rows_for_company_deal(run, renewal_deal)
    if len(expansion_contracts) < 2 or len(renewal_contracts) < 2:
        return False
    increase = Decimal(str(config["contract_value_increase"]))
    if Decimal(str(expansion_contracts[-1].get("total_contract_value"))) != Decimal(str(expansion_contracts[0].get("total_contract_value"))) + increase:
        return False
    return parse_date(renewal_contracts[-1].get("end_date")) == parse_date(renewal_contracts[0].get("end_date")) + timedelta(days=int(config["term_days"]))


def _canceled(run, found, by_company, deals, contracts, subscriptions) -> bool:
    deal_id = _new_business_deal(by_company, deals, found["churn"])
    sub_rows = _subscription_rows(run, deal_id)
    contract_rows = _contract_rows_for_company_deal(run, deal_id)
    if not sub_rows or latest(sub_rows).get("status") != "churned" or latest(sub_rows).get("emitted_event") != "subscription_churned":
        return False
    if not contract_rows or contract_rows[-1].get("status") != "terminated":
        return False
    for row in run.rows["dealhub.subscription"] + run.rows["dealhub.contract"]:
        if row.get("status") == "canceled":
            return False
    return True


def _soft_deleted(run, found, leads, quotes, by_company, deals) -> bool:
    company_id = found["churn"]
    domain = latest(group_rows(run.rows["hubspot.company"], "hubspot_company_id")[company_id]).get("primary_domain")
    firm_id = _firm_for_domain(run, domain)
    users = group_rows([row for row in run.rows["product.user"] if row.get("product_firm_id") == firm_id], "product_user_source_id")
    if not any(latest(rows).get("status") == "inactive" for rows in users.values()):
        return False
    twin = found["domain twin"]
    twin_leads = [rows for rows in leads.values() if latest(rows).get("hubspot_company_id") == twin]
    if len(twin_leads) != 1:
        return False
    sequence = tuple((row.get("status"), row.get("emitted_event")) for row in twin_leads[0])
    if sequence != (("new", "lead_created"), ("disqualified", "lead_disqualified")):
        return False
    if any(row.get("hubspot_deal_id") for row in twin_leads[0]):
        return False
    regression = _quotes_for_deal(run, by_company[found["stage_regression"]][0])
    return bool(regression) and regression[-1].get("status") == "expired"


def _adoption_case(run, found, by_company, deals, code_by_id, config) -> bool:
    low = found["low_adoption"]
    domain = latest(group_rows(run.rows["hubspot.company"], "hubspot_company_id")[low]).get("primary_domain")
    firm_id = _firm_for_domain(run, domain)
    usages = [row for row in run.rows["product.usage"] if row.get("product_firm_id") == firm_id]
    outcomes = {row.get("product_usage_source_id") for row in run.rows["product.outcome"]}
    if len(usages) != 1 or code_by_id.get(usages[0].get("product_workflow_id")) != "case_analysis" or usages[0].get("product_usage_source_id") in outcomes:
        return False
    churn_domain = latest(group_rows(run.rows["hubspot.company"], "hubspot_company_id")[found["churn"]]).get("primary_domain")
    churn_firm = _firm_for_domain(run, churn_domain)
    churn_usages = sorted(
        [row for row in run.rows["product.usage"] if row.get("product_firm_id") == churn_firm],
        key=lambda row: parse_timestamp(row.get("occurred_at")) or 0,
    )
    return len(churn_usages) == 2 and churn_usages[1].get("work_unit_count") < churn_usages[0].get("work_unit_count")


def _new_business_deal(by_company, deals, company_id):
    for deal_id in by_company.get(company_id, []):
        wins = [row for row in deals[deal_id] if row.get("emitted_event") == "opportunity_won" and row.get("opportunity_type") == "new_business"]
        if wins:
            return deal_id
    return by_company.get(company_id, [None])[0]


def _typed_deal(by_company, deals, company_id, opportunity_type):
    for deal_id in by_company.get(company_id, []):
        wins = [row for row in deals[deal_id] if row.get("emitted_event") == "opportunity_won" and row.get("opportunity_type") == opportunity_type]
        if wins:
            return deal_id
    return None


def _deal_won_type(rows):
    wins = [row for row in rows if row.get("emitted_event") == "opportunity_won"]
    if len(wins) != 1:
        return None
    return wins[0].get("opportunity_type")


def _contracts_for_deal(run, deal_id):
    return {row.get("dealhub_contract_id") for row in run.rows["dealhub.contract"] if row.get("hubspot_deal_id") == deal_id}


def _contract_rows_for_company_deal(run, deal_id):
    ids = _contracts_for_deal(run, deal_id)
    rows = [row for row in run.rows["dealhub.contract"] if row.get("dealhub_contract_id") in ids]
    grouped = group_rows(rows, "dealhub_contract_id")
    if len(grouped) != 1:
        return []
    return next(iter(grouped.values()))


def _subscription_rows(run, deal_id):
    contract_ids = _contracts_for_deal(run, deal_id)
    rows = [row for row in run.rows["dealhub.subscription"] if row.get("dealhub_contract_id") in contract_ids]
    grouped = group_rows(rows, "dealhub_subscription_id")
    if not grouped:
        return []
    return next(iter(grouped.values()))


def _subscription_events(run, deal_id):
    return {row.get("emitted_event") for row in _subscription_rows(run, deal_id) if row.get("emitted_event")}


def _quotes_for_deal(run, deal_id):
    rows = [row for row in run.rows["dealhub.quote"] if row.get("hubspot_deal_id") == deal_id]
    grouped = group_rows(rows, "dealhub_quote_id")
    if len(grouped) != 1:
        return []
    return next(iter(grouped.values()))


def _quote_for_deal(run, deal_id):
    rows = _quotes_for_deal(run, deal_id)
    if not rows:
        return None
    return rows[0].get("dealhub_quote_id")


def _latest_counts(grouped, field_name):
    counts = defaultdict(int)
    for rows in grouped.values():
        counts[latest(rows).get(field_name)] += 1
    return counts


def _compare_alloc(run, defects, label, expected, observed) -> None:
    keys = set(expected) | set(observed)
    for key in sorted(keys, key=lambda item: str(item)):
        if int(expected.get(key, 0)) != int(observed.get(key, 0)):
            add_defect(
                defects, run, "distributions_and_edge_cases",
                f"Latest {label} equals a largest-remainder allocation.",
                field=str(key), actual=f"allocated={expected.get(key, 0)} observed={observed.get(key, 0)}",
            )


def _mix_rows(weights, allocated, observed):
    keys = sorted(set(weights) | set(allocated) | set(observed), key=str)
    return [
        (str(key), str(weights.get(key, 0)), str(allocated.get(key, 0)), str(observed.get(key, 0)))
        for key in keys
    ]


def _renewed(subscriptions) -> int:
    return sum(
        1 for rows in subscriptions.values()
        if any(row.get("emitted_event") == "subscription_renewed" and row.get("status") == "active" for row in rows)
    )


def _expanded(subscriptions) -> int:
    return sum(
        1 for rows in subscriptions.values()
        if any(row.get("emitted_event") == "subscription_expanded" and row.get("status") == "active" for row in rows)
    )


def _churned(subscriptions) -> int:
    return sum(
        1 for rows in subscriptions.values()
        if latest(rows).get("status") == "churned" and latest(rows).get("emitted_event") == "subscription_churned"
    )


def _parent_count(row) -> int:
    return sum(row.get(name) is not None for name in ("hubspot_company_id", "hubspot_contact_id", "hubspot_lead_id", "hubspot_deal_id"))


def _clicks_exceed(row) -> bool:
    clicks = row.get("click_count")
    impressions = row.get("impression_count")
    return isinstance(clicks, int) and isinstance(impressions, int) and clicks > impressions


def _duplicate_contacts(contacts) -> int:
    emails = defaultdict(set)
    for contact_id, rows in contacts.items():
        email = latest(rows).get("email_normalized")
        if email:
            emails[email].add(contact_id)
    return sum(len(ids) for ids in emails.values() if len(ids) > 1)


def _domain_matches(firms, companies) -> int:
    domains = {row.get("primary_domain") for rows in companies.values() for row in rows if row.get("primary_domain")}
    return sum(1 for row in firms if row.get("primary_domain") in domains)


def _churn_without_later_booking(subscriptions, bookings) -> bool:
    found = False
    for subscription_id, rows in subscriptions.items():
        churns = [row for row in rows if row.get("emitted_event") == "subscription_churned"]
        if not churns:
            continue
        churn_at = parse_timestamp(churns[0].get("observed_at"))
        later = [
            booking for booking in bookings
            if booking.get("dealhub_subscription_id") == subscription_id
            and parse_timestamp(booking.get("booked_at")) is not None
            and parse_timestamp(booking.get("booked_at")) >= churn_at
        ]
        if not later:
            found = True
    return found
