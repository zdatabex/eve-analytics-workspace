"""JSON Lines drops and one manifest per source system."""

from __future__ import annotations

import json
import shutil
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
    grouped = _by_source(contracts)
    _retain_only(directory, set(grouped))
    for source, source_contracts in grouped.items():
        source_dir = directory / source
        source_dir.mkdir(parents=True, exist_ok=True)
        expected = {contract.file_name for contract in source_contracts} | {"manifest.json"}
        _retain_only(source_dir, expected)
        entities = {}
        for contract in source_contracts:
            rows = sorted(
                dataset.rows.get(contract.id, []),
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
            (source_dir / contract.file_name).write_text(text, encoding="utf-8")
            entities[contract.source_entity] = len(rows)
        manifest = {
            "configuration_file": dataset.config_file,
            "delivery_id": dataset.delivery_id,
            "end_date": dataset.end_date.isoformat(),
            "entities": entities,
            "seed": dataset.seed,
            "start_date": dataset.start_date.isoformat(),
        }
        (source_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return directory


def _by_source(contracts: dict[str, Contract]) -> dict[str, list[Contract]]:
    grouped: dict[str, list[Contract]] = {}
    for contract in contracts.values():
        grouped.setdefault(contract.source_system, []).append(contract)
    return {
        source: sorted(items, key=lambda contract: contract.source_entity)
        for source, items in sorted(grouped.items())
    }


def _retain_only(directory: Path, names: set[str]) -> None:
    for child in list(directory.iterdir()):
        if child.name in names:
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        else:
            shutil.rmtree(child)
