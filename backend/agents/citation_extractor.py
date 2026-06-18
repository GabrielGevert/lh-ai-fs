"""Agent 1: CitationExtractor.

Pulls every legal authority out of the motion together with the proposition it
is offered for and any quoted language. It deliberately does NOT judge accuracy,
that is the AuthorityVerifier's job. Keeping extraction and verification separate
keeps each prompt focused and lets us measure them independently.
"""

from pydantic import BaseModel

from llm import call_llm_json
from schemas import Citation

NAME = "CitationExtractor"

SYSTEM_PROMPT = """You are a meticulous legal citation extractor.

Extract EVERY legal authority cited in the motion below, including:
- case citations in the body (e.g. "Privette v. Superior Court, 5 Cal.4th 689 (1993)")
- statutes and code sections (e.g. "Code of Civil Procedure Section 335.1")
- every case listed in footnote string cites (extract each one separately)

For each authority capture:
- citation_text: the citation exactly as written
- proposition: the legal proposition it is offered to support, paraphrased from the surrounding sentence
- direct_quotes: any text in quotation marks that the motion attributes to this authority (empty list if none)
- location: where it appears, e.g. "Section III.A", "Statement of Facts", or "Footnote 1"
- is_footnote: true only if it appears in a footnote

Do NOT assess whether the citation is accurate, real, or supportive. Only extract.
Assign ids C1, C2, C3, ... in order of appearance.
Return JSON: {"citations": [ ... ]}."""


class _Response(BaseModel):
    citations: list[Citation]


def run(motion_text: str, model: str = "gpt-4o") -> list[Citation]:
    """Extract all citations from the motion text."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"MOTION:\n\n{motion_text}"},
    ]
    return call_llm_json(messages, schema=_Response, model=model).citations
