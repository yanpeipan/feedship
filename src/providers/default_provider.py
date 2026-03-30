"""Default provider - fallback only, never matches directly.

This provider is used when no other provider matches a URL.
match() returns False so it never matches URLs directly,
and priority() returns 0 so it's only tried after all other
providers have failed.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from src.providers import PROVIDERS
from src.providers.base import Article, FetchedResult, Raw

if TYPE_CHECKING:
    from scrapling.engines.toolbelt.custom import Response

    from src.discovery.models import DiscoveredFeed
    from src.models import FeedType


class DefaultProvider:
    """Fallback provider for unknown URL types.

    This provider never matches URLs directly. It is only used when
    no other provider matches a URL. The crawl() and parse() methods
    should not be called on this provider in practice.
    """

    def match(self, url: str, response: Response = None, feed_type: FeedType = None) -> bool:
        """Never matches - only used as fallback.

        Args:
            url: URL to match (ignored).
            response: Optional HTTP response (ignored).
            feed_type: Optional FeedType (ignored).

        Returns:
            Always False - this provider is only a fallback.
        """
        return False

    def priority(self) -> int:
        """Lowest priority - only tried when all else fails.

        Returns:
            0 (lowest priority).
        """
        return 0

    def fetch_articles(self, feed: Feed) -> FetchedResult:
        """Not implemented - should not be called.

        This provider is only used as fallback when no other provider
        matches. If called, it indicates a bug in provider selection.

        Args:
            feed: Feed object (ignored).

        Returns:
            Never returns - raises NotImplementedError.
        """
        raise NotImplementedError(
            "DefaultProvider is fallback only and should not be called"
        )

    def parse_articles(self, entries: list[Raw]) -> list[Article]:
        """Not implemented - should not be called.

        Args:
            entries: Raw content list (ignored).

        Returns:
            Never returns - raises NotImplementedError.
        """
        raise NotImplementedError(
            "DefaultProvider is fallback only and should not be called"
        )

    def parse_feed(self, url: str, response: Response = None) -> DiscoveredFeed:
        """DefaultProvider is fallback only - always returns invalid.

        Args:
            url: URL to parse feed for (ignored).
            response: Ignored.

        Returns:
            DiscoveredFeed with valid=False (fallback provider).
        """
        return DiscoveredFeed(
            url=url,
            title=None,
            feed_type="unknown",
            source=f"provider_{self.__class__.__name__}",
            page_url=url,
            valid=False,
        )

    def discover(self, url: str, response: Response = None, depth: int = 1) -> list[DiscoveredFeed]:
        """Not implemented - DefaultProvider is fallback only.

        Args:
            url: URL to discover feeds for (ignored).
            response: Ignored.
            depth: Ignored.

        Returns:
            Never returns - raises NotImplementedError.
        """
        raise NotImplementedError(
            "DefaultProvider is fallback only and should not be called"
        )

# Register this provider - it will be sorted last by priority()
PROVIDERS.append(DefaultProvider())
