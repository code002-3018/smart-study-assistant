"""FastAPI backend for Smart Study Assistant – Multi-Agent PDF Analyzer.

Endpoints
---------
- POST /upload           : Upload PDF and create a processing session
- POST /process          : Run extraction + topic prioritization
- POST /generate_summary : Generate short + detailed summaries
- POST /generate_mcq     : Generate MCQs per chapter
- GET  /final_pdf        : Download final compiled Study Pack PDF
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# Load environment variables from .env file
load_dotenv()

from backend.agents.extractor import PDFExtractionAgent
from backend.agents.topic_agent import TopicPrioritizationAgent
from backend.agents.summary_agent import SummaryAgent
from backend.agents.mcq_agent import MCQGeneratorAgent
from backend.agents.notes_agent import NotesGeneratorAgent
from backend.agents.final_agent import FinalReportAgent


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


app = FastAPI(title="Smart Study Assistant – Multi-Agent PDF Analyzer")

# Simple in-memory session store; fine for demo / academic projects.
SESSIONS: dict[str, Dict[str, Any]] = {}


# Enable CORS for local dev and simple deployments
origins = [
    "http://localhost",
    "http://localhost:5500",  # Frontend Live Server
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "*",  # widen if needed for Render/frontend hosting
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, str]:
    """Health/info endpoint."""

    return {"message": "Smart Study Assistant backend is running."}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> JSONResponse:
    """Upload a PDF and create a processing session.

    Returns a session_id that the frontend can use for subsequent
    processing steps.
    """

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    session_id = str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = session_dir / file.filename
    content = await file.read()
    pdf_path.write_bytes(content)

    SESSIONS[session_id] = {"pdf_path": str(pdf_path)}

    return JSONResponse({"session_id": session_id, "filename": file.filename})


@app.post("/process")
async def process_pdf(session_id: str) -> JSONResponse:
    """Run PDF extraction and topic prioritization for a given session."""

    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    pdf_path = session.get("pdf_path")
    if not pdf_path:
        raise HTTPException(status_code=400, detail="No PDF uploaded for this session.")

    extractor = PDFExtractionAgent()
    topic_agent = TopicPrioritizationAgent()

    extracted = extractor.run(pdf_path)
    topics = topic_agent.run(extracted["chapters"])

    session["extracted"] = extracted
    session["topics"] = topics

    return JSONResponse({"extracted": extracted, "topics": topics})


@app.post("/generate_summary")
async def generate_summary(session_id: str) -> JSONResponse:
    """Generate short and detailed summaries for the session content."""

    session = SESSIONS.get(session_id)
    if not session or "extracted" not in session:
        raise HTTPException(status_code=400, detail="Run /process first for this session.")

    extracted = session["extracted"]
    text = extracted.get("clean_text") or extracted.get("raw_text")
    if not text:
        raise HTTPException(status_code=400, detail="No text available for summarization.")

    agent = SummaryAgent()
    summaries = agent.run(text)
    session["summaries"] = summaries

    return JSONResponse({"summaries": summaries})


@app.post("/generate_mcq")
async def generate_mcq(session_id: str) -> JSONResponse:
    """Generate MCQs per chapter for the current session."""

    session = SESSIONS.get(session_id)
    if not session or "extracted" not in session:
        raise HTTPException(status_code=400, detail="Run /process first for this session.")

    chapters = session["extracted"].get("chapters", [])
    if not chapters:
        raise HTTPException(status_code=400, detail="No chapters available for MCQ generation.")

    agent = MCQGeneratorAgent()
    mcqs = agent.run(chapters)
    session["mcqs"] = mcqs

    return JSONResponse({"mcqs": mcqs})


@app.post("/generate_notes")
async def generate_notes(session_id: str) -> JSONResponse:
    """Generate structured revision notes for the session."""

    session = SESSIONS.get(session_id)
    if not session or "extracted" not in session:
        raise HTTPException(status_code=400, detail="Run /process first for this session.")

    extracted = session["extracted"]
    text = extracted.get("clean_text") or extracted.get("raw_text")
    if not text:
        raise HTTPException(status_code=400, detail="No text available for notes generation.")

    agent = NotesGeneratorAgent()
    notes = agent.run(text)
    session["notes"] = notes

    return JSONResponse({"notes": notes})


@app.get("/final_pdf")
async def final_pdf(session_id: str) -> StreamingResponse:
    """Build and stream the final Study Pack PDF for download."""

    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    topics = session.get("topics")
    summaries = session.get("summaries")
    mcqs = session.get("mcqs")
    notes = session.get("notes")

    if not all([topics, summaries, mcqs, notes]):
        raise HTTPException(
            status_code=400,
            detail="Please run /process, /generate_summary, /generate_mcq and /generate_notes first.",
        )

    agent = FinalReportAgent()
    pdf_bytes = agent.build_pdf(
        topics=topics,
        summaries=summaries,
        mcqs=mcqs,
        notes=notes,
    )

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="study_pack.pdf"',
        },
    )


if __name__ == "__main__":
    # Allow `python backend/main.py` for quick local testing
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
