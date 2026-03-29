"""Provider registry and dynamic loading for the plugin architecture.

Discovers and loads all *_provider.py modules from src/providers/ directory,
sorted by priority. Provides discover() function for provider lookup.
"""
from __future__ import annotations

import glob
import importlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional

from src.providers.base import ContentProvider
from src.discovery.models import DiscoveredFeed

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response

logger = logging.getLogger(__name__)

# Discovered providers, populated at import time
PROVIDERS: List[ContentProvider] = []


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


def discover(url: str, response: "Response" = None, depth: int = 1, discover: bool = True) -> List["DiscoveredFeed"]:
    """Find and fetch feeds from providers matching a URL.

    Args:
        url: URL to match against providers.
        response: Optional HTTP response from discovery phase.
            If provided, match() uses content_type from response.
            If None, match() only uses URL.
        depth: Current crawl depth (1 = initial URL, can make HTTP requests;
               >1 = BFS deeper, should use response only if available).
        discover: Whether to run provider discovery (default: True).
            When False, only uses parse_feed() for validation.

    Returns:
        List of DiscoveredFeed from matching providers sorted by priority.
        Empty list if no providers match or all discover() calls return empty.
    """
    matched = [p for p in PROVIDERS if p.match(url, response)]
    feeds = []
    seen = set()
    for provider in matched:
        # Validate URL via parse_feed (returns DiscoveredFeed)
        try:
            discovered = provider.parse_feed(url, response)
            if discovered and discovered.url not in seen:
                seen.add(discovered.url)
                feeds.append(discovered)
        except Exception:
            pass

        # Discover additional feeds if enabled
        if discover:
            try:
                discovered = provider.discover(url, response, depth)
                for feed in discovered:
                    if feed.url not in seen:
                        seen.add(feed.url)
                        feeds.append(feed)
            except Exception:
                pass
    return feeds


def get_all_providers() -> List[ContentProvider]:
    """Return all loaded providers sorted by priority.

    Returns:
        All providers in PROVIDERS list (already sorted by priority descending).
    """
    return PROVIDERS


# Load providers at module import time
load_providers()