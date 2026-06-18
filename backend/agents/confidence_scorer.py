"""Agent 4: ConfidenceScorer.

Consolidates the raw citation verdicts and fact findings into a single, deduplicated
list of Findings, each with a severity, a calibrated confidence, and one-sentence
reasoning. Items that are merely corroborated or an honest "cannot_verify" with no
underlying problem are dropped here, so uncertainty never becomes a flag.
"""

import json

from pydantic import BaseModel

from llm import call_llm_json
from schemas import CitationVerdict, FactFinding, Finding

NAME = "ConfidenceScorer"

SYSTEM_PROMPT = """You are the calibration layer of a legal verification pipeline.

You receive raw outputs from two upstream agents: citation verdicts and fact findings.
Turn the genuine problems into a single consolidated list of findings.

For each finding choose a type:
- misquote, fabricated_citation, misrepresented_authority, irrelevant_jurisdiction (citation issues)
- factual_contradiction, unsupported_claim, misleading_argument (record/argument issues)

Rules:
- Only include real problems. Drop corroborated facts and bare "cannot_verify" with no issue.
- Flag a citation to an out-of-jurisdiction court (e.g. Texas, Florida) offered as binding
  in California as irrelevant_jurisdiction.
- severity = impact on the motion's success (high / medium / low).
- confidence = a decimal 0.0-1.0 of how sure the pipeline is, with one-sentence
  confidence_reasoning. Inherit and temper the upstream confidence; downgrade speculation.
- Merge duplicates that describe the same underlying problem.
- claim = what the motion asserts; evidence = what the record or the law actually says.
- Carry source_documents from the underlying fact finding into the finding; do not leave it empty
  when the upstream finding listed sources. Use only these keys: motion_for_summary_judgment,
  police_report, medical_records_excerpt, witness_statement.

Assign ids like "1", "2", ... Return JSON: {"findings": [ ... ]}."""


class _Response(BaseModel):
    findings: list[Finding]


def run(
    verdicts: list[CitationVerdict],
    fact_findings: list[FactFinding],
    model: str = "gpt-4o",
) -> list[Finding]:
    payload = {
        "citation_verdicts": [v.model_dump() for v in verdicts],
        "fact_findings": [f.model_dump() for f in fact_findings],
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"RAW AGENT OUTPUT:\n\n{json.dumps(payload, indent=2)}"},
    ]
    return call_llm_json(messages, schema=_Response, model=model).findings
