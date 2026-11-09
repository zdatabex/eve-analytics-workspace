"""Named GTM lifecycle journeys.

The baseline sampler remains the default. ``build_dataset`` calls this
population only when the loaded configuration contains ``journeys``.
Journey counts and the sequences below decide the records. Retained
DATA-003 count and rate keys stay in the file for the loader and are not
used to size or resolve a journey.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from eve_data_generation.config import CANONICAL_LIFECYCLE, JOURNEY_NAMES, Config
from eve_data_generation.dealhub import DealHubGenerator
from eve_data_generation.errors import ConfigError, GenerationError
from eve_data_generation.hubspot import CONVERTING_LEAD, HubSpotGenerator
from eve_data_generation.marketing import MarketingGenerator
from eve_data_generation.product import ProductGenerator
from eve_data_generation.sampling import WINDOW_ERROR, inclusive_dates
from eve_data_generation.world import World

CUSTOMER_JOURNEYS = (
    "new_business_conversion",
    "expansion",
    "renewal",
    "churn",
    "low_adoption",
)

REQUIRED_WORKFLOWS = (
    "case_intake",
    "document_collection",
    "medical_record_review",
    "document_summarization",
    "demand_letter_generation",
    "case_analysis",
    "settlement_preparation",
)

PLANS = {
    "won": {
        "before_quote": ("evaluation", "proposal"),
        "quotes": ("draft", "sent", "accepted"),
        "after_quote": ("negotiation", "closed_won"),
    },
    "lost": {
        "before_quote": ("evaluation", "proposal"),
        "quotes": ("draft", "sent", "rejected"),
        "after_quote": ("negotiation", "closed_lost"),
    },
    "regression": {
        "before_quote": ("evaluation", "proposal"),
        "quotes": ("draft", "sent", "expired"),
        "after_quote": ("evaluation", "negotiation"),
    },
}

NEW_BUSINESS_USAGE = (
    ("case_intake", None),
    ("document_collection", None),
    ("medical_record_review", None),
    ("document_summarization", "exported"),
    ("demand_letter_generation", "draft_completed"),
    ("settlement_preparation", "review_accepted"),
)

BOOKING_RANGES = {
    "new_business": "booking_amount_new_business",
    "expansion": "booking_amount_expansion",
    "renewal": "booking_amount_renewal",
}


def scenario_population(world: World) -> None:
    config = world.config
    if config.journeys is None:
        raise GenerationError("scenario population requires journeys")
    _require_term_room(config)
    hubspot = HubSpotGenerator(world)
    dealhub = DealHubGenerator(world)
    marketing = MarketingGenerator(world)
    product = ProductGenerator(world)

    campaign = _campaign(world, marketing)
    _performance(world, marketing, campaign)
    workflows = {
        entry.code: product.add_workflow(entry.code, entry.name)
        for entry in config.workflows
    }
    missing = [code for code in REQUIRED_WORKFLOWS if code not in workflows]
    if missing:
        raise ConfigError(f"workflows must include {', '.join(missing)}")

    cursor = {"index": 0}
    for name in JOURNEY_NAMES:
        for instance in range(1, config.journeys[name] + 1):
            _journey(
                world,
                name,
                instance,
                cursor,
                hubspot,
                dealhub,
                marketing,
                product,
                campaign,
                workflows,
            )
    if world.late_remaining:
        raise GenerationError(WINDOW_ERROR)


def _journey(world, name, instance, cursor, hubspot, dealhub, marketing, product, campaign, workflows) -> None:
    if name in CUSTOMER_JOURNEYS:
        state = _open_customer(
            world,
            name,
            instance,
            cursor,
            hubspot,
            dealhub,
            marketing,
            product,
            campaign,
            contact_count=2 if name == "new_business_conversion" else 1,
            duplicate_email=name == "new_business_conversion",
            activities=name == "new_business_conversion",
            renews=name == "renewal",
        )
        if name == "new_business_conversion":
            _adoption(world, product, state, workflows, "healthy")
            _domain_twin(world, hubspot, state, cursor, campaign)
        elif name == "expansion":
            _expansion(world, hubspot, dealhub, state)
        elif name == "renewal":
            _renewal(world, hubspot, dealhub, state)
        elif name == "churn":
            _adoption(world, product, state, workflows, "churn")
            _churn(world, hubspot, dealhub, product, state)
        elif name == "low_adoption":
            _adoption(world, product, state, workflows, "low")
        return
    if name == "lost_opportunity":
        _run_opportunity(
            world, name, instance, cursor, hubspot, dealhub, marketing, campaign,
            plan="lost", contact_count=1, duplicate_email=False, activities=False,
        )
        return
    if name == "stage_regression":
        _run_opportunity(
            world, name, instance, cursor, hubspot, dealhub, marketing, campaign,
            plan="regression", contact_count=1, duplicate_email=False, activities=False,
        )
        return
    raise GenerationError(f"unknown journey {name}")


def _open_customer(
    world, name, instance, cursor, hubspot, dealhub, marketing, product, campaign,
    contact_count, duplicate_email, activities, renews,
) -> dict:
    bundle = _run_opportunity(
        world, name, instance, cursor, hubspot, dealhub, marketing, campaign,
        plan="won",
        contact_count=contact_count,
        duplicate_email=duplicate_email,
        activities=activities,
    )
    commercial = _commercialize(world, dealhub, bundle, renews)
    _restage(hubspot, bundle["company"], "customer")
    firm = _add_firm(world, product, bundle, cursor)
    return {**bundle, **commercial, "firm": firm}


def _run_opportunity(
    world, name, instance, cursor, hubspot, dealhub, marketing, campaign,
    plan, contact_count, duplicate_email, activities,
) -> dict:
    index = _next_index(cursor)
    company = _add_company(world, hubspot, index, _domain(name, instance), "prospect")
    contacts = _add_contacts(world, hubspot, company, contact_count, duplicate_email)
    marketing.add_touch(
        campaign["marketing_campaign_id"],
        None,
        None,
        company["hubspot_company_id"],
    )
    deal_id = world.ids.hubspot()
    lead = hubspot.add_lead(
        latest_status="converted",
        company_id=company["hubspot_company_id"],
        contact_id=contacts[0]["hubspot_contact_id"],
        campaign_id=campaign["marketing_campaign_id"],
        deal_id=deal_id,
        path=CONVERTING_LEAD,
    )
    if lead["converted_at"] is None:
        raise GenerationError("a converting lead has no lead_converted observation")
    amount = world.money("hubspot_amount")
    owner_name = world.choice(world.config.owner_names)
    expected_close_date = _expected_close(world)
    deal = {
        "hubspot_deal_id": deal_id,
        "company_name": company["firm_name"],
        "hubspot_company_id": company["hubspot_company_id"],
        "hubspot_contact_id": contacts[0]["hubspot_contact_id"],
        "hubspot_lead_id": lead["hubspot_lead_id"],
        "dealhub_subscription_id": None,
        "opportunity_type": "new_business",
        "amount": amount,
        "owner_name": owner_name,
        "expected_close_date": expected_close_date,
        "created_at": lead["converted_at"],
        "win_at": None,
    }
    _observe(hubspot, deal, "discovery", deal["created_at"], True)
    if activities:
        _activities(world, hubspot, company, contacts[0], lead, deal)
    spec = PLANS[plan]
    for stage in spec["before_quote"]:
        _observe(hubspot, deal, stage, world.timestamp(), False)
    quote = _quotes(dealhub, world, deal, spec["quotes"])
    for stage in spec["after_quote"]:
        _observe(hubspot, deal, stage, world.timestamp(), False)
    return {"company": company, "contacts": contacts, "lead": lead, "deal": deal, "quote": quote}


def _commercialize(world: World, dealhub: DealHubGenerator, bundle: dict, renews: bool) -> dict:
    deal = bundle["deal"]
    if deal["win_at"] is None:
        raise GenerationError("a customer journey needs a won deal")
    config = world.config
    start = _contract_start(world, renews)
    end = _plus_days(start, config.term_days, config.end_date)
    total_contract_value = world.money("total_contract_value")
    seat_count = world.integer("seat_count")
    recurring_amount = world.money("recurring_amount")
    plan_code = world.choice(config.plan_codes)
    billing_frequency = world.choice(world.allowed("dealhub.subscription", "billing_frequency"))
    contract = dealhub.add_contract(
        quote_id=bundle["quote"]["dealhub_quote_id"],
        deal_id=deal["hubspot_deal_id"],
        company_id=deal["hubspot_company_id"],
        total_contract_value=total_contract_value,
        start_date=start,
        end_date=end,
        observed_at=world.timestamp(),
    )
    subscription = _subscription(
        dealhub,
        world,
        contract_id=contract["dealhub_contract_id"],
        company_id=deal["hubspot_company_id"],
        plan_code=plan_code,
        seat_count=seat_count,
        recurring_amount=recurring_amount,
        billing_frequency=billing_frequency,
        term_start=start,
        term_end=end,
        status="pending",
        emitted_event=None,
    )
    active_at = world.timestamp()
    dealhub.add_subscription(
        contract_id=contract["dealhub_contract_id"],
        company_id=deal["hubspot_company_id"],
        plan_code=plan_code,
        seat_count=seat_count,
        recurring_amount=recurring_amount,
        billing_frequency=billing_frequency,
        term_start=start,
        term_end=end,
        observed_at=active_at,
        status="active",
        emitted_event=None,
        subscription_id=subscription["dealhub_subscription_id"],
        subscription_number=subscription["subscription_number"],
    )
    dealhub.add_booking(
        company_id=deal["hubspot_company_id"],
        deal_id=deal["hubspot_deal_id"],
        contract_id=contract["dealhub_contract_id"],
        subscription_id=subscription["dealhub_subscription_id"],
        booking_type="new_business",
        booking_amount=world.money(BOOKING_RANGES["new_business"]),
        booked_at=world.timestamp(),
    )
    return {
        "contract_id": contract["dealhub_contract_id"],
        "contract_number": contract["contract_number"],
        "quote_id": bundle["quote"]["dealhub_quote_id"],
        "subscription_id": subscription["dealhub_subscription_id"],
        "subscription_number": subscription["subscription_number"],
        "plan_code": plan_code,
        "seat_count": seat_count,
        "recurring_amount": recurring_amount,
        "billing_frequency": billing_frequency,
        "term_start": start,
        "term_end": end,
        "total_contract_value": total_contract_value,
        "start_date": start,
        "end_date": end,
        "active_at": active_at,
        "new_business_deal_id": deal["hubspot_deal_id"],
    }


def _expansion(world, hubspot, dealhub, state) -> None:
    config = world.config
    follow = _follow_on(world, hubspot, state, "expansion")
    seat_count = state["seat_count"] + config.expansion_seat_increase
    recurring_amount = (state["recurring_amount"] + config.expansion_recurring_increase).quantize(Decimal("0.01"))
    total_contract_value = (state["total_contract_value"] + config.contract_value_increase).quantize(Decimal("0.01"))
    observed_at = world.timestamp()
    _subscription(
        dealhub,
        world,
        contract_id=state["contract_id"],
        company_id=state["company"]["hubspot_company_id"],
        plan_code=state["plan_code"],
        seat_count=seat_count,
        recurring_amount=recurring_amount,
        billing_frequency=state["billing_frequency"],
        term_start=state["term_start"],
        term_end=state["term_end"],
        status="active",
        emitted_event="subscription_expanded",
        observed_at=observed_at,
        subscription_id=state["subscription_id"],
        subscription_number=state["subscription_number"],
    )
    dealhub.add_contract(
        quote_id=state["quote_id"],
        deal_id=state["new_business_deal_id"],
        company_id=state["company"]["hubspot_company_id"],
        total_contract_value=total_contract_value,
        start_date=state["start_date"],
        end_date=state["end_date"],
        observed_at=world.timestamp(),
        contract_id=state["contract_id"],
        contract_number=state["contract_number"],
    )
    dealhub.add_booking(
        company_id=state["company"]["hubspot_company_id"],
        deal_id=follow["hubspot_deal_id"],
        contract_id=state["contract_id"],
        subscription_id=state["subscription_id"],
        booking_type="expansion",
        booking_amount=world.money(BOOKING_RANGES["expansion"]),
        booked_at=world.timestamp(),
    )


def _renewal(world, hubspot, dealhub, state) -> None:
    config = world.config
    follow = _follow_on(world, hubspot, state, "renewal")
    term_end = _plus_days(state["term_end"], config.term_days, config.end_date)
    end_date = _plus_days(state["end_date"], config.term_days, config.end_date)
    dealhub.add_subscription(
        contract_id=state["contract_id"],
        company_id=state["company"]["hubspot_company_id"],
        plan_code=state["plan_code"],
        seat_count=state["seat_count"],
        recurring_amount=state["recurring_amount"],
        billing_frequency=state["billing_frequency"],
        term_start=state["term_start"],
        term_end=term_end,
        observed_at=world.timestamp(),
        status="active",
        emitted_event="subscription_renewed",
        subscription_id=state["subscription_id"],
        subscription_number=state["subscription_number"],
    )
    dealhub.add_contract(
        quote_id=state["quote_id"],
        deal_id=state["new_business_deal_id"],
        company_id=state["company"]["hubspot_company_id"],
        total_contract_value=state["total_contract_value"],
        start_date=state["start_date"],
        end_date=end_date,
        observed_at=world.timestamp(),
        contract_id=state["contract_id"],
        contract_number=state["contract_number"],
    )
    dealhub.add_booking(
        company_id=state["company"]["hubspot_company_id"],
        deal_id=follow["hubspot_deal_id"],
        contract_id=state["contract_id"],
        subscription_id=state["subscription_id"],
        booking_type="renewal",
        booking_amount=world.money(BOOKING_RANGES["renewal"]),
        booked_at=world.timestamp(),
    )


def _churn(world, hubspot, dealhub, product, state) -> None:
    observed_at = world.timestamp()
    dealhub.add_subscription(
        contract_id=state["contract_id"],
        company_id=state["company"]["hubspot_company_id"],
        plan_code=state["plan_code"],
        seat_count=state["seat_count"],
        recurring_amount=state["recurring_amount"],
        billing_frequency=state["billing_frequency"],
        term_start=state["term_start"],
        term_end=state["term_end"],
        observed_at=observed_at,
        status="churned",
        emitted_event="subscription_churned",
        subscription_id=state["subscription_id"],
        subscription_number=state["subscription_number"],
    )
    dealhub.add_contract(
        quote_id=state["quote_id"],
        deal_id=state["new_business_deal_id"],
        company_id=state["company"]["hubspot_company_id"],
        total_contract_value=state["total_contract_value"],
        start_date=state["start_date"],
        end_date=state["end_date"],
        observed_at=world.timestamp(),
        contract_id=state["contract_id"],
        contract_number=state["contract_number"],
        status="terminated",
    )
    _restage(hubspot, state["company"], "former_customer")
    user = state["user"]
    product.add_user(
        state["firm"]["product_firm_id"],
        user["email_normalized"],
        "inactive",
        user_id=user["product_user_source_id"],
    )


def _adoption(world, product, state, workflows, mode: str) -> None:
    user = product.add_user(
        state["firm"]["product_firm_id"],
        f"analyst@{state['firm']['primary_domain']}",
        "active",
    )
    state["user"] = user
    if mode == "healthy":
        for code, outcome in NEW_BUSINESS_USAGE:
            units = (
                world.config.integer_ranges["work_unit_count"].maximum
                if code == "document_collection"
                else world.integer("work_unit_count")
            )
            _use(product, user, state["firm"], workflows[code], units, outcome)
        return
    if mode == "churn":
        bounds = world.config.integer_ranges["work_unit_count"]
        workflow = workflows["case_intake"]
        _use(product, user, state["firm"], workflow, bounds.maximum, None)
        _use(product, user, state["firm"], workflow, bounds.minimum, None)
        return
    if mode == "low":
        _use(
            product,
            user,
            state["firm"],
            workflows["case_analysis"],
            world.integer("work_unit_count"),
            None,
        )
        return
    raise GenerationError(f"unknown adoption mode {mode}")


def _domain_twin(world, hubspot, state, cursor, campaign) -> None:
    company = state["company"]
    twin = _add_company(
        world,
        hubspot,
        _next_index(cursor),
        company["primary_domain"],
        _other_stage(world.config),
    )
    hubspot.add_lead(
        latest_status="disqualified",
        company_id=twin["hubspot_company_id"],
        contact_id=None,
        campaign_id=campaign["marketing_campaign_id"],
        deal_id=None,
    )


def _follow_on(world, hubspot, state, opportunity_type: str) -> dict:
    company = state["company"]
    contact_id = state["contacts"][0]["hubspot_contact_id"]
    return hubspot.add_deal(
        company_id=company["hubspot_company_id"],
        company_name=company["firm_name"],
        contact_id=contact_id,
        lead_id=None,
        subscription_id=state["subscription_id"],
        opportunity_type=opportunity_type,
        latest_stage="closed_won",
        amount=world.money("hubspot_amount"),
        owner_name=world.choice(world.config.owner_names),
        expected_close_date=_expected_close(world),
    )


def _campaign(world: World, marketing: MarketingGenerator) -> dict:
    name = world.config.campaign_names[0]
    channel = world.choice(world.allowed("marketing.campaign", "channel"))
    return marketing.add_campaign(name, channel)


def _performance(world: World, marketing: MarketingGenerator, campaign: dict) -> None:
    for day in inclusive_dates(world.config.start_date, world.config.end_date):
        impressions = world.integer("impression_count")
        clicks = world.rng.randint(0, impressions)
        marketing.add_performance(
            campaign["marketing_campaign_id"],
            day,
            world.money("spend_amount"),
            impressions,
            clicks,
        )


def _add_company(world, hubspot, index: int, domain: str, stage: str) -> dict:
    config = world.config
    prefix = config.firm_prefixes[index % len(config.firm_prefixes)]
    suffix = config.hubspot_firm_suffixes[index % len(config.hubspot_firm_suffixes)]
    return hubspot.add_company(
        firm_name=f"{prefix} {suffix}",
        primary_domain=domain,
        state=world.choice(config.states),
        segment=world.choice(world.allowed("hubspot.company", "segment")),
        practice_focus=world.choice(config.practice_focuses),
        icp_fit=world.choice(world.allowed("hubspot.company", "icp_fit")),
        owner_name=world.choice(config.owner_names),
        lifecycle_stage=stage,
    )


def _restage(hubspot, company: dict, stage: str) -> None:
    hubspot.add_company(
        firm_name=company["firm_name"],
        primary_domain=company["primary_domain"],
        state=company["state"],
        segment=company["segment"],
        practice_focus=company["practice_focus"],
        icp_fit=company["icp_fit"],
        owner_name=company["owner_name"],
        lifecycle_stage=stage,
        company_id=company["hubspot_company_id"],
    )


def _add_contacts(world, hubspot, company: dict, count: int, duplicate_email: bool) -> list[dict]:
    contacts = []
    shared = f"shared-{company['hubspot_company_id']}@example.com"
    for offset in range(count):
        if duplicate_email:
            email = shared
        else:
            email = f"contact-{company['hubspot_company_id']}-{offset}@example.com"
        contacts.append(
            hubspot.add_contact(
                company_id=company["hubspot_company_id"],
                full_name=world.choice(world.config.person_names),
                email_normalized=email,
                title=world.choice(world.config.titles),
                buying_role=world.choice(world.allowed("hubspot.contact", "buying_role")),
            )
        )
    return contacts


def _activities(world, hubspot, company, contact, lead, deal) -> None:
    for offset, activity_type in enumerate(("call", "email", "meeting")):
        phrases = world.config.activity_subjects[activity_type]
        hubspot.add_activity(
            activity_type,
            phrases[offset % len(phrases)],
            company["hubspot_company_id"],
            contact["hubspot_contact_id"],
            lead["hubspot_lead_id"],
            deal["hubspot_deal_id"],
        )


def _quotes(dealhub, world, deal, statuses: tuple[str, ...]) -> dict:
    amount = world.money("quoted_amount")
    quote_id = None
    quote_number = None
    last = None
    for status in statuses:
        last = dealhub.add_quote(
            deal["hubspot_deal_id"],
            deal["hubspot_company_id"],
            status,
            None if status == "draft" else amount,
            quote_id,
            quote_number,
        )
        quote_id = last["dealhub_quote_id"]
        quote_number = last["quote_number"]
    if last is None:
        raise GenerationError("a quote sequence is empty")
    return last


def _observe(hubspot, deal: dict, stage: str, observed_at, opening: bool) -> None:
    event = hubspot.observe_deal(
        deal_id=deal["hubspot_deal_id"],
        company_name=deal["company_name"],
        company_id=deal["hubspot_company_id"],
        contact_id=deal["hubspot_contact_id"],
        lead_id=deal["hubspot_lead_id"],
        subscription_id=deal["dealhub_subscription_id"],
        opportunity_type=deal["opportunity_type"],
        stage=stage,
        amount=deal["amount"],
        owner_name=deal["owner_name"],
        expected_close_date=deal["expected_close_date"],
        created_at=deal["created_at"],
        observed_at=observed_at,
        opening=opening,
    )
    if event == "opportunity_won":
        deal["win_at"] = observed_at


def _subscription(dealhub, world, **kwargs) -> dict:
    observed_at = kwargs.pop("observed_at", None)
    if observed_at is None:
        observed_at = world.timestamp()
    return dealhub.add_subscription(observed_at=observed_at, **kwargs)


def _add_firm(world, product, bundle: dict, cursor: dict) -> dict:
    company = bundle["company"]
    index = _next_index(cursor)
    prefix = world.config.firm_prefixes[index % len(world.config.firm_prefixes)]
    suffix = world.config.product_firm_suffixes[index % len(world.config.product_firm_suffixes)]
    return product.add_firm(
        firm_name=f"{prefix} {suffix}",
        primary_domain=company["primary_domain"],
        state=company["state"],
        ingested_at=bundle["deal"]["win_at"],
    )


def _use(product, user, firm, workflow, units: int, outcome: str | None) -> None:
    usage = product.add_usage(
        user["product_user_source_id"],
        firm["product_firm_id"],
        workflow["product_workflow_id"],
        units,
    )
    if outcome is None:
        return
    product.add_outcome(
        usage["product_usage_source_id"],
        usage["product_user_source_id"],
        usage["product_firm_id"],
        usage["product_workflow_id"],
        outcome,
    )


def _domain(journey: str, instance: int) -> str:
    slug = journey.replace("_", "-")
    if instance == 1:
        return f"{slug}.example"
    return f"{slug}-{instance}.example"


def _other_stage(config: Config) -> str:
    for value in config.lifecycle_stage_catalog:
        if value not in CANONICAL_LIFECYCLE:
            return value
    raise ConfigError(
        "lifecycle_stage_catalog must include a value other than prospect, customer, and former_customer"
    )


def _next_index(cursor: dict) -> int:
    cursor["index"] += 1
    return cursor["index"]


def _require_term_room(config: Config) -> None:
    if config.end_date - config.start_date < timedelta(days=config.term_days * 2):
        raise GenerationError(WINDOW_ERROR)


def _expected_close(world: World) -> date:
    span = (world.config.end_date - world.config.start_date).days
    return world.config.start_date + timedelta(days=world.rng.randrange(span + 1))


def _contract_start(world: World, renews: bool) -> date:
    config = world.config
    multiples = 2 if renews else 1
    latest = config.end_date - timedelta(days=config.term_days * multiples)
    if latest < config.start_date:
        raise GenerationError(WINDOW_ERROR)
    span = (latest - config.start_date).days
    return config.start_date + timedelta(days=world.rng.randrange(span + 1))


def _plus_days(start: date, days: int, window_end: date) -> date:
    target = start + timedelta(days=days)
    if target > window_end:
        raise GenerationError(WINDOW_ERROR)
    return target
