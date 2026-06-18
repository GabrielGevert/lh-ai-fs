"""Evaluation harness. Run from the repo root:

    python eval/run_evals.py              # runs the live pipeline (needs OPENAI_API_KEY)
    python eval/run_evals.py --report r.json   # scores a saved report, no API calls

Reports precision, recall, and hallucination rate against eval/ground_truth.json,
then writes eval/results.json. We care more about honest numbers than high ones.
"""

import argparse
import json
import sys
from pathlib import Path

from matcher import evaluate

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "backend" / "documents"
GROUND_TRUTH = REPO_ROOT / "eval" / "ground_truth.json"
RESULTS_OUT = REPO_ROOT / "eval" / "results.json"


def load_documents() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in DOCS_DIR.glob("*.txt")}


def run_live_pipeline() -> dict:
    # Imported lazily and assembled here for now; a later block routes this through
    # the orchestrator so eval and the API share one pipeline definition.
    sys.path.insert(0, str(REPO_ROOT / "backend"))
    from agents import authority_verifier, citation_extractor, fact_checker
    from schemas import VerificationReport

    documents = load_documents()
    citations = citation_extractor.run(documents["motion_for_summary_judgment"])
    verdicts = authority_verifier.run(citations)
    fact_findings = fact_checker.run(documents)
    report = VerificationReport(
        case="Rivera v. Harmon Construction Group",
        citations=verdicts,
        fact_findings=fact_findings,
    )
    return report.model_dump()


def _print_report(results: dict) -> None:
    print("\n=== BS Detector eval ===")
    print(f"recall             {results['recall']:.0%}  ({results['caught']}/{results['total_flaws']} planted flaws caught)")
    print(f"precision          {results['precision']:.0%}  ({results['matched_detections']}/{results['total_detections']} detections were real)")
    print(f"hallucination rate {results['hallucination_rate']:.0%}  ({results['ungrounded_detections']}/{results['grounding_assessable']} quoted detections ungrounded)")

    by_cat: dict[str, list] = {}
    for f in results["per_flaw"]:
        by_cat.setdefault(f["category"], []).append(f)
    print("\nrecall by category:")
    for cat, items in sorted(by_cat.items()):
        hit = sum(1 for i in items if i["caught"])
        print(f"  {cat:10} {hit}/{len(items)}")

    if results["missed"]:
        print(f"\nmissed flaws: {', '.join(results['missed'])}")
    print(f"\nfull results written to {RESULTS_OUT.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the BS Detector pipeline.")
    parser.add_argument("--report", help="Path to a saved report JSON; skips the live pipeline.")
    args = parser.parse_args()

    if args.report:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    else:
        report = run_live_pipeline()

    ground_truth = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    results = evaluate(report, ground_truth, load_documents())

    RESULTS_OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    _print_report(results)


if __name__ == "__main__":
    main()
