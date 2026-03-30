"""Deep BFS crawling for feed discovery with rate limiting and robots.txt compliance (DISC-07, DISC-08)."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any
from urllib.parse import urljoin, urlparse

import feedparser
from scrapling import Selector
from trafilatura.feeds import FEED_TYPES

# Suppress scrapling 0.4.x deprecation warning
_scrapling_logger = logging.getLogger("scrapling")
_scrapling_logger.disabled = True
from robotexclusionrulesparser import RobotExclusionRulesParser

from src.constants import BROWSER_HEADERS
from src.discovery.models import DiscoveredFeed, DiscoveredResult
from src.utils.scraping_utils import fetch_with_fallback


def compute_link_selectors(html: str, page_url: str) -> dict[str, Selector]:
    """Compute CSS selectors for link href prefixes from HTML.

    For each link like '/news/2026-03-03/xxxxx', returns CSS attribute
    selectors that match links sharing the same path prefix.

    Args:
        html: Raw HTML content.
        page_url: URL the HTML was fetched from.

    Returns:
        Dict mapping CSS selector path (e.g., '/news/') to Selector with
        path, example link URL, link text, and count.
    """
    from urllib.parse import urlparse as _urlparse

    from src.discovery.models import LinkSelector as LinkSelectorModel

    selectors: dict[str, LinkSelectorModel] = {}
    page = Selector(content=html)

    # Check for <base href> override
    base_override: str | None = None
    head = page.find('head')
    if head:
        base_tag = head.find('base[href]')
        if base_tag:
            base_override = base_tag.attrib['href']

    base_parsed = _urlparse(page_url)

    for anchor in page.css('a[href]'):
        href = anchor.attrib.get('href', '')
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue

        # Resolve relative URLs
        if base_override:
            absolute = urljoin(base_override, href)
        else:
            absolute = urljoin(page_url, href)

        parsed = _urlparse(absolute)

        # Skip external hosts or non-HTTP
        if parsed.netloc.lower() != base_parsed.netloc.lower():
            continue
        if parsed.scheme not in ('http', 'https'):
            continue

        path = parsed.path.rstrip('/')
        if not path:
            path = '/'

        # Get link text (prefer aria-label for accessible text)
        link_text = anchor.attrib.get('aria-label', '') or ''
        if not link_text:
            link_text = getattr(anchor, 'text', '') or ''
            link_text = link_text.strip()

        # Count CSS selectors for the full path and each parent segment
        parts = path.split('/')
        for i in range(1, len(parts)):
            parent = '/'.join(parts[:i]) + '/'
            if parent in selectors:
                selectors[parent].count += 1
            else:
                selectors[parent] = LinkSelectorModel(
                    path=parent,
                    link=absolute,
                    text=link_text,
                    count=1,
                )

    return selectors


def normalize_url_for_visit(url: str) -> str:
    """Normalize URL for visited-set tracking.

    - Remove fragments (#...)
    - Strip trailing slashes
    - Lowercase scheme + host

    Args:
        url: URL to normalize.

    Returns:
        Normalized URL string.
    """
    parsed = urlparse(url)

    # Remove fragment
    scheme_host = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"

    # Strip trailing slash from path
    path = parsed.path.rstrip('/')
    if not path:
        path = '/'

    # Reconstruct without fragment
    return f"{scheme_host}{path}"


async def _validate_and_extract_title(url: str) -> tuple[bool, str | None, str | None, bytes | None]:
    """Validate feed and extract title with a single HTTP request.

    Args:
        url: The feed URL to validate and extract title from.

    Returns:
        Tuple of (is_valid, feed_type, title, body).
        is_valid: True if URL returns HTTP 200 with valid feed Content-Type.
        feed_type: 'rss', 'atom', or 'rdf' based on Content-Type.
        title: Feed title if found, None otherwise.
        body: Raw response body for selectors computation, None if not valid feed.
    """
    try:
        response = await asyncio.to_thread(Fetcher.get, url, headers=BROWSER_HEADERS)
        if response.status != 200:
            return False, None, None, None
        content_type = response.headers.get('content-type', '').lower()

        # Determine feed type using trafilatura FEED_TYPES
        feed_type = None
        if any(ft in content_type for ft in FEED_TYPES):
            for keyword in ('atom', 'rdf', 'rss', 'json'):
                if keyword in content_type:
                    feed_type = keyword if keyword != 'rdf' else 'rdf'
                    break
        # Fallback: detect from URL path for generic xml types
        if feed_type is None and 'xml' in content_type:
            lower_url = url.lower()
            if '/rss' in lower_url or '.rss' in lower_url:
                feed_type = 'rss'
            elif '/atom' in lower_url:
                feed_type = 'atom'
            elif '/rdf' in lower_url:
                feed_type = 'rdf'

        # Extract title from response body (only for feeds)
        title = None
        body = response.body
        if feed_type is None:
            # Not a feed but we have the body - return it for selectors
            return False, None, None, body

        try:
            feed = feedparser.parse(body)
            if feed.feed:
                title = feed.feed.get('title')
        except Exception:
            pass  # Title extraction is best-effort

        return True, feed_type, title, body
    except Exception:
        return False, None, None, None


async def _quick_validate_feed(url: str) -> tuple[bool, str | None]:
    """Quick feed validation via HEAD request only.

    Only checks HTTP 200 + Content-Type header, skipping full feed parsing.

    Args:
        url: The feed URL to validate.

    Returns:
        Tuple of (is_valid, feed_type).
    """
    is_valid, feed_type, _, _ = await _validate_and_extract_title(url)
    return is_valid, feed_type


async def deep_crawl(start_url: str, max_depth: int = 1, auto_discover: bool = True) -> DiscoveredResult:
    """Discover feeds using BFS crawling up to max_depth.

    Args:
        start_url: Starting URL for crawling.
        max_depth: Maximum crawl depth (1 = current page only, 2+ = BFS crawl).
        auto_discover: Whether to run auto-discovery (default: True).

    Returns:
        DiscoveredResult with feeds list and selectors dict.
        For max_depth=1, selectors contains link path prefix counts.
        For max_depth>1, selectors is empty (expensive to compute).
    """
    # Import here to avoid circular imports
    from src.discovery.models import LinkSelector as LinkSelectorModel
    from src.providers import discover as providers_discover

    selectors: dict[str, LinkSelectorModel] = {}
    if max_depth <= 1:
        # Use providers.discover() for feed discovery - validation is delegated to providers
        try:
            response = await asyncio.to_thread(fetch_with_fallback, start_url, headers=BROWSER_HEADERS)
            if response.status == 200:
                # providers_discover returns only valid=True feeds
                feeds = providers_discover(start_url, response, depth=1, discover=auto_discover)
                if feeds:
                    # Normalize URLs and deduplicate
                    seen: set[str] = set()
                    unique_feeds: list[DiscoveredFeed] = []
                    for feed in feeds:
                        normalized = normalize_url_for_visit(feed.url)
                        if normalized not in seen:
                            seen.add(normalized)
                            # Update URL to normalized form
                            feed = DiscoveredFeed(
                                url=normalized,
                                title=feed.title,
                                feed_type=feed.feed_type,
                                source=feed.source,
                                page_url=feed.page_url,
                                valid=feed.valid,
                            )
                            unique_feeds.append(feed)
                    return DiscoveredResult(url=start_url, max_depth=max_depth, feeds=unique_feeds, selectors=selectors)
        except Exception:
            pass

        # max_depth <= 1 must return here - never fall through to BFS
        return DiscoveredResult(url=start_url, max_depth=max_depth, feeds=[], selectors=selectors)

    # Deep crawl (max_depth > 1)
    # Normalize start URL
    normalized_start = normalize_url_for_visit(start_url)

    # BFS queue: (url, depth)
    queue: deque[tuple[str, int]] = deque()
    queue.append((start_url, 1))

    visited: set[str] = set()
    visited.add(normalized_start)

    # Rate limiting: last request timestamp per host
    last_request_time: dict[str, float] = {}

    # robots.txt cache: parsed robots per host
    robots_cache: dict[str, RobotExclusionRulesParser | None] = {}

    # Semaphore to limit concurrent requests (5 concurrent)
    semaphore = asyncio.Semaphore(5)

    # All discovered feeds
    all_feeds: list[DiscoveredFeed] = []

    def get_host(url: str) -> str:
        """Extract host from URL."""
        return urlparse(url).netloc.lower()

    async def _fetch_page(url: str) -> tuple[str | None, str, Any]:
        """Fetch a page and return (html, final_url, response)."""
        async with semaphore:
            host = get_host(url)

            # Rate limiting: 2 seconds per host
            now = time.time()
            if host in last_request_time:
                sleep_time = max(0, 2.0 - (now - last_request_time[host]))
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            last_request_time[host] = time.time()

            try:
                response = await asyncio.to_thread(
                    Fetcher.get, url, headers=BROWSER_HEADERS
                )
                if response.status != 200:
                    return None, url, None
                return response.text, response.url, response
            except Exception:
                return None, url, None

    async def _check_robots(url: str, depth: int) -> bool:
        """Check if robots.txt allows crawling a URL.

        Only checks when depth > 1 (lazy mode).

        Args:
            url: URL to check.
            depth: Current crawl depth.

        Returns:
            True if crawling is allowed, False otherwise.
        """
        if depth <= 1:
            # Depth 1 is like normal browser - don't check robots.txt
            return True

        host = get_host(url)

        if host not in robots_cache:
            # Fetch and parse robots.txt
            robots_url = f"{urlparse(url).scheme.lower()}://{host}/robots.txt"
            parser = RobotExclusionRulesParser()
            try:
                response = await asyncio.to_thread(Fetcher.get, robots_url)
                if response.status == 200:
                    parser.parse(response.text.splitlines())
                else:
                    # No robots.txt - permissive
                    parser = None
            except Exception:
                parser = None
            robots_cache[host] = parser

        parser = robots_cache[host]
        if parser is None:
            # No robots.txt - allow crawling
            return True

        return parser.can_fetch(url, user_agent='*')

    def _extract_links(html: str, page_url: str, base_host: str) -> list[str]:
        """Extract internal links from HTML.

        Args:
            html: Raw HTML content.
            page_url: URL the HTML was fetched from.
            base_host: Host to restrict links to (same-domain).

        Returns:
            List of absolute URLs found on the page that may be feed URLs.
        """
        links = []
        page = Selector(content=html)

        # Check for <base href> override
        base_override: str | None = None
        head = page.find('head')
        if head:
            base_tag = head.find('base[href]')
            if base_tag:
                base_override = base_tag.attrib['href']

        # Use CSS selectors to find feed-like links directly
        # Look for hrefs containing: rss, feed, atom in the path
        feed_selectors = [
            'a[href*="rss"]',
            'a[href*="feed"]',
            'a[href*="atom"]',
            'a[href$=".xml"]',
        ]

        for selector in feed_selectors:
            for anchor in page.css(selector):
                href = anchor.attrib['href']

                # Resolve relative URLs
                if base_override:
                    absolute = urljoin(base_override, href)
                else:
                    absolute = urljoin(page_url, href)

                parsed = urlparse(absolute)

                # Skip different hosts
                if parsed.netloc.lower() != base_host:
                    continue

                if absolute not in links:
                    links.append(absolute)

        return links

    # Process queue with BFS
    while queue:
        url, depth = queue.popleft()

        if depth > max_depth:
            continue

        # Check robots.txt (only if depth > 1)
        if not await _check_robots(url, depth):
            continue

        # Fetch page
        html, final_url, response = await _fetch_page(url)
        if html is None:
            continue

        # Normalize final URL for visited check
        normalized_final = normalize_url_for_visit(final_url)
        if normalized_final in visited:
            continue
        visited.add(normalized_final)

        # Extract links for next depth
        base_host = get_host(final_url)

        # Discover feeds using providers.discover()
        page_feeds = providers_discover(final_url, response, depth, discover=auto_discover)
        all_feeds.extend(page_feeds)

        # Queue internal links for next depth
        if depth < max_depth:
            links = _extract_links(html, final_url, base_host)
            for link in links:
                normalized_link = normalize_url_for_visit(link)
                if normalized_link not in visited:
                    visited.add(normalized_link)
                    queue.append((link, depth + 1))

    # Deduplicate feeds by URL
    seen: set[str] = set()
    unique_feeds: list[DiscoveredFeed] = []
    for feed in all_feeds:
        if feed.url not in seen:
            seen.add(feed.url)
            unique_feeds.append(feed)

    return DiscoveredResult(url=start_url, max_depth=max_depth, feeds=unique_feeds, selectors=selectors)
