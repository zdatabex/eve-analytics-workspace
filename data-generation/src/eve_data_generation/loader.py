"""Load one ingestion drop per source into raw_<source_system>."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb

from eve_data_generation.contracts import Contract, load_contracts
from eve_data_generation.errors import GenerationError
from eve_data_generation.paths import DEFAULT_WAREHOUSE, WAREHOUSE_ENV

_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
_TYPES = {
    "string": "VARCHAR",
    "enum": "VARCHAR",
    "decimal": "DECIMAL(18,2)",
    "integer": "BIGINT",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
}


def warehouse_path(explicit: str | Path | None = None, schema: str | None = None) -> Path:
    """Select the DuckDB file.

    ``--warehouse`` wins, then a non-empty ``EVE_DATA_GENERATION_DUCKDB_PATH``.
    Otherwise the file is ``data/warehouse/<schema>``, or ``dev_data_003`` when
    the configuration omits ``schema``. ``schema`` names that file. It is not a
    DuckDB schema.
    """

    if explicit is not None and str(explicit).strip():
        return Path(explicit)
    configured = os.environ.get(WAREHOUSE_ENV, "").strip()
    if configured:
        return Path(configured)
    if schema is None:
        return DEFAULT_WAREHOUSE
    return DEFAULT_WAREHOUSE.parent / _ident(schema)


def _ident(value: str) -> str:
    if not _IDENT.fullmatch(value):
        raise GenerationError(f"unsafe SQL identifier {value}")
    return value


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _parse(value, field_type: str):
    if value is None:
        return None
    if field_type == "decimal":
        return Decimal(value).quantize(Decimal("0.01"))
    if field_type == "integer":
        return int(value)
    if field_type == "date":
        return date.fromisoformat(value)
    if field_type == "timestamp":
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    return value


def _read_jsonl(path: Path) -> list[dict]:
    if path.stat().st_size == 0:
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def load_dataset(
    directory: Path,
    database: str | Path | None = None,
    schema_name: str | None = None,
) -> Path:
    """Replace every raw source table from the drop directory.

    ``schema_name`` selects the warehouse file when no explicit file or
    environment path is set. Tables land in ``raw_<source_system>``.
    """

    contracts = load_contracts()
    target = warehouse_path(database, schema_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(target))
    try:
        catalog = connection.execute("SELECT current_catalog()").fetchone()[0]
        grouped: dict[str, list[Contract]] = {}
        for contract in contracts.values():
            grouped.setdefault(contract.source_system, []).append(contract)
        for source, source_contracts in grouped.items():
            schema = _ident(f"raw_{source}")
            qualified_schema = f"{_quote(catalog)}.{_quote(schema)}"
            connection.execute(f"CREATE SCHEMA IF NOT EXISTS {qualified_schema}")
            for contract in source_contracts:
                _replace_table(connection, qualified_schema, contract, directory)
    finally:
        connection.close()
    return target


def _replace_table(connection, qualified_schema: str, contract: Contract, directory: Path) -> None:
    path = directory / contract.source_system / contract.file_name
    if not path.is_file():
        raise GenerationError(f"missing entity file {path}")
    table = _quote(_ident(contract.table_name))
    columns = []
    for field in contract.columns:
        nullability = "" if field.nullable else " NOT NULL"
        columns.append(f"{_quote(_ident(field.name))} {_TYPES[field.type]}{nullability}")
    connection.execute(f"CREATE OR REPLACE TABLE {qualified_schema}.{table} ({', '.join(columns)})")
    rows = _read_jsonl(path)
    if not rows:
        return
    names = [field.name for field in contract.columns]
    payload = [
        tuple(_parse(row.get(field.name), field.type) for field in contract.columns)
        for row in rows
    ]
    placeholders = ", ".join(["?"] * len(names))
    column_sql = ", ".join(_quote(_ident(name)) for name in names)
    connection.executemany(
        f"INSERT INTO {qualified_schema}.{table} ({column_sql}) VALUES ({placeholders})",
        payload,
    )
