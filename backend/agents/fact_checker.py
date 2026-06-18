"""Agent 3: FactConsistencyChecker.

Compares the motion's factual assertions against the supporting record and flags
contradictions and unsupported claims. The prompt forbids inventing a
contradiction when the record is silent, that protects the hallucination rate.
"""

from pydantic import BaseModel

from llm import call_llm_json
from schemas import FactFinding

NAME = "FactConsistencyChecker"

SYSTEM_PROMPT = """You are a fact-checker comparing a legal motion against the underlying record.

You are given the motion and three supporting documents:
- police_report
- medical_records_excerpt
- witness_statement

For each MATERIAL factual claim in the motion (dates, who did what, safety equipment,
inspections, who controlled the work), classify it:
- "contradicted": the record directly conflicts with the motion's claim
- "unsupported": the motion asserts something the record neither supports nor mentions
- "corroborated": the record confirms the claim
- "cannot_verify": not enough information either way

RULES:
- Quote the actual source passage in supporting_evidence.
- In source_documents use only these keys: motion_for_summary_judgment, police_report,
  medical_records_excerpt, witness_statement.
- Never invent a contradiction. Silence in the record is "unsupported" or "cannot_verify".
- Include a few "corroborated" claims so precision can be measured, not only flags.
- confidence MUST be a decimal number between 0.0 and 1.0 (e.g. 0.85), never a word.

Assign ids F1, F2, F3, ... Return JSON: {"findings": [ ... ]}."""


class _Response(BaseModel):
    findings: list[FactFinding]


def run(documents: dict[str, str], model: str = "gpt-4o") -> list[FactFinding]:
    motion = documents["motion_for_summary_judgment"]
    support = "\n\n".join(
        f"=== {name} ===\n{text}"
        for name, text in documents.items()
        if name != "motion_for_summary_judgment"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"MOTION:\n\n{motion}\n\n\nSUPPORTING RECORD:\n\n{support}"},
    ]
    return call_llm_json(messages, schema=_Response, model=model).findings
