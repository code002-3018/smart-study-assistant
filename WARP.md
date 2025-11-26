# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development commands

All commands are intended to be run from the repository root `smart-study-assistant/`.

### Environment setup

- Create a virtual environment (Python 3.10+ recommended):
  - Cross-platform:
    - `python -m venv .venv`
  - Activate:
    - PowerShell (Windows): `. .venv/Scripts/Activate.ps1`
    - bash/zsh (macOS/Linux): `source .venv/bin/activate`
- Install dependencies:
  - `pip install -r requirements.txt`

### Run the backend (FastAPI)

- Development server with auto-reload (default for local work):
  - `uvicorn backend.main:app --reload`
- Alternative entrypoint (also used by `if __name__ == "__main__"` guard):
  - `python backend/main.py`
- The backend listens on `http://localhost:8000` by default in local dev.

### Run the frontend

The frontend is a static HTML+Tailwind client in `frontend/`.

- Quick local hosting from the project root:
  - `python -m http.server 5500`
- Then open: `http://localhost:5500/frontend/index.html`.
- The frontend uses `ssa_api_base` from `localStorage` to locate the backend:
  - Defaults to `http://localhost:8000`.
  - To point at a deployed backend, set in the browser console:
    - `localStorage.setItem("ssa_api_base", "https://your-backend-url" )`

### Health checks and basic API usage

- Health check: `GET /` → `{ "message": "Smart Study Assistant backend is running." }`.
- Main workflow endpoints (base URL is typically `http://localhost:8000` during dev):
  - `POST /upload` – multipart file upload (`file`) for the source PDF; returns `{ session_id }`.
  - `POST /process?session_id=...` – runs extraction + topic prioritization; caches `extracted` + `topics` in memory.
  - `POST /generate_summary?session_id=...` – computes short + detailed summaries; caches `summaries`.
  - `POST /generate_mcq?session_id=...` – generates MCQs per chapter; caches `mcqs`.
  - `POST /generate_notes?session_id=...` – generates revision notes; caches `notes`.
  - `GET /final_pdf?session_id=...` – streams the compiled Study Pack PDF.

The shipped frontend (`frontend/index.html` and `frontend/result.html`) orchestrates these endpoints automatically; you normally do not need to call them manually unless testing/debugging.

### Deployment (Render)

Render is configured via `render.yaml`:

- Build: `pip install -r requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port 10000`
- Important environment variables (set in Render dashboard):
  - `LLM_PROVIDER` (e.g. `gemini`, `deepseek`, `llama`)
  - `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `HF_API_KEY`

### Linting and tests

- There is currently no dedicated lint or test configuration checked into this repo (no `tests/` directory, no tooling in `requirements.txt`).
- If you introduce a pytest-based test suite, typical commands will be:
  - Run all tests: `pytest`
  - Run a specific file: `pytest path/to/test_file.py`
  - Run a specific test: `pytest path/to/test_file.py -k test_name`

These pytest commands are suggestions only; verify they match whatever test tooling you add.

## High-level architecture

### Top-level layout

- `backend/` – FastAPI application and multi-agent orchestration.
  - `main.py` – API entrypoint, session management, and wiring between HTTP endpoints and agents.
  - `agents/` – each file implements a single-responsibility agent in the study pack pipeline.
  - `utils/` – PDF parsing and generic text-cleaning helpers.
  - `models/` – abstraction over external LLM providers.
- `frontend/` – Minimal static HTML+Tailwind UI for uploading PDFs and visualizing the generated Study Pack.
- `requirements.txt` – runtime Python dependencies.
- `render.yaml` – Render deployment definition.

### Request flow and session model

The backend is intentionally simple and stateless per request; cross-request state is held in an in-memory session store:

- `SESSIONS: dict[str, Dict[str, Any]]` in `backend/main.py` is keyed by `session_id` (UUID).
- `/upload` stores `pdf_path` under the session and writes the PDF to `uploads/<session_id>/`.
- Subsequent endpoints enrich the same session object with additional keys:
  - `/process` → `extracted` (raw + clean text + chapters), `topics` (per-chapter importance).
  - `/generate_summary` → `summaries` (short + detailed strings).
  - `/generate_mcq` → `mcqs` (per-chapter MCQ lists).
  - `/generate_notes` → `notes` (markdown-style revision notes).
- `/final_pdf` expects all of `topics`, `summaries`, `mcqs`, and `notes` to be present; it fails fast with a 400 if any are missing to keep the pipeline order explicit.

This in-memory session approach is acceptable for local dev, demos, and single-instance deployments (e.g., Kaggle, small Render service). For anything multi-instance or long-lived, backing `SESSIONS` with a shared store (Redis, database) would be the main architectural upgrade.

### Agents and responsibilities

Each agent is a thin, focused layer over utilities and the `LLMClient` abstraction:

- `PDFExtractionAgent` (`backend/agents/extractor.py`)
  - Calls `extract_structured_pdf` to get `raw_text` + `chapters` from a PDF path.
  - Applies `clean_text` to each chapter and to the full document, returning `raw_text`, `clean_text`, and `chapters` back to the caller.
- `TopicPrioritizationAgent` (`backend/agents/topic_agent.py`)
  - Uses `TfidfVectorizer` (scikit-learn) on chapter contents.
  - Adds a simple keyword boost for exam-relevant terms ("definition", "theorem", "PYQ", etc.).
  - Normalizes scores into `[0, 1]` and buckets into `High` / `Medium` / `Low` weightage.
  - Returns per-chapter objects with `title`, `score`, `weightage`, and a `snippet` of content.
- `SummaryAgent` (`backend/agents/summary_agent.py`)
  - Uses `LLMClient` to generate two summaries from the (cleaned) document text:
    - `short_summary`: 3–5 bullet style points.
    - `detailed_summary`: 200–300 word narrative.
  - Prompts are sized with substring limits (`text[:6000]`, `text[:8000]`) to stay within provider token limits.
- `MCQGeneratorAgent` (`backend/agents/mcq_agent.py`)
  - Builds a strict JSON-only prompt per chapter instructing the LLM to return at least 10 MCQs.
  - Attempts to `json.loads` the LLM response and extracts `mcqs`.
  - On JSON parse failure, returns a fallback pseudo-question embedding the raw model output so the caller can debug.
- `NotesGeneratorAgent` (`backend/agents/notes_agent.py`)
  - Produces `notes_markdown` with bullet points, definitions, Q/A pairs, and optional markdown tables for comparisons.
- `FinalReportAgent` (`backend/agents/final_agent.py`)
  - Uses a custom `_StudyPackPDF` subclass of `FPDF` to render a multi-section PDF:
    - Title page and high-level blurb.
    - Table of contents (non-linked, static text).
    - Topic weightage overview (score and snippet per chapter).
    - Short + detailed summaries.
    - MCQs grouped by chapter, including answers and explanations.
    - Raw markdown notes rendered as plain text.
  - Returns the final PDF as `bytes` for streaming via `StreamingResponse`.

### PDF and text utilities

- `backend/utils/pdf_utils.py`
  - `extract_text_from_pdf` – wraps `pypdf.PdfReader` to produce page-joined text.
  - `detect_headings` – heuristic heading detector based on line length, casing, numeric/roman numeral prefixes.
  - `split_into_chapters` – slices the document by detected headings into `{title, content}` chapters, or a single "Full Document" chapter as a fallback.
  - `extract_structured_pdf` – convenience that returns `{ raw_text, chapters }`.
- `backend/utils/text_cleaner.py`
  - `clean_text` – normalizes whitespace, replaces non-breaking spaces and bullet characters.
  - `split_into_paragraphs` / `split_into_sentences` – simple regex-based helpers for potential future agents.

### LLM provider abstraction

- `backend/models/llm.py` defines `LLMClient`, which routes to one of three providers based on `LLM_PROVIDER`:
  - `gemini` (default) → Google Gemini 2.0 Flash (`/v1beta/models/gemini-2.0-flash:generateContent`).
  - `deepseek` → DeepSeek-V3 via an OpenAI-compatible `/chat/completions` endpoint.
  - `llama` → Llama 3.1 70B via HuggingFace Inference API.
- All providers are invoked via `requests` with provider-specific JSON payloads and response parsing.
- Each provider requires its own API key from the environment:
  - `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `HF_API_KEY`.

When modifying or adding agents that call LLMs, prefer going through `LLMClient.generate(...)` so that provider switching remains centralized and controlled via environment configuration.

### Frontend integration

- `frontend/index.html`
  - Uploads a single PDF via `/upload`.
  - Sequentially calls `/process`, `/generate_summary`, `/generate_mcq`, `/generate_notes`.
  - Redirects to `result.html?session_id=...` when the pipeline finishes.
- `frontend/result.html`
  - On load, re-calls the same pipeline endpoints (idempotent for the same `session_id`) and renders the responses:
    - Topic list with scores and weightage.
    - Short and detailed summaries.
    - MCQs grouped by chapter.
    - Raw markdown notes.
  - Provides a "Download Study Pack PDF" button that hits `/final_pdf` and triggers a browser download.
- `frontend/styles.css` contains minor font and scrollbar tweaks; the main styling is handled by Tailwind via CDN.

For backend changes that alter response shapes, keep these two HTML files in sync with any new fields or structural changes to the JSON payloads.