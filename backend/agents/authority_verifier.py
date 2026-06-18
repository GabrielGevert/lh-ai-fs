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
   - "likely_real": ONLY if you actually recognize this specific case or statute by name and holding.
     A plausible-looking citation format is NOT evidence the case exists. Never infer existence from formatting.
   - "likely_fabricated": clear signs of invention (a holding you know to be wrong attributed to it,
     an implausible reporter/court pairing, or a case you would expect to know but do not).
   - "cannot_verify": you do not recognize it. When torn between real and fabricated, choose cannot_verify.
2. supports_proposition: does the authority support the proposition it is cited for?
   ("yes" / "no" / "partial" / "cannot_verify")
   - Set "no" if the proposition misstates well-established law EVEN IF you cannot verify the case exists.
     Example: claiming OSHA compliance creates a presumption of due care is backwards; the OSH Act does
     not create such a presumption. State the correct rule in reasoning.
   - Set "no" if a case you DO recognize is cited for something it does not actually hold.
3. quote_accuracy: for any direct quote, is it accurate, altered/overbroad, or not something the source says?
   ("accurate" / "altered" / "not_in_source" / "cannot_verify"; use "no_quote" when there is no quote)

CRITICAL RULES:
- NEVER invent a holding to justify a verdict. If unsure about existence, say "cannot_verify".
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
