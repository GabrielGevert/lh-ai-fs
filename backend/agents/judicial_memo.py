"""Agent 5: JudicialMemoAgent.

Synthesizes the most serious findings into a single measured paragraph addressed to
a judge. Only high-confidence findings are mentioned, so the memo never amplifies a
speculative flag.
"""

import json

from llm import call_llm
from schemas import Finding

NAME = "JudicialMemoAgent"

SYSTEM_PROMPT = """You are a neutral judicial law clerk. Given a list of verification findings about a
motion, write ONE paragraph (max ~120 words) for the judge summarizing the most serious problems.

- Mention only findings with confidence >= 0.6.
- Be measured and precise; do not overstate or speculate.
- No bullet points, no headings, a single prose paragraph.
- If there are no qualifying findings, say that no material verification problems were found."""


def run(findings: list[Finding], model: str = "gpt-4o") -> str:
    serialized = json.dumps([f.model_dump() for f in findings], indent=2)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"FINDINGS:\n\n{serialized}"},
    ]
    return call_llm(messages, model=model).strip()
