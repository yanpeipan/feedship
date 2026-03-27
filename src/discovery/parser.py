"""HTML link element parser for feed autodiscovery (DISC-01, DISC-03)."""
from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.discovery.models import DiscoveredFeed


def resolve_url(page_url: str, href: str, base_href: str | None = None) -> str:
    """Resolve a relative URL to an absolute URL.

    Args:
        page_url: The original page URL.
        href: The href attribute value (may be relative or absolute).
        base_href: Optional <base href> override from page head.

    Returns:
        Absolute URL string.
    """
    if base_href:
        return urljoin(base_href, href)
    return urljoin(page_url, href)


def extract_feed_type(content_type: str) -> str | None:
    """Extract feed type from Content-Type string.

    Args:
        content_type: Content-Type header value.

    Returns:
        'rss', 'atom', 'rdf' or None if not a feed type.
    """
    ct_lower = content_type.lower()
    if 'rss' in ct_lower:
        return 'rss'
    if 'atom' in ct_lower:
        return 'atom'
    if 'rdf' in ct_lower:
        return 'rdf'
    return None


def parse_link_elements(html: str, page_url: str) -> list[DiscoveredFeed]:
    """Parse HTML for autodiscovery <link> tags in <head>.

    Args:
        html: Raw HTML content of the page.
        page_url: The URL the HTML was fetched from (for URL resolution).

    Returns:
        List of DiscoveredFeed objects found via autodiscovery.
    """
    feeds: list[DiscoveredFeed] = []

    soup = BeautifulSoup(html, 'lxml')

    # Find <head> element
    head = soup.find('head')
    if not head:
        return feeds

    # Check for <base href=""> override in <head>
    base_tag = head.find('base', href=True)
    base_href: str | None = base_tag.get('href') if base_tag else None

    # Find all <link> tags in <head> with rel="alternate"
    for link in head.find_all('link'):
        rel = link.get('rel', '')
        # Handle rel as either string or list
        if isinstance(rel, list):
            rel_values = [r.lower() for r in rel]
        else:
            rel_values = [rel.lower()]

        if 'alternate' not in rel_values:
            continue

        href = link.get('href')
        if not href:
            continue

        link_type = link.get('type', '')
        feed_type = extract_feed_type(link_type)
        if not feed_type:
            continue

        # Resolve URL (handles relative URLs and base href override)
        absolute_url = resolve_url(page_url, href, base_href)

        # Extract title if present
        title: Optional[str] = link.get('title')

        feeds.append(DiscoveredFeed(
            url=absolute_url,
            title=title,
            feed_type=feed_type,
            source='autodiscovery',
            page_url=page_url,
        ))

    return feeds
