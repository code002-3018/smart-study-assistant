# Smart Study Assistant – Multi-Agent PDF Analyzer

Smart Study Assistant is an end-to-end multi-agent system that turns your PDFs (notes, syllabus, previous year question papers) into a complete exam-ready **Study Pack**:

- Clean extracted text and chapter-wise structure
- Topic importance with weightage (High / Medium / Low)
- Short and detailed summaries
- MCQs with options, answers, and explanations
- Bullet-style notes and Q/A
- Final downloadable **Study Pack PDF**

Backend is built with **FastAPI**, frontend with **HTML + TailwindCSS**, and the AI layer uses **free model providers** (Gemini 2.0 Flash, DeepSeek-V3, or Llama 3.1 70B via HuggingFace Inference API).

---

## Folder Structure

```text
project/
  backend/
    main.py
    agents/
      extractor.py
      topic_agent.py
      summary_agent.py
      mcq_agent.py
      notes_agent.py
      final_agent.py
    utils/
      pdf_utils.py
      text_cleaner.py
    models/
      llm.py
    static/
    templates/
  frontend/
    index.html
    result.html
    styles.css
  requirements.txt
  render.yaml
  README.md
```

Your actual project directory on disk is `smart-study-assistant`, but the logical project root is represented as `project/` above.

---

## Workflow Diagram (ASCII)

```text
          ┌────────────────────────┐
          │   Frontend (HTML)     │
          │  index.html / upload  │
          └─────────┬─────────────┘
                    │ POST /upload (PDF)
                    ▼
          ┌────────────────────────┐
          │  FastAPI Backend       │
          │  Session Manager       │
          └─────────┬─────────────┘
                    │ session_id
                    ▼
       ┌───────────────────────────────┐
       │  PDF Extraction Agent         │
       │  (extractor.py)              │
       └─────────┬────────────────────┘
                 │ raw + clean text, chapters
                 ▼
       ┌───────────────────────────────┐
       │ Topic Prioritization Agent    │
       │ (topic_agent.py, TF-IDF)     │
       └─────────┬────────────────────┘
                 │ topics + weightage
                 ▼
       ┌───────────────────────────────┐
       │ Summary Agent                 │
       │ (short + detailed)           │
       └─────────┬────────────────────┘
                 │ summaries
                 ▼
       ┌───────────────────────────────┐
       │ MCQ Generator Agent           │
       └─────────┬────────────────────┘
                 │ MCQs per chapter
                 ▼
       ┌───────────────────────────────┐
       │ Notes Generator Agent         │
       └─────────┬────────────────────┘
                 │ markdown notes
                 ▼
       ┌───────────────────────────────┐
       │ Final Report Agent            │
       │  (final PDF via fpdf2)       │
       └─────────┬────────────────────┘
                 │ bytes
                 ▼
         Frontend result.html
      (view topics, summaries,
         MCQs, notes, PDF)
```

---

## Backend API Overview

Base URL (local): `http://localhost:8000`

- `POST /upload`  – Upload a PDF, returns `{ session_id }`.
- `POST /process` – Run **PDFExtractionAgent** and **TopicPrioritizationAgent``, stores results in memory.
- `POST /generate_summary` – Run **SummaryAgent**, returns short + detailed summaries.
- `POST /generate_mcq` – Run **MCQGeneratorAgent**, returns MCQs per chapter.
- `POST /generate_notes` – Run **NotesGeneratorAgent**, returns markdown notes.
- `GET /final_pdf` – Use **FinalReportAgent** to build and stream the final Study Pack PDF.

Each session is stored in an in-memory `SESSIONS` dict keyed by `session_id`. This is acceptable for demos and Kaggle submissions; for production, plug in Redis or a database.

---

## Environment Variables & Model Providers

All model keys are read from environment variables; **no keys are hard-coded**.

- `LLM_PROVIDER` – one of: `gemini`, `deepseek`, `llama` (default: `gemini`)
- `GEMINI_API_KEY` – for Gemini 2.0 Flash (Generative Language API)
- `DEEPSEEK_API_KEY` – for DeepSeek-V3
- `HF_API_KEY` – for Llama 3.1 70B via HuggingFace Inference API

You can sign up for free tiers of these providers and paste keys into local `.env` or Render dashboard.

Example `.env` (do NOT commit this):

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_key_here
# Or, switch providers:
# LLM_PROVIDER=deepseek
# DEEPSEEK_API_KEY=your_deepseek_key_here
# LLM_PROVIDER=llama
# HF_API_KEY=your_hf_key_here
```

---

## Running Locally

### 1. Create & activate virtual environment

```bash
python -m venv .venv
# Windows PowerShell
. .venv/Scripts/Activate.ps1
# or on cmd
.venv\Scripts\activate.bat
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

In PowerShell:

```powershell
$env:LLM_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "YOUR_GEMINI_KEY"
```

(or the equivalent for DeepSeek / HuggingFace.)

### 4. Run the backend

```bash
uvicorn backend.main:app --reload
```

This exposes the API at `http://localhost:8000`.

### 5. Open the frontend

You can open `frontend/index.html` directly in your browser, or serve it with a basic web server:

```bash
# simple static server from project root
python -m http.server 5500
```

Then visit `http://localhost:5500/frontend/index.html`.

If you host the backend at a different origin, update `ssa_api_base` in `localStorage` from the browser console:

```js
localStorage.setItem("ssa_api_base", "https://your-backend-url.onrender.com");
```

---

## Render Deployment Guide

1. **Push the repo to GitHub/GitLab/Bitbucket.**
2. Log into Render and create a **New Web Service**.
3. Connect your repository and select the branch with this project.
4. Render reads `render.yaml` and auto-configures:
   - Runtime: Python
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn backend.main:app --host 0.0.0.0 --port 10000`
5. In Render dashboard, set environment variables:
   - `LLM_PROVIDER` (e.g. `gemini`)
   - `GEMINI_API_KEY` (or `DEEPSEEK_API_KEY` / `HF_API_KEY`)
6. Deploy. Once live, note your backend URL, e.g.:
   `https://smart-study-assistant.onrender.com`.
7. On your local machine, serve the `frontend/` folder (or host it on a static site provider) and set:

```js
localStorage.setItem("ssa_api_base", "https://smart-study-assistant.onrender.com");
```

The frontend will now call the Render backend for all operations.

---

## Ready-to-Submit Kaggle Writeup (Template)

You can paste this into a Kaggle notebook description or report and adapt PDFs/datasets as needed.

### 1. Problem Statement

Students often struggle to convert large, unstructured PDFs (lecture notes, syllabus, previous year question papers) into concise, exam-ready material. The goal of this project is to automatically transform such PDFs into a structured **Study Pack** containing summaries, topic importance, MCQs, and revision notes.

### 2. Data

- Input: User-uploaded academic PDFs (notes, syllabus, PYQs).
- Pre-processing: Text is extracted via `pypdf`, cleaned, and split into chapter-like sections using simple heading heuristics.

On Kaggle, you can attach any appropriate PDF dataset (e.g., open-source textbooks or course notes) as the input source.

### 3. Methodology

1. **PDF Extraction Agent**
   - Extracts raw text from pages.
   - Detects headings based on casing and numbering patterns.
   - Splits text into chapters (title + content).

2. **Topic Prioritization Agent**
   - Uses TF-IDF (via `scikit-learn`) to measure importance per chapter.
   - Adds keyword-based boosts for exam-relevant phrases (e.g. “definition”, “theorem”, “PYQ”).
   - Normalizes scores and assigns weightage: High / Medium / Low.

3. **Summary Agent**
   - Uses a free LLM provider (Gemini / DeepSeek / Llama) via a unified client.
   - Produces a short 3–5 line summary and a detailed 200–300 word summary.

4. **MCQ Generator Agent**
   - Prompts the LLM to return JSON-formatted MCQs per chapter.
   - Each MCQ includes the question, four options, the correct answer, and an explanation.

5. **Notes Generator Agent**
   - Converts the full document into bullet notes, definitions, Q/A pairs, and small comparison tables (markdown-style).

6. **Final Report Agent**
   - Uses `fpdf2` to compile topics, summaries, MCQs, and notes into a single PDF.
   - Adds a title page and a simple table of contents.

### 4. Implementation Details

- **Backend**: FastAPI, multi-agent orchestration in `backend/main.py`.
- **Frontend**: Minimal HTML + TailwindCSS UI for uploading PDFs and reviewing results.
- **LLM Access**: `backend/models/llm.py` abstracts Gemini / DeepSeek / Llama, all driven by environment variables.
- **Study Pack PDF**: `backend/agents/final_agent.py` constructs the final PDF.

### 5. Experiments & Evaluation (Suggested)

- Qualitatively evaluate:
  - Faithfulness of summaries.
  - Coverage of important topics vs. original PDFs.
  - Quality and difficulty of generated MCQs.
- Optionally collect human ratings from students/teachers.
- Quantitative proxies (where possible):
  - ROUGE/BERTScore between summaries and reference notes.
  - Diversity/coverage metrics for MCQs.

### 6. Limitations & Future Work

- Reliance on LLM quality and prompt design.
- In-memory session store (not persistent).
- Simple heading detection may fail on highly formatted PDFs.

Future improvements:

- Integrate a more robust layout parser (e.g., PDF miner/vision-based models).
- Add user feedback loops to iteratively refine summaries and MCQs.
- Persist sessions in a database and add user authentication.

---

## ZIP Download Structure

If you compress the project root (`smart-study-assistant`) into a ZIP, the internal structure will look like this:

```text
smart-study-assistant.zip
└── project/
    ├── backend/
    │   ├── main.py
    │   ├── agents/
    │   │   ├── extractor.py
    │   │   ├── topic_agent.py
    │   │   ├── summary_agent.py
    │   │   ├── mcq_agent.py
    │   │   ├── notes_agent.py
    │   │   └── final_agent.py
    │   ├── utils/
    │   │   ├── pdf_utils.py
    │   │   └── text_cleaner.py
    │   ├── models/
    │   │   └── llm.py
    │   ├── static/
    │   └── templates/
    ├── frontend/
    │   ├── index.html
    │   ├── result.html
    │   └── styles.css
    ├── requirements.txt
    ├── render.yaml
    └── README.md
```

You can rename `project/` inside the ZIP to any desired name when distributing, but the internal layout should remain the same.
