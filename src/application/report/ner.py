"""Layer 1: NER + Entity Resolution — extract and normalize entities from articles."""

from __future__ import annotations

import logging
import re
from typing import Any

from src.application.report.models import ArticleEnriched

logger = logging.getLogger(__name__)


def normalize_entity(name: str, _type: str | None = None) -> str:
    """Normalize entity name to lowercase underscore slug.

    Examples:
        "Google Gemma 4" -> "google_gemma_4"
        "gemma-4" -> "gemma_4"
        "OpenAI" -> "openai"
        "Sam Altman" -> "sam_altman"
    """
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    return s


class NERExtractor:
    """Extract named entities from articles using LLM batch processing."""

    def __init__(self, batch_size: int = 5):
        self.batch_size = batch_size

    async def extract_batch(
        self, articles: list[dict[str, Any]]
    ) -> list[ArticleEnriched]:
        """Stub: returns articles with empty entities until NER replacement is implemented."""
        return [
            ArticleEnriched(
                id=a["id"],
                title=a.get("title", ""),
                link=a.get("link", ""),
                summary=a.get("summary", ""),
                quality_score=a.get("quality_score", 0.0),
                feed_weight=a.get("feed_weight", 0.0),
                published_at=a.get("published_at", ""),
                feed_id=a.get("feed_id", "unknown"),
                entities=[],
                dimensions=[],
            )
            for a in articles
        ]
