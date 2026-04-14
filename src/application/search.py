"""Search result formatting functions for CLI presentation.

Separates formatting logic from CLI presentation, making search results
reusable by other callers without CLI dependencies.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from src.application.config import format_published_date


def format_articles(
    items: list[dict[str, Any]], verbose: bool = False
) -> list[dict[str, Any]]:
    """Format articles for display using unified score field interface.

    Assumes items are dicts from rank_*_results with a score field (0-1 normalized).
    No mode branching - all article types use the same formatting logic.

    Args:
        items: List of article dicts with score field from rank_*_results
        verbose: Include full details if True

    Returns:
        List of dicts with unified fields: id, title, source, date, score
    """
    return _format_items(items, verbose)


def _format_items(items: list[dict[str, Any]], verbose: bool) -> list[dict[str, Any]]:
    """Format articles for display using unified score field interface.

    Assumes items are dicts with score field from rank_*_results.
    Handles all article types (list, FTS, semantic) through unified interface.

    Args:
        items: List of article dicts with score field from rank_*_results
        verbose: Include full details if True

    Returns:
        List of dicts with unified fields: id, title, source, date, score
    """
    formatted = []
    for item in items:
        title = _truncate(item.get("title") or "No title", 60)
        date = format_published_date(item.get("published_at"))
        score_val = item.get("score")

        # Format score as percentage (0-1 normalized from rank_*_results)
        score = f"{int(score_val * 100)}%" if score_val is not None else "N/A"

        # Extract source - prefer feed_name (list/FTS) or domain from url (semantic)
        feed_name = item.get("feed_name")
        url = item.get("url")
        if feed_name:
            source = _truncate(feed_name, 15)
        elif url:
            try:
                parsed = urlparse(url)
                source = parsed.netloc[:15] if parsed.netloc else "-"
            except Exception:
                source = "-"
        else:
            source = "-"

        # Extract article ID - prefer id, fall back to sqlite_id
        article_id = item.get("id") or item.get("sqlite_id") or ""

        # Base fields always present
        base = {
            "id": article_id[:8] if article_id and not verbose else article_id,
            "title": title,
            "source": source,
            "date": date,
            "score": score,
        }

        # Add verbose-only fields based on what's available
        if verbose:
            # Link from FTS results
            if item.get("link"):
                base["link"] = item["link"]
            # Description from FTS results
            if item.get("description"):
                base["description_preview"] = _truncate(item["description"], 100)
            # URL and document from semantic results
            if item.get("url"):
                base["url"] = url
            if item.get("document"):
                base["document_preview"] = _truncate(item["document"], 150)

        formatted.append(base)
    return formatted


def rank_fts_results(articles: list[Any]) -> list[dict[str, Any]]:
    """Rank FTS search results with fixed score.

    FTS keyword search has no similarity metric, so all results get score=1.0.

    Args:
        articles: List of ArticleListItem from search_articles_fts.

    Returns:
        List of dicts with all original article fields PLUS score=1.0.
        Returns empty list if input is empty.
    """
    if not articles:
        return []
    return [{**vars(article), "score": 1.0} for article in articles]


def rank_list_results(items: list[Any]) -> list[dict[str, Any]]:
    """Rank list results with fixed score.

    List results have no similarity metric, so all results get score=1.0.

    Args:
        items: List of ArticleListItem from list_articles.

    Returns:
        List of dicts with all original item fields PLUS score=1.0.
        Returns empty list if input is empty.
    """
    if not items:
        return []
    return [{**vars(item), "score": 1.0} for item in items]


def format_fts_results(
    articles: list[Any], verbose: bool = False
) -> list[dict[str, Any]]:
    """Format FTS5 keyword search results for display.

    Takes output from search_articles_fts (list of ArticleListItem) and
    formats fields for unified CLI presentation.

    Args:
        articles: List of ArticleListItem from search_articles_fts with keys:
            - title: Article title or None
            - feed_name: Name of the feed
            - published_at: Publication date or None
            - link: URL link or None
            - description: Short description or None
        verbose: If True, include link and description preview.
                 If False, show truncated summary.

    Returns:
        List of dicts with unified formatted fields:
        - id: article_id[:8] (non-verbose) or article_id (verbose)
        - title: article title (truncated to 60 chars)
        - source: feed_name (truncated to 15 chars)
        - date: published_at (formatted as yyyy-mm-dd)
        - score: "FTS" (indicates FTS keyword search)
        - link: article link (verbose only)
        - description_preview: truncated description (verbose only)
    """
    return format_articles(articles, verbose=verbose)


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
