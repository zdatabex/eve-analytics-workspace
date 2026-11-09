"""Filesystem locations owned by the data-generation component."""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
DATA_GENERATION_ROOT = PACKAGE_DIR.parents[1]
REPO_ROOT = PACKAGE_DIR.parents[2]
CONTRACTS_ROOT = REPO_ROOT / "contracts" / "source"
CONFIG_DIR = DATA_GENERATION_ROOT / "config"
OUTPUT_ROOT = DATA_GENERATION_ROOT / "output"
DEFAULT_WAREHOUSE = OUTPUT_ROOT / "warehouse" / "dev_data_003"
SCHEMA_NAME = "dev_data_003"
WAREHOUSE_ENV = "EVE_DATA_GENERATION_DUCKDB_PATH"
