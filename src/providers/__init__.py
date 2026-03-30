"""Provider registry and dynamic loading for the plugin architecture.

Discovers and loads all *_provider.py modules from src/providers/ directory,
sorted by priority. Provides discover() function for provider lookup.
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.discovery.models import DiscoveredFeed
from src.providers.base import ContentProvider

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response

    from src.models import FeedType

logger = logging.getLogger(__name__)

# Discovered providers, populated at import time
PROVIDERS: list[ContentProvider] = []


def load_providers() -> None:
    """Load all providers from src/providers/ directory.

    Discovers *_provider.py files, imports each module (which triggers
    self-registration via PROVIDERS.append()), then sorts providers
    by priority descending.

    Excludes __init__.py and base.py from loading.
    """
    providers_dir = Path(__file__).parent

    # Find all provider modules (exclude __init__ and base)
    provider_files = sorted(providers_dir.glob("*_provider.py"))
    logger.debug("Found provider files: %s", [f.stem for f in provider_files])

    for filepath in provider_files:
        module_name = filepath.stem
        if module_name in ("__init__", "base"):
            continue

        full_module = f"src.providers.{module_name}"
        try:
            importlib.import_module(full_module)
            logger.debug("Loaded provider module: %s", full_module)
        except Exception:
            logger.exception("Failed to load provider %s", full_module)

    # Sort by priority descending (higher priority first)
    PROVIDERS.sort(key=lambda p: p.priority(), reverse=True)
    logger.info("Loaded %d providers", len(PROVIDERS))


def discover(
    url: str,
    response: Response = None,
    depth: int = 1,
    discover: bool = True,
    feed_type: FeedType = None,
) -> list[DiscoveredFeed]:
    """Find and fetch feeds from providers matching a URL.

    Args:
        url: URL to match against providers.
        response: Optional HTTP response from discovery phase.
            If provided, match() uses content_type from response.
            If None, match() only uses URL.
        depth: Current crawl depth (1 = initial URL, can make HTTP requests;
               >1 = BFS deeper, should use response only if available).
        discover: Whether to run provider discovery (default: True).
        feed_type: Optional FeedType to restrict provider matching.

    Returns:
        List of DiscoveredFeed from matching providers sorted by priority.
        Both parse_feed() and discover() return feeds with valid field set appropriately.
        Callers should filter by valid=True for confirmed feeds.
    """
    matched = [p for p in PROVIDERS if p.match(url, response, feed_type)]
    feeds = []
    seen = set()
    for provider in matched:
        # Validate URL via parse_feed (returns DiscoveredFeed with valid set appropriately)
        discovered = provider.parse_feed(url, response)
        if discovered and discovered.valid and discovered.url not in seen:
            seen.add(discovered.url)
            feeds.append(discovered)

        # Discover additional feeds if enabled
        if discover:
            try:
                discovered_list = provider.discover(url, response, depth)
                # Validate discovered feeds in parallel using ThreadPoolExecutor
                import concurrent.futures

                def _validate_one(
                    feed: DiscoveredFeed, *, provider: ContentProvider = provider
                ) -> DiscoveredFeed | None:
                    if feed.url in seen:
                        return None
                    try:
                        return provider.parse_feed(feed.url, None)
                    except Exception:
                        return None

                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [
                        executor.submit(_validate_one, f) for f in discovered_list
                    ]
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            validated = future.result()
                            if validated and validated.valid:
                                seen.add(validated.url)
                                feeds.append(validated)
                        except Exception:
                            pass
            except Exception:
                pass
    return feeds


def get_all_providers() -> list[ContentProvider]:
    """Return all loaded providers sorted by priority.

    Returns:
        All providers in PROVIDERS list (already sorted by priority descending).
    """
    return PROVIDERS


def match(
    url: str, response: Response = None, feed_type: FeedType = None
) -> list[ContentProvider]:
    """Find providers matching a URL.

    Args:
        url: URL to match against providers.
        response: Optional HTTP response from discovery phase.
            If provided, match() uses content_type from response.
            If None, match() only uses URL.
        feed_type: Optional FeedType to restrict provider matching.

    Returns:
        List of ContentProvider that match this URL, sorted by priority descending.
    """
    return [p for p in PROVIDERS if p.match(url, response, feed_type)]


def match_first(
    url: str, response: Response = None, feed_type: FeedType = None
) -> ContentProvider | None:
    """Return first (highest priority) provider matching URL, or None.

    Args:
        url: URL to match against providers.
        response: Optional HTTP response from discovery phase.
        feed_type: Optional FeedType to restrict provider matching.

    Returns:
        Highest priority ContentProvider matching URL, or None if no match.
    """
    matched = match(url, response, feed_type)
    return matched[0] if matched else None


# Load providers at module import time
load_providers()
