# Architecture Research: uvloop Async Concurrency Integration

**Domain:** RSS reader CLI with async fetch concurrency
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Executive Summary

The v1.5 milestone introduces uvloop for concurrent feed fetching. The current `fetch --all` command processes feeds sequentially, creating a bottleneck when handling 10+ feeds. This architecture document maps how uvloop integrates with the existing provider plugin architecture while maintaining SQLite write serialization.

## Current Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer (click)                         │
├─────────────────────────────────────────────────────────────────┤
│  feed.py: fetch --all → feed_refresh                            │
│  crawl.py: crawl <url>                                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   Application Layer                               │
├─────────────────────────────────────────────────────────────────┤
│  feed.py: fetch_one(), fetch_all()                              │
│  crawl.py: crawl_url()                                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Provider Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  base.py: ContentProvider protocol                               │
│  rss_provider.py: RSSProvider.crawl() [sync httpx]             │
│  github_release_provider.py: GitHubReleaseProvider.crawl()      │
│  default_provider.py: DefaultProvider.crawl()                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Storage Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  sqlite.py: store_article(), get_db() [serial writes]           │
└─────────────────────────────────────────────────────────────────┘
```

### Current Fetch Flow (Sequential)

```
fetch --all (CLI)
    ↓
fetch_all() [feed.py:193]
    ↓ (sequential loop over feeds)
for feed_obj in feeds:
    ↓
    fetch_one(feed_obj) [feed.py:117]
        ↓
        provider = discover_or_default(feed.url)[0]
        ↓
        raw_items = provider.crawl(feed.url)  ←── sync httpx.get()
        ↓
        for raw in raw_items:
            store_article(...)  ←── serial SQLite write
```

### Provider Interface (Current)

```python
class ContentProvider(Protocol):
    def match(self, url: str) -> bool: ...
    def priority(self) -> int: ...
    def crawl(self, url: str) -> List[Raw]: ...  # Currently sync
    def parse(self, raw: Raw) -> Article: ...
    def feed_meta(self, url: str) -> Feed: ...   # Currently sync
```

## Target Architecture (Concurrent)

### System Overview with uvloop

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer (click)                         │
├─────────────────────────────────────────────────────────────────┤
│  feed.py: fetch --all → uvloop.run(fetch_all_async())          │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   Application Layer (async)                      │
├─────────────────────────────────────────────────────────────────┤
│  feed.py: fetch_one_async(), fetch_all_async()                  │
│  crawl.py: crawl_url_async()                                    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                 Provider Layer (async variants)                  │
├─────────────────────────────────────────────────────────────────┤
│  base.py: ContentProvider protocol + crawl_async() default       │
│  rss_provider.py: RSSProvider.crawl_async() [httpx.AsyncClient]  │
│  github_release_provider.py: GitHubReleaseProvider.crawl_async() │
│  default_provider.py: DefaultProvider.crawl_async()              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Storage Layer                                │
├─────────────────────────────────────────────────────────────────┤
│  sqlite.py: store_article() [called from asyncio.to_thread]      │
└─────────────────────────────────────────────────────────────────┘
```

### New Async Fetch Flow

```
fetch --all (CLI)
    ↓
uvloop.install()  ←── once at app startup
    ↓
asyncio.run(fetch_all_async())  ←── or uvloop.run()
    ↓
fetch_all_async():
    feeds = list_feeds()
    semaphore = asyncio.Semaphore(10)  ←── configurable concurrency
    tasks = [
        fetch_one_async(feed, semaphore)
        for feed in feeds
    ]
    results = await asyncio.gather(*tasks)  ←── concurrent fetch
    ↓
    gather results, update totals
    ↓
    await asyncio.gather(*write_tasks)  ←── serial writes via to_thread
```

## Integration Points

### 1. CLI Entry Point

**File:** `src/cli/feed.py` (fetch command)

**NEW:** Add uvloop.run() wrapper for async fetch.

```python
# Option: Wrapper (simpler, no click async complexity)
@cli.command("fetch")
@click.option("--all", "do_fetch_all", is_flag=True)
@click.pass_context
def fetch(ctx: click.Context, do_fetch_all: bool):
    if do_fetch_all:
        import uvloop
        uvloop.run(fetch_all_async())
```

**Decision:** uvloop.run() wrapper is simpler and avoids click's async edge cases.

### 2. Application Layer (feed.py)

**NEW:** `fetch_one_async()` and `fetch_all_async()` functions.

```python
async def fetch_one_async(feed: Feed, semaphore: asyncio.Semaphore) -> dict:
    """Async fetch with semaphore-controlled concurrency."""
    async with semaphore:
        providers = discover_or_default(feed.url)
        if not providers:
            return {"new_articles": 0, "error": f"No provider for {feed.url}"}

        provider = providers[0]
        raw_items = await provider.crawl_async(feed.url)  # NEW: async method

        # SQLite writes remain serial via asyncio.to_thread
        write_tasks = []
        for raw in raw_items:
            article = provider.parse(raw)
            # Schedule serial write
            write_tasks.append(asyncio.to_thread(store_article, ...))

        await asyncio.gather(*write_tasks)
        return {"new_articles": len(raw_items)}

async def fetch_all_async() -> dict:
    """Concurrent fetch for all feeds."""
    feeds = list_feeds()
    semaphore = asyncio.Semaphore(10)  # Configurable

    tasks = [fetch_one_async(feed, semaphore) for feed in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate results...
```

### 3. Provider Protocol Extension

**File:** `src/providers/base.py`

**NEW:** Add optional `crawl_async()` method to protocol with default implementation.

```python
@runtime_checkable
class ContentProvider(Protocol):
    # Existing sync methods...
    def crawl(self, url: str) -> List[Raw]: ...

    # NEW: async variant with default implementation
    async def crawl_async(self, url: str) -> List[Raw]:
        """Async fetch. Default impl runs sync crawl() in thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.crawl, url)
```

**Design decision:** Provide default implementation that wraps sync `crawl()` in `asyncio.to_thread()`. This allows:
- Gradual migration: providers without explicit `crawl_async` still work
- Backward compatibility: sync code continues to function

### 4. RSS Provider Async Variant

**File:** `src/providers/rss_provider.py`

**NEW:** Add `crawl_async()` using `httpx.AsyncClient`.

```python
async def fetch_feed_content_async(
    url: str,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
) -> tuple[Optional[bytes], Optional[str], Optional[str], int]:
    """Async feed fetch with conditional request support."""
    headers: dict[str, str] = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    request_headers = {**BROWSER_HEADERS, **headers}

    # NEW: httpx.AsyncClient context
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=request_headers,
            timeout=30.0,
            follow_redirects=True
        )

    if response.status_code == 304:
        return None, None, None, 304

    response.raise_for_status()
    return response.content, response.headers.get("etag"), response.headers.get("last-modified"), response.status_code

class RSSProvider:
    async def crawl_async(self, url: str) -> List[Raw]:
        """Async crawl using httpx.AsyncClient."""
        _feed_title_var.set(None)
        try:
            content, etag, last_modified, status_code = await fetch_feed_content_async(url)
            if content is None:
                return []

            parsed = feedparser.parse(content)
            if parsed.feed:
                _feed_title_var.set(parsed.feed.get("title"))

            entries, bozo_flag, bozo_exception = parse_feed(content, url)
            return entries
        except Exception as e:
            logger.error("RSSProvider.crawl_async(%s) failed: %s", url, e)
            return []
```

### 5. GitHub Release Provider Async Variant

**File:** `src/providers/github_release_provider.py`

**NEW:** Add `crawl_async()` using `asyncio.to_thread()` for PyGithub (sync).

```python
class GitHubReleaseProvider:
    async def crawl_async(self, url: str) -> List[Raw]:
        """Async crawl. PyGithub is sync, so run in thread."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.crawl, url)
```

### 6. SQLite Storage Layer

**File:** `src/storage/sqlite.py`

**NEW:** No changes required. SQLite writes are already called via `asyncio.to_thread()` from the async functions. The `store_article()` function is already thread-safe via connection-per-call pattern.

**Key insight:** Using `asyncio.to_thread()` for every write serializes them due to SQLite locking. The semaphore controls network I/O concurrency, not write concurrency.

## Component Changes Summary

| File | Change Type | Purpose |
|------|-------------|---------|
| `src/cli/feed.py` | MODIFY | Add `uvloop.run()` wrapper for async fetch |
| `src/application/feed.py` | ADD | `fetch_one_async()`, `fetch_all_async()` |
| `src/providers/base.py` | MODIFY | Add optional `crawl_async()` to protocol with default impl |
| `src/providers/rss_provider.py` | MODIFY | Add `crawl_async()`, `fetch_feed_content_async()` |
| `src/providers/github_release_provider.py` | MODIFY | Add `crawl_async()` wrapper |
| `src/providers/default_provider.py` | MODIFY | Add `crawl_async()` wrapper |
| `src/application/crawl.py` | MODIFY | Add `crawl_url_async()` variant if parallel URL fetching needed |
| `pyproject.toml` | MODIFY | Add `uvloop` dependency |

## Build Order (Considering Dependencies)

```
Phase 1: Dependency + Protocol
  1. Add uvloop to pyproject.toml
  2. Add crawl_async() to ContentProvider protocol with default implementation

Phase 2: Core Async Application
  3. Add fetch_feed_content_async() to rss_provider.py
  4. Add crawl_async() to RSSProvider
  5. Add crawl_async() to GitHubReleaseProvider (run_in_executor)
  6. Add crawl_async() to DefaultProvider (run_in_executor)

Phase 3: Async Fetch Integration
  7. Add fetch_one_async() to application/feed.py
  8. Add fetch_all_async() to application/feed.py
  9. Modify CLI feed.py to use uvloop.run(fetch_all_async())

Phase 4: Crawl URL Async (if needed for parallel URL arguments)
  10. Add crawl_url_async() to application/crawl.py
```

## Concurrency Control

### Semaphore-Based Rate Limiting

```python
# Default: 10 concurrent requests
CONCURRENCY_LIMIT = 10

async def fetch_all_async():
    feeds = list_feeds()
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    async def bounded_fetch(feed):
        async with semaphore:
            return await fetch_one_async(feed, semaphore)

    tasks = [bounded_fetch(feed) for feed in feeds]
    await asyncio.gather(*tasks)
```

### Configurable Concurrency

```python
# From CLI: rss-reader fetch --all --concurrency 20
# From config: concurrency in settings (via dynaconf)
```

### SQLite Write Serialization

SQLite writes are serialized by:
1. All writes go through `asyncio.to_thread(store_article, ...)`
2. `to_thread()` uses a thread pool but SQLite's locking serializes writes
3. `busy_timeout=5000` handles lock waits

**No changes needed to storage layer.** The existing pattern works correctly with async.

## uvloop Installation Pattern

```python
# src/__main__.py or entry point
import uvloop

def main():
    uvloop.install()  # Install uvloop as the default event loop
    # CLI commands continue normally
    from src.cli import cli
    cli()

if __name__ == "__main__":
    main()
```

**Alternative (lazy install):**

```python
# At start of async function
def fetch_all_async():
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass  # Fall back to standard asyncio
    # ... rest of async code
```

**Decision:** Install at app startup in `__main__.py` for consistency.

## Error Handling

### Per-Feed Error Isolation

```python
async def fetch_one_async(feed, semaphore):
    async with semaphore:
        try:
            # ... fetch logic
            return {"new_articles": count}
        except Exception as e:
            logger.error("Failed to fetch %s: %s", feed.url, e)
            return {"new_articles": 0, "error": str(e)}
```

### Aggregate on gather()

```python
results = await asyncio.gather(*tasks, return_exceptions=True)

for i, result in enumerate(results):
    if isinstance(result, Exception):
        errors.append(f"{feeds[i].name}: {result}")
        error_count += 1
    else:
        total_new += result.get("new_articles", 0)
        success_count += 1
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Async in Click Without uvloop

**What people do:** Use `@click.command()` with async def but forget to install uvloop.

**Why bad:** Default asyncio event loop is slower; uvloop gives 2-4x I/O improvement.

**Do this instead:** Always `uvloop.install()` before running async code.

### Anti-Pattern 2: Concurrent SQLite Writes

**What people do:** Call `store_article()` directly from multiple async tasks without to_thread.

**Why bad:** SQLite write locks cause "database is locked" errors.

**Do this instead:** Use `asyncio.to_thread(store_article, ...)` to serialize writes.

### Anti-Pattern 3: Blocking Sync Libraries in Async Context

**What people do:** Call PyGithub (sync) directly in async function.

**Why bad:** Blocks the event loop, defeating concurrency benefit.

**Do this instead:** `await loop.run_in_executor(None, sync_function, *args)`.

### Anti-Pattern 4: Missing Error Isolation

**What people do:** Let one feed's exception crash the entire gather.

**Why bad:** One bad feed breaks all other feeds.

**Do this instead:** Use `return_exceptions=True` in asyncio.gather().

## Sources

- [uvloop Documentation](https://magicstack.github.io/uvloop/current/) (HIGH confidence)
- [httpx Async Client](https://www.python-httpx.org/async/) (HIGH confidence)
- [asyncio.gather docs](https://docs.python.org/3/library/asyncio-task.html#asyncio.gather) (HIGH confidence)
- [asyncio.Semaphore docs](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore) (HIGH confidence)
- [SQLite + asyncio patterns](https://docs.python.org/3/library/sqlite3.html) (HIGH confidence)

---

*Architecture research for: uvloop async concurrency integration*
*Researched: 2026-03-25*
