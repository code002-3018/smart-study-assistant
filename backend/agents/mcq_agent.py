"""MCQ Generator Agent.

Creates 10+ MCQs per chapter, each with:
- question
- 4 options
- correct answer
- brief explanation
"""

from __future__ import annotations

import json
from typing import List, Dict, Any

from backend.models.llm import LLMClient


class MCQGeneratorAgent:
    """Agent that generates exam-style MCQs for each chapter."""

    def __init__(self) -> None:
        self.client = LLMClient()

    def _build_prompt(self, chapter_title: str, content: str) -> str:
        return (
            "Generate 10 multiple-choice questions (MCQs) for this chapter. "
            "Return ONLY a valid JSON object, nothing else before or after. "
            "Use this EXACT format:\n\n"
            '```json\n'
            '{\n'
            '  "mcqs": [\n'
            '    {\n'
            '      "question": "What is the definition of X?",\n'
            '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
            '      "answer": "Option A",\n'
            '      "explanation": "Brief explanation here"\n'
            '    }\n'
            '  ]\n'
            '}\n'
            '```\n\n'
            "IMPORTANT: Return ONLY the JSON object. Do not include any text before or after the JSON. "
            "Do not include markdown code blocks or any formatting - just raw JSON.\n\n"
            f"CHAPTER TITLE: {chapter_title}\n\nCONTENT:\n{content[:6000]}"
        )

    def generate_for_chapter(self, chapter: Dict[str, Any]) -> Dict[str, Any]:
        title = chapter.get("title", "Untitled Chapter")
        content = chapter.get("content", "")

        prompt = self._build_prompt(title, content)
        raw = self.client.generate(prompt, max_tokens=2048, temperature=0.7)

        # Try to parse JSON; handle markdown code blocks if present
        try:
            # Remove markdown code blocks if present
            clean_raw = raw.strip()
            if clean_raw.startswith("```"):
                # Extract content between ```json and ```
                lines = clean_raw.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.strip().startswith("```"):
                        if not in_json:
                            in_json = True
                        else:
                            break
                    elif in_json:
                        json_lines.append(line)
                clean_raw = "\n".join(json_lines)
            
            data = json.loads(clean_raw)
            mcqs = data.get("mcqs", [])
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error for chapter '{title}': {e}")
            print(f"Raw LLM output: {raw[:500]}...")
            mcqs = [
                {
                    "question": "LLM output could not be parsed as JSON.",
                    "options": ["A) See raw output in logs", "B) ", "C) ", "D) "],
                    "answer": "A) See raw output in logs",
                    "explanation": raw[:1000],
                }
            ]

        return {"title": title, "mcqs": mcqs}

    def run(self, chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: list[Dict[str, Any]] = []
        for chapter in chapters:
            results.append(self.generate_for_chapter(chapter))
        return results
