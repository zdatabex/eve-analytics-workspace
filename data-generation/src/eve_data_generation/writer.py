"""JSON Lines output and manifest."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from eve_data_generation.contracts import Contract
from eve_data_generation.dataset import Dataset
from eve_data_generation.errors import GenerationError


def json_value(value):
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        raise GenerationError("boolean is not a source value")
    if isinstance(value, int):
        return value
    if isinstance(value, Decimal):
        return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, date):
        return value.isoformat()
    raise GenerationError(f"cannot serialize {type(value).__name__}")


def write_dataset(dataset: Dataset, contracts: dict[str, Contract], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for contract_id in sorted(contracts):
        contract = contracts[contract_id]
        rows = sorted(
            dataset.rows.get(contract_id, []),
            key=lambda row: tuple(row[name] for name in contract.observation_key),
        )
        lines = [
            json.dumps(
                {key: json_value(row[key]) for key in sorted(row)},
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            for row in rows
        ]
        text = "" if not lines else "\n".join(lines) + "\n"
        (directory / contract.file_name).write_text(text, encoding="utf-8")
    manifest = {
        "configuration_file": dataset.config_file,
        "delivery_id": dataset.delivery_id,
        "end_date": dataset.end_date.isoformat(),
        "entities": {contract_id: len(dataset.rows.get(contract_id, [])) for contract_id in sorted(contracts)},
        "seed": dataset.seed,
        "start_date": dataset.start_date.isoformat(),
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return directory
