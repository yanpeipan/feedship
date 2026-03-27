"""Search result formatting functions for CLI presentation.

Separates formatting logic from CLI presentation, making search results
reusable by other callers without CLI dependencies.
"""

from __future__ import annotations

from typing import Any

from src.application.articles import ArticleListItem


def format_semantic_results(results: list[dict[str, Any]], verbose: bool = False) -> list[dict[str, Any]]:
    """Format semantic search results for display.

    Takes output from search_articles_semantic (list of dicts with article_id,
    sqlite_id, title, url, distance, document) and converts L2 distance to
    cosine similarity for normalized display.

    Args:
        results: List of dicts from search_articles_semantic with keys:
            - article_id: ChromaDB ID (guid)
            - sqlite_id: SQLite nanoid or None
            - title: Article title or None
            - url: Article URL or None
            - distance: L2 distance (float) or None
            - document: Full content text or None
        verbose: If True, include full details (id, url, document preview).
                 If False, show truncated summary.

    Returns:
        List of dicts with formatted fields:
        - id_display: sqlite_id[:8] or "" (non-verbose), full sqlite_id or "" (verbose)
        - title: article title
        - source: url or "-" (non-verbose), url or "" (verbose)
        - date: "-" (non-verbose), "" (verbose)
        - similarity: percentage string like "85.5%" or "N/A"
        - url: full url (verbose only)
        - document_preview: truncated content (verbose only)
    """
    formatted = []
    for result in results:
        title = result.get("title") or "No title"
        url = result.get("url") or ""
        distance = result.get("distance")
        sqlite_id = result.get("sqlite_id")

        # Convert L2 distance to cosine similarity for normalized embeddings:
        # L2_dist = sqrt(2 - 2*cos_sim) => cos_sim = 1 - dist^2/2
        if distance is not None:
            cos_sim = max(0.0, 1.0 - (distance * distance / 2.0))
            similarity = f"{round(cos_sim * 100, 1)}%"
        else:
            similarity = "N/A"

        if verbose:
            formatted.append({
                "id_display": sqlite_id[:8] if sqlite_id else "",
                "title": title,
                "source": url or "",
                "date": "",
                "similarity": similarity,
                "url": url,
                "document_preview": _truncate(result.get("document"), 150) if result.get("document") else "",
            })
        else:
            id_display = f"{sqlite_id[:8]} | " if sqlite_id else ""
            formatted.append({
                "id_display": id_display,
                "title": title,
                "source": url or "-",
                "date": "-",
                "similarity": similarity,
            })
    return formatted


def format_fts_results(articles: list[ArticleListItem], verbose: bool = False) -> list[dict[str, Any]]:
    """Format FTS5 keyword search results for display.

    Takes output from search_articles (list of ArticleListItem) and
    formats fields with appropriate truncation for display.

    Args:
        articles: List of ArticleListItem from search_articles with keys:
            - title: Article title or None
            - feed_name: Name of the feed
            - pub_date: Publication date or None
            - link: URL link or None
            - description: Short description or None
        verbose: If True, include link and description preview.
                 If False, show truncated summary.

    Returns:
        List of dicts with formatted fields:
        - title: article title (truncated to 50 chars)
        - source: feed_name (truncated to 25 chars)
        - date: pub_date (truncated to 10 chars)
        - link: article link (verbose only)
        - description_preview: truncated description (verbose only)
    """
    formatted = []
    for article in articles:
        title = _truncate(article.title, 50) if article.title else "No title"
        source = _truncate(article.feed_name, 25) if article.feed_name else "Unknown"
        date = _truncate(article.pub_date, 10) if article.pub_date else "No date"

        if verbose:
            desc_preview = _truncate(article.description, 100) if article.description else ""
            formatted.append({
                "title": title,
                "source": source,
                "date": date,
                "link": article.link or "",
                "description_preview": desc_preview,
            })
        else:
            formatted.append({
                "title": title,
                "source": source,
                "date": date,
            })
    return formatted


def _truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."
