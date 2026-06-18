"""Pipeline orchestrator.

Runs the five agents in order and degrades gracefully: if one agent raises, the
error is recorded in the report's `errors` list and the remaining stages run with
whatever data is available, rather than failing the whole request.
"""

from typing import Callable, TypeVar

from agents import (
    authority_verifier,
    citation_extractor,
    confidence_scorer,
    fact_checker,
    judicial_memo,
)
from schemas import VerificationReport

CASE_NAME = "Rivera v. Harmon Construction Group"

T = TypeVar("T")


def _safe(name: str, fn: Callable[[], T], default: T, errors: list[str]) -> T:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - any agent failure should degrade, not crash
        errors.append(f"{name}: {exc}")
        return default


def run_pipeline(documents: dict[str, str], model: str = "gpt-4o") -> VerificationReport:
    errors: list[str] = []
    motion = documents["motion_for_summary_judgment"]

    citations = _safe(citation_extractor.NAME, lambda: citation_extractor.run(motion, model), [], errors)
    verdicts = _safe(authority_verifier.NAME, lambda: authority_verifier.run(citations, model), [], errors)
    fact_findings = _safe(fact_checker.NAME, lambda: fact_checker.run(documents, model), [], errors)
    findings = _safe(
        confidence_scorer.NAME,
        lambda: confidence_scorer.run(verdicts, fact_findings, model),
        [],
        errors,
    )
    memo = _safe(judicial_memo.NAME, lambda: judicial_memo.run(findings, model), "", errors)

    return VerificationReport(
        case=CASE_NAME,
        findings=findings,
        citations=verdicts,
        fact_findings=fact_findings,
        judicial_memo=memo,
        errors=errors,
    )
