"""Product source generator."""

from __future__ import annotations

from eve_data_generation.world import World


class ProductGenerator:
    def __init__(self, world: World) -> None:
        self.world = world

    def add_workflow(self, code: str, name: str) -> dict:
        workflow_id = self.world.ids.prefixed("wf_")
        self.world.emit(
            "product.ai_workflow",
            {
                "product_workflow_id": workflow_id,
                "workflow_code": code,
                "workflow_name": name,
            },
            None,
        )
        return {
            "product_workflow_id": workflow_id,
            "workflow_code": code,
            "workflow_name": name,
        }

    def add_firm(
        self,
        firm_name: str,
        primary_domain: str | None,
        state: str | None,
        ingested_at=None,
    ) -> dict:
        firm_id = self.world.ids.prefixed("frm_")
        self.world.emit(
            "product.firm",
            {
                "product_firm_id": firm_id,
                "firm_name": firm_name,
                "primary_domain": primary_domain,
                "state": state,
            },
            ingested_at,
        )
        return {
            "product_firm_id": firm_id,
            "firm_name": firm_name,
            "primary_domain": primary_domain,
            "state": state,
        }

    def add_user(
        self,
        firm_id: str,
        email_normalized: str | None,
        status: str,
        user_id: str | None = None,
    ) -> dict:
        user_id = user_id or self.world.ids.prefixed("usr_")
        observed_at = self.world.timestamp()
        self.world.emit(
            "product.user",
            {
                "product_user_source_id": user_id,
                "email_normalized": email_normalized,
                "status": status,
                "observed_at": observed_at,
                "product_firm_id": firm_id,
            },
            observed_at,
        )
        return {
            "product_user_source_id": user_id,
            "email_normalized": email_normalized,
            "status": status,
            "observed_at": observed_at,
            "product_firm_id": firm_id,
        }

    def add_usage(self, user_id: str, firm_id: str, workflow_id: str, work_unit_count: int) -> dict:
        if work_unit_count < 1:
            raise ValueError("work_unit_count must be at least 1")
        usage_id = self.world.ids.prefixed("usg_")
        occurred_at = self.world.timestamp()
        self.world.emit(
            "product.usage",
            {
                "product_usage_source_id": usage_id,
                "occurred_at": occurred_at,
                "work_unit_count": work_unit_count,
                "product_user_source_id": user_id,
                "product_firm_id": firm_id,
                "product_workflow_id": workflow_id,
            },
            occurred_at,
        )
        return {
            "product_usage_source_id": usage_id,
            "occurred_at": occurred_at,
            "product_user_source_id": user_id,
            "product_firm_id": firm_id,
            "product_workflow_id": workflow_id,
        }

    def add_outcome(
        self,
        usage_id: str,
        user_id: str,
        firm_id: str,
        workflow_id: str,
        outcome_type: str,
    ) -> dict:
        outcome_id = self.world.ids.prefixed("out_")
        occurred_at = self.world.timestamp()
        self.world.emit(
            "product.outcome",
            {
                "product_outcome_source_id": outcome_id,
                "occurred_at": occurred_at,
                "outcome_type": outcome_type,
                "product_usage_source_id": usage_id,
                "product_user_source_id": user_id,
                "product_firm_id": firm_id,
                "product_workflow_id": workflow_id,
            },
            occurred_at,
        )
        return {"product_outcome_source_id": outcome_id, "occurred_at": occurred_at}
