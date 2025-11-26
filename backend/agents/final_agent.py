"""Final Report Agent.

Combines outputs from all agents into a single nicely formatted
PDF study pack with table of contents.
"""

from __future__ import annotations

from io import BytesIO
from typing import List, Dict, Any

from fpdf import FPDF


class _StudyPackPDF(FPDF):
    """Custom PDF class for the study pack layout."""

    def header(self) -> None:  # type: ignore[override]
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Smart Study Assistant - Study Pack", ln=1, align="C")
        self.ln(2)

    def footer(self) -> None:  # type: ignore[override]
        self.set_y(-15)
        self.set_font("Arial", size=8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")



def _safe_text(text: str) -> str:
    """Remove or replace characters that cause encoding issues."""
    if not text:
        return ""
    
    # Replace common problematic characters
    replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201c': '"',  # Left double quote
        '\u201d': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2022': '*',  # Bullet
        '\u2026': '...', # Ellipsis
        '\u00a0': ' ',  # Non-breaking space
        '\u2019': "'",  # Another quote variant
        '\u00b0': ' degrees',  # Degree symbol
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Try to encode to Latin-1, if it fails, use ASCII with ignore
    try:
        return text.encode('latin-1', 'ignore').decode('latin-1')
    except Exception:
        # Fallback: keep only ASCII characters
        return ''.join(char if ord(char) < 128 else '?' for char in text)



class FinalReportAgent:
    """Agent that builds the final PDF from intermediate artifacts."""

    def build_pdf(
        self,
        *,
        topics: List[Dict[str, Any]],
        summaries: Dict[str, Any],
        mcqs: List[Dict[str, Any]],
        notes: Dict[str, Any],
    ) -> bytes:
        pdf = _StudyPackPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Title Page
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "Smart Study Assistant - Multi-Agent PDF Analyzer", ln=1)
        pdf.ln(4)

        pdf.set_font("Arial", size=11)
        pdf.multi_cell(
            0,
            6,
            "This auto-generated study pack summarizes your uploaded material, "
            "highlights important topics, and provides MCQs and revision notes.",
        )

        # Table of Contents (simple, not page-linked)
        pdf.ln(6)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 8, "Table of Contents", ln=1)
        pdf.set_font("Arial", size=11)
        toc_items = [
            "1. Topic Weightage Overview",
            "2. Summaries (Short + Detailed)",
            "3. MCQs by Chapter",
            "4. Revision Notes",
        ]
        for item in toc_items:
            pdf.cell(0, 6, f"- {item}", ln=1)

        # Section 1: Topic Weightage
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "1. Topic Weightage Overview", ln=1)
        pdf.set_font("Arial", size=11)
        if not topics:
            pdf.cell(0, 8, "No topics detected.", ln=1)
        else:
            for topic in topics:
                line = f"[{topic['weightage']}] {_safe_text(topic['title'])} (score={topic['score']:.3f})"
                pdf.multi_cell(0, 6, line)
                if topic.get("snippet"):
                    pdf.set_font("Arial", size=10)
                    pdf.multi_cell(0, 5, f"Snippet: {_safe_text(topic['snippet'][:300])}...")
                    pdf.set_font("Arial", size=11)
                pdf.ln(2)

        # Section 2: Summaries
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "2. Summaries", ln=1)

        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Short Summary", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, _safe_text(summaries.get("short_summary", "Not available.")))

        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "Detailed Summary", ln=1)
        pdf.set_font("Arial", size=11)
        pdf.multi_cell(0, 6, _safe_text(summaries.get("detailed_summary", "Not available.")))

        # Section 3: MCQs
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "3. MCQs by Chapter", ln=1)
        pdf.set_font("Arial", size=11)

        if not mcqs:
            pdf.cell(0, 8, "No MCQs generated.", ln=1)
        else:
            for chapter_mcqs in mcqs:
                pdf.set_font("Arial", "B", 12)
                pdf.ln(3)
                pdf.multi_cell(0, 6, f"Chapter: {_safe_text(chapter_mcqs.get('title', 'Untitled'))}")
                pdf.set_font("Arial", size=11)
                for idx, item in enumerate(chapter_mcqs.get("mcqs", []), start=1):
                    pdf.ln(1)
                    pdf.multi_cell(0, 6, f"Q{idx}. {_safe_text(item.get('question', ''))}")
                    options = item.get("options", [])
                    for opt_idx, opt in zip(["A", "B", "C", "D"], options):
                        pdf.multi_cell(0, 5, f"   {opt_idx}) {_safe_text(opt)}")
                    pdf.set_font("Arial", "I", 10)
                    pdf.multi_cell(0, 5, f"Answer: {_safe_text(item.get('answer', ''))}")
                    explanation = item.get("explanation", "")
                    if explanation:
                        pdf.multi_cell(0, 5, f"Explanation: {_safe_text(explanation)}")
                    pdf.set_font("Arial", size=11)

        # Section 4: Revision Notes
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "4. Revision Notes", ln=1)
        pdf.set_font("Arial", size=11)
        notes_md = notes.get("notes_markdown", "No notes generated.")
        pdf.multi_cell(0, 6, _safe_text(notes_md))

        buffer = BytesIO()
        pdf.output(buffer)
        return buffer.getvalue()
