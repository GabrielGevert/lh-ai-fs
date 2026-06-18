# Reflection

## What this is

A multi-agent pipeline that reads a Motion for Summary Judgment plus its supporting
record (police report, medical records, witness statement) and produces a structured
verification report: fabricated or misrepresented citations, altered quotes, and facts
that contradict the record. The full report is returned by `POST /analyze` and rendered
in the UI; an eval harness measures how well it works.

## How I decomposed the problem

Five agents, each with one job and an explicit prompt, passing typed Pydantic objects
(not raw text) between them:

1. **CitationExtractor** pulls every citation, the proposition it supports, and any quotes.
2. **AuthorityVerifier** judges each citation: does it exist, does it support the claim, is the quote accurate.
3. **FactConsistencyChecker** compares the motion's factual claims against the record.
4. **ConfidenceScorer** consolidates the raw outputs into deduplicated findings with severity and calibrated confidence.
5. **JudicialMemoAgent** writes a one-paragraph summary for the judge.

Extraction and verification are separate on purpose: extraction is cheap and near-deterministic,
verification is expensive and needs legal judgment. Splitting them keeps each prompt focused and
lets the eval attribute failures to the right stage. The orchestrator runs all five with per-agent
error handling, so one failing agent degrades the report (its error is recorded in `errors`) instead
of crashing the request.

## The central tradeoff

The AuthorityVerifier relies on the model's parametric knowledge of law. It has no access to a real
legal database (Westlaw, CourtListener), so it cannot truly confirm that a case is fabricated rather
than obscure-but-real. This is the biggest limitation of the system.

My response was to calibrate for honesty over coverage:

- An unrecognized citation defaults to `cannot_verify`, never to `likely_real` inferred from a
  plausible-looking format. Early on the model was calling fabricated footnote cases "likely real"
  purely because the citation format looked valid; the calibrated prompt fixed that.
- Fabrication is only ever flagged as a low-confidence inference from "cannot verify", and the
  hallucination metric exists specifically to keep that honest.
- Where the model can reason without a lookup, it does: it catches a citation that misstates
  well-established law (the Kellerman cite claims OSHA compliance creates a presumption of due care,
  which is backwards) by judging the proposition's legal soundness, not the case's existence.

The result is a deliberately conservative pipeline: it prefers silence and "could not verify" over
false flags. The eval shows this paid off, 100% precision at 62% recall.

## Eval design

The ground truth is a hand-built answer key of 13 flaws I found by close reading, each with
discriminating keywords. Scoring:

- **precision** counts detections that map to a real flaw (no false alarms).
- **recall** counts planted flaws caught. An honest "cannot_verify" or "corroborated" is never
  counted as a detection, so expressing uncertainty is never punished.
- **hallucination rate** is a grounding check: among detections that quote the record, the fraction
  whose quote cannot be found in any document. This catches a flag invented from a passage that does
  not exist, which precision alone would miss.

Keyword matching is intentionally conservative, so reported recall is a lower bound. An optional
`--judge` flag adds an LLM that re-checks only the keyword-missed flaws for semantic matches; I report
both numbers (62% keyword, 69% judged) rather than picking the flattering one.

Limitations of the eval: the ground truth is my own reading of one case, so it is small and could be
incomplete or biased; keyword matching can undercount; the judge adds variance.

## What it catches and what it misses

Caught with high confidence: the wrong incident date (March 14 vs March 12), the false claim that
Rivera wore no PPE, the unsupported OSHA-inspection claim, the Privette misquote, the out-of-jurisdiction
footnote cases, and the misstated OSHA rule.

Missed: the Seabright cite (the model rates it "partial" rather than wrong, so it does not surface);
the omitted retained-control exception to Privette and the dated assumption-of-risk defense (these are
legal-reasoning gaps no current agent looks for); and the uncorroborated "eight years of experience"
(genuinely unverifiable, where staying silent is the correct behavior).

## What I would do with more time

- Give the AuthorityVerifier a real lookup tool (CourtListener API) to turn `cannot_verify` into
  grounded verdicts, the single biggest quality lever.
- Add a sixth agent for legal-reasoning gaps (omitted exceptions and superseded doctrines).
- Capture page/line locations for each finding so the UI can link back to the source.
- Calibrate confidence against multiple samples and add prompt-regression tests to CI.
- Expand the ground truth across several cases so the eval numbers mean more.
