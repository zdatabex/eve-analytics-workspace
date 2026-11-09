"""Shared generation context: contracts, clock, identifiers, and row emission."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from eve_data_generation.config import Config
from eve_data_generation.contracts import Contract
from eve_data_generation.errors import GenerationError, ValidationError
from eve_data_generation.ids import IdFactory
from eve_data_generation.sampling import Clock, window_bounds


class World:
    def __init__(self, config: Config, contracts: dict[str, Contract]) -> None:
        self.config = config
        self.contracts = contracts
        self.rng = random.Random(config.seed)
        self.clock = Clock(config.start_date, config.end_date)
        self.ids = IdFactory()
        self.delivery_id = config.delivery_id
        self.window_start, self.window_end = window_bounds(config.start_date, config.end_date)
        self.rows: dict[str, list[dict]] = {contract_id: [] for contract_id in contracts}
        late_count = config.late_event_count if config.journeys is not None else 0
        self.late_remaining = late_count or 0

    def timestamp(self) -> datetime:
        return self.clock.take()

    def choice(self, items: tuple | list):
        if not items:
            raise GenerationError("cannot choose from an empty catalog")
        return items[self.rng.randrange(len(items))]

    def allowed(self, contract_id: str, field_name: str) -> tuple[str, ...]:
        return self.contracts[contract_id].allowed(field_name)

    def money(self, range_name: str) -> Decimal:
        bounds = self.config.amount_ranges[range_name]
        low = int((bounds.minimum * 100).to_integral_value(rounding=ROUND_HALF_UP))
        high = int((bounds.maximum * 100).to_integral_value(rounding=ROUND_HALF_UP))
        cents = self.rng.randint(low, high)
        return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))

    def integer(self, range_name: str) -> int:
        bounds = self.config.integer_ranges[range_name]
        return self.rng.randint(bounds.minimum, bounds.maximum)

    def emit(
        self,
        contract_id: str,
        values: dict,
        business_ts: datetime | None,
        ingested_at: datetime | None = None,
    ) -> dict:
        contract = self.contracts[contract_id]
        row = dict(values)
        row["source_system"] = contract.source_system
        row["delivery_id"] = self.delivery_id
        if ingested_at is None:
            ingested_at = self._late_ingested(contract, business_ts)
        if ingested_at is None:
            ingested_at = business_ts if business_ts is not None else self.window_start
        row["ingested_at"] = ingested_at
        _check_row(self, contract, row, business_ts)
        self.rows[contract_id].append(row)
        return row

    def _late_ingested(self, contract: Contract, business_ts: datetime | None) -> datetime | None:
        """Shift the next immutable rows by ``ingest_lag_days`` when a scenario asks for them."""

        if self.late_remaining <= 0 or business_ts is None or contract.history != "immutable":
            return None
        lag_days = self.config.ingest_lag_days
        if lag_days is None:
            return None
        lagged = business_ts + timedelta(days=lag_days)
        if lagged > self.window_end:
            return None
        self.late_remaining -= 1
        return lagged


def _check_domain(value: str) -> None:
    if value != value.strip().lower() or "://" in value or "/" in value or "@" in value or not value:
        raise ValidationError(f"primary_domain is not a lowercase host: {value!r}")


def _check_email(value: str) -> None:
    if value != value.strip().lower() or "@" not in value or not value:
        raise ValidationError(f"email_normalized is not lowercase and trimmed: {value!r}")


def _check_row(world: World, contract: Contract, row: dict, business_ts: datetime | None) -> None:
    expected = {field.name for field in contract.columns}
    if set(row) != expected:
        missing = expected - set(row)
        extra = set(row) - expected
        raise ValidationError(f"{contract.id} columns mismatch missing={sorted(missing)} extra={sorted(extra)}")
    for field in contract.columns:
        value = row[field.name]
        if value is None:
            if not field.nullable:
                raise ValidationError(f"{contract.id}.{field.name} is required")
            continue
        if isinstance(value, str) and value == "":
            raise ValidationError(f"{contract.id}.{field.name} is an empty string")
        if field.type in {"string", "enum"}:
            if not isinstance(value, str):
                raise ValidationError(f"{contract.id}.{field.name} must be a string")
            if field.allowed_values is not None and value not in field.allowed_values:
                raise ValidationError(f"{contract.id}.{field.name} has value {value!r}")
        elif field.type == "decimal":
            if not isinstance(value, Decimal) or value < 0 or value.as_tuple().exponent < -2:
                raise ValidationError(f"{contract.id}.{field.name} must be a non-negative decimal")
        elif field.type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(f"{contract.id}.{field.name} must be an integer")
            if value < 0:
                raise ValidationError(f"{contract.id}.{field.name} cannot be negative")
        elif field.type == "date":
            if not isinstance(value, date) or isinstance(value, datetime):
                raise ValidationError(f"{contract.id}.{field.name} must be a date")
            if not world.config.start_date <= value <= world.config.end_date:
                raise ValidationError(f"{contract.id}.{field.name} is outside the date window")
        elif field.type == "timestamp":
            if not isinstance(value, datetime):
                raise ValidationError(f"{contract.id}.{field.name} must be a timestamp")
            if not world.window_start <= value <= world.window_end:
                raise ValidationError(f"{contract.id}.{field.name} is outside the date window")
        else:
            raise ValidationError(f"{contract.id}.{field.name} has unknown type {field.type}")
        if field.name == "primary_domain":
            _check_domain(value)
        if field.name == "email_normalized":
            _check_email(value)
    if "created_at" in row and "observed_at" in row:
        if row["observed_at"] < row["created_at"]:
            raise ValidationError(f"{contract.id} observed_at is before created_at")
    ingested = row["ingested_at"]
    for name in ("observed_at", "occurred_at", "booked_at", "created_at"):
        if isinstance(row.get(name), datetime) and ingested < row[name]:
            raise ValidationError(f"{contract.id} ingested_at is before {name}")
    if business_ts is not None and ingested < business_ts:
        raise ValidationError(f"{contract.id} ingested_at is before the business timestamp")
    if "performance_date" in row and isinstance(row["performance_date"], date):
        midnight = datetime.combine(row["performance_date"], datetime.min.time())
        if ingested < midnight:
            raise ValidationError("campaign performance ingested_at is before performance_date")
    if row["source_system"] != contract.source_system:
        raise ValidationError(f"{contract.id} source_system does not match the contract")
    if not row["delivery_id"]:
        raise ValidationError(f"{contract.id} delivery_id is empty")
