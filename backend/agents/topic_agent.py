"""Topic Prioritization Agent.

Uses TF-IDF and simple keyword scoring to assign weightage
(High / Medium / Low) to topics/chapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any

from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


@dataclass
class TopicImportance:
    title: str
    score: float
    weightage: str


class TopicPrioritizationAgent:
    """Agent that scores each chapter/topic for exam importance."""

    def __init__(self) -> None:
        # Keywords roughly tuned for academic material and PYQs
        self.keywords = [
            "definition",
            "theorem",
            "proof",
            "example",
            "exercise",
            "important",
            "properties",
            "application",
            "previous year question",
            "pyq",
        ]

    def _keyword_boost(self, text: str) -> float:
        text_lower = text.lower()
        return sum(1.0 for kw in self.keywords if kw in text_lower)

    def run(self, chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not chapters:
            return []

        docs = [c.get("content", "") for c in chapters]
        titles = [c.get("title", "Untitled") for c in chapters]

        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = vectorizer.fit_transform(docs)

        # Aggregate TF-IDF score per chapter as mean TF-IDF + keyword boost
        base_scores = np.asarray(tfidf.mean(axis=1)).reshape(-1)
        boosts = np.array([self._keyword_boost(text) for text in docs])
        scores = base_scores + 0.2 * boosts

        # Normalize to [0, 1]
        if scores.max() > 0:
            scores = (scores - scores.min()) / (scores.max() - scores.min() + 1e-8)
        else:
            scores = np.zeros_like(scores)

        topics: list[Dict[str, Any]] = []
        for title, score, chapter in zip(titles, scores, chapters):
            if score >= 0.66:
                weight = "High"
            elif score >= 0.33:
                weight = "Medium"
            else:
                weight = "Low"

            topics.append(
                {
                    "title": title,
                    "score": float(round(float(score), 3)),
                    "weightage": weight,
                    "snippet": chapter.get("content", "")[:400],
                }
            )

        return topics
