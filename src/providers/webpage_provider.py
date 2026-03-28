"""Webpage provider - renders JS-heavy pages and extracts article items via CSS selectors.

Falls back to Readability for generic article extraction.

Site-specific extraction rules are defined in config.yaml under "webpage_sites".
See docs/WebpageProvider.md for configuration format.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import List, Optional

from src.providers import PROVIDERS
from src.providers.base import Article, ContentProvider, CrawlResult, Raw

logger = logging.getLogger(__name__)


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    from urllib.parse import urlparse
    return urlparse(url).netloc


def _get_site_config(url: str) -> dict:
    """Get site config for URL from config.yaml.

    Returns the matching site's config dict, or empty dict if no match.
    """
    from src.application.config import get_webpage_sites

    domain = _extract_domain(url)
    sites = get_webpage_sites()
    for site_domain, config in sites.items():
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

    if path_segment and path_segment in site_config:
        return site_config[path_segment]
    return site_config.get("_default", {})


def _construct_article_link(item, section_config: dict) -> Optional[str]:
    """Construct article URL from item's image URL using configured pattern.

    Uses link_pattern and link_uuid_regex from section_config to build the article URL:
    1. Search item images for the configured uuid_regex
    2. If found, interpolate uuid into link_pattern

    Example config:
        link_pattern: "https://pro.example.com/article/{uuid}"
        link_uuid_regex: "/cover_image/([0-9a-f-]{36})/"

    Returns None if no pattern is configured or no UUID found.
    """
    link_pattern = section_config.get("link_pattern")
    link_uuid_regex = section_config.get("link_uuid_regex")

    if not link_pattern or not link_uuid_regex:
        return None

    imgs = item.css("img")
    for img in imgs:
        src = img.attrib.get("src", "")
        uuid_match = re.search(link_uuid_regex, src)
        if uuid_match:
            return link_pattern.replace("{uuid}", uuid_match.group(1))
    return None


def _parse_relative_date(date_str: str | None) -> Optional[str]:
    """Parse common date formats found on news sites.

    Supports:
      - "03月27日" (Chinese month-day) -> "2026-03-27"
      - "2024-12-01" (ISO date)
      - "3分钟前", "2小时前" -> today
    """
    if not date_str:
        return None
    date_str = date_str.strip()

    # "03月27日" format
    m = re.match(r"(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        now = datetime.now()
        year = now.year
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

    # "3分钟前", "2小时前" etc. -> use today
    return datetime.now().strftime("%Y-%m-%d")


class WebpageProvider:
    """Content provider for JS-rendered web pages.

    Uses Scrapling's DynamicFetcher (Playwright) to render pages with JavaScript,
    then extracts article items via CSS selectors defined in config.yaml.

    Falls back to Readability for generic single-article extraction when no
    site-specific config exists.

    Priority: 100 (higher than RSS=200, lower than GitHubReleaseProvider=300)
    """

    def __init__(self) -> None:
        self._dynamic_fetcher_initialized = False

    def match(self, url: str) -> bool:
        """Check if URL should be handled by this provider.

        Returns True for HTTP(S) URLs that are NOT obvious RSS/Atom feed paths.
        Priority ensures this is only used when no higher-priority provider matches.
        """
        if not url.startswith("http"):
            return False
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
        1. If site has config: use CSS selectors + DynamicFetcher
        2. Else: use Readability to extract single article from the page itself

        Args:
            url: URL of the page to crawl.

        Returns:
            List of raw article dicts with extracted fields.
        """
        try:
            site_config = _get_site_config(url)
            if site_config:
                items = self._crawl_impl(url)
                if items:
                    return items

            logger.debug("WebpageProvider: no site config for %s, trying Readability fallback", url)
            return self._crawl_readability(url)
        except Exception as e:
            logger.error("WebpageProvider.crawl(%s) failed: %s", url, e)
            return []

    def _crawl_impl(self, url: str) -> List[Raw]:
        """Site-specific extraction via CSS selectors and DynamicFetcher."""
        from scrapling import DynamicFetcher, Selector

        site_config = _get_site_config(url)
        section_config = _get_section_config(url, site_config)

        wait_sel = section_config.get("wait_selector", "article")
        item_sel = section_config.get("item", "article")
        title_sel = section_config.get("title")
        time_sel = section_config.get("time")
        tags_sel = section_config.get("tags")
        desc_sel = section_config.get("description")

        Fetcher = self._get_dynamic_fetcher()
        fetcher = Fetcher()

        try:
            r = fetcher.fetch(url, timeout=30000, wait_selector=wait_sel)
        except Exception as e:
            logger.warning(
                "DynamicFetcher.fetch(%s) with wait_selector=%s failed: %s, retrying without...",
                url, wait_sel, e,
            )
            r = fetcher.fetch(url, timeout=30000)

        body = r.body.decode("utf-8", errors="replace") if isinstance(r.body, bytes) else str(r.body)
        root = Selector(body)

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
            # Try explicit link selector first
            link_els = item.css("a")
            if link_els:
                link = link_els[0].attrib.get("href")
            # Fall back to generic link construction via UUID pattern
            if not link:
                link = _construct_article_link(item, section_config)

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
                "link": link,
                "pub_date": pub_date,
                "tags": tags,
                "description": description,
                "source_url": url,
            })

        return results

    def _crawl_readability(self, url: str) -> List[Raw]:
        """Fallback: use Readability to extract article content from a single page.

        When no site config exists for a URL, this treats the URL itself as
        an article page and extracts its title/content for storage.
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
            try:
                from lxml.html import fromstring
                root = fromstring(content)
                text_content = root.text_content()
                description = text_content.strip()[:500] if text_content else None
            except Exception:
                description = re.sub(r"<[^>]+>", "", content).strip()[:500]
        else:
            description = None

        if not title:
            return []

        return [{
            "title": title,
            "link": url,
            "pub_date": datetime.now().strftime("%Y-%m-%d"),
            "tags": [],
            "description": description,
            "source_url": url,
        }]

    async def crawl_async(self, url: str, etag: Optional[str] = None, last_modified: Optional[str] = None) -> CrawlResult:
        """Async crawl using asyncio.to_thread for the blocking DynamicFetcher."""
        import asyncio

        _ = etag, last_modified
        loop = asyncio.get_running_loop()
        try:
            entries = await loop.run_in_executor(None, self.crawl, url)
        except Exception as e:
            logger.error("WebpageProvider.crawl_async(%s) failed: %s", url, e)
            entries = []
        return CrawlResult(entries=entries)

    def parse(self, raw: Raw) -> Article:
        """Convert raw dict to Article dict."""
        from src.utils import generate_article_id

        title = raw.get("title")
        link = raw.get("link")
        guid = generate_article_id(raw) if not link else link
        pub_date = raw.get("pub_date")
        description = raw.get("description")
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
        """Fetch page and extract feed metadata (title)."""
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
