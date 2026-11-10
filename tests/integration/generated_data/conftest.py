"""Session fixture for the generated-data suite."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from validate_generated import run_suite


@pytest.fixture(scope="session")
def suite():
    repo = Path(__file__).resolve().parents[3]
    return run_suite(repo)
