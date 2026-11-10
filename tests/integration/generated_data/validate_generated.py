"""Generate the four committed datasets and validate them.

The suite shells out to the public generate and load commands. It does not
import eve_data_generation.validate.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import duckdb
import yaml

from model import (
    DEVELOPMENT_END,
    DEVELOPMENT_START,
    ContractSpec,
    DatasetRun,
    Defect,
    add_defect,
    as_date,
    generate_command,
    load_contracts,
    parse_date,
    parse_decimal,
    parse_timestamp,
)
from population import check_population
from quality import (
    check_commercial,
    check_completeness,
    check_configuration,
    check_foreign_keys,
    check_keys,
    check_lifecycle,
    check_schema,
    check_temporal,
    check_usage,
)
from report import render


CONFIGS = (
    {
        "path": "data-generation/config/default.yaml",
        "population": "baseline",
        "seed": 1003,
        "load_schema": "dev_data_003",
    },
    {
        "path": "data-generation/config/test.yaml",
        "population": "baseline",
        "seed": 7,
        "load_schema": "dev_data_003",
    },
    {
        "path": "data-generation/config/scenarios.yaml",
        "population": "scenario",
        "seed": 1004,
        "load_schema": "dev_data_004",
    },
    {
        "path": "data-generation/config/scenarios-test.yaml",
        "population": "scenario",
        "seed": 4004,
        "load_schema": "dev_data_004",
    },
)

REPORT_NAME = "DATA-005-report.md"


@dataclass
class SuiteResult:
    defects: list[Defect]
    report_text: str
    committed_text: str
    runs: list[DatasetRun]


def run_suite(repo: Path) -> SuiteResult:
    report_path = repo / "tests" / "integration" / "generated_data" / REPORT_NAME
    committed = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    contracts = load_contracts(repo / "contracts" / "source")
    development_days = (DEVELOPMENT_END - DEVELOPMENT_START).days
    watched = (
        repo / "data" / "warehouse" / "dev_data_003",
        repo / "data" / "warehouse" / "dev_data_004",
    )
    output_root = repo / "data-generation" / "output"
    generated_root = repo / "data" / "generated"
    before_watched = {path: _snapshot(path) for path in watched}
    before_output = output_root.exists()
    before_generated = generated_root.exists()
    defects: list[Defect] = []
    recommendations: list[tuple[str, str]] = []
    runs: list[DatasetRun] = []
    with tempfile.TemporaryDirectory(prefix="data-005-") as temporary:
        root = Path(temporary)
        for spec in CONFIGS:
            runs.append(_prepare(repo, root, spec, contracts, defects, development_days))
        for run in runs:
            if not run.generated:
                continue
            check_schema(run, contracts, defects)
            check_keys(run, contracts, defects)
            check_foreign_keys(run, contracts, defects)
            check_completeness(run, contracts, defects)
            check_lifecycle(run, contracts, defects)
            check_temporal(run, contracts, defects)
            check_commercial(run, contracts, defects)
            check_usage(run, contracts, defects)
            check_population(run, defects, recommendations)
            _load(repo, run, contracts, defects)
        _warehouse_untouched(
            runs[0] if runs else None,
            before_watched,
            before_output,
            before_generated,
            output_root,
            generated_root,
            defects,
        )
    defects = _cap(defects)
    recommendations = sorted(set(recommendations))
    text = render(runs, defects, recommendations)
    report_path.write_text(text, encoding="utf-8")
    return SuiteResult(defects=defects, report_text=text, committed_text=committed, runs=runs)


def _prepare(repo, root, spec, contracts, defects, development_days) -> DatasetRun:
    path = spec["path"]
    run = DatasetRun(
        path=path,
        population=spec["population"],
        expected_seed=spec["seed"],
        load_schema=spec["load_schema"],
        generate_command=generate_command(path),
        seed=str(spec["seed"]),
    )
    config_path = repo / path
    if not config_path.exists():
        add_defect(defects, run, "schema_compliance", "The committed configuration file exists.", field="config", actual="missing")
        return run
    run.config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    start = as_date(run.config.get("start_date"))
    end = as_date(run.config.get("end_date"))
    run.start = start.isoformat() if start else ""
    run.end = end.isoformat() if end else ""
    run.delivery_id = f"dlv_{run.config.get('seed')}"
    run.seed = str(run.config.get("seed"))
    check_configuration(run, defects, development_days)
    first = root / Path(path).stem / "first"
    second = root / Path(path).stem / "second"
    run.warehouse = root / Path(path).stem / "warehouse.duckdb"
    first_ok = _generate(repo, path, first, run, defects)
    second_ok = _generate(repo, path, second, run, defects)
    if first_ok and second_ok:
        _compare_bytes(first, second, run, defects)
        run.reproducible = not any(item.check == "reproducibility" and item.config_path == path for item in defects)
    elif not any(item.check == "reproducibility" and item.config_path == path for item in defects):
        add_defect(
            defects, run, "reproducibility",
            "Two generate commands with the same file and an explicit output directory produce the same file bytes.",
            field="generate", actual="generation failed",
        )
    if not first_ok:
        return run
    run.directory = first
    run.generated = True
    _read_dataset(run, contracts, defects)
    return run


def _generate(repo: Path, config: str, output: Path, run: DatasetRun, defects: list[Defect]) -> bool:
    completed = subprocess.run(
        [sys.executable, "-m", "eve_data_generation", "generate", "--config", config, "--output", str(output)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        add_defect(
            defects, run, "reproducibility",
            "The suite generates the committed configuration with the existing generate command.",
            field="generate", actual=(completed.stderr or completed.stdout).strip()[:500],
        )
        return False
    return True


def _compare_bytes(first: Path, second: Path, run: DatasetRun, defects: list[Defect]) -> None:
    left = _files(first)
    right = _files(second)
    if set(left) != set(right):
        add_defect(
            defects, run, "reproducibility",
            "Two generate commands with the same file produce the same file bytes, including manifest.json and row order.",
            field="files", actual=f"left={sorted(left)} right={sorted(right)}",
        )
        return
    for name in sorted(left):
        if left[name] != right[name]:
            add_defect(
                defects, run, "reproducibility",
                "Two generate commands with the same file produce the same file bytes, including manifest.json and row order.",
                field=name, actual="byte mismatch",
            )


def _files(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def _read_dataset(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    run.manifests = {}
    if run.directory is not None:
        for source in sorted({contract.source_system for contract in contracts.values()}):
            manifest_path = run.directory / source / "manifest.json"
            if manifest_path.is_file():
                run.manifests[source] = json.loads(manifest_path.read_text(encoding="utf-8"))
    run.manifest = next(iter(run.manifests.values()), None)
    if isinstance(run.manifest, dict) and run.manifest.get("delivery_id"):
        run.delivery_id = str(run.manifest.get("delivery_id"))
    for contract in contracts.values():
        path = run.directory / contract.file_name
        if not path.exists():
            run.row_counts[contract.id] = "missing"
            run.rows[contract.id] = []
            continue
        rows = []
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if line:
                rows.append(json.loads(line))
        run.rows[contract.id] = rows
        run.row_counts[contract.id] = str(len(rows))


def _load(repo: Path, run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    env = os.environ.copy()
    env["EVE_DATA_GENERATION_DUCKDB_PATH"] = str(run.warehouse)
    completed = _load_once(repo, run, env)
    if completed.returncode != 0:
        add_defect(
            defects, run, "load_readback",
            "The load command writes raw_<source_system>.<source_entity> into the temporary warehouse file.",
            field="load", actual=(completed.stderr or completed.stdout).strip()[:500],
        )
        return
    _compare_warehouse(run, contracts, defects)
    if not run.path.endswith("test.yaml"):
        return
    before = _table_counts(run, contracts)
    second = _load_once(repo, run, env)
    if second.returncode != 0:
        add_defect(
            defects, run, "load_readback",
            "A second load of test.yaml replaces the table contents.",
            field="load", actual=(second.stderr or second.stdout).strip()[:500],
        )
        return
    after = _table_counts(run, contracts)
    if before != after:
        add_defect(
            defects, run, "load_readback",
            "A second load of test.yaml replaces the table contents and does not append a duplicate copy.",
            field="rows", actual=f"before={before} after={after}",
        )
    _compare_warehouse(run, contracts, defects)


def _load_once(repo: Path, run: DatasetRun, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable, "-m", "eve_data_generation", "load",
            "--config", run.path,
            "--dataset-dir", str(run.directory),
            "--warehouse", str(run.warehouse),
        ],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _compare_warehouse(run: DatasetRun, contracts: dict[str, ContractSpec], defects: list[Defect]) -> None:
    connection = duckdb.connect(str(run.warehouse), read_only=True)
    try:
        schemas = {
            row[0]
            for row in connection.execute(
                "select schema_name from information_schema.schemata"
            ).fetchall()
        }
        retired = sorted(schemas & {"dev_data_003", "dev_data_004", "dev_data_005"})
        if retired:
            add_defect(
                defects, run, "load_readback",
                "The temporary file has no schema named dev_data_003, dev_data_004, or dev_data_005.",
                field="schema", actual=retired,
            )
        table_names = connection.execute(
            "select table_schema, table_name from information_schema.tables"
        ).fetchall()
        retired_tables = sorted(
            f"{schema}.{table}" for schema, table in table_names if str(table).startswith("src_")
        )
        if retired_tables:
            add_defect(
                defects, run, "load_readback",
                "The temporary file has no table named src_<source_system>_<source_entity>.",
                field="table", actual=retired_tables,
            )
        for contract in contracts.values():
            if contract.raw_schema not in schemas:
                add_defect(
                    defects, run, "load_readback",
                    "The load command writes schema raw_<source_system> and table <source_entity>.",
                    contract=contract.path, entity=contract.id, field="schema",
                    actual=sorted(schemas),
                )
                continue
            columns = [
                row[0]
                for row in connection.execute(
                    """
                    select column_name
                    from information_schema.columns
                    where table_schema = ? and table_name = ?
                    order by ordinal_position
                    """,
                    [contract.raw_schema, contract.table_name],
                ).fetchall()
            ]
            expected = [column.name for column in contract.columns]
            if columns != expected:
                add_defect(
                    defects, run, "load_readback",
                    "Columns are the contract fields followed by the ingestion fields.",
                    contract=contract.path, entity=contract.id, field="columns",
                    actual=columns,
                )
                continue
            quoted = ", ".join(f'"{name}"' for name in expected)
            loaded = connection.execute(
                f'select {quoted} from "{contract.raw_schema}"."{contract.table_name}"'
            ).fetchall()
            json_rows = [
                tuple(_normalize_json(row.get(column.name), column) for column in contract.columns)
                for row in run.rows.get(contract.id, [])
            ]
            db_rows = [
                tuple(_normalize_db(value, column) for value, column in zip(record, contract.columns))
                for record in loaded
            ]
            if Counter(json_rows) != Counter(db_rows):
                add_defect(
                    defects, run, "load_readback",
                    "Values match the JSON Lines, including nulls and exact decimals.",
                    contract=contract.path, entity=contract.id, field="rows",
                    actual=f"json={len(json_rows)} warehouse={len(loaded)}",
                )
    finally:
        connection.close()


def _table_counts(run: DatasetRun, contracts: dict[str, ContractSpec]) -> dict[str, int]:
    connection = duckdb.connect(str(run.warehouse), read_only=True)
    try:
        counts = {}
        for contract in contracts.values():
            counts[contract.id] = connection.execute(
                f'select count(*) from "{contract.raw_schema}"."{contract.table_name}"'
            ).fetchone()[0]
        return counts
    finally:
        connection.close()


def _normalize_json(value, column):
    if value is None:
        return None
    if column.type == "decimal":
        parsed = parse_decimal(value)
        return None if parsed is None else parsed
    if column.type == "integer":
        return None if isinstance(value, bool) else value
    if column.type == "date":
        return parse_date(value)
    if column.type == "timestamp":
        return parse_timestamp(value)
    return value


def _normalize_db(value, column):
    if value is None:
        return None
    if column.type == "decimal":
        parsed = parse_decimal(f"{value:.2f}") if not isinstance(value, str) else parse_decimal(value)
        return parsed
    if column.type == "integer":
        return int(value)
    if column.type == "date":
        return value
    if column.type == "timestamp":
        return value.replace(tzinfo=None) if getattr(value, "tzinfo", None) else value
    return value


def _warehouse_untouched(
    run,
    before_watched: dict[Path, tuple | None],
    output_existed: bool,
    generated_existed: bool,
    output_root: Path,
    generated_root: Path,
    defects: list[Defect],
) -> None:
    if run is None:
        return
    changed = []
    for path, before in before_watched.items():
        after = _snapshot(path)
        if before != after:
            changed.append(path.name)
    output_created = not output_existed and output_root.exists()
    generated_created = not generated_existed and generated_root.exists()
    if changed or output_created or generated_created:
        add_defect(
            defects, run, "load_readback",
            "The suite does not write data-generation/output/ or data/generated/, "
            "and it does not create or replace data/warehouse/dev_data_003 or data/warehouse/dev_data_004.",
            field="warehouse",
            actual=(
                f"changed={changed} output_created={output_created} "
                f"generated_created={generated_created}"
            ),
        )


def _snapshot(path: Path):
    if not path.exists():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return (path.stat().st_size, digest)


def _cap(defects: list[Defect]) -> list[Defect]:
    grouped: dict[tuple[str, str], list[Defect]] = {}
    for item in defects:
        grouped.setdefault((item.check, item.config_path), []).append(item)
    capped = []
    for items in grouped.values():
        items.sort(key=lambda item: item.sort_key())
        capped.extend(items[:25])
        if len(items) > 25:
            sample = items[0]
            capped.append(
                Defect(
                    config_path=sample.config_path,
                    seed=sample.seed,
                    generate_command=sample.generate_command,
                    check=sample.check,
                    contract="n/a",
                    rule="Additional failures of this check were omitted from the report.",
                    entity="n/a",
                    observation_key="n/a",
                    field="failures",
                    actual=f"{len(items)} failures; first 25 listed",
                )
            )
    capped.sort(key=lambda item: item.sort_key())
    return capped


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    result = run_suite(repo)
    print(f"defects={len(result.defects)}")
    for item in result.defects[:50]:
        print(item.one_line())
    return 1 if result.defects else 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
