"""Web crawling operations for RSS reader.

Provides functions for crawling arbitrary URLs and extracting article content
using Readability algorithm. Handles rate limiting, robots.txt compliance (lazy mode),
and article storage in the existing articles table.
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from readability import Document
from robotexclusionrulesparser import RobotExclusionRulesParser

from src.db import get_connection
from src.models import Article

logger = logging.getLogger(__name__)

# Rate limiting state: {host: last_request_timestamp}
_rate_limit_state: dict[str, float] = {}


def ensure_crawled_feed() -> None:
    """Create 'crawled' system feed if it doesn't exist.

    Creates feed with id='crawled', name='Crawled Pages', url=''.
    This is the system feed for storing crawled web pages.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM feeds WHERE id = 'crawled'")
        if cursor.fetchone() is None:
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """INSERT INTO feeds (id, name, url, created_at)
                   VALUES ('crawled', 'Crawled Pages', '', ?)""",
                (now,)
            )
            conn.commit()
    finally:
        conn.close()


def crawl_url(url: str, ignore_robots: bool = False) -> Optional[dict]:
    """Fetch and extract article content from a URL.

    Args:
        url: URL to crawl
        ignore_robots: If True, skip robots.txt check (lazy mode)

    Returns:
        Dict with title, link, content, or None on failure

    Raises:
        Logs warnings for robots.txt failures (continues in lazy mode)
        Logs errors and returns None for fetch/extraction failures
    """
    parsed = urlparse(url)
    host = parsed.netloc

    # D-03: Rate limiting - 2-second delay between requests to same host
    if host in _rate_limit_state:
        elapsed = time.time() - _rate_limit_state[host]
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
    _rate_limit_state[host] = time.time()

    # D-02: robots.txt check (unless ignore_robots flag set)
    if not ignore_robots:
        robots_url = f"{parsed.scheme}://{host}/robots.txt"
        try:
            parser = RobotExclusionRulesParser()
            response = httpx.get(robots_url, timeout=10.0)
            parser.parse(response.text)
            if not parser.can_fetch(url, "*"):
                logger.warning("Blocked by robots.txt: %s", url)
                return None
        except Exception as e:
            # D-05: Lazy mode - log warning but continue on robots.txt errors
            logger.warning("Failed to fetch robots.txt for %s: %s", host, e)

    # Fetch page content with httpx
    try:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError, httpx.TimeoutException) as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None

    # D-01 + D-04: Extract content with Readability
    try:
        doc = Document(response.text)
        title = doc.title()
        # summary() returns HTML; strip tags for plain text content
        soup = BeautifulSoup(doc.summary(), 'html.parser')
        content = soup.get_text(separator='\n', strip=True)

        # D-05: Handle empty extraction
        if not content or len(content) < 100:
            logger.warning("Extracted content too short from %s", url)
            return None

    except Exception as e:
        logger.error("Failed to extract content from %s: %s", url, e)
        return None

    # D-07: Store in articles table with feed_id='crawled'
    # Ensure system feed exists
    ensure_crawled_feed()

    # Generate article ID: use URL as guid (with crawl: prefix)
    article_id = f"crawl:{hashlib.sha256(url.encode()).hexdigest()[:16]}"
    now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # D-07: Store article - use URL as link, content field for full text
        cursor.execute(
            """INSERT OR IGNORE INTO articles
               (id, feed_id, title, link, guid, pub_date, description, content, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (article_id, 'crawled', title, url, article_id, now, None, content, now)
        )

        # Sync to FTS5 (same pattern as refresh_feed)
        cursor.execute(
            """INSERT INTO articles_fts(rowid, title, description, content)
               SELECT id, title, description, content FROM articles WHERE id = ?""",
            (article_id,)
        )

        conn.commit()
    finally:
        conn.close()

    return {
        'title': title,
        'link': url,
        'content': content,
    }