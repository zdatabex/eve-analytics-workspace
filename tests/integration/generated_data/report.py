"""Render the DATA-005 data-quality report. The report has no wall-clock timestamp."""

from __future__ import annotations

from model import CHECKS, CHECK_TITLES, DatasetRun, Defect


def render(runs: list[DatasetRun], defects: list[Defect], recommendations: list[tuple[str, str]]) -> str:
    lines = [
        "# DATA-005 data-quality report",
        "",
        "This report records the validation of the four committed synthetic datasets. It has no wall-clock timestamp.",
        "",
        "## Datasets",
        "",
    ]
    for run in runs:
        lines.extend(_dataset_section(run))
    for index, check in enumerate(CHECKS, start=1):
        if check == "load_readback":
            title = "Load read-back"
        else:
            title = CHECK_TITLES[check]
        lines.extend(["", f"## {index}. {title}", ""])
        lines.extend(_result_table(runs, defects, check))
        if check == "distributions_and_edge_cases":
            lines.extend(_distribution_sections(runs))
        check_defects = [item for item in defects if item.check == check]
        lines.extend(["", "### Defects", ""])
        if not check_defects:
            lines.append("No defects.")
        else:
            for number, item in enumerate(check_defects, start=1):
                lines.extend(_defect_block(number, item))
                lines.append("")
    lines.extend(["", "## Recommendations", ""])
    if not recommendations:
        lines.append("None.")
    else:
        for config_path, text in recommendations:
            lines.append(f"- `{config_path}`: {text}")
    lines.append("")
    return "\n".join(lines)


def _dataset_section(run: DatasetRun) -> list[str]:
    lines = [
        f"### {run.path}",
        "",
        f"- Population: {run.population}",
        f"- Seed: {run.seed or run.expected_seed}",
        f"- Window: {run.start or 'unknown'} through {run.end or 'unknown'}",
        f"- Delivery id: {run.delivery_id or 'unknown'}",
        f"- Warehouse file: {run.load_schema}",
        f"- Generate command: `{run.generate_command}`",
        "",
        "| Entity | Rows |",
        "| --- | --- |",
    ]
    for entity, count in sorted(run.row_counts.items()):
        lines.append(f"| {entity} | {count} |")
    if not run.row_counts:
        lines.append("| n/a | n/a |")
    lines.append("")
    return lines


def _result_table(runs: list[DatasetRun], defects: list[Defect], check: str) -> list[str]:
    lines = [
        "| Configuration | Result | Failures |",
        "| --- | --- | --- |",
    ]
    for run in runs:
        count = sum(1 for item in defects if item.check == check and item.config_path == run.path)
        result = "defect" if count else "pass"
        lines.append(f"| {run.path} | {result} | {count} |")
    return lines


def _distribution_sections(runs: list[DatasetRun]) -> list[str]:
    lines = ["", "### Distributions", ""]
    for run in runs:
        if run.population == "baseline":
            lines.extend(_baseline_distribution(run))
        else:
            lines.extend(_scenario_inventory(run))
    lines.extend(["", "### Edge cases", ""])
    for run in runs:
        lines.append(f"#### {run.path}")
        lines.append("")
        lines.append("| Case | Status |")
        lines.append("| --- | --- |")
        for name, status in run.edges:
            lines.append(f"| {name} | {status} |")
        if not run.edges:
            lines.append("| n/a | missing |")
        lines.append("")
    return lines


def _baseline_distribution(run: DatasetRun) -> list[str]:
    distribution = run.distribution
    lines = [f"#### {run.path}", ""]
    lines.extend([
        "| Count | Expected | Observed |",
        "| --- | --- | --- |",
    ])
    for label, expected, observed in distribution.get("counts", []):
        lines.append(f"| {label} | {expected} | {observed} |")
    lines.extend([
        "",
        "| Rate | Population | Population size | share_count | Observed | Fails when different |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in distribution.get("rates", []):
        lines.append("| " + " | ".join(row) + " |")
    for title, rows in distribution.get("mixes", []):
        lines.extend([
            "",
            f"##### {title}",
            "",
            "| Label | Weight | Allocated | Observed |",
            "| --- | --- | --- | --- |",
        ])
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
    lines.extend([
        "",
        "| Emitted event | Status |",
        "| --- | --- |",
    ])
    for name, status in distribution.get("events", []):
        lines.append(f"| {name} | {status} |")
    lines.append("")
    lines.append(
        "`duplicate_contact_email_rate` and `domain_match_rate` are recorded beside `share_count` and do not fail the suite by themselves."
    )
    lines.append("")
    return lines


def _scenario_inventory(run: DatasetRun) -> list[str]:
    lines = [
        f"#### {run.path}",
        "",
        "Baseline count and rate keys are not applied to this file as population targets.",
        "",
        "| Journey | Expected | Observed |",
        "| --- | --- | --- |",
    ]
    for name, expected, observed in run.journeys:
        lines.append(f"| {name} | {expected} | {observed} |")
    if not run.journeys:
        lines.append("| n/a | n/a | n/a |")
    lines.append("")
    return lines


def _defect_block(number: int, item: Defect) -> list[str]:
    return [
        f"{number}. Configuration: `{item.config_path}`",
        f"   Seed: {item.seed}",
        f"   Generate command: `{item.generate_command}`",
        f"   Check: {item.check}",
        f"   Contract: `{item.contract}`",
        f"   Rule: {item.rule}",
        f"   Entity: {item.entity}",
        f"   observation_key: {item.observation_key}",
        f"   Field: {item.field}",
        f"   Actual: {item.actual}",
    ]
