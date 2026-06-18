"""Agent 2: AuthorityVerifier.

For each extracted citation, judges three things using the model's legal
knowledge:
  1. does the cited authority plausibly exist (or is it fabricated),
  2. does it actually support the stated proposition,
  3. is any quoted language accurate or quietly altered.

This agent relies on the model's parametric knowledge of US/California law, it has
no access to a real legal database. To keep the hallucination rate low, the prompt
is calibrated to prefer "cannot_verify" over inventing a holding. Each citation is
verified independently so one uncertain case cannot contaminate the others.
"""

from llm import call_llm_json
from schemas import Citation, CitationVerdict

NAME = "AuthorityVerifier"

SYSTEM_PROMPT = """You are a skeptical legal-research verifier. You assess one citation at a time
using only your own knowledge of US and California law. You have NO access to a legal database.

Assess three things:
1. exists_verdict:
   - "likely_real" only if you are genuinely familiar with this case/statute
   - "likely_fabricated" if the citation looks invented (unknown case, implausible reporter/jurisdiction pairing)
   - "cannot_verify" if you simply do not know
2. supports_proposition: does the authority, as you understand it, support the proposition it is cited for?
   ("yes" / "no" / "partial" / "cannot_verify")
3. quote_accuracy: for any direct quote, is it accurate, altered/overbroad, or not something the source says?
   ("accurate" / "altered" / "not_in_source" / "cannot_verify"; use "no_quote" when there is no quote)

CRITICAL RULES:
- NEVER invent a holding or claim a case says something to justify a verdict. If unsure, say "cannot_verify".
- Watch for real cases cited for propositions they do not hold (misrepresented authority).
- Watch for quotes that overstate a rule (e.g. turning a rebuttable presumption into an absolute "never").
- Watch for out-of-jurisdiction citations (e.g. Texas or Florida cases) offered as if binding in California.
- confidence (0.0-1.0) reflects how sure you are of YOUR assessment, not of the citation.

Return JSON matching the schema with fields: citation_id, citation_text, exists_verdict,
supports_proposition, quote_accuracy, reasoning, confidence."""


def _verify_one(citation: Citation, model: str) -> CitationVerdict:
    quotes = "\n".join(f'  - "{q}"' for q in citation.direct_quotes) or "  (none)"
    user = (
        f"Citation: {citation.citation_text}\n"
        f"Cited to support: {citation.proposition}\n"
        f"Direct quotes attributed to it:\n{quotes}\n"
        f"Location: {citation.location}"
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
    verdict = call_llm_json(messages, schema=CitationVerdict, model=model)
    # Trust our own id over whatever the model echoes back.
    verdict.citation_id = citation.id
    verdict.citation_text = citation.citation_text
    return verdict


def run(citations: list[Citation], model: str = "gpt-4o") -> list[CitationVerdict]:
    """Verify each citation independently."""
    return [_verify_one(c, model) for c in citations]
