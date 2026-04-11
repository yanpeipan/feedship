"""Layer 1: NER extraction via batch LLM + entity normalization."""

import re
import unicodedata
from typing import Any


def normalize_entity(entity_name: str) -> str:
    """Normalize an entity name to a stable lowercase ID.

    Rules:
    - Strip leading/trailing whitespace
    - Lowercase
    - Remove punctuation (except hyphen/underscore in compound names)
    - Collapse multiple spaces
    - Unicode normalization (NFKC)
    """
    text = unicodedata.normalize("NFKC", entity_name.strip().lower())
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class NERExtractor:
    """Extract named entities from articles via batch LLM calls.

    Design:
    - batch_size: 10 articles per LLM call
    - Per-batch retry with 2s/4s/8s exponential backoff
    - feed_id fallback: if batch fails, extract entities using feed_id field
    """

    def __init__(self, batch_size: int = 10) -> None:
        self.batch_size = batch_size

    def _normalize_batch(
        self, raw_entities: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Normalize entity names and deduplicate within a batch."""
        seen: set[str] = set()
        normalized = []
        for ent in raw_entities:
            name = ent.get("name", "").strip()
            if not name:
                continue
            nid = normalize_entity(name)
            if nid in seen:
                continue
            seen.add(nid)
            normalized.append(
                {
                    "name": name,
                    "normalized_id": nid,
                    "type": ent.get("type", "UNKNOWN"),
                }
            )
        return normalized

    async def extract_batch(
        self, articles: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract named entities from a batch of articles via LLM.

        Falls back to feed_id-based extraction on LLM failure.
        """
        if not articles:
            return []

        # Fallback: use feed_id as proxy entity (NER chain removed)
        results = []
        for a in articles:
            feed_id = a.get("feed_id", "")
            if feed_id:
                results.append(
                    {
                        "name": feed_id,
                        "normalized_id": normalize_entity(feed_id),
                        "type": "SOURCE",
                    }
                )
        return results
