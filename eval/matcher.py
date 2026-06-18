"""Match a pipeline report against the ground-truth answer key and score it.

Metrics:
- recall: fraction of planted flaws caught by at least one detection.
- precision: fraction of detections that map to a real flaw (not a false flag).
- hallucination_rate: among detections that quote the record, the fraction whose
  quote cannot be found in any document. This is a grounding check, it catches a
  flag invented from a passage that does not exist, which precision alone misses.

A "detection" is any statement the pipeline makes that something is wrong. An
appropriate "cannot_verify" or "corroborated" is deliberately NOT a detection, so
expressing uncertainty is never punished as a false flag.
"""

import re

_DOUBLE_QUOTE_RE = re.compile(r'"([^"]{8,})"')
_SINGLE_QUOTE_RE = re.compile(r"'([^']{10,})'")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _loose(text: str) -> str:
    # Strip punctuation for grounding so a faithful quote that the model truncated
    # with a trailing period still matches the source passage.
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def _extract_quotes(text: str) -> list[str]:
    # Models quote source passages with either double or single quotes. Single-quote
    # spans must contain a space so word contractions ("Apex's") are not treated as quotes.
    text = text.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    spans = _DOUBLE_QUOTE_RE.findall(text)
    spans += [s for s in _SINGLE_QUOTE_RE.findall(text) if " " in s]
    return [_norm(s) for s in spans]


def detections_from_report(report: dict) -> list[dict]:
    dets: list[dict] = []

    for c in report.get("citations", []):
        flagged = (
            c.get("exists_verdict") == "likely_fabricated"
            or c.get("supports_proposition") == "no"
            or c.get("quote_accuracy") in ("altered", "not_in_source")
        )
        if flagged:
            dets.append({
                "kind": "citation",
                "text": _norm(f"{c.get('citation_text', '')} {c.get('reasoning', '')}"),
                "quotes": [],
                "raw": c,
            })

    for f in report.get("fact_findings", []):
        if f.get("verdict") in ("contradicted", "unsupported"):
            blob = f"{f.get('claim_in_motion', '')} {f.get('supporting_evidence', '')} {f.get('reasoning', '')}"
            dets.append({
                "kind": "fact",
                "text": _norm(blob),
                "quotes": _extract_quotes(f.get("supporting_evidence", "")),
                "raw": f,
            })

    # Normalized findings (added in a later block) are always positive detections.
    for f in report.get("findings", []):
        blob = f"{f.get('summary', '')} {f.get('claim', '')} {f.get('evidence', '')}"
        dets.append({
            "kind": "finding",
            "text": _norm(blob),
            "quotes": _extract_quotes(f.get("evidence", "")),
            "raw": f,
        })

    return dets


def _matches(detection: dict, flaw: dict) -> bool:
    text = detection["text"]
    if not all(_norm(kw) in text for kw in flaw.get("keywords", [])):
        return False
    any_of = flaw.get("any_of")
    if any_of and not any(_norm(a) in text for a in any_of):
        return False
    return bool(flaw.get("keywords") or any_of)


def evaluate(report: dict, ground_truth: dict, documents: dict[str, str]) -> dict:
    flaws = ground_truth["flaws"]
    detections = detections_from_report(report)

    per_flaw = [
        {"id": f["id"], "category": f["category"], "severity": f["severity"],
         "caught": any(_matches(d, f) for d in detections)}
        for f in flaws
    ]
    caught = sum(1 for f in per_flaw if f["caught"])
    recall = caught / len(flaws) if flaws else 0.0

    matched = [d for d in detections if any(_matches(d, f) for f in flaws)]
    precision = len(matched) / len(detections) if detections else 0.0

    docs_loose = _loose(" ".join(documents.values()))
    grounded_assessable = [d for d in detections if d["quotes"]]
    ungrounded = [d for d in grounded_assessable
                  if not any(_loose(q) in docs_loose for q in d["quotes"])]
    hallucination_rate = len(ungrounded) / len(grounded_assessable) if grounded_assessable else 0.0

    return {
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "hallucination_rate": round(hallucination_rate, 3),
        "caught": caught,
        "total_flaws": len(flaws),
        "total_detections": len(detections),
        "matched_detections": len(matched),
        "grounding_assessable": len(grounded_assessable),
        "ungrounded_detections": len(ungrounded),
        "per_flaw": per_flaw,
        "missed": [f["id"] for f in per_flaw if not f["caught"]],
    }
