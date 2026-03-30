"""Generic HTML parsing utilities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response
    from scrapling import Selector

_logger = logging.getLogger(__name__)

# Block detection: status codes that indicate anti-bot blocking
_BLOCK_STATUS_CODES = {403, 429}
# Block pages typically have very small content
_BLOCK_CONTENT_MIN_BYTES = 1000


def _looks_like_block_page(html_content: str | None) -> bool:
    """Check if HTML content looks like a block/challenge page.

    Args:
        html_content: HTML string to check.

    Returns:
        True if content appears to be a block page (very small or empty).
    """
    if not html_content:
        return True
    # Only consider it a block page if content is very small
    # (genuine pages typically have >10KB of content)
    return len(html_content) < _BLOCK_CONTENT_MIN_BYTES


def fetch_with_fallback(
    url: str,
    headers: dict | None = None,
    timeout: int = 30,
) -> "Response | None":
    """Fetch a URL with automatic fallback from basic Fetcher to stealth fetcher.

    Strategy:
        1. Try Fetcher().get() - fast, works for most sites
        2. If blocked (403/429) or content looks like block page,
           fall back to StealthyFetcher().fetch() - slower but bypasses bots

    Args:
        url: URL to fetch.
        headers: Optional HTTP headers (uses BROWSER_HEADERS if None).
        timeout: Request timeout in seconds.

    Returns:
        Response object with .html_content, .status, etc., or None on failure.
    """
    from scrapling import Fetcher, StealthyFetcher

    if headers is None:
        from src.constants import BROWSER_HEADERS
        headers = BROWSER_HEADERS

    # Fast path: try basic Fetcher
    try:
        fetcher = Fetcher()
        response = fetcher.get(url, headers=headers, timeout=timeout)
        status = getattr(response, "status", 0)
        html = getattr(response, "html_content", None) or ""

        if status in _BLOCK_STATUS_CODES or _looks_like_block_page(html):
            _logger.debug(f"Basic fetch blocked ({status}), trying stealth fetcher for {url}")
        else:
            return response
    except Exception as e:
        _logger.debug(f"Basic fetch failed ({e}), trying stealth fetcher for {url}")

    # Fallback: try stealth fetcher (slower but bypasses most anti-bots)
    try:
        stealth = StealthyFetcher()
        return stealth.fetch(url, headers=headers, timeout=timeout * 1000)
    except Exception as e:
        _logger.warning(f"Stealth fetcher also failed for {url}: {e}")
        return None


def parse_html_body(response: "Response") -> str | None:
    """Parse HTML body from HTTP response.

    Args:
        response: HTTP response object with .body attribute.

    Returns:
        HTML string or None if not available.
    """
    if not response:
        return None
    try:
        if response.body:
            return response.body.decode('utf-8', errors='replace') if isinstance(response.body, bytes) else str(response.body)
    except Exception:
        pass
    return None


def find_base_href(page: "Selector") -> str | None:
    """Extract <base href> override from page head.

    Args:
        page: Parsed HTML page (scrapling Selector).

    Returns:
        Base href URL or None.
    """
    head = page.find('head')
    if head:
        base_tag = head.find('base[href]')
        if base_tag:
            return base_tag.attrib['href']
    return None
