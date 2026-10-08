"""
Unit tests for pipeline/quality.py — Week 5 Assignment, Part 2.

Four example tests are written for you. Add the rest: every check gets one test
where it passes and one where it fails, and the failing test breaks ONE thing in
good_facts.

Run from Week5/assignment/:
    pytest -v
"""

import pytest

import quality
from quality import DataQualityError, run_quality_checks

REQUIRED_KEYS = {"check", "passed", "detail"}


# ── Examples (provided) ──────────────────────────────────────────────────────

def test_good_batch_passes_every_check(good_facts):
    results = run_quality_checks(good_facts)
    failed = [r["check"] for r in results if not r["passed"]]
    assert failed == []


def test_every_check_returns_the_same_keys(good_facts):
    # In the class quality.py some checks returned "details" and others "detail".
    # This test stops that from coming back.
    for result in run_quality_checks(good_facts):
        assert set(result) == REQUIRED_KEYS, result["check"]


def test_negative_fare_fails(good_facts):
    bad = good_facts.copy()
    bad.loc[0, "fare_amount"] = -1.00
    result = quality.check_no_negative_fare(bad)
    assert result["passed"] is False


def test_run_reports_every_failure_not_just_the_first(good_facts):
    bad = good_facts.copy()
    bad.loc[0, "fare_amount"] = -1.00                 # breaks no_negative_fare
    bad.loc[1, "trip_status"] = "Completed "          # breaks valid_status
    with pytest.raises(DataQualityError) as exc:
        run_quality_checks(bad)
    assert "no_negative_fare" in str(exc.value)
    assert "valid_status" in str(exc.value)


# ── Your tests ───────────────────────────────────────────────────────────────
# TODO: one passing and one failing test per check, plus:
#   - an empty batch (empty_facts fixture) does not raise
#   - fare_formula fails on a fare rounded the wrong way (47.62 instead of 47.63)
