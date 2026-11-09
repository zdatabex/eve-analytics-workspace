"""Acceptance tests for the four committed synthetic datasets."""

from __future__ import annotations

import pytest

from model import CHECKS


@pytest.mark.parametrize("check", CHECKS)
def test_generated_data_check(suite, check):
    failures = [item.one_line() for item in suite.defects if item.check == check]
    assert failures == []


def test_report_matches_committed_text(suite):
    assert suite.report_text == suite.committed_text
