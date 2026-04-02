"""Utility modules."""

from __future__ import annotations

import hashlib
import time

from nanoid import generate


def generate_feed_id() -> str:
    """Generate a unique ID for a new feed (nanoid, same as articles).

    Returns:
        A new nanoid string.
    """
    return generate()


def generate_article_id(entry) -> str:
    """Generate a unique article ID from a feed entry.

    Uses guid if available, falls back to link, then generates a hash
    from link and published_at.

    Args:
        entry: A feedparser entry dict.

    Returns:
        A unique string identifier for the article.
    """
    # Try guid first
    article_id = entry.get("id")
    if article_id:
        return article_id

    # Fall back to link
    link = entry.get("link")
    if link:
        return link

    # Last resort: hash of link + published_at
    published_at = entry.get("published") or entry.get("updated") or ""
    hash_input = f"{link}:{published_at}"
    return hashlib.sha256(hash_input.encode()).hexdigest()


def get_current_timestamp() -> str:
    """Return current timestamp in YYYY-MM-DD HH:MM:SS format."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def parse_article_entry(entry: dict, feed_id: str) -> dict:
    """Convert raw article entry to storage format dict.

    Args:
        entry: Feedparser article entry dict.
        feed_id: ID of the feed this article belongs to.

    Returns:
        Dict with guid, title, content, description, link, feed_id, published_at.
    """
    article_guid = entry.get("guid") or generate_article_id(entry)
    return {
        "guid": article_guid,
        "title": entry.get("title") or "",
        "content": entry.get("content") or "",
        "description": entry.get("description") or "",
        "link": entry.get("link") or "",
        "feed_id": feed_id,
        "published_at": entry.get("published_at"),
    }
