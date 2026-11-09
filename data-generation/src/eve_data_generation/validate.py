"""Contract checks for a generated dataset."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime

from eve_data_generation.contracts import Contract
from eve_data_generation.errors import ValidationError

FORBIDDEN = {
    "account_id",
    "contact_id",
    "lead_id",
    "opportunity_id",
    "quote_id",
    "contract_id",
    "subscription_id",
    "booking_id",
    "campaign_id",
    "campaign_performance_id",
    "marketing_touch_id",
    "activity_id",
    "product_user_id",
    "ai_workflow_id",
    "product_usage_id",
    "product_outcome_id",
    "lifecycle_event_id",
    "surviving_account_id",
    "surviving_contact_id",
    "surviving_lead_id",
    "surviving_opportunity_id",
    "surviving_subscription_id",
    "surviving_product_user_id",
    "commercial_status",
    "effective_start",
    "effective_end",
    "is_current",
    "customer_converted",
    "adoption_reached",
    "lifecycle_event",
}

ID_PREFIX = {
    "dealhub_quote_id": "qte_",
    "dealhub_contract_id": "ctr_",
    "dealhub_subscription_id": "sub_",
    "dealhub_booking_id": "bkg_",
    "marketing_campaign_id": "cmp_",
    "marketing_touch_source_id": "tch_",
    "product_firm_id": "frm_",
    "product_user_source_id": "usr_",
    "product_workflow_id": "wf_",
    "product_usage_source_id": "usg_",
    "product_outcome_source_id": "out_",
}

HUBSPOT_IDS = {
    "hubspot_company_id",
    "hubspot_contact_id",
    "hubspot_lead_id",
    "hubspot_deal_id",
    "hubspot_activity_id",
}

DOCUMENT_NUMBERS = {
    "dealhub.quote": ("dealhub_quote_id", "quote_number"),
    "dealhub.contract": ("dealhub_contract_id", "contract_number"),
    "dealhub.subscription": ("dealhub_subscription_id", "subscription_number"),
    "dealhub.booking": ("dealhub_booking_id", "booking_number"),
    "marketing.campaign": ("marketing_campaign_id", "campaign_code"),
    "product.ai_workflow": ("product_workflow_id", "workflow_code"),
}

PARENTS = ("hubspot_company_id", "hubspot_contact_id", "hubspot_lead_id", "hubspot_deal_id")
TOUCH_PARENTS = ("hubspot_contact_id", "hubspot_lead_id", "hubspot_company_id")


def validate_dataset(dataset, contracts: dict[str, Contract]) -> None:
    for contract_id, contract in contracts.items():
        rows = dataset.rows.get(contract_id, [])
        _keys(contract, rows)
        for row in rows:
            if set(row) & FORBIDDEN:
                raise ValidationError(f"{contract_id} contains a canonical column")
            if row["delivery_id"] != dataset.delivery_id:
                raise ValidationError("delivery_id is not stable for the run")
            _identifier_shape(row)
    _relationships(dataset, contracts)
    _documents(dataset)
    _leads(dataset)
    _deals(dataset)
    _agreements(dataset)
    _commercial(dataset)
    _product(dataset)
    _subscriptions(dataset)


def _keys(contract: Contract, rows: list[dict]) -> None:
    seen = set()
    for row in rows:
        key = tuple(row[name] for name in contract.observation_key)
        if key in seen:
            raise ValidationError(f"duplicate observation key on {contract.id}")
        seen.add(key)


def _identifier_shape(row: dict) -> None:
    for name, value in row.items():
        if not isinstance(value, str) or not value:
            continue
        if name in HUBSPOT_IDS and not re.fullmatch(r"[0-9]+", value):
            raise ValidationError(f"{name} is not a numeric HubSpot identifier")
        prefix = ID_PREFIX.get(name)
        if prefix and not value.startswith(prefix):
            raise ValidationError(f"{name} is missing prefix {prefix}")


def _group(rows: list[dict], field: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row[field]].append(row)
    for items in grouped.values():
        if items and "observed_at" in items[0]:
            items.sort(key=lambda item: item["observed_at"])
    return grouped


def _in_effect(rows: list[dict], moment: datetime) -> dict | None:
    eligible = [row for row in rows if row["observed_at"] <= moment]
    if not eligible:
        return None
    return eligible[-1]


def _ids(dataset, contract_id: str, field: str) -> set[str]:
    return {row[field] for row in dataset.rows.get(contract_id, [])}


def _relationships(dataset, contracts: dict[str, Contract]) -> None:
    for contract in contracts.values():
        for relationship in contract.relationships:
            parents = _ids(dataset, relationship.contract_id, relationship.reference_field)
            for row in dataset.rows.get(contract.id, []):
                value = row.get(relationship.field)
                if value is None:
                    if relationship.required:
                        raise ValidationError(f"{contract.id}.{relationship.field} is required")
                    continue
                if value not in parents:
                    raise ValidationError(
                        f"{contract.id}.{relationship.field} cites {value} which was not emitted"
                    )


def _documents(dataset) -> None:
    for contract_id, (identifier, number) in DOCUMENT_NUMBERS.items():
        by_id: dict[str, set[str]] = defaultdict(set)
        owners: dict[str, set[str]] = defaultdict(set)
        for row in dataset.rows.get(contract_id, []):
            by_id[row[identifier]].add(row[number])
            owners[row[number]].add(row[identifier])
        for source_id, numbers in by_id.items():
            if len(numbers) != 1:
                raise ValidationError(f"{number} is not stable for {source_id}")
        for document, source_ids in owners.items():
            if len(source_ids) != 1:
                raise ValidationError(f"{number} {document} is used by more than one source identifier")


def _leads(dataset) -> None:
    for lead_id, rows in _group(dataset.rows.get("hubspot.lead", []), "hubspot_lead_id").items():
        created = [row for row in rows if row["emitted_event"] == "lead_created"]
        if len(created) != 1 or created[0]["status"] != "new" or created[0]["observed_at"] != created[0]["created_at"]:
            raise ValidationError(f"lead {lead_id} does not open with lead_created")
        if any(row["created_at"] != rows[0]["created_at"] for row in rows):
            raise ValidationError(f"lead {lead_id} changes created_at")
        statuses = {row["status"] for row in rows}
        if "qualified" in statuses and "disqualified" in statuses:
            raise ValidationError(f"lead {lead_id} is both qualified and disqualified")
        if any(row["status"] == "working" and row["emitted_event"] is not None for row in rows):
            raise ValidationError(f"lead {lead_id} emits an event while working")
        converted = [row for row in rows if row["emitted_event"] == "lead_converted"]
        qualified = [row for row in rows if row["emitted_event"] == "lead_qualified"]
        if converted:
            if not converted[0]["hubspot_deal_id"]:
                raise ValidationError(f"converted lead {lead_id} has no deal")
            if not qualified or qualified[0]["observed_at"] >= converted[0]["observed_at"]:
                raise ValidationError(f"converted lead {lead_id} is not preceded by lead_qualified")
        for row in rows:
            if row["emitted_event"] != "lead_converted" and row["hubspot_deal_id"] is not None:
                raise ValidationError(f"lead {lead_id} cites a deal before conversion")
            if row["hubspot_company_id"] is None and row["hubspot_contact_id"] is None and row["status"] == "converted":
                raise ValidationError(f"orphan lead {lead_id} is converted")


def _deals(dataset) -> None:
    for deal_id, rows in _group(dataset.rows.get("hubspot.deal", []), "hubspot_deal_id").items():
        opening = rows[0]
        if opening["stage"] != "discovery" or opening["emitted_event"] != "opportunity_opened":
            raise ValidationError(f"deal {deal_id} does not open at discovery")
        if opening["observed_at"] != opening["created_at"]:
            raise ValidationError(f"deal {deal_id} opening observed_at differs from created_at")
        if any(row["created_at"] != opening["created_at"] for row in rows):
            raise ValidationError(f"deal {deal_id} changes created_at")
        if any(row["hubspot_company_id"] != opening["hubspot_company_id"] for row in rows):
            raise ValidationError(f"deal {deal_id} changes company")
        events = {row["emitted_event"] for row in rows}
        if "opportunity_won" in events and "opportunity_lost" in events:
            raise ValidationError(f"deal {deal_id} is both won and lost")
        for row in rows:
            if row["opportunity_type"] == "new_business" and row["dealhub_subscription_id"] is not None:
                raise ValidationError(f"new-business deal {deal_id} cites a subscription")
            if row["opportunity_type"] in {"expansion", "renewal"} and not row["dealhub_subscription_id"]:
                raise ValidationError(f"{row['opportunity_type']} deal {deal_id} has no subscription")


def _agreements(dataset) -> None:
    contacts = _group(dataset.rows.get("hubspot.contact", []), "hubspot_contact_id")
    leads = _group(dataset.rows.get("hubspot.lead", []), "hubspot_lead_id")
    deals = _group(dataset.rows.get("hubspot.deal", []), "hubspot_deal_id")
    subscriptions = _group(dataset.rows.get("dealhub.subscription", []), "dealhub_subscription_id")
    for row in dataset.rows.get("hubspot.deal", []):
        _same_company(contacts, row["hubspot_contact_id"], row["hubspot_company_id"], row["observed_at"], "deal contact")
        if row["dealhub_subscription_id"]:
            sub_rows = subscriptions.get(row["dealhub_subscription_id"], [])
            if not sub_rows or any(item["hubspot_company_id"] != row["hubspot_company_id"] for item in sub_rows):
                raise ValidationError("deal subscription company does not match the deal")
    for row in dataset.rows.get("marketing.touch", []):
        if not row["marketing_campaign_id"] or not any(row[name] for name in TOUCH_PARENTS):
            raise ValidationError("a touch needs a campaign and a HubSpot parent")
        _same_company(contacts, row["hubspot_contact_id"], row["hubspot_company_id"], row["occurred_at"], "touch contact")
        _same_company(leads, row["hubspot_lead_id"], row["hubspot_company_id"], row["occurred_at"], "touch lead")
    for row in dataset.rows.get("hubspot.activity", []):
        if not any(row[name] for name in PARENTS):
            raise ValidationError("an activity needs a parent")
        _same_company(contacts, row["hubspot_contact_id"], row["hubspot_company_id"], row["occurred_at"], "activity contact")
        _same_company(leads, row["hubspot_lead_id"], row["hubspot_company_id"], row["occurred_at"], "activity lead")
        if row["hubspot_deal_id"] and row["hubspot_company_id"]:
            effective = _in_effect(deals.get(row["hubspot_deal_id"], []), row["occurred_at"])
            if effective is None or effective["hubspot_company_id"] != row["hubspot_company_id"]:
                raise ValidationError("activity company does not match the deal at occurred_at")
        if row["hubspot_deal_id"] and _in_effect(deals.get(row["hubspot_deal_id"], []), row["occurred_at"]) is None:
            raise ValidationError("activity cites a deal before that deal exists")


def _same_company(grouped, source_id, company_id, moment, label: str) -> None:
    if not source_id or not company_id:
        return
    effective = _in_effect(grouped.get(source_id, []), moment)
    if effective is None:
        raise ValidationError(f"{label} has no observation in effect")
    parent_company = effective.get("hubspot_company_id")
    if parent_company is not None and parent_company != company_id:
        raise ValidationError(f"{label} company does not agree")


def _commercial(dataset) -> None:
    deals = _group(dataset.rows.get("hubspot.deal", []), "hubspot_deal_id")
    quotes = _group(dataset.rows.get("dealhub.quote", []), "dealhub_quote_id")
    contracts = _group(dataset.rows.get("dealhub.contract", []), "dealhub_contract_id")
    bookings = dataset.rows.get("dealhub.booking", [])
    contracts_by_deal = defaultdict(set)
    for rows in contracts.values():
        contracts_by_deal[rows[0]["hubspot_deal_id"]].add(rows[0]["dealhub_contract_id"])
    for deal_id, rows in deals.items():
        wins = [row for row in rows if row["emitted_event"] == "opportunity_won"]
        if len(wins) > 1:
            raise ValidationError(f"deal {deal_id} wins more than once")
        if not wins:
            continue
        win = wins[0]
        if win["stage"] != "closed_won":
            raise ValidationError(f"winning deal {deal_id} is not closed_won")
        if win["opportunity_type"] == "new_business":
            if len(contracts_by_deal[deal_id]) != 1:
                raise ValidationError(f"new-business win {deal_id} does not have one contract")
            contract_id = next(iter(contracts_by_deal[deal_id]))
            first = min(contracts[contract_id], key=lambda item: item["observed_at"])
            effective = _in_effect(quotes.get(first["dealhub_quote_id"], []), first["observed_at"])
            if (
                effective is None
                or effective["hubspot_deal_id"] != deal_id
                or effective["status"] != "accepted"
                or effective["quoted_amount"] is None
            ):
                raise ValidationError(f"new-business win {deal_id} needs an accepted quote")
            deal_bookings = [booking for booking in bookings if booking["hubspot_deal_id"] == deal_id]
            if len(deal_bookings) != 1 or deal_bookings[0]["booking_type"] != "new_business":
                raise ValidationError(f"new-business win {deal_id} needs one new-business booking")
        elif win["opportunity_type"] in {"expansion", "renewal"}:
            if contracts_by_deal[deal_id]:
                raise ValidationError(f"{win['opportunity_type']} deal {deal_id} created a contract")
        else:
            raise ValidationError(f"unexpected winning type on {deal_id}")
    for booking in bookings:
        effective = _in_effect(deals.get(booking["hubspot_deal_id"], []), booking["booked_at"])
        if effective is None or effective["opportunity_type"] != booking["booking_type"]:
            raise ValidationError("booking_type does not match the deal in effect at booked_at")
        if booking["booking_amount"] < 0:
            raise ValidationError("booking_amount is negative")
    for rows in contracts.values():
        if any(row["end_date"] < row["start_date"] for row in rows):
            raise ValidationError("contract end_date is before start_date")
        if len({row["contract_number"] for row in rows}) != 1:
            raise ValidationError("contract_number changed")
    for quote_rows in quotes.values():
        for quote in quote_rows:
            if quote["status"] != "draft" and quote["quoted_amount"] is None:
                raise ValidationError("quoted_amount is required when the quote is no longer draft")


def _subscriptions(dataset) -> None:
    bookings = dataset.rows.get("dealhub.booking", [])
    for subscription_id, rows in _group(dataset.rows.get("dealhub.subscription", []), "dealhub_subscription_id").items():
        churns = [row for row in rows if row["emitted_event"] == "subscription_churned"]
        if len(churns) > 1:
            raise ValidationError(f"subscription {subscription_id} churns more than once")
        if any(row["term_end"] < row["term_start"] for row in rows):
            raise ValidationError(f"subscription {subscription_id} term is reversed")
        if any(row["seat_count"] < 0 for row in rows):
            raise ValidationError(f"subscription {subscription_id} has a negative seat count")
        if churns:
            churn_at = churns[0]["observed_at"]
            later = [
                booking
                for booking in bookings
                if booking["dealhub_subscription_id"] == subscription_id and booking["booked_at"] >= churn_at
            ]
            if later:
                raise ValidationError(f"subscription {subscription_id} has a booking at churn")
            if churns[0]["status"] != "churned":
                raise ValidationError("churn status is not churned")
        for row in rows:
            if row["emitted_event"] in {"subscription_renewed", "subscription_expanded"} and row["status"] != "active":
                raise ValidationError("renewal or expansion is not active")


def _product(dataset) -> None:
    users = _group(dataset.rows.get("product.user", []), "product_user_source_id")
    usages = {row["product_usage_source_id"]: row for row in dataset.rows.get("product.usage", [])}
    cited = set()
    for row in dataset.rows.get("product.usage", []):
        if row["work_unit_count"] < 1:
            raise ValidationError("work_unit_count must be at least 1")
        effective = _in_effect(users.get(row["product_user_source_id"], []), row["occurred_at"])
        if effective is None or effective["product_firm_id"] != row["product_firm_id"]:
            raise ValidationError("usage firm does not match the user in effect")
    for row in dataset.rows.get("product.outcome", []):
        usage = usages.get(row["product_usage_source_id"])
        if usage is None:
            raise ValidationError("outcome cites a missing usage")
        if row["product_usage_source_id"] in cited:
            raise ValidationError("more than one outcome cites a usage")
        cited.add(row["product_usage_source_id"])
        if row["occurred_at"] < usage["occurred_at"]:
            raise ValidationError("outcome is before its usage")
        for field in ("product_user_source_id", "product_firm_id", "product_workflow_id"):
            if row[field] != usage[field]:
                raise ValidationError("outcome does not match its usage")
