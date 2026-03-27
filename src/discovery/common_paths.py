"""Well-known feed URL paths for fallback probing (DISC-02)."""
from __future__ import annotations

import re
from typing import Sequence

# Root-level well-known paths for candidate generation
_ROOT_PATH_PATTERNS = (
    "/feed",
    "/feed/",
    "/rss",
    "/rss.xml",
    "/atom.xml",
    "/feed.xml",
    "/index.xml",
)


def _discover_feed_subdirs(html: str, base: str) -> set[str]:
    """Discover feed-containing subdirectories from page links.

    Args:
        html: Raw HTML content of the page.
        base: Base URL (scheme://host) for constructing full paths.

    Returns:
        Set of discovered subdirectory paths that may contain feeds.
    """
    from scrapling import Selector

    subdirs: set[str] = set()
    page = Selector(content=html)

    # Find all <a href=""> tags
    for anchor in page.css('a[href]'):
        href = anchor.attrib['href']

        # Skip non-HTTP URLs, fragments, mailto, tel, and protocol-relative URLs
        if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue

        # Handle root-relative paths (/blog/rss.xml) - these are same-domain
        if href.startswith('/'):
            # Root-relative path - use it directly
            path = href
        else:
            # Parse full URL for other cases
            from urllib.parse import urlparse
            parsed = urlparse(href)
            path = parsed.path

        # Only care about paths with 2+ segments containing feed-like filenames
        if not path:
            continue

        segments = path.strip('/').split('/')
        if len(segments) < 2:
            continue

        # Check if path ends with feed-like filename
        filename = segments[-1].lower()
        if filename in ('rss.xml', 'atom.xml', 'feed.xml', 'index.xml', 'rss', 'feed', 'atom'):
            # Extract subdirectory (everything except the filename)
            subdir = '/' + '/'.join(segments[:-1])
            subdirs.add(subdir)

    return subdirs


def generate_feed_candidates(base_url: str, html: str | None = None) -> list[str]:
    """Generate candidate feed URLs from base URL.

    If html is provided, uses dynamic subdirectory discovery from page links.
    Otherwise falls back to root-level patterns only.

    Args:
        base_url: Base URL to generate candidates from (e.g., 'https://example.com').
        html: Optional HTML content for dynamic subdirectory discovery.

    Returns:
        List of candidate feed URLs including root-level and subdirectory paths.
    """
    from urllib.parse import urlparse
    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if parsed.port:
        base += f":{parsed.port}"

    candidates = []

    # Root-level candidates (always included)
    for path in _ROOT_PATH_PATTERNS:
        candidates.append(base + path)

    # Dynamic subdirectory candidates (if html provided)
    if html:
        subdirs = _discover_feed_subdirs(html, base)
        for subdir in subdirs:
            for filename in ('rss.xml', 'atom.xml', 'feed.xml', 'index.xml'):
                candidates.append(f"{base}{subdir}/{filename}")

    return candidates


# Regex patterns for feed-related URL paths
# These replace both WELL_KNOWN_PATHS and _COMMON_FEED_SUBDIRS
# Each pattern matches URL paths that may be feed URLs
_FEED_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Root-level: /feed, /feed/, /feed.xml, /feed.xml/, /rss, /rss.xml, /atom.xml, /feed.xml, /index.xml
    re.compile(r"^/feed/?\.?xml$"),
    re.compile(r"^/feed/?$"),
    re.compile(r"^/rss\.?xml$"),
    re.compile(r"^/rss$"),
    re.compile(r"^/atom\.xml$"),
    re.compile(r"^/feed\.xml$"),
    re.compile(r"^/index\.xml$"),
    # Subdirectory-level: /{anything}/rss.xml, /{anything}/atom.xml, /{anything}/feed.xml
    re.compile(r"^/[^/]+/rss\.xml$"),
    re.compile(r"^/[^/]+/atom\.xml$"),
    re.compile(r"^/[^/]+/feed\.xml$"),
)


def matches_feed_path_pattern(path: str) -> bool:
    """Check if a URL path matches any feed path pattern.

    Args:
        path: URL path to check (e.g., '/news/rss.xml', '/feed').

    Returns:
        True if the path matches any feed-related pattern.
    """
    return any(p.match(path) for p in _FEED_PATH_PATTERNS)


# MIME types for feed Content-Type validation (DISC-04)
FEED_CONTENT_TYPES: tuple[str, ...] = (
    "application/rss+xml",
    "application/atom+xml",
    "application/rdf+xml",
    "application/xml",
    "text/xml",
)
