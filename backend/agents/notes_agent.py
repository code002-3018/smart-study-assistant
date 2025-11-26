"""Notes Generator Agent.

Converts content into clean bullet notes, tables and Q/A style
revisions using the LLM.
"""

from __future__ import annotations

from typing import Dict, Any

from backend.models.llm import LLMClient


class NotesGeneratorAgent:
    """Agent that generates structured study notes from content."""

    def __init__(self) -> None:
        self.client = LLMClient()

    def run(self, text: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert note-making assistant. You create compact, "
            "high-yield notes for exam revision."
        )

        prompt = (
            "From the content below, create structured study notes with:\n"
            "- Bullet point summaries of key ideas\n"
            "- Important definitions (term : definition)\n"
            "- Short Q/A pairs (question : answer)\n"
            "- If useful, small markdown-style tables for comparisons.\n\n"
            "Use clear headings and markdown where appropriate.\n\n"
            f"CONTENT:\n{text[:8000]}"
        )

        notes = self.client.generate(
            prompt,
            system_prompt=system_prompt,
            max_tokens=1024,
            temperature=0.5,
        )

        return {"notes_markdown": notes.strip()}
