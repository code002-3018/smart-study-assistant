"""PDF Extraction Agent.

Responsible for:
- Loading uploaded PDFs
- Extracting raw text
- Cleaning text
- Detecting headings and splitting into chapters/topics
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from backend.utils.pdf_utils import extract_structured_pdf
from backend.utils.text_cleaner import clean_text


class PDFExtractionAgent:
    """Agent that extracts and structures content from a PDF file."""

    def run(self, pdf_path: str | Path) -> Dict[str, Any]:
        structured = extract_structured_pdf(pdf_path)
        raw_text = structured["raw_text"]
        chapters = structured["chapters"]

        # Clean chapter content
        for ch in chapters:
            ch["content"] = clean_text(ch.get("content", ""))

        return {
            "raw_text": raw_text,
            "clean_text": clean_text(raw_text),
            "chapters": chapters,
        }
