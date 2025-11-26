"""PDF utilities for extracting and structuring text from PDFs.

This module uses pypdf to extract raw text from a PDF and then
splits it into chapters/sections based on simple heading heuristics.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any

from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extract plain text from a PDF file.

    Parameters
    ----------
    pdf_path: str | Path
        Path to the PDF file on disk.
    """
    path = Path(pdf_path)
    reader = PdfReader(path)
    chunks: list[str] = []
    for page in reader.pages:
        # Extract text from each page and guard against None
        text = page.extract_text() or ""
        chunks.append(text)
    return "\n".join(chunks)


def detect_headings(lines: List[str]) -> List[int]:
    """Return indices of lines that look like headings.

    Heuristics:
    - Line is short (<= 80 chars)
    - Either mostly uppercase or starts with a digit/roman numeral.
    """

    heading_indices: list[int] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) <= 80:
            if stripped.isupper():
                heading_indices.append(idx)
                continue
            if stripped[0].isdigit():
                heading_indices.append(idx)
                continue
            # Simple roman numeral heuristic (I., II., III., etc.)
            if stripped.split(" ", 1)[0].rstrip(".").upper() in {
                "I",
                "II",
                "III",
                "IV",
                "V",
                "VI",
                "VII",
                "VIII",
                "IX",
                "X",
            }:
                heading_indices.append(idx)
    return heading_indices


def split_into_chapters(text: str) -> List[Dict[str, Any]]:
    """Split text into chapters/sections based on detected headings.

    Returns a list of chapters with a title and content.
    """

    lines = [ln for ln in text.splitlines()]
    heading_indices = detect_headings(lines)

    if not heading_indices:
        # Fallback: single chapter
        return [
            {
                "title": "Full Document",
                "content": text,
            }
        ]

    chapters: list[dict[str, str]] = []
    for i, start_idx in enumerate(heading_indices):
        end_idx = heading_indices[i + 1] if i + 1 < len(heading_indices) else len(lines)
        title = lines[start_idx].strip()
        body_lines = lines[start_idx + 1 : end_idx]
        content = "\n".join(body_lines).strip()
        chapters.append({"title": title or f"Section {i + 1}", "content": content})

    return chapters


def extract_structured_pdf(pdf_path: str | Path) -> Dict[str, Any]:
    """High-level helper to extract and structure PDF content.

    Returns
    -------
    dict with keys:
        - raw_text
        - chapters: list[{title, content}]
    """

    raw_text = extract_text_from_pdf(pdf_path)
    chapters = split_into_chapters(raw_text)
    return {"raw_text": raw_text, "chapters": chapters}
