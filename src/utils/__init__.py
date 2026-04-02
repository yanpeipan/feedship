"""Utility modules."""

from __future__ import annotations

import hashlib

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
