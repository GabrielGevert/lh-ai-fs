"""Unit tests for schema validation, especially confidence coercion."""

import pytest
from pydantic import ValidationError

from schemas import FactFinding, VerificationReport


def _fact(confidence):
    return FactFinding(
        id="F1", claim_in_motion="x", supporting_evidence="y",
        verdict="contradicted", reasoning="z", confidence=confidence,
    )


def test_word_confidence_is_coerced_to_number():
    assert _fact("high").confidence == 0.9
    assert _fact("low").confidence == 0.3
    assert _fact("medium").confidence == 0.6


def test_numeric_confidence_passes_through():
    assert _fact(0.42).confidence == 0.42


def test_out_of_range_confidence_rejected():
    with pytest.raises(ValidationError):
        _fact(1.5)


def test_report_has_safe_defaults():
    report = VerificationReport(case="Test")
    assert report.findings == []
    assert report.citations == []
    assert report.fact_findings == []
    assert report.errors == []
