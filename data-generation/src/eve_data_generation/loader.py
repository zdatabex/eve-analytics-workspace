"""Load generated JSON Lines into the isolated dev_data_003 schema."""

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
from eve_data_generation.paths import DEFAULT_WAREHOUSE, SCHEMA_NAME, WAREHOUSE_ENV

_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")
_TYPES = {
    "string": "VARCHAR",
    "enum": "VARCHAR",
    "decimal": "DECIMAL(18,2)",
    "integer": "BIGINT",
    "date": "DATE",
    "timestamp": "TIMESTAMP",
}


def warehouse_path(explicit: str | Path | None = None) -> Path:
    if explicit is not None and str(explicit).strip():
        return Path(explicit)
    configured = os.environ.get(WAREHOUSE_ENV, "").strip()
    if not configured:
        return DEFAULT_WAREHOUSE
    return Path(configured)


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
    if not path.exists() or path.stat().st_size == 0:
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def load_dataset(directory: Path, database: str | Path | None = None) -> Path:
    """Replace every source table in schema dev_data_003."""

    contracts = load_contracts()
    target = warehouse_path(database)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(target))
    try:
        schema = _ident(SCHEMA_NAME)
        catalog = connection.execute("SELECT current_catalog()").fetchone()[0]
        qualified_schema = f"{_quote(catalog)}.{_quote(schema)}"
        connection.execute(f"CREATE SCHEMA IF NOT EXISTS {qualified_schema}")
        for contract in contracts.values():
            _replace_table(connection, qualified_schema, contract, directory)
    finally:
        connection.close()
    return target


def _replace_table(connection, qualified_schema: str, contract: Contract, directory: Path) -> None:
    table = _quote(_ident(contract.table_name))
    columns = []
    for field in contract.columns:
        nullability = "" if field.nullable else " NOT NULL"
        columns.append(f"{_quote(_ident(field.name))} {_TYPES[field.type]}{nullability}")
    connection.execute(f"CREATE OR REPLACE TABLE {qualified_schema}.{table} ({', '.join(columns)})")
    rows = _read_jsonl(directory / contract.file_name)
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
