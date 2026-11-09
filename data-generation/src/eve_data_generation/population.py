"""Baseline sampler. DATA-004 can replace this function; it does not live here.

The dataset builder calls the HubSpot, DealHub, Marketing, and Product
generators in referential order. This module decides volumes, rates, and
relationships. Entity generators own field shape and lifecycle paths.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from eve_data_generation.config import Bounds, Config
from eve_data_generation.dealhub import DealHubGenerator
from eve_data_generation.errors import GenerationError
from eve_data_generation.hubspot import HubSpotGenerator
from eve_data_generation.marketing import MarketingGenerator
from eve_data_generation.product import ProductGenerator
from eve_data_generation.sampling import assign_labels, choose_share, inclusive_dates
from eve_data_generation.world import World


def baseline_population(world: World) -> None:
    config = world.config
    hubspot = HubSpotGenerator(world)
    dealhub = DealHubGenerator(world)
    marketing = MarketingGenerator(world)
    product = ProductGenerator(world)

    campaigns = _campaigns(world, marketing)
    _performance(world, marketing, campaigns)
    workflows = [
        product.add_workflow(entry.code, entry.name)
        for entry in config.workflows
    ]

    companies = _companies(world, hubspot)
    contacts = _contacts(world, hubspot, companies)
    leads = _leads(world, hubspot, companies, campaigns)
    _touches(world, marketing, campaigns, companies, contacts, leads)

    pre_count, single_indexes = _activity_plan(world)
    _pre_deal_activities(world, hubspot, companies, leads, pre_count, single_indexes)

    new_business, subscriptions = _new_business(world, hubspot, dealhub, companies, leads)
    all_deals = _lifecycle(world, hubspot, dealhub, companies, subscriptions, new_business)
    _null_deal_amounts(world, all_deals)
    _post_deal_activities(world, hubspot, all_deals, pre_count, single_indexes)

    firms = _firms(world, product, companies, new_business)
    _usage(world, product, firms, workflows)


def _campaigns(world: World, marketing: MarketingGenerator) -> list[dict]:
    config = world.config
    if config.campaign_count == 0:
        return []
    channels = assign_labels(world.rng, config.campaign_count, config.channel_mix)
    campaigns = []
    for index, channel in enumerate(channels):
        name = config.campaign_names[index % len(config.campaign_names)]
        if config.campaign_count > 1:
            name = f"{name} {index + 1}"
        campaigns.append(marketing.add_campaign(name, channel))
    return campaigns


def _performance(world: World, marketing: MarketingGenerator, campaigns: list[dict]) -> None:
    dates = inclusive_dates(world.config.start_date, world.config.end_date)
    slots = [(campaign, day) for campaign in campaigns for day in dates]
    nulls = set(choose_share(world.rng, len(slots), world.config.null_performance_measure_rate))
    exceeds = set(choose_share(world.rng, len(slots), world.config.clicks_exceed_impressions_rate))
    for index, (campaign, day) in enumerate(slots):
        impressions = world.integer("impression_count")
        excess = world.integer("click_excess")
        spend = world.money("spend_amount")
        plain_clicks = world.rng.randint(0, impressions)
        clicks = impressions + excess if index in exceeds else plain_clicks
        if index in nulls:
            spend = None
        marketing.add_performance(
            campaign["marketing_campaign_id"],
            day,
            spend,
            impressions,
            clicks,
        )


def _companies(world: World, hubspot: HubSpotGenerator) -> list[dict]:
    config = world.config
    nulls = set(choose_share(world.rng, config.account_count, config.null_company_domain_rate))
    changes = set(choose_share(world.rng, config.account_count, config.company_change_rate))
    companies = []
    for index in range(config.account_count):
        prefix = config.firm_prefixes[index % len(config.firm_prefixes)]
        suffix = config.hubspot_firm_suffixes[index % len(config.hubspot_firm_suffixes)]
        stage = config.lifecycle_stage_catalog[index % len(config.lifecycle_stage_catalog)]
        company = hubspot.add_company(
            firm_name=f"{prefix} {suffix}",
            primary_domain=None if index in nulls else f"firm-{index + 1}.example",
            state=world.choice(config.states),
            segment=world.choice(world.allowed("hubspot.company", "segment")),
            practice_focus=world.choice(config.practice_focuses),
            icp_fit=world.choice(world.allowed("hubspot.company", "icp_fit")),
            owner_name=world.choice(config.owner_names),
            lifecycle_stage=stage,
        )
        company["name_index"] = index
        company["contacts"] = []
        companies.append(company)
    for index in sorted(changes):
        company = companies[index]
        alternatives = [
            value
            for value in config.lifecycle_stage_catalog
            if value != company["hubspot_lifecycle_stage"]
        ]
        hubspot.add_company(
            firm_name=company["firm_name"],
            primary_domain=company["primary_domain"],
            state=company["state"],
            segment=company["segment"],
            practice_focus=company["practice_focus"],
            icp_fit=company["icp_fit"],
            owner_name=company["owner_name"],
            lifecycle_stage=alternatives[index % len(alternatives)],
            company_id=company["hubspot_company_id"],
        )
    return companies


def _contacts(world: World, hubspot: HubSpotGenerator, companies: list[dict]) -> list[dict]:
    contacts = []
    for company in companies:
        for _ in range(world.config.contacts_per_account):
            person = world.choice(world.config.person_names)
            email = _email(person, len(contacts))
            contact = hubspot.add_contact(
                company_id=company["hubspot_company_id"],
                full_name=person,
                email_normalized=email,
                title=world.choice(world.config.titles),
                buying_role=world.choice(world.allowed("hubspot.contact", "buying_role")),
            )
            company["contacts"].append(contact)
            contacts.append(contact)
    _duplicate_emails(world, contacts)
    return contacts


def _duplicate_emails(world: World, contacts: list[dict]) -> None:
    if not contacts:
        return
    recipients = set(
        choose_share(world.rng, len(contacts), world.config.duplicate_contact_email_rate)
    )
    if not recipients:
        return
    if len(recipients) == len(contacts):
        source = 0
    else:
        source = next(index for index in range(len(contacts)) if index not in recipients)
    email = contacts[source]["email_normalized"]
    for index in recipients:
        if index == source:
            continue
        contact_id = contacts[index]["hubspot_contact_id"]
        contacts[index]["email_normalized"] = email
        for row in world.rows["hubspot.contact"]:
            if row["hubspot_contact_id"] == contact_id:
                row["email_normalized"] = email


def _leads(world: World, hubspot: HubSpotGenerator, companies: list[dict], campaigns: list[dict]) -> list[dict]:
    config = world.config
    if config.lead_count == 0:
        return []
    labels = assign_labels(world.rng, config.lead_count, config.lead_status_mix)
    orphans = set(choose_share(world.rng, config.lead_count, config.orphan_lead_rate))
    labels = _orphans_are_not_converted(labels, orphans)
    converted = [index for index, label in enumerate(labels) if label == "converted"]
    if converted and not companies:
        raise GenerationError("a converted lead needs a company for its deal")
    company_for = [None] * config.lead_count
    for offset, index in enumerate(converted):
        company_for[index] = companies[offset % len(companies)]
    others = [
        index
        for index, label in enumerate(labels)
        if index not in orphans and label != "converted"
    ]
    for offset, index in enumerate(others):
        if companies:
            company_for[index] = companies[offset % len(companies)]
    reserved = {index: world.ids.hubspot() for index in converted}
    leads = []
    for index, status in enumerate(labels):
        company = company_for[index]
        contact_id = None
        company_id = None
        if company is not None and company["contacts"]:
            contact_id = company["contacts"][index % len(company["contacts"])]["hubspot_contact_id"]
            company_id = company["hubspot_company_id"]
        elif company is not None:
            company_id = company["hubspot_company_id"]
        campaign_id = None
        if campaigns:
            campaign_id = campaigns[index % len(campaigns)]["marketing_campaign_id"]
        lead = hubspot.add_lead(
            latest_status=status,
            company_id=company_id,
            contact_id=contact_id,
            campaign_id=campaign_id,
            deal_id=reserved.get(index),
        )
        leads.append(lead)
    return leads


def _orphans_are_not_converted(labels: list[str], orphans: set[int]) -> list[str]:
    updated = list(labels)
    for index in sorted(orphans):
        if updated[index] != "converted":
            continue
        swap = next(
            (
                other
                for other in range(len(updated))
                if other not in orphans and updated[other] != "converted"
            ),
            None,
        )
        if swap is None:
            updated[index] = "disqualified"
        else:
            updated[index], updated[swap] = updated[swap], updated[index]
    return updated


def _touches(world, marketing, campaigns, companies, contacts, leads) -> None:
    count = world.config.touch_count
    if count == 0:
        return
    if not campaigns:
        raise GenerationError("attribution touches need a campaign")
    if not companies and not contacts and not leads:
        raise GenerationError("attribution touches need a HubSpot parent")
    for index in range(count):
        campaign_id = campaigns[index % len(campaigns)]["marketing_campaign_id"]
        contact_id = lead_id = company_id = None
        kind = world.rng.randrange(3)
        if kind == 0 and contacts:
            contact = contacts[world.rng.randrange(len(contacts))]
            contact_id = contact["hubspot_contact_id"]
            company_id = contact["hubspot_company_id"]
        elif kind == 1 and leads:
            lead = leads[world.rng.randrange(len(leads))]
            lead_id = lead["hubspot_lead_id"]
            company_id = lead["hubspot_company_id"]
        elif companies:
            company_id = companies[world.rng.randrange(len(companies))]["hubspot_company_id"]
        elif contacts:
            contact = contacts[world.rng.randrange(len(contacts))]
            contact_id = contact["hubspot_contact_id"]
            company_id = contact["hubspot_company_id"]
        else:
            lead = leads[world.rng.randrange(len(leads))]
            lead_id = lead["hubspot_lead_id"]
            company_id = lead["hubspot_company_id"]
        marketing.add_touch(campaign_id, contact_id, lead_id, company_id)


def _activity_plan(world: World) -> tuple[int, set[int]]:
    count = world.config.activity_count
    pre_count = count // 2 if count >= 2 else count
    selected = set(choose_share(world.rng, count, world.config.single_parent_activity_rate))
    return pre_count, selected


def _subject(config: Config, activity_type: str, index: int) -> str:
    phrases = config.activity_subjects[activity_type]
    return phrases[index % len(phrases)]


def _pre_deal_activities(world, hubspot, companies, leads, pre_count, single_indexes) -> None:
    if pre_count == 0:
        return
    if not companies:
        raise GenerationError("pre-deal activities need a company")
    types = world.allowed("hubspot.activity", "activity_type")
    for index in range(pre_count):
        company = companies[index % len(companies)]
        activity_type = types[index % len(types)]
        subject = _subject(world.config, activity_type, index)
        if index in single_indexes:
            hubspot.add_activity(activity_type, subject, company["hubspot_company_id"], None, None, None)
            continue
        if not company["contacts"]:
            raise GenerationError("a multi-parent activity needs a contact on the company")
        contact_id = company["contacts"][0]["hubspot_contact_id"]
        lead = next(
            (item for item in leads if item["hubspot_company_id"] == company["hubspot_company_id"]),
            None,
        )
        hubspot.add_activity(
            activity_type,
            subject,
            company["hubspot_company_id"],
            contact_id,
            None if lead is None else lead["hubspot_lead_id"],
            None,
        )


def _new_business(world, hubspot, dealhub, companies, leads) -> tuple[list[dict], list[dict]]:
    converted = [lead for lead in leads if lead["status"] == "converted"]
    if not converted:
        return [], []
    stages = assign_labels(world.rng, len(converted), world.config.stage_mix)
    deals = []
    subscriptions = []
    companies_by_id = {company["hubspot_company_id"]: company for company in companies}
    for lead, stage in zip(converted, stages):
        company = companies_by_id[lead["hubspot_company_id"]]
        deal = hubspot.add_deal(
            company_id=lead["hubspot_company_id"],
            company_name=company["firm_name"],
            contact_id=lead["hubspot_contact_id"],
            lead_id=lead["hubspot_lead_id"],
            subscription_id=None,
            opportunity_type="new_business",
            latest_stage=stage,
            amount=world.money("hubspot_amount"),
            owner_name=world.choice(world.config.owner_names),
            expected_close_date=_draw_date(world),
            deal_id=lead["hubspot_deal_id"],
        )
        deals.append(deal)
        if stage == "closed_won":
            subscriptions.append(_open_commercial(world, dealhub, deal))
    return deals, subscriptions


def _open_commercial(world: World, dealhub: DealHubGenerator, deal: dict) -> dict:
    win_at = deal["win_at"]
    quote = dealhub.add_accepted_quote(
        deal["hubspot_deal_id"],
        deal["hubspot_company_id"],
        world.money("quoted_amount"),
        win_at,
    )
    start = win_at.date()
    end = _shift_date(start, world.config.term_days, world.config.end_date)
    contract = dealhub.add_contract(
        quote_id=quote["dealhub_quote_id"],
        deal_id=deal["hubspot_deal_id"],
        company_id=deal["hubspot_company_id"],
        total_contract_value=world.money("total_contract_value"),
        start_date=start,
        end_date=end,
        observed_at=win_at,
    )
    subscription = dealhub.add_subscription(
        contract_id=contract["dealhub_contract_id"],
        company_id=deal["hubspot_company_id"],
        plan_code=world.choice(world.config.plan_codes),
        seat_count=world.integer("seat_count"),
        recurring_amount=world.money("recurring_amount"),
        billing_frequency=world.choice(world.allowed("dealhub.subscription", "billing_frequency")),
        term_start=start,
        term_end=end,
        observed_at=win_at,
        status="active",
        emitted_event=None,
    )
    dealhub.add_booking(
        company_id=deal["hubspot_company_id"],
        deal_id=deal["hubspot_deal_id"],
        contract_id=contract["dealhub_contract_id"],
        subscription_id=subscription["dealhub_subscription_id"],
        booking_type="new_business",
        booking_amount=world.money("booking_amount_new_business"),
        booked_at=win_at,
    )
    return {
        "dealhub_subscription_id": subscription["dealhub_subscription_id"],
        "subscription_number": subscription["subscription_number"],
        "dealhub_contract_id": contract["dealhub_contract_id"],
        "contract_number": contract["contract_number"],
        "dealhub_quote_id": quote["dealhub_quote_id"],
        "hubspot_company_id": deal["hubspot_company_id"],
        "new_business_deal_id": deal["hubspot_deal_id"],
        "plan_code": world.rows["dealhub.subscription"][-1]["plan_code"],
        "seat_count": world.rows["dealhub.subscription"][-1]["seat_count"],
        "recurring_amount": world.rows["dealhub.subscription"][-1]["recurring_amount"],
        "billing_frequency": world.rows["dealhub.subscription"][-1]["billing_frequency"],
        "term_start": start,
        "term_end": end,
        "total_contract_value": contract["total_contract_value"],
        "start_date": start,
        "end_date": end,
    }


def _lifecycle(world, hubspot, dealhub, companies, subscriptions, new_business) -> list[dict]:
    expansion = set(choose_share(world.rng, len(subscriptions), world.config.expansion_rate))
    renewal = set(choose_share(world.rng, len(subscriptions), world.config.renewal_rate))
    churn = set(choose_share(world.rng, len(subscriptions), world.config.churn_rate))
    deals = list(new_business)
    companies_by_id = {company["hubspot_company_id"]: company for company in companies}
    for index in range(len(subscriptions)):
        if index in expansion:
            deals.append(_follow_on(world, hubspot, dealhub, subscriptions[index], companies_by_id, "expansion"))
    for index in range(len(subscriptions)):
        if index in renewal:
            deals.append(_follow_on(world, hubspot, dealhub, subscriptions[index], companies_by_id, "renewal"))
    for index in range(len(subscriptions)):
        if index in churn:
            _churn(world, dealhub, subscriptions[index])
    return deals


def _follow_on(world, hubspot, dealhub, subscription, companies_by_id, opportunity_type: str) -> dict:
    company = companies_by_id[subscription["hubspot_company_id"]]
    contact_id = company["contacts"][0]["hubspot_contact_id"] if company["contacts"] else None
    deal = hubspot.add_deal(
        company_id=subscription["hubspot_company_id"],
        company_name=company["firm_name"],
        contact_id=contact_id,
        lead_id=None,
        subscription_id=subscription["dealhub_subscription_id"],
        opportunity_type=opportunity_type,
        latest_stage="closed_won",
        amount=world.money("hubspot_amount"),
        owner_name=world.choice(world.config.owner_names),
        expected_close_date=_draw_date(world),
    )
    win_at = deal["win_at"]
    if opportunity_type == "expansion":
        subscription["seat_count"] += 1
        subscription["recurring_amount"] = _nudge(
            subscription["recurring_amount"],
            world.config.amount_ranges["recurring_amount"],
            Decimal("10.00"),
        )
        event = "subscription_expanded"
        booking_range = "booking_amount_expansion"
    else:
        subscription["term_end"] = _shift_date(
            subscription["term_end"],
            world.config.term_days,
            world.config.end_date,
        )
        subscription["end_date"] = _shift_date(
            subscription["end_date"],
            world.config.term_days,
            world.config.end_date,
        )
        event = "subscription_renewed"
        booking_range = "booking_amount_renewal"
    dealhub.add_subscription(
        contract_id=subscription["dealhub_contract_id"],
        company_id=subscription["hubspot_company_id"],
        plan_code=subscription["plan_code"],
        seat_count=subscription["seat_count"],
        recurring_amount=subscription["recurring_amount"],
        billing_frequency=subscription["billing_frequency"],
        term_start=subscription["term_start"],
        term_end=subscription["term_end"],
        observed_at=win_at,
        status="active",
        emitted_event=event,
        subscription_id=subscription["dealhub_subscription_id"],
        subscription_number=subscription["subscription_number"],
    )
    if opportunity_type == "expansion":
        subscription["total_contract_value"] = _nudge(
            subscription["total_contract_value"],
            world.config.amount_ranges["total_contract_value"],
            Decimal("100.00"),
        )
    dealhub.add_contract(
        quote_id=subscription["dealhub_quote_id"],
        deal_id=subscription["new_business_deal_id"],
        company_id=subscription["hubspot_company_id"],
        total_contract_value=subscription["total_contract_value"],
        start_date=subscription["start_date"],
        end_date=subscription["end_date"],
        observed_at=win_at,
        contract_id=subscription["dealhub_contract_id"],
        contract_number=subscription["contract_number"],
    )
    dealhub.add_booking(
        company_id=subscription["hubspot_company_id"],
        deal_id=deal["hubspot_deal_id"],
        contract_id=subscription["dealhub_contract_id"],
        subscription_id=subscription["dealhub_subscription_id"],
        booking_type=opportunity_type,
        booking_amount=world.money(booking_range),
        booked_at=win_at,
    )
    return deal


def _churn(world: World, dealhub: DealHubGenerator, subscription: dict) -> None:
    observed_at = world.timestamp()
    dealhub.add_subscription(
        contract_id=subscription["dealhub_contract_id"],
        company_id=subscription["hubspot_company_id"],
        plan_code=subscription["plan_code"],
        seat_count=subscription["seat_count"],
        recurring_amount=subscription["recurring_amount"],
        billing_frequency=subscription["billing_frequency"],
        term_start=subscription["term_start"],
        term_end=subscription["term_end"],
        observed_at=observed_at,
        status="churned",
        emitted_event="subscription_churned",
        subscription_id=subscription["dealhub_subscription_id"],
        subscription_number=subscription["subscription_number"],
    )


def _null_deal_amounts(world: World, deals: list[dict]) -> None:
    selected = set(choose_share(world.rng, len(deals), world.config.null_deal_amount_rate))
    chosen = {deals[index]["hubspot_deal_id"] for index in selected}
    for row in world.rows["hubspot.deal"]:
        if row["hubspot_deal_id"] in chosen:
            row["amount"] = None


def _post_deal_activities(world, hubspot, deals, pre_count, single_indexes) -> None:
    post_count = world.config.activity_count - pre_count
    if post_count == 0:
        return
    if not deals:
        raise GenerationError("activities that cite a deal need a deal")
    types = world.allowed("hubspot.activity", "activity_type")
    for offset in range(post_count):
        index = pre_count + offset
        deal = deals[offset % len(deals)]
        activity_type = types[index % len(types)]
        subject = _subject(world.config, activity_type, index)
        if index in single_indexes:
            hubspot.add_activity(activity_type, subject, None, None, None, deal["hubspot_deal_id"])
            continue
        hubspot.add_activity(
            activity_type,
            subject,
            deal["hubspot_company_id"],
            deal["hubspot_contact_id"],
            deal["hubspot_lead_id"],
            deal["hubspot_deal_id"],
        )


def _firms(world, product: ProductGenerator, companies, new_business) -> list[dict]:
    winners = []
    seen = set()
    wins_at = {}
    for deal in new_business:
        if deal["latest_stage"] != "closed_won":
            continue
        company_id = deal["hubspot_company_id"]
        wins_at.setdefault(company_id, deal["win_at"])
        if company_id not in seen:
            seen.add(company_id)
            winners.append(next(company for company in companies if company["hubspot_company_id"] == company_id))
    matched = _domain_matches(world, winners)
    firms = []
    for index, company in enumerate(winners):
        name_index = company["name_index"]
        prefix = world.config.firm_prefixes[name_index % len(world.config.firm_prefixes)]
        suffix = world.config.product_firm_suffixes[name_index % len(world.config.product_firm_suffixes)]
        if company["hubspot_company_id"] in matched and company["primary_domain"]:
            domain = company["primary_domain"]
        else:
            domain = f"unmatched-{index + 1}.example"
        firms.append(
            product.add_firm(
                firm_name=f"{prefix} {suffix}",
                primary_domain=domain,
                state=company["state"],
                ingested_at=wins_at[company["hubspot_company_id"]],
            )
        )
    return firms


def _domain_matches(world: World, winners: list[dict]) -> set[str]:
    selected = choose_share(world.rng, len(winners), world.config.domain_match_rate)
    chosen = {winners[index]["hubspot_company_id"] for index in selected}
    blanks = [company for company in winners if company["hubspot_company_id"] in chosen and not company["primary_domain"]]
    donors = [
        company
        for company in winners
        if company["hubspot_company_id"] not in chosen and company["primary_domain"]
    ]
    for blank, donor in zip(blanks, donors):
        chosen.remove(blank["hubspot_company_id"])
        chosen.add(donor["hubspot_company_id"])
    return chosen


def _usage(world, product: ProductGenerator, firms, workflows) -> None:
    user_count = len(firms) * world.config.product_users_per_customer
    if user_count == 0 or not workflows:
        return
    null_emails = set(choose_share(world.rng, user_count, world.config.null_user_email_rate))
    statuses = world.allowed("product.user", "status")
    users = []
    for index in range(user_count):
        firm = firms[index // world.config.product_users_per_customer]
        email = None if index in null_emails else f"user-{index + 1}@example.com"
        users.append(
            product.add_user(
                firm_id=firm["product_firm_id"],
                email_normalized=email,
                status=world.choice(statuses),
            )
        )
    usages = []
    for user in users:
        for _ in range(world.config.usage_events_per_user):
            workflow = workflows[world.rng.randrange(len(workflows))]
            usages.append(
                product.add_usage(
                    user_id=user["product_user_source_id"],
                    firm_id=user["product_firm_id"],
                    workflow_id=workflow["product_workflow_id"],
                    work_unit_count=world.integer("work_unit_count"),
                )
            )
    chosen = set(choose_share(world.rng, len(usages), world.config.outcome_rate))
    outcome_types = world.allowed("product.outcome", "outcome_type")
    for index, usage in enumerate(usages):
        if index not in chosen:
            continue
        product.add_outcome(
            usage_id=usage["product_usage_source_id"],
            user_id=usage["product_user_source_id"],
            firm_id=usage["product_firm_id"],
            workflow_id=usage["product_workflow_id"],
            outcome_type=world.choice(outcome_types),
        )


def _draw_date(world: World) -> date:
    span = (world.config.end_date - world.config.start_date).days
    return world.config.start_date + timedelta(days=world.rng.randrange(span + 1))


def _shift_date(start: date, days: int, window_end: date) -> date:
    target = start + timedelta(days=days)
    if target > window_end:
        return window_end
    return target


def _nudge(amount: Decimal, bounds: Bounds, step: Decimal) -> Decimal:
    penny = Decimal("0.01")
    if amount + step <= bounds.maximum:
        return (amount + step).quantize(penny)
    if amount + penny <= bounds.maximum:
        return (amount + penny).quantize(penny)
    if amount - penny >= bounds.minimum:
        return (amount - penny).quantize(penny)
    return amount.quantize(penny)


def _email(name: str, index: int) -> str:
    slug = "".join(character if character.isalnum() else "." for character in name.lower())
    while ".." in slug:
        slug = slug.replace("..", ".")
    return f"{slug.strip('.')}.{index}@example.com"
