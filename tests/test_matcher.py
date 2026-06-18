"""Unit tests for the deterministic eval logic (no API calls)."""

import matcher


def test_extract_quotes_handles_double_single_and_contractions():
    text = (
        'The report says "a clearly quoted passage here" and also '
        "'another spaced passage here' but not a don't contraction."
    )
    quotes = matcher._extract_quotes(text)
    assert "a clearly quoted passage here" in quotes
    assert "another spaced passage here" in quotes
    assert all("don't" not in q for q in quotes)


def test_matches_requires_keywords_and_any_of():
    det = {"text": "the motion misquotes privette by saying never liable"}
    assert matcher._matches(det, {"keywords": ["privette"], "any_of": ["never"]})
    assert not matcher._matches(det, {"keywords": ["privette"], "any_of": ["jurisdiction"]})
    assert not matcher._matches(det, {"keywords": ["seabright"]})


def test_detections_skip_uncertainty_and_corroboration():
    report = {
        "citations": [
            {"citation_id": "C1", "citation_text": "Real Case", "reasoning": "ok",
             "exists_verdict": "likely_real", "supports_proposition": "yes", "quote_accuracy": "no_quote"},
            {"citation_id": "C2", "citation_text": "Bad Case", "reasoning": "altered quote",
             "exists_verdict": "likely_real", "supports_proposition": "no", "quote_accuracy": "altered"},
        ],
        "fact_findings": [
            {"id": "F1", "claim_in_motion": "x", "supporting_evidence": "y", "reasoning": "z",
             "verdict": "corroborated", "source_documents": [], "confidence": 0.9},
            {"id": "F2", "claim_in_motion": "wrong date march 14", "supporting_evidence": "'march 12'",
             "reasoning": "z", "verdict": "contradicted", "source_documents": [], "confidence": 0.9},
        ],
        "findings": [],
    }
    dets = matcher.detections_from_report(report)
    # A supported real citation and a corroborated fact are not detections.
    assert len(dets) == 2
    kinds = sorted(d["kind"] for d in dets)
    assert kinds == ["citation", "fact"]


def _docs():
    return {"police_report": "The incident occurred on March 12, 2021 at the site."}


def _ground_truth():
    return {"flaws": [
        {"id": "B1", "category": "fact", "type": "factual_contradiction", "severity": "high", "any_of": ["march 14"]},
        {"id": "Z9", "category": "fact", "type": "unsupported_claim", "severity": "low", "any_of": ["never appears"]},
    ]}


def test_evaluate_recall_precision_and_grounding():
    report = {
        "citations": [],
        "findings": [],
        "fact_findings": [
            {"id": "F1", "claim_in_motion": "incident on March 14, 2021",
             "supporting_evidence": "police report: 'The incident occurred on March 12, 2021'",
             "reasoning": "dates differ", "verdict": "contradicted",
             "source_documents": ["police_report"], "confidence": 0.95},
        ],
    }
    res = matcher.evaluate(report, _ground_truth(), _docs())
    assert res["recall"] == 0.5          # B1 caught, Z9 missed
    assert res["precision"] == 1.0       # the single detection maps to a real flaw
    assert res["hallucination_rate"] == 0.0  # quote (minus trailing punctuation) is grounded
    assert "Z9" in res["missed"]


def test_evaluate_flags_ungrounded_quote_as_hallucination():
    report = {
        "citations": [],
        "findings": [],
        "fact_findings": [
            {"id": "F1", "claim_in_motion": "claim",
             "supporting_evidence": "record says 'this passage does not exist anywhere'",
             "reasoning": "made up", "verdict": "contradicted",
             "source_documents": ["police_report"], "confidence": 0.9},
        ],
    }
    res = matcher.evaluate(report, _ground_truth(), _docs())
    assert res["hallucination_rate"] == 1.0
