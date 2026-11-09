"""Command line for generate and load."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from eve_data_generation.config import load_config
from eve_data_generation.contracts import load_contracts
from eve_data_generation.dataset import build_dataset
from eve_data_generation.errors import ConfigError, GenerationError
from eve_data_generation.loader import load_dataset
from eve_data_generation.paths import OUTPUT_ROOT
from eve_data_generation.writer import write_dataset


def dataset_dir(config_file: str, override: str | None) -> Path:
    if override:
        return Path(override)
    return OUTPUT_ROOT / Path(config_file).stem


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eve-data-generation")
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="Write a synthetic dataset")
    generate.add_argument("--config", required=True, help="Path to a generation YAML file")
    generate.add_argument("--output", help="Dataset directory. Defaults to output/<config name>")

    load = commands.add_parser("load", help="Load a dataset into dev_data_003")
    load.add_argument("--config", required=True, help="Path to the generation YAML file")
    load.add_argument("--dataset-dir", help="Dataset directory. Defaults to output/<config name>")
    load.add_argument("--warehouse", help="DuckDB file. Overrides EVE_DATA_GENERATION_DUCKDB_PATH")

    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        directory = dataset_dir(config.config_file, getattr(args, "output", None) or getattr(args, "dataset_dir", None))
        if args.command == "generate":
            dataset = build_dataset(config)
            write_dataset(dataset, load_contracts(), directory)
            print(directory)
        else:
            load_dataset(directory, args.warehouse)
            print(directory)
    except (ConfigError, GenerationError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
