# Feature Research: uvloop Async Concurrency

**Domain:** CLI RSS reader async HTTP fetching
**Researched:** 2026-03-25
**Confidence:** MEDIUM (based on training data; verification needed for performance benchmarks)

## Feature Landscape

### Table Stakes (Required for v1.5)

These features are required for the uvloop/async concurrency milestone. Missing them means the feature does not work.

| Feature | Why Required | Complexity | Notes |
|---------|--------------|------------|-------|
| uvloop event loop installation | Without it, asyncio runs on default event loop which is slower | LOW | `pip install uvloop`; install before setting event loop |
| `asyncio.run()` or `uvloop.run()` entry point | Replaces `if __name__ == "__main__"` pattern | LOW | All async code starts from a single entry point |
| httpx.AsyncClient | HTTP client that supports `await client.get()` | LOW | Drop-in async replacement for `httpx.get()` |
| Semaphore-based concurrency limiting | Prevents overwhelming servers or hitting rate limits | MEDIUM | `asyncio.Semaphore(n)` where n = max concurrent requests |
| Thread pool for feedparser | feedparser is blocking (not async-native) | MEDIUM | Use `asyncio.to_thread()` or `loop.run_in_executor()` to run feedparser parsing |
| Serial SQLite writes | SQLite has locking issues with concurrent writes | LOW | Keep existing `store_article()` calls sequential after all fetches complete |

### Differentiators (Value-Add for v1.5)

These features enhance the core async functionality but are not strictly required.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Configurable concurrency limit | Users with many feeds may want more; users with slow connections may want less | LOW | CLI argument `--concurrency N` defaulting to 10 |
| Per-feed progress reporting | Users see which feed is being fetched during `fetch --all` | MEDIUM | Requires async logging that does not block |
| Graceful degradation on fetch failure | One failed feed does not cancel all others | LOW | Already handled by try/except in existing code |
| Batch SQLite writes | Group multiple articles in single transaction | MEDIUM | Reduces I/O but adds complexity |

### Anti-Features (Commonly Requested, Avoid for v1.5)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| True parallel SQLite reads | Concurrent reads seem beneficial | SQLite supports concurrent reads fine; writes are the bottleneck | Current approach is fine |
| Async for single feed fetch | Consistency of async patterns | Adds complexity for no benefit when fetching one feed | Keep `fetch_one()` sync, only `fetch_all()` async |
| Dynamic concurrency (auto-tune) | "Smart" rate limiting | Hard to implement correctly; simple fixed limit is more predictable | Fixed configurable limit |

## Feature Dependencies

```
uvloop installation
    └──requires──> asyncio event loop policy set
                         └──requires──> httpx.AsyncClient usage
                                            └──requires──> async/await in fetch_all()
                                                                      │
                                              ┌───────────────────────┴───────────────────────┐
                                              │                                               │
                                    feedparser blocking                           SQLite serial writes
                                    (needs thread pool)                         (no special handling)
```

### Dependency Notes

- **uvloop requires event loop policy set before any async code runs:** `asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())` must happen at application startup, before any `async def` is called.
- **httpx.AsyncClient requires async context:** Use `async with httpx.AsyncClient() as client:` pattern. Cannot mix sync `httpx.get()` with async code.
- **feedparser is synchronous:** It will block the event loop. Must run in thread pool via `asyncio.to_thread(feedparser.parse, content)`.
- **SQLite writes remain serial:** The existing `store_article()` calls in `fetch_one()` can stay sequential since network I/O dominates anyway.

## MVP Definition (v1.5)

### Launch With

- [ ] **uvloop event loop as default** — `asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())` at app startup
- [ ] **httpx.AsyncClient for HTTP requests** — Replace `httpx.get()` with `await client.get()` in `fetch_feed_content()`
- [ ] **async fetch_all() with Semaphore** — Concurrent fetches limited by semaphore (default 10)
- [ ] **Thread pool for feedparser.parse()** — `await asyncio.to_thread(feedparser.parse, content)` to avoid blocking event loop
- [ ] **SQLite writes after concurrent fetch phase** — All network fetches complete, then serial writes (existing code path works)

### Add After Validation (v1.6+)

- [ ] `--concurrency` CLI argument for configurable parallel fetch limit
- [ ] Per-feed progress logging during concurrent fetch
- [ ] Batch article storage with single transaction

### Future Consideration (v2+)

- [ ] Async generator for streaming article results
- [ ] Connection pooling with keep-alive across fetches

## Technical Implementation Patterns

### Pattern 1: uvloop Setup

```python
import asyncio
import uvloop

# At application startup (before any async code)
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

# Then run async code
async def main():
    # async code here

if __name__ == "__main__":
    uvloop.run(main())
```

**Note:** uvloop only works on Linux/macOS. On Windows, falls back to default asyncio event loop. Use `uvloop.isInstalled()` to check.

### Pattern 2: httpx AsyncClient with Semaphore

```python
import asyncio
import httpx
from typing import List

async def fetch_feed(client: httpx.AsyncClient, url: str, semaphore: asyncio.Semaphore) -> bytes:
    async with semaphore:
        response = await client.get(url, timeout=30.0)
        return response.content

async def fetch_all_feeds(urls: List[str], max_concurrent: int = 10) -> List[bytes]:
    semaphore = asyncio.Semaphore(max_concurrent)
    async with httpx.AsyncClient() as client:
        tasks = [fetch_feed(client, url, semaphore) for url in urls]
        return await asyncio.gather(*tasks)
```

### Pattern 3: Blocking feedparser in Thread Pool

```python
import asyncio
import feedparser

async def parse_feed_async(content: bytes) -> list:
    # feedparser.parse() is blocking, run in thread pool
    return await asyncio.to_thread(feedparser.parse, content)

# Usage
entries = await parse_feed_async(content)
```

### Pattern 4: Serial SQLite Writes After Concurrent Fetches

```python
async def fetch_and_store_all(feeds: list[Feed]) -> dict:
    # Phase 1: Concurrent fetch (fast)
    urls = [feed.url for feed in feeds]
    contents = await fetch_all_feeds(urls, max_concurrent=10)

    # Phase 2: Serial parse and store (only writes are serial)
    for feed, content in zip(feeds, contents):
        entries = await parse_feed_async(content)
        for entry in entries:
            store_article(...)  # Existing sync function, called sequentially
```

## Performance Expectations

| Scenario | Sequential (current) | Concurrent (v1.5) | Speedup |
|----------|---------------------|-------------------|---------|
| 10 feeds, 1s each | ~10s | ~1s (10 concurrent) | 10x |
| 50 feeds, 1s each | ~50s | ~5-6s (10 concurrent) | ~8-10x |
| 100 feeds, 1s each | ~100s | ~10-12s (10 concurrent) | ~8-10x |

**Key insight:** Concurrency is I/O-bound, not CPU-bound. The bottleneck is network latency, not parsing speed. feedparser runs in thread pool so it does not block other fetches.

**Rate limiting note:** The existing 2s per-host rate limit in `crawl_url()` uses `time.sleep()` which blocks the thread. With async, this should become `asyncio.sleep()` to allow other tasks to run during the wait. However, since crawl_url is not used in the RSS feed fetch path, this may not be needed for v1.5.

## Competitor Feature Analysis

| Feature | Miniflux | FreshRSS | Our Approach |
|---------|----------|----------|--------------|
| Concurrent fetching | Yes (background refresh) | Yes (background refresh) | CLI-first, on-demand with `--all` |
| Configurable concurrency | Config file | Admin panel | CLI argument `--concurrency` |
| Async architecture | Go routines | PHP (sync) | Python uvloop/asyncio |

## Sources

- [uvloop documentation](https://magicstack.github.io/uvloop/) (MEDIUM confidence - training data)
- [httpx async documentation](https://www.python-httpx.org/async/) (MEDIUM confidence - training data)
- [asyncio.Semaphore pattern](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore) (HIGH confidence - official docs)
- [feedparser is synchronous](https://feedparser.readthedocs.io/en/latest/) (HIGH confidence - library design)

---

*Feature research for: uvloop async concurrency*
*Researched: 2026-03-25*
