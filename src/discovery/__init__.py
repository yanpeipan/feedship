"""Discovery service for RSS/Atom feed auto-discovery from website URLs."""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import urljoin
from typing import TYPE_CHECKING

from src.discovery.common_paths import FEED_CONTENT_TYPES, generate_feed_candidates
from src.discovery.deep_crawl import deep_crawl, compute_link_selectors
from src.discovery.fetcher import validate_feed
from src.discovery.models import DiscoveredFeed, DiscoveredResult, LinkSelector
from src.discovery.parser import parse_link_elements
from src.constants import BROWSER_HEADERS

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """Normalize input URL by adding scheme if missing.

    Args:
        url: Input URL which may lack scheme.

    Returns:
        URL with scheme prepended.
    """
    url = url.strip()
    if not url:
        raise ValueError("URL cannot be empty")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def probe_well_known_paths(page_url: str) -> list[str]:
    """Generate candidate feed URLs from well-known root paths.

    Args:
        page_url: Base page URL to probe.

    Returns:
        List of candidate feed URLs.
    """
    return generate_feed_candidates(page_url)


async def validate_and_wrap(
    url: str, page_url: str, source: str
) -> DiscoveredFeed | None:
    """Validate a feed URL and wrap in DiscoveredFeed if valid.

    Args:
        url: Feed URL to validate.
        page_url: Original page URL.
        source: Discovery source ('autodiscovery' or 'well_known_path').

    Returns:
        DiscoveredFeed if valid, None otherwise.
    """
    is_valid, feed_type = await validate_feed(url)
    if not is_valid:
        return None
    return DiscoveredFeed(
        url=url,
        title=None,
        feed_type=feed_type,
        source=source,
        page_url=page_url,
        valid=True,
    )


def _sync_fetch_page_response(url: str) -> "Response | None":
    """Fetch a page and return scrapling Response for provider matching.

    This is a synchronous function suitable for running in a thread pool.

    Args:
        url: Page URL to fetch.

    Returns:
        scrapling Response object, or None if fetch fails.
    """
    try:
        from scrapling import Fetcher
        response = Fetcher.get(url, headers=BROWSER_HEADERS)
        return response
    except Exception:
        return None


async def discover_feeds(url: str, max_depth: int = 1) -> DiscoveredResult:
    """Discover RSS/Atom/RDF feeds from a website URL.

    Args:
        url: Website URL to discover feeds from.
        max_depth: Maximum crawl depth (1 = current page only, 2+ = BFS crawl).

    Returns:
        DiscoveredResult containing list of DiscoveredFeed objects found.
        For max_depth=1, selectors contains link path prefix counts.
    """
    # Single-page discovery: delegate to deep_crawl (handles subdirectory probing)
    return await deep_crawl(url, max_depth)


# Public exports
__all__ = ["discover_feeds", "DiscoveredFeed", "DiscoveredResult", "LinkSelector", "deep_crawl"]
