# Provider System

## Provider Interface

```python
class ContentProvider(Protocol):
    def match(self, url: str) -> bool:
        """Return True if this provider handles the URL."""

    def priority(self) -> int:
        """Higher = tried first. Default RSS returns 50."""

    def crawl(self, url: str) -> List[Raw]:
        """Fetch raw content from URL. Return list of raw items (may be empty)."""

    def parse(self, raw: Raw) -> Article:
        """Convert raw item to Article dict."""

    def feed_meta(self, url: str) -> FeedMeta:
        """Fetch feed metadata (title, etag) WITHOUT crawling full content. Raises if unavailable."""

    def tag_parsers(self) -> List[TagParser]:
        """Return tag parsers for articles from this provider."""
```

**Key improvement:** `feed_meta()` must NOT call `crawl()` - it should only fetch headers or a lightweight HEAD request to get metadata.

**Article dict shape:**
```python
{
    "title": str,
    "link": str,
    "guid": str,
    "pub_date": str | None,   # ISO 8601
    "description": str | None,
    "content": str | None,
}
```

## TagParser Interface

```python
class TagParser(Protocol):
    def parse_tags(self, article: Article) -> List[str]:
        """Return tags for this article."""
```

Tag merging: union of all tags from all tag parsers, deduplicated.
`['a', 'b'] + ['a', 'c'] = ['a', 'b', 'c']`

## Provider Registration

Providers register themselves by appending to `PROVIDERS` list in `src/providers/__init__.py`. Each provider class is instantiated once at module load time.

**Rule: Providers must not import each other** (avoid circular deps). Shared logic goes in `src/providers/base.py`.

## Default RSS Provider

- `match(url)` returns `False` (only matched as fallback)
- When no provider matches: `discover_or_default` returns `[default_rss_provider]`
- `priority()` returns `50` (lowest; providers with higher priority are tried first)
- `feed_meta()` does lightweight HEAD request only, NOT full crawl()
