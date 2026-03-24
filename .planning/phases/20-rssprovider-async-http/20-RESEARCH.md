# Phase 20: RSSProvider Async HTTP - Research

**Researched:** 2026-03-25
**Domain:** httpx.AsyncClient async HTTP patterns for RSS feed fetching
**Confidence:** HIGH

## Summary

Phase 20 requires RSSProvider to implement true async HTTP using `httpx.AsyncClient` instead of the default executor-based `run_in_executor_crawl()`. The key challenges are:
1. Converting `fetch_feed_content()` to async while maintaining conditional request support (etag/last_modified headers)
2. Running `feedparser.parse()` in thread pool executor since it's CPU-bound and not async-aware
3. Ensuring `AsyncClient` is properly closed via context manager
4. The existing `crawl_async()` in base.py provides `run_in_executor_crawl()` as default - RSSProvider must override this with true async

**Primary recommendation:** Create async `fetch_feed_content_async()` using `httpx.AsyncClient` context manager, then create `crawl_async()` that awaits both the HTTP fetch and the feedparser.parse() in executor.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 3.0.x | Async HTTP client | Drop-in async replacement for httpx.get(), supports both sync/async |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| feedparser | 6.0.x | RSS/Atom parsing | CPU-bound, must run in executor |

**Version note:** CLAUDE.md recommends httpx 0.27.x, but current pypi shows 3.0.1. The async API is stable across versions.

## Architecture Patterns

### Pattern 1: Async HTTP with Conditional Requests

**What:** Async version of fetch_feed_content with etag/last_modified support
**When to use:** When fetching feeds with cache validation
**Example:**
```python
async def fetch_feed_content_async(
    client: httpx.AsyncClient,
    url: str,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
) -> tuple[Optional[bytes], Optional[str], Optional[str], int]:
    """Fetch feed content asynchronously with conditional request support."""
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    request_headers = {**BROWSER_HEADERS, **headers}
    response = await client.get(
        url,
        headers=request_headers,
        timeout=30.0,
        follow_redirects=True
    )

    if response.status_code == 304:
        return None, None, None, 304

    response.raise_for_status()
    new_etag = response.headers.get("etag")
    new_last_modified = response.headers.get("last-modified")

    return response.content, new_etag, new_last_modified, response.status_code
```

### Pattern 2: feedparser in Thread Pool Executor

**What:** Run CPU-bound feedparser.parse() in executor to avoid blocking event loop
**When to use:** Always when parsing feeds in async context
**Example:**
```python
async def parse_feed_async(content: bytes, url: str) -> tuple[list, bool, Optional[Exception]]:
    """Parse feed in thread pool executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,  # use default executor
        _parse_feed_thread_safe,
        content,
        url
    )

def _parse_feed_thread_safe(content: bytes, url: str) -> tuple[list, bool, Optional[Exception]]:
    """Thread-safe wrapper for parse_feed."""
    return parse_feed(content, url)
```

### Pattern 3: AsyncClient Context Manager

**What:** Use `async with httpx.AsyncClient() as client:` for automatic cleanup
**When to use:** Every time you create an AsyncClient
**Example:**
```python
async def crawl_async(self, url: str) -> List[Raw]:
    """Async crawl using httpx.AsyncClient."""
    _feed_title_var.set(None)
    try:
        async with httpx.AsyncClient() as client:
            content, etag, last_modified, status_code = await fetch_feed_content_async(
                client, url
            )
            if content is None:
                logger.warning("RSS feed %s returned 304 Not Modified", url)
                return []

            # Parse in thread pool
            parsed, bozo_flag, bozo_exception = await parse_feed_async(content, url)
            if parsed.feed:
                _feed_title_var.set(parsed.feed.get("title"))

            return parsed.entries if parsed else []
    except Exception as e:
        logger.error("RSSProvider.crawl_async(%s) failed: %s", url, e)
        return []
```

### Pattern 4: Concurrent Feed Fetching with Semaphore

**What:** Use asyncio.Semaphore to limit concurrent HTTP requests
**When to use:** When fetching multiple feeds concurrently
**Example:**
```python
# From asyncio_utils.py - for fetch_all_async (Phase 21)
concurrency_limit = asyncio.Semaphore(10)

async def fetch_one_async(feed: Feed) -> dict:
    async with concurrency_limit:
        providers = discover_or_default(feed.url)
        if not providers:
            return {"new_articles": 0, "error": f"No provider for {feed.url}"}

        provider = providers[0]
        raw_items = await provider.crawl_async(feed.url)
        # ... process items
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP client | Build custom async wrapper | httpx.AsyncClient | Handles connection pooling, timeouts, redirects, HTTP/2 |
| Feed parsing in async | Call feedparser directly in async context | run_in_executor | feedparser is CPU-bound, would block event loop |
| Client lifecycle | Manual open/close | Context manager (`async with`) | Ensures cleanup on exceptions |

## Common Pitfalls

### Pitfall 1: AsyncClient Not Closed
**What goes wrong:** "Unclosed client session" warnings, connection leaks, socket exhaustion
**Why it happens:** httpx.AsyncClient maintains connection pool that must be explicitly closed
**How to avoid:** Always use `async with httpx.AsyncClient() as client:` context manager
**Warning signs:** "Unclosed client session" in logs, connection reset errors

### Pitfall 2: feedparser Blocking Event Loop
**What goes wrong:** Event loop stalls during feed parsing, async benefits lost
**Why it happens:** feedparser.parse() is CPU-bound synchronous code
**How to avoid:** Wrap in `loop.run_in_executor(None, feedparser.parse, content)`
**Warning signs:** All async tasks freeze during parse phase

### Pitfall 3: Forgetting to Await
**What goes wrong:** Coroutine not executed, empty results
**Why it happens:** `client.get()` returns coroutine, not result
**How to avoid:** Always `await client.get()` not just `client.get()`

## Code Examples

### Complete crawl_async() Implementation
```python
async def crawl_async(self, url: str) -> List[Raw]:
    """Fetch and parse RSS/Atom feed content asynchronously.

    Args:
        url: URL of the feed to crawl.

    Returns:
        List of feedparser entry dicts, or empty list on error.
    """
    _feed_title_var.set(None)
    try:
        async with httpx.AsyncClient() as client:
            content, etag, last_modified, status_code = await fetch_feed_content_async(
                client, url
            )
            if content is None:
                logger.warning("RSS feed %s returned 304 Not Modified", url)
                return []

            # Parse in thread pool to avoid blocking event loop
            loop = asyncio.get_running_loop()
            parsed = await loop.run_in_executor(
                None,
                feedparser.parse,
                content
            )

            if parsed.feed:
                _feed_title_var.set(parsed.feed.get("title"))

            entries, bozo_flag, bozo_exception = parse_feed(content, url)
            if bozo_flag and bozo_exception:
                logger.warning("Malformed feed at %s: %s", url, bozo_exception)

            logger.debug("RSSProvider.crawl_async(%s) returned %d entries", url, len(entries))
            return entries
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            logger.info("httpx returned 403 for %s, trying Scrapling fallback", url)
            return await self._crawl_with_scrapling_async(url)
        logger.error("RSSProvider.crawl_async(%s) HTTP error: %s", url, e)
        return []
    except Exception as e:
        logger.error("RSSProvider.crawl_async(%s) failed: %s", url, e)
        return []
```

### Integration with existing parse_feed()
The existing `parse_feed()` function is already thread-safe. It can be called directly in the executor:
```python
entries, bozo_flag, bozo_exception = await loop.run_in_executor(
    None,
    parse_feed,
    content,
    url
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| httpx.get() sync | httpx.AsyncClient with await | Phase 20 | True async I/O for HTTP |
| feedparser.parse() in async | run_in_executor(feedparser.parse) | Phase 20 | Non-blocking parse |
| Default run_in_executor_crawl | Override crawl_async() | Phase 20 | Direct async instead of thread wrapper |

## Open Questions

1. **Scrapling fallback in async context**
   - What we know: `_crawl_with_scrapling()` is sync, used for 403 Cloudflare fallback
   - What's unclear: Should `_crawl_with_scrapling_async()` use `asyncio.to_thread()` or be fully async?
   - Recommendation: Use `asyncio.to_thread()` for Phase 20, full async Scrapling in future phase if needed

2. **feed_meta() async version**
   - What we know: `feed_meta()` uses sync httpx.get()
   - What's unclear: Should feed_meta() also get async version?
   - Recommendation: Keep sync for now, focus on UVLP-03 only

## Environment Availability

Step 2.6: SKIPPED (no external dependencies - code changes only)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | none |
| Quick run command | `pytest tests/test_rss_provider.py -x -v` |
| Full suite command | `pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command |
|--------|----------|-----------|-------------------|
| UVLP-03 | RSSProvider.crawl_async() uses httpx.AsyncClient | unit | `pytest tests/test_rss_provider.py::test_crawl_async -x` |
| UVLP-03 | feedparser.parse() runs in executor | unit | `pytest tests/test_rss_provider.py::test_crawl_async_not_blocking -x` |
| UVLP-03 | AsyncClient properly closed | unit | `pytest tests/test_rss_provider.py::test_async_client_closed -x` |

### Wave 0 Gaps
- `tests/test_rss_provider.py` - existing test file may not cover async methods
- Check for existing: `grep -l "crawl_async" tests/`

## Sources

### Primary (HIGH confidence)
- httpx 3.0.1 documentation - AsyncClient usage patterns
- Existing `asyncio_utils.py` - run_in_executor pattern
- Existing `rss_provider.py` - current sync implementation to convert

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md` - httpx.AsyncClient lifecycle patterns (already verified)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - httpx is well-documented with stable async API
- Architecture: HIGH - patterns from asyncio_utils.py provide clear template
- Pitfalls: HIGH - documented in existing planning research

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (30 days for stable patterns)
