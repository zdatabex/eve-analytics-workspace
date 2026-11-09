"""HubSpot source generator."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from eve_data_generation.world import World

PIPELINE = ("discovery", "evaluation", "proposal", "negotiation", "closed_won")
LOST_PATH = ("discovery", "evaluation", "proposal", "negotiation", "closed_lost")


def stages_through(latest: str) -> tuple[str, ...]:
    if latest == "closed_lost":
        return LOST_PATH
    if latest not in PIPELINE:
        raise ValueError(f"unknown deal stage {latest}")
    return PIPELINE[: PIPELINE.index(latest) + 1]


def deal_event(stage: str, index: int) -> str:
    if index == 0:
        return "opportunity_opened"
    if stage in {"evaluation", "proposal", "negotiation"}:
        return "opportunity_stage_changed"
    if stage == "closed_won":
        return "opportunity_won"
    if stage == "closed_lost":
        return "opportunity_lost"
    raise ValueError(f"no deal event for {stage}")


def lead_path(latest: str) -> tuple[tuple[str, str | None], ...]:
    if latest == "new":
        return (("new", "lead_created"),)
    if latest == "working":
        return (("new", "lead_created"), ("working", None))
    if latest == "qualified":
        return (("new", "lead_created"), ("qualified", "lead_qualified"))
    if latest == "disqualified":
        return (("new", "lead_created"), ("disqualified", "lead_disqualified"))
    if latest == "converted":
        return (
            ("new", "lead_created"),
            ("qualified", "lead_qualified"),
            ("converted", "lead_converted"),
        )
    raise ValueError(f"unknown lead status {latest}")


CONVERTING_LEAD = (
    ("new", "lead_created"),
    ("working", None),
    ("qualified", "lead_qualified"),
    ("converted", "lead_converted"),
)


class HubSpotGenerator:
    def __init__(self, world: World) -> None:
        self.world = world

    def add_company(
        self,
        firm_name: str,
        primary_domain: str | None,
        state: str,
        segment: str,
        practice_focus: str,
        icp_fit: str,
        owner_name: str,
        lifecycle_stage: str,
        company_id: str | None = None,
    ) -> dict:
        company_id = company_id or self.world.ids.hubspot()
        observed_at = self.world.timestamp()
        self.world.emit(
            "hubspot.company",
            {
                "hubspot_company_id": company_id,
                "firm_name": firm_name,
                "primary_domain": primary_domain,
                "state": state,
                "segment": segment,
                "practice_focus": practice_focus,
                "icp_fit": icp_fit,
                "owner_name": owner_name,
                "hubspot_lifecycle_stage": lifecycle_stage,
                "observed_at": observed_at,
            },
            observed_at,
        )
        return {
            "hubspot_company_id": company_id,
            "firm_name": firm_name,
            "primary_domain": primary_domain,
            "state": state,
            "segment": segment,
            "practice_focus": practice_focus,
            "icp_fit": icp_fit,
            "owner_name": owner_name,
            "hubspot_lifecycle_stage": lifecycle_stage,
            "observed_at": observed_at,
        }

    def add_contact(
        self,
        company_id: str,
        full_name: str,
        email_normalized: str | None,
        title: str,
        buying_role: str,
    ) -> dict:
        contact_id = self.world.ids.hubspot()
        observed_at = self.world.timestamp()
        self.world.emit(
            "hubspot.contact",
            {
                "hubspot_contact_id": contact_id,
                "full_name": full_name,
                "email_normalized": email_normalized,
                "title": title,
                "buying_role": buying_role,
                "observed_at": observed_at,
                "hubspot_company_id": company_id,
            },
            observed_at,
        )
        return {
            "hubspot_contact_id": contact_id,
            "full_name": full_name,
            "email_normalized": email_normalized,
            "hubspot_company_id": company_id,
            "observed_at": observed_at,
        }

    def add_lead(
        self,
        latest_status: str,
        company_id: str | None,
        contact_id: str | None,
        campaign_id: str | None,
        deal_id: str | None,
        path: tuple[tuple[str, str | None], ...] | None = None,
    ) -> dict:
        lead_id = self.world.ids.hubspot()
        created_at = None
        converted_at = None
        steps = path if path is not None else lead_path(latest_status)
        for status, event in steps:
            observed_at = self.world.timestamp()
            if created_at is None:
                created_at = observed_at
            if event == "lead_converted":
                converted_at = observed_at
            self.world.emit(
                "hubspot.lead",
                {
                    "hubspot_lead_id": lead_id,
                    "status": status,
                    "created_at": created_at,
                    "observed_at": observed_at,
                    "emitted_event": event,
                    "hubspot_company_id": company_id,
                    "hubspot_contact_id": contact_id,
                    "marketing_campaign_id": campaign_id,
                    "hubspot_deal_id": deal_id if event == "lead_converted" else None,
                },
                observed_at,
            )
        return {
            "hubspot_lead_id": lead_id,
            "status": steps[-1][0],
            "hubspot_company_id": company_id,
            "hubspot_contact_id": contact_id,
            "hubspot_deal_id": deal_id,
            "created_at": created_at,
            "converted_at": converted_at,
        }

    def observe_deal(
        self,
        deal_id: str,
        company_name: str,
        company_id: str,
        contact_id: str | None,
        lead_id: str | None,
        subscription_id: str | None,
        opportunity_type: str,
        stage: str,
        amount: Decimal | None,
        owner_name: str,
        expected_close_date,
        created_at: datetime,
        observed_at: datetime,
        opening: bool,
    ) -> str:
        event = deal_event(stage, 0 if opening else 1)
        name = self.world.config.opportunity_name_template.format(
            firm_name=company_name,
            opportunity_type=opportunity_type,
        )
        self.world.emit(
            "hubspot.deal",
            {
                "hubspot_deal_id": deal_id,
                "opportunity_name": name,
                "opportunity_type": opportunity_type,
                "stage": stage,
                "amount": amount,
                "expected_close_date": expected_close_date,
                "owner_name": owner_name,
                "forecast_category": self.world.config.forecast_by_stage[stage],
                "created_at": created_at,
                "observed_at": observed_at,
                "emitted_event": event,
                "hubspot_company_id": company_id,
                "hubspot_contact_id": contact_id,
                "hubspot_lead_id": lead_id,
                "dealhub_subscription_id": subscription_id,
            },
            observed_at,
        )
        return event

    def add_deal(
        self,
        company_id: str,
        company_name: str,
        contact_id: str | None,
        lead_id: str | None,
        subscription_id: str | None,
        opportunity_type: str,
        latest_stage: str,
        amount: Decimal | None,
        owner_name: str,
        expected_close_date,
        deal_id: str | None = None,
    ) -> dict:
        deal_id = deal_id or self.world.ids.hubspot()
        path = stages_through(latest_stage)
        if path[0] != "discovery":
            raise ValueError("a deal opens at discovery")
        created_at = None
        win_at = None
        for index, stage in enumerate(path):
            observed_at = self.world.timestamp()
            if created_at is None:
                created_at = observed_at
            event = self.observe_deal(
                deal_id=deal_id,
                company_name=company_name,
                company_id=company_id,
                contact_id=contact_id,
                lead_id=lead_id,
                subscription_id=subscription_id,
                opportunity_type=opportunity_type,
                stage=stage,
                amount=amount,
                owner_name=owner_name,
                expected_close_date=expected_close_date,
                created_at=created_at,
                observed_at=observed_at,
                opening=index == 0,
            )
            if event == "opportunity_won":
                win_at = observed_at
        return {
            "hubspot_deal_id": deal_id,
            "hubspot_company_id": company_id,
            "hubspot_contact_id": contact_id,
            "hubspot_lead_id": lead_id,
            "opportunity_type": opportunity_type,
            "latest_stage": latest_stage,
            "amount": amount,
            "owner_name": owner_name,
            "win_at": win_at,
            "created_at": created_at,
        }

    def add_activity(
        self,
        activity_type: str,
        subject: str,
        company_id: str | None,
        contact_id: str | None,
        lead_id: str | None,
        deal_id: str | None,
    ) -> dict:
        activity_id = self.world.ids.hubspot()
        occurred_at = self.world.timestamp()
        self.world.emit(
            "hubspot.activity",
            {
                "hubspot_activity_id": activity_id,
                "activity_type": activity_type,
                "subject": subject,
                "occurred_at": occurred_at,
                "hubspot_company_id": company_id,
                "hubspot_contact_id": contact_id,
                "hubspot_lead_id": lead_id,
                "hubspot_deal_id": deal_id,
            },
            occurred_at,
        )
        return {"hubspot_activity_id": activity_id, "occurred_at": occurred_at}
