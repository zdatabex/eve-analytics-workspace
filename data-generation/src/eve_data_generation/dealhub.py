"""DealHub source generator."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from eve_data_generation.world import World


class DealHubGenerator:
    def __init__(self, world: World) -> None:
        self.world = world

    def add_quote(
        self,
        deal_id: str,
        company_id: str,
        status: str,
        quoted_amount: Decimal | None,
        quote_id: str | None = None,
        quote_number: str | None = None,
    ) -> dict:
        quote_id = quote_id or self.world.ids.prefixed("qte_")
        quote_number = quote_number or self.world.ids.document("Q")
        observed_at = self.world.timestamp()
        self.world.emit(
            "dealhub.quote",
            {
                "dealhub_quote_id": quote_id,
                "quote_number": quote_number,
                "status": status,
                "quoted_amount": quoted_amount,
                "observed_at": observed_at,
                "hubspot_deal_id": deal_id,
                "hubspot_company_id": company_id,
            },
            observed_at,
        )
        return {
            "dealhub_quote_id": quote_id,
            "quote_number": quote_number,
            "hubspot_deal_id": deal_id,
            "hubspot_company_id": company_id,
            "observed_at": observed_at,
            "status": status,
        }

    def add_accepted_quote(
        self,
        deal_id: str,
        company_id: str,
        quoted_amount: Decimal,
        observed_at: datetime,
    ) -> dict:
        quote_id = self.world.ids.prefixed("qte_")
        quote_number = self.world.ids.document("Q")
        self.world.emit(
            "dealhub.quote",
            {
                "dealhub_quote_id": quote_id,
                "quote_number": quote_number,
                "status": "accepted",
                "quoted_amount": quoted_amount,
                "observed_at": observed_at,
                "hubspot_deal_id": deal_id,
                "hubspot_company_id": company_id,
            },
            observed_at,
        )
        return {
            "dealhub_quote_id": quote_id,
            "quote_number": quote_number,
            "hubspot_deal_id": deal_id,
            "hubspot_company_id": company_id,
        }

    def add_contract(
        self,
        quote_id: str,
        deal_id: str,
        company_id: str,
        total_contract_value: Decimal,
        start_date: date,
        end_date: date,
        observed_at: datetime,
        contract_id: str | None = None,
        contract_number: str | None = None,
        status: str = "active",
    ) -> dict:
        contract_id = contract_id or self.world.ids.prefixed("ctr_")
        contract_number = contract_number or self.world.ids.document("C")
        self.world.emit(
            "dealhub.contract",
            {
                "dealhub_contract_id": contract_id,
                "contract_number": contract_number,
                "status": status,
                "total_contract_value": total_contract_value,
                "start_date": start_date,
                "end_date": end_date,
                "observed_at": observed_at,
                "dealhub_quote_id": quote_id,
                "hubspot_deal_id": deal_id,
                "hubspot_company_id": company_id,
            },
            observed_at,
        )
        return {
            "dealhub_contract_id": contract_id,
            "contract_number": contract_number,
            "dealhub_quote_id": quote_id,
            "hubspot_deal_id": deal_id,
            "hubspot_company_id": company_id,
            "total_contract_value": total_contract_value,
            "start_date": start_date,
            "end_date": end_date,
        }

    def add_subscription(
        self,
        contract_id: str,
        company_id: str,
        plan_code: str,
        seat_count: int,
        recurring_amount: Decimal,
        billing_frequency: str,
        term_start: date,
        term_end: date,
        observed_at: datetime,
        status: str,
        emitted_event: str | None,
        subscription_id: str | None = None,
        subscription_number: str | None = None,
    ) -> dict:
        subscription_id = subscription_id or self.world.ids.prefixed("sub_")
        subscription_number = subscription_number or self.world.ids.document("S")
        self.world.emit(
            "dealhub.subscription",
            {
                "dealhub_subscription_id": subscription_id,
                "subscription_number": subscription_number,
                "status": status,
                "plan_code": plan_code,
                "seat_count": seat_count,
                "recurring_amount": recurring_amount,
                "billing_frequency": billing_frequency,
                "term_start": term_start,
                "term_end": term_end,
                "observed_at": observed_at,
                "emitted_event": emitted_event,
                "dealhub_contract_id": contract_id,
                "hubspot_company_id": company_id,
            },
            observed_at,
        )
        return {
            "dealhub_subscription_id": subscription_id,
            "subscription_number": subscription_number,
            "dealhub_contract_id": contract_id,
            "hubspot_company_id": company_id,
        }

    def add_booking(
        self,
        company_id: str,
        deal_id: str,
        contract_id: str,
        subscription_id: str,
        booking_type: str,
        booking_amount: Decimal,
        booked_at: datetime,
    ) -> dict:
        booking_id = self.world.ids.prefixed("bkg_")
        booking_number = self.world.ids.document("B")
        self.world.emit(
            "dealhub.booking",
            {
                "dealhub_booking_id": booking_id,
                "booking_number": booking_number,
                "booking_type": booking_type,
                "booking_amount": booking_amount,
                "booked_at": booked_at,
                "hubspot_company_id": company_id,
                "hubspot_deal_id": deal_id,
                "dealhub_contract_id": contract_id,
                "dealhub_subscription_id": subscription_id,
            },
            booked_at,
        )
        return {"dealhub_booking_id": booking_id, "booking_number": booking_number}
