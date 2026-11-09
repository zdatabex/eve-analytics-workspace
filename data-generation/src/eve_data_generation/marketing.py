"""Marketing source generator."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from eve_data_generation.world import World


class MarketingGenerator:
    def __init__(self, world: World) -> None:
        self.world = world

    def add_campaign(self, name: str, channel: str) -> dict:
        campaign_id = self.world.ids.prefixed("cmp_")
        campaign_code = self.world.ids.document("CMP")
        self.world.emit(
            "marketing.campaign",
            {
                "marketing_campaign_id": campaign_id,
                "campaign_code": campaign_code,
                "campaign_name": name,
                "channel": channel,
            },
            None,
        )
        return {
            "marketing_campaign_id": campaign_id,
            "campaign_code": campaign_code,
            "campaign_name": name,
            "channel": channel,
        }

    def add_performance(
        self,
        campaign_id: str,
        performance_date: date,
        spend_amount: Decimal | None,
        impression_count: int | None,
        click_count: int | None,
    ) -> None:
        ingested = datetime.combine(performance_date, datetime.min.time())
        self.world.emit(
            "marketing.campaign_performance",
            {
                "marketing_campaign_id": campaign_id,
                "performance_date": performance_date,
                "spend_amount": spend_amount,
                "impression_count": impression_count,
                "click_count": click_count,
            },
            ingested,
        )

    def add_touch(
        self,
        campaign_id: str,
        contact_id: str | None,
        lead_id: str | None,
        company_id: str | None,
    ) -> dict:
        touch_id = self.world.ids.prefixed("tch_")
        occurred_at = self.world.timestamp()
        self.world.emit(
            "marketing.touch",
            {
                "marketing_touch_source_id": touch_id,
                "occurred_at": occurred_at,
                "marketing_campaign_id": campaign_id,
                "hubspot_contact_id": contact_id,
                "hubspot_lead_id": lead_id,
                "hubspot_company_id": company_id,
            },
            occurred_at,
        )
        return {"marketing_touch_source_id": touch_id, "occurred_at": occurred_at}
