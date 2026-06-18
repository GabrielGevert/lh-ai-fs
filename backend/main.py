from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents import authority_verifier, citation_extractor
from schemas import VerificationReport

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOCUMENTS_DIR = Path(__file__).parent / "documents"

CASE_NAME = "Rivera v. Harmon Construction Group"


def load_documents() -> dict[str, str]:
    """Load all documents from the documents directory."""
    documents = {}
    for file_path in DOCUMENTS_DIR.glob("*.txt"):
        documents[file_path.stem] = file_path.read_text()
    return documents


@app.post("/analyze")
async def analyze() -> VerificationReport:
    documents = load_documents()
    motion = documents["motion_for_summary_judgment"]

    # Tier 1 pipeline: extract citations, then verify each one.
    # Fact-checking, scoring, and the judicial memo are wired in later blocks.
    citations = citation_extractor.run(motion)
    verdicts = authority_verifier.run(citations)

    return VerificationReport(
        case=CASE_NAME,
        citations=verdicts,
    )
