"""Load merged source contracts from contracts/source."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from eve_data_generation.errors import GenerationError
from eve_data_generation.paths import CONTRACTS_ROOT


@dataclass(frozen=True)
class Field:
    name: str
    type: str
    nullable: bool
    allowed_values: tuple[str, ...] | None


@dataclass(frozen=True)
class Relationship:
    field: str
    contract_id: str
    reference_field: str
    required: bool


@dataclass(frozen=True)
class Contract:
    id: str
    source_system: str
    source_entity: str
    history: str
    source_identifier: tuple[str, ...]
    observation_key: tuple[str, ...]
    fields: tuple[Field, ...]
    ingestion: tuple[Field, ...]
    relationships: tuple[Relationship, ...]

    @property
    def columns(self) -> tuple[Field, ...]:
        return self.fields + self.ingestion

    @property
    def table_name(self) -> str:
        return self.source_entity

    @property
    def file_name(self) -> str:
        return f"{self.source_entity}.jsonl"

    @property
    def raw_schema(self) -> str:
        return f"raw_{self.source_system}"

    def field(self, name: str) -> Field:
        for column in self.columns:
            if column.name == name:
                return column
        raise GenerationError(f"{self.id} has no field {name}")

    def allowed(self, name: str) -> tuple[str, ...]:
        values = self.field(name).allowed_values
        if not values:
            raise GenerationError(f"{self.id}.{name} has no allowed_values")
        return values


def _field(payload: dict) -> Field:
    allowed = payload.get("allowed_values")
    return Field(
        name=payload["name"],
        type=payload["type"],
        nullable=bool(payload["nullable"]),
        allowed_values=tuple(allowed) if allowed else None,
    )


def _relationship(payload: dict) -> Relationship:
    system, entity, field = payload["references"].split(".")
    return Relationship(
        field=payload["field"],
        contract_id=f"{system}.{entity}",
        reference_field=field,
        required=bool(payload["required"]),
    )


def load_contract(path: Path) -> Contract:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Contract(
        id=document["id"],
        source_system=document["source_system"],
        source_entity=document["source_entity"],
        history=document["history"],
        source_identifier=tuple(document["source_identifier"]),
        observation_key=tuple(document["observation_key"]),
        fields=tuple(_field(field) for field in document["fields"]),
        ingestion=tuple(_field(field) for field in document["ingestion"]),
        relationships=tuple(_relationship(item) for item in document.get("relationships") or []),
    )


def load_contracts(root: Path | None = None) -> dict[str, Contract]:
    directory = root or CONTRACTS_ROOT
    if not directory.is_dir():
        raise GenerationError(f"source contracts not found at {directory}")
    contracts = {}
    for path in sorted(directory.glob("*/*.yaml")):
        contract = load_contract(path)
        contracts[contract.id] = contract
    if not contracts:
        raise GenerationError(f"no source contracts found under {directory}")
    return contracts
