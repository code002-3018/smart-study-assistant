"""Summary Agent.

Generates short (3–5 line) and detailed (200–300 word) summaries
of the extracted document using the configured LLM provider.
"""

from __future__ import annotations

from typing import Dict, Any

from backend.models.llm import LLMClient


class SummaryAgent:
    """Agent that generates multi-granularity summaries."""

    def __init__(self) -> None:
        self.client = LLMClient()

    def run(self, text: str) -> Dict[str, Any]:
        system_prompt = (
            "You are an expert study assistant. You write clear, concise "
            "summaries tailored for students preparing for exams."
        )

        short_prompt = (
            "Write a very short summary of the following content "
            "in 3–5 bullet points. Focus on the core ideas only.\n\n"
            f"CONTENT:\n{text[:6000]}"
        )

        detailed_prompt = (
            "Write a detailed study summary (200–300 words) of the "
            "following content. Use clear paragraphs and keep the "
            "tone student-friendly.\n\n"
            f"CONTENT:\n{text[:8000]}"
        )

        short_summary = self.client.generate(
            short_prompt,
            system_prompt=system_prompt,
            max_tokens=256,
            temperature=0.4,
        )

        detailed_summary = self.client.generate(
            detailed_prompt,
            system_prompt=system_prompt,
            max_tokens=512,
            temperature=0.5,
        )

        return {
            "short_summary": short_summary.strip(),
            "detailed_summary": detailed_summary.strip(),
        }
