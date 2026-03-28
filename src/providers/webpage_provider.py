"""Webpage provider - renders JS-heavy pages and extracts article items via CSS selectors.

Falls back to Readability for generic article extraction.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional

from src.providers import PROVIDERS
from src.providers.base import Article, ContentProvider, CrawlResult, Raw

logger = logging.getLogger(__name__)

# Site-specific configurations: domain -> section -> selectors
# When a site has no matching section, "_default" is used.
# When link is None, article URL is constructed via _construct_article_link().
SITE_CONFIGS: dict[str, dict] = {
    "jiqizhixin.com": {
        "_default": {
            "wait_selector": ".home__article-item",
            "item": ".home__article-item",
            "title": ".home__article-item__title",
            "time": ".home__article-item__time",
            "tags": ".home__article-item__tag-item",
            "description": None,
            "link": None,
        },
        "articles": {
            "wait_selector": ".article-card",
            "item": ".article-card",
            "title": ".article-card__title",
            "time": ".article-card__time",
            "tags": ".article-card__tags > div",
            "description": None,
            "link": None,
        },
    },
    # Add more sites here as needed:
    # "36kr.com": {
    #     "_default": {
    #         "wait_selector": ".article-item",
    #         "item": ".article-item",
    #         "title": ".title",
    #         "time": ".time",
    #         "tags": ".tag",
    #         "description": ".desc",
    #         "link": "a[href]",
    #     },
    # },
}


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    return urlparse(url).netloc


def _get_site_config(url: str) -> dict:
    """Get site config for URL, return default if not found."""
    domain = _extract_domain(url)
    for site_domain, config in SITE_CONFIGS.items():
        if site_domain in domain:
            return config
    return {}


def _get_section_config(url: str, site_config: dict) -> dict:
    """Get the most specific section config for a URL.

    Matches URL path against section keys (e.g. "articles", "repos").
    Falls back to "_default" if no path match found.
    """
    if not site_config:
        return {}

    from urllib.parse import urlparse
    path = urlparse(url).path.strip("/")
    path_segment = path.split("/")[0] if path else ""

    # Try path segment match first
    if path_segment and path_segment in site_config:
        return site_config[path_segment]
    # Fall back to _default
    return site_config.get("_default", {})


def _construct_article_link(page_url: str, item, root, section_config: dict) -> Optional[str]:
    """Try to construct article URL from the item's own image.

    For jiqizhixin.com, articles use /article/{uuid} pattern.
    UUIDs are extracted from the article cover image inside each item.
    """
    domain = _extract_domain(page_url)
    if 'jiqizhixin' in domain:
        # Image inside item: https://image.jiqizhixin.com/uploads/article/cover_image/{uuid}/...
        imgs = item.css('img')
        for img in imgs:
            src = img.attrib.get('src', '')
            uuid_match = re.search(r'/article/cover_image/([0-9a-f-]{36})/', src)
            if uuid_match:
                return f"https://www.jiqizhixin.com/article/{uuid_match.group(1)}"
    return None


def _parse_relative_date(date_str: str | None) -> Optional[str]:
    """Parse Chinese date formats like '03月27日' to ISO format."""
    if not date_str:
        return None
    date_str = date_str.strip()

    # "03月27日" format
    m = re.match(r"(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        now = datetime.now()
        year = now.year
        # If month < current month, assume last year
        if month > now.month:
            year -= 1
        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")

    # "2023-12-01" format
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.isoformat()
    except ValueError:
        pass

    # "3分钟前", "2小时前" etc - just use today
    return datetime.now().strftime("%Y-%m-%d")


class WebpageProvider:
    """Content provider for JS-rendered web pages.

    Uses Scrapling's DynamicFetcher (Playwright) to render pages with JavaScript,
    then extracts article items via CSS selectors. Falls back to Readability
    for generic article extraction.

    Priority: 100 (higher than RSS=50, lower than GitHub=200)
    """

    def __init__(self) -> None:
        self._dynamic_fetcher_initialized = False

    def match(self, url: str) -> bool:
        """Check if URL should be handled by this provider.

        Returns True for HTTP(S) URLs that are NOT obvious RSS/Atom feed paths.
        Provider priority (100) ensures it is only used when no higher-priority
        provider (GitHubReleaseProvider/RSSProvider) matches.

        Priority ordering:
          300 - GitHubReleaseProvider (github.com)
          200 - RSSProvider (RSS/Atom feeds)
          100 - WebpageProvider (generic web pages)
        """
        if not url.startswith("http"):
            return False
        # Exclude obvious RSS/Atom feed paths - these are handled by RSSProvider (200)
        lower = url.lower()
        if any(ext in lower for ext in (
            ".rss", ".atom", "/feed", "/feed.xml",
            "/atom.xml", "/rss.xml", "/index.xml",
        )):
            return False
        return True

    def priority(self) -> int:
        return 100

    def _get_dynamic_fetcher(self):
        """Lazy-load DynamicFetcher to avoid startup cost."""
        if not self._dynamic_fetcher_initialized:
            from scrapling import DynamicFetcher
            self._DynamicFetcher = DynamicFetcher
            self._dynamic_fetcher_initialized = True
        return self._DynamicFetcher

    def crawl(self, url: str) -> List[Raw]:
        """Fetch and parse a web page, extracting article items.

        Strategy:
        1. If site has SITE_CONFIG: use CSS selectors + DynamicFetcher
        2. Else: use Readability to extract single article from the page itself

        Args:
            url: URL of the page to crawl.

        Returns:
            List of raw article dicts with extracted fields.
        """
        try:
            # Step 1: try site-specific extraction
            site_config = _get_site_config(url)
            if site_config:
                items = self._crawl_impl(url)
                if items:
                    return items

            # Step 2: Readability fallback — extract single article from page itself
            logger.debug("WebpageProvider: no site config for %s, trying Readability fallback", url)
            return self._crawl_readability(url)
        except Exception as e:
            logger.error("WebpageProvider.crawl(%s) failed: %s", url, e)
            return []

    def _crawl_impl(self, url: str) -> List[Raw]:
        """Internal crawl implementation."""
        from scrapling import DynamicFetcher, Selector

        # Get site config
        site_config = _get_site_config(url)
        section_config = _get_section_config(url, site_config)
        wait_sel = section_config.get("wait_selector", "article")
        item_sel = section_config.get("item", "article")
        title_sel = section_config.get("title")
        time_sel = section_config.get("time")
        tags_sel = section_config.get("tags")
        desc_sel = section_config.get("description")
        link_sel = section_config.get("link")

        # Fetch with JS rendering
        Fetcher = self._get_dynamic_fetcher()
        fetcher = Fetcher()

        try:
            r = fetcher.fetch(url, timeout=30000, wait_selector=wait_sel)
        except Exception as e:
            logger.warning("DynamicFetcher.fetch(%s) with wait_selector=%s failed: %s, retrying without...", url, wait_sel, e)
            r = fetcher.fetch(url, timeout=30000)

        body = r.body.decode("utf-8", errors="replace") if isinstance(r.body, bytes) else str(r.body)
        root = Selector(body)

        # Extract article items
        items = root.css(item_sel)
        logger.debug("WebpageProvider found %d items with selector '%s'", len(items), item_sel)

        results = []
        for item in items:
            title = None
            if title_sel:
                title_els = item.css(title_sel)
                if title_els:
                    title = title_els[0].text.strip() if title_els[0].text else None

            link = None
            if link_sel:
                link_els = item.css(link_sel)
                if link_els:
                    link = link_els[0].attrib.get("href")
            if not link:
                # Try to find any anchor inside the item
                anchors = item.css("a")
                if anchors:
                    link = anchors[0].attrib.get("href")

            pub_date = None
            if time_sel:
                time_els = item.css(time_sel)
                if time_els:
                    pub_date = _parse_relative_date(time_els[0].text)

            tags = []
            if tags_sel:
                tag_els = item.css(tags_sel)
                tags = [t.text.strip() for t in tag_els if t.text]

            description = None
            if desc_sel:
                desc_els = item.css(desc_sel)
                if desc_els and desc_els[0].text:
                    description = desc_els[0].text.strip()

            if not title:
                continue

            results.append({
                "title": title,
                "link": link or _construct_article_link(url, item, root, section_config),
                "pub_date": pub_date,
                "tags": tags,
                "description": description,
                "source_url": url,
            })

        return results

    def _crawl_readability(self, url: str) -> List[Raw]:
        """Fallback: use Readability to extract article content from a single page.

        When no SITE_CONFIG exists for a URL, this treats the URL itself as
        an article page and extracts its title/content for storage.
        The page is still rendered via DynamicFetcher (JS-aware) first.

        Returns:
            List containing a single Raw dict (or empty list on failure).
        """
        from scrapling import DynamicFetcher

        Fetcher = self._get_dynamic_fetcher()
        fetcher = Fetcher()

        try:
            r = fetcher.fetch(url, timeout=30000)
        except Exception as e:
            logger.warning("Readability fallback: DynamicFetcher failed for %s: %s", url, e)
            return []

        body = r.body.decode("utf-8", errors="replace") if isinstance(r.body, bytes) else str(r.body)

        try:
            from readability import Document
        except ImportError:
            logger.warning("Readability not installed, cannot extract content for %s", url)
            return []

        try:
            doc = Document(body, url=url)
        except Exception as e:
            logger.warning("Readability parsing failed for %s: %s", url, e)
            return []

        title = doc.short_title() or None
        content = doc.summary() if hasattr(doc, "summary") else None
        if content:
            # Strip HTML tags using lxml (already a scrapling dependency)
            try:
                from lxml.html import fromstring, tostring
                root = fromstring(content)
                text_content = root.text_content()
                description = text_content.strip()[:500] if text_content else None
            except Exception:
                # Fallback: strip tags with regex
                import re
                description = re.sub(r"<[^>]+>", "", content).strip()[:500]
        else:
            description = None

        if not title:
            return []

        return [{
            "title": title,
            "link": url,  # The URL itself is the article
            "pub_date": datetime.now().strftime("%Y-%m-%d"),
            "tags": [],
            "description": description,
            "source_url": url,
        }]

    async def crawl_async(self, url: str, etag: Optional[str] = None, last_modified: Optional[str] = None) -> CrawlResult:
        """Async crawl using asyncio.to_thread for the blocking DynamicFetcher."""
        import asyncio

        _ = etag, last_modified  # Not used for webpage provider
        loop = asyncio.get_running_loop()
        try:
            entries = await loop.run_in_executor(None, self.crawl, url)
        except Exception as e:
            logger.error("WebpageProvider.crawl_async(%s) failed: %s", url, e)
            entries = []
        return CrawlResult(entries=entries)

    def parse(self, raw: Raw) -> Article:
        """Convert raw dict to Article dict.

        Args:
            raw: Raw article dict from crawl().

        Returns:
            Article dict.
        """
        from src.utils import generate_article_id

        title = raw.get("title")
        link = raw.get("link")
        guid = generate_article_id(raw) if not link else link
        pub_date = raw.get("pub_date")
        description = raw.get("description")
        # For Readability fallback, raw contains actual article HTML content.
        # For list extraction, raw contains description (already text).
        content = raw.get("content") or raw.get("description")

        return Article(
            title=title,
            link=link,
            guid=guid,
            pub_date=pub_date,
            description=description,
            content=content,
        )

    def feed_meta(self, url: str) -> "Feed":
        """Fetch page and extract feed metadata (title).

        Args:
            url: URL of the page.

        Returns:
            Feed object with name populated from page title.
        """
        from src.models import Feed
        from src.application.config import get_timezone

        try:
            from scrapling import DynamicFetcher, Selector
        except ImportError:
            raise ValueError("scrapling is required for WebpageProvider. Install with: pip install radar[webpage]")

        Fetcher = self._get_dynamic_fetcher()
        fetcher = Fetcher()

        try:
            r = fetcher.fetch(url, timeout=30000)
        except Exception as e:
            logger.warning("feed_meta fetch failed for %s: %s, using URL as title", url, e)
            title = url
        else:
            body = r.body.decode("utf-8", errors="replace") if isinstance(r.body, bytes) else str(r.body)
            root = Selector(body)
            title_el = root.css("title")
            title = title_el[0].text.strip() if title_el and title_el[0].text else url
            # Clean up title (remove site name suffix)
            title = re.sub(r"\s*[-–|]\s*[^-|]+$", "", title).strip()

        now = datetime.now(get_timezone()).isoformat()
        return Feed(
            id="",
            name=title,
            url=url,
            etag=None,
            last_modified=None,
            last_fetched=now,
            created_at=now,
        )


# Register this provider
PROVIDERS.append(WebpageProvider())
