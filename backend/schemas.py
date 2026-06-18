"""Pydantic models exchanged between agents.

Agents pass these structured objects to each other, never raw text blobs.
Each model maps to one stage of the pipeline:

    CitationExtractor   -> list[Citation]
    AuthorityVerifier   -> list[CitationVerdict]
    FactConsistencyChecker -> list[FactFinding]
    ConfidenceScorer    -> list[Finding]
    JudicialMemoAgent   -> str
    Orchestrator        -> VerificationReport
"""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

_WORD_CONFIDENCE = {"very high": 0.95, "high": 0.9, "medium": 0.6, "moderate": 0.6, "low": 0.3, "very low": 0.1}


def _coerce_confidence(value: object) -> object:
    """Models sometimes return confidence as a word ('high') instead of a number.
    Map known words to a score so one stray value cannot crash the pipeline."""
    if isinstance(value, str):
        return _WORD_CONFIDENCE.get(value.strip().lower(), value)
    return value


Confidence = Annotated[float, BeforeValidator(_coerce_confidence), Field(ge=0.0, le=1.0)]

# Document keys, the stems of the .txt files under backend/documents/.
SourceDoc = Literal[
    "motion_for_summary_judgment",
    "police_report",
    "medical_records_excerpt",
    "witness_statement",
]

FindingType = Literal[
    "misquote",
    "fabricated_citation",
    "misrepresented_authority",
    "factual_contradiction",
    "unsupported_claim",
    "legal_omission",
    "misleading_argument",
    "irrelevant_jurisdiction",
    "unverifiable",
]

Severity = Literal["high", "medium", "low"]


class Citation(BaseModel):
    """A single legal authority cited in the motion. Output of CitationExtractor."""

    id: str = Field(description="Stable id, e.g. 'C1'.")
    citation_text: str = Field(description="The citation as written, e.g. 'Privette v. Superior Court, 5 Cal.4th 689 (1993)'.")
    proposition: str = Field(description="The legal proposition the citation is offered to support.")
    direct_quotes: list[str] = Field(default_factory=list, description="Text in quotation marks attributed to this authority.")
    location: str = Field(default="", description="Where it appears, e.g. 'Section III.A' or 'Footnote 1'.")
    is_footnote: bool = False


class CitationVerdict(BaseModel):
    """Assessment of one citation. Output of AuthorityVerifier."""

    citation_id: str
    citation_text: str
    exists_verdict: Literal["likely_real", "likely_fabricated", "cannot_verify"]
    supports_proposition: Literal["yes", "no", "partial", "cannot_verify"]
    quote_accuracy: Literal["accurate", "altered", "not_in_source", "cannot_verify", "no_quote"]
    reasoning: str
    confidence: Confidence


class FactFinding(BaseModel):
    """A factual claim in the motion checked against the record. Output of FactConsistencyChecker."""

    id: str
    claim_in_motion: str
    supporting_evidence: str = Field(description="The relevant passage(s) from the record, quoted.")
    source_documents: list[SourceDoc] = Field(default_factory=list)
    verdict: Literal["contradicted", "unsupported", "corroborated", "cannot_verify"]
    reasoning: str
    confidence: Confidence


class Finding(BaseModel):
    """A normalized, scored issue ready for the report. Output of ConfidenceScorer."""

    id: str
    type: FindingType
    severity: Severity
    confidence: Confidence
    confidence_reasoning: str
    summary: str
    claim: str = Field(description="What the motion asserts.")
    evidence: str = Field(description="What the record or the law actually says.")
    source_documents: list[SourceDoc] = Field(default_factory=list)
    location_in_motion: str = ""


class VerificationReport(BaseModel):
    """The full response of POST /analyze."""

    case: str
    findings: list[Finding] = Field(default_factory=list)
    citations: list[CitationVerdict] = Field(default_factory=list)
    fact_findings: list[FactFinding] = Field(default_factory=list)
    judicial_memo: str = ""
    errors: list[str] = Field(default_factory=list, description="Agents that failed, for graceful degradation visibility.")
