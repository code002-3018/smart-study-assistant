"""Text cleaning utilities.

This module provides simple helpers to normalize whitespace and
prepare text segments for downstream LLM agents.
"""

from __future__ import annotations

import re
from typing import List


_whitespace_re = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Normalize whitespace and remove obvious artifacts."""

    text = text.replace("\u00a0", " ")  # non-breaking spaces
    text = _whitespace_re.sub(" ", text)
    # Normalize stray bullet characters
    text = text.replace("\u2022", "-")
    return text.strip()


def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs by blank lines."""

    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return parts


def split_into_sentences(text: str) -> List[str]:
    """Very lightweight sentence splitter.

    For production, consider using an NLP library, but for a
    lightweight academic project this heuristic is often sufficient.
    """

    # Split on ., ?, ! followed by space or end-of-string
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]
