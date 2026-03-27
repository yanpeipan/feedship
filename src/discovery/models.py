from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class DiscoveredFeed:
    """Represents a discovered RSS/Atom/RDF feed from a website URL.

    Attributes:
        url: Absolute URL of the discovered feed.
        title: Title of the feed if available from autodiscovery link, else None.
        feed_type: Feed type string ('rss', 'atom', 'rdf') detected from type attribute.
        source: How the feed was discovered ('autodiscovery' or 'well_known_path').
        page_url: The original page URL where this feed was discovered.
    """
    url: str
    title: Optional[str]
    feed_type: str  # 'rss', 'atom', or 'rdf'
    source: str  # 'autodiscovery' or 'well_known_path'
    page_url: str  # Original page URL
