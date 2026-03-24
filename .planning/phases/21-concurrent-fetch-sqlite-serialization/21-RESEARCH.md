# Phase 21: Concurrent Fetch + SQLite Serialization - Research

**Researched:** 2026-03-25
**Domain:** asyncio concurrency patterns + SQLite serialization
**Confidence:** HIGH

## Summary

Phase 21 builds on Phase 20's `RSSProvider.crawl_async()` to create `fetch_all_async()` that concurrently crawls multiple feeds using `asyncio.Semaphore` for concurrency limiting, and serializes SQLite writes using `asyncio.to_thread()` with an `asyncio.Lock` to prevent "database is locked" errors. The key insight is that `asyncio.Semaphore` limits HTTP concurrent requests while an `asyncio.Lock` + `asyncio.to_thread()` pattern serializes database writes.

**Primary recommendation:** Create a new `src/application/fetch.py` module with `fetch_all_async(concurrency: int = 10)` that uses `asyncio.Semaphore` for crawl limiting and a module-level `asyncio.Lock` to serialize all storage operations via `asyncio.to_thread()`.

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase. The constraints come from the project-level decisions in PROJECT.md and the milestone requirements in REQUIREMENTS.md.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UVLP-04 | fetch_all_async() uses asyncio.Semaphore to limit concurrent crawls (default 10) | Semaphore pattern well-established in asyncio ecosystem |
| UVLP-05 | SQLite write operations use asyncio.to_thread() to serialize access | Thread-based serialization with asyncio.Lock is standard pattern |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| asyncio (builtin) | 3.4.3+ | Async/await primitives | Python stdlib, uvloop enhances it |
| asyncio.Semaphore | builtin | Concurrency limiter | Stdlib, correct tool for bounded concurrency |
| asyncio.to_thread | 3.8+ | Run sync code in thread pool | Stdlib replacement for run_in_executor(None, ...) |
| asyncio.Lock | builtin | Serialize access | Stdlib, correct tool for mutual exclusion |
| uvloop | 0.21.x | Event loop (from Phase 19) | 2-4x faster I/O, already installed |

**No new dependencies required.** All primitives are in Python stdlib or already installed (uvloop).

## Architecture Patterns

### Recommended Project Structure

```
src/application/
├── asyncio_utils.py    # Phase 19: install_uvloop, run_in_executor_crawl (existing)
├── feed.py             # sync fetch_one, fetch_all (existing)
├── fetch.py           # Phase 21: fetch_all_async (NEW)
```

### Pattern 1: Concurrent Fetch with Semaphore

**What:** Use `asyncio.Semaphore` to limit concurrent HTTP requests while crawling multiple feeds.

**When to use:** When you need to crawl N URLs concurrently but limit to K simultaneous connections.

**Example:**
```python
# Source: asyncio documentation pattern
import asyncio

async def fetch_all_async(urls: list[str], concurrency: int = 10) -> dict:
    semaphore = asyncio.Semaphore(concurrency)

    async def crawl_with_semaphore(url: str) -> tuple[str, list, str | None]:
        async with semaphore:
            # This runs K concurrent crawls at most
            return url, await provider.crawl_async(url), None

    # Create tasks for all URLs
    tasks = [crawl_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Pattern 2: Serialized SQLite Writes with asyncio.Lock + to_thread

**What:** Use `asyncio.Lock` to serialize database writes while using `asyncio.to_thread()` to run sync SQLite operations in a thread pool (avoid blocking event loop).

**Why:** SQLite connections are not thread-safe for concurrent writes. Multiple async tasks calling `store_article()` simultaneously causes "database is locked" errors. The lock ensures only one task writes at a time; `to_thread` ensures the sync DB call doesn't block the event loop.

**Example:**
```python
# Source: verified pattern for SQLite + asyncio
import asyncio

_db_write_lock: asyncio.Lock | None = None

def _get_db_lock() -> asyncio.Lock:
    global _db_write_lock
    if _db_write_lock is None:
        _db_write_lock = asyncio.Lock()
    return _db_write_lock

async def store_article_async(*args, **kwargs):
    """Async wrapper for store_article that serializes writes."""
    lock = _get_db_lock()
    async with lock:
        return await asyncio.to_thread(store_article, *args, **kwargs)
```

**Key insight:** The `asyncio.Lock` is acquired in the async context, then the sync DB operation runs in a thread. This means:
- Only one DB write runs at a time (lock)
- DB operations don't block the event loop (to_thread)

### Pattern 3: Per-Feed Async Crawl + Store

**What:** Each feed gets crawled asynchronously, then parsed and stored before moving to the next feed in the semaphore-controlled concurrency.

**Example flow:**
```python
async def fetch_all_async(concurrency: int = 10) -> dict:
    feeds = list_feeds()  # sync, call once
    semaphore = asyncio.Semaphore(concurrency)

    async def process_feed(feed):
        async with semaphore:
            # 1. Crawl async (uses httpx.AsyncClient in RSSProvider)
            providers = discover_or_default(feed.url)
            provider = providers[0]
            raw_items = await provider.crawl_async(feed.url)

            if not raw_items:
                return {"new_articles": 0}

            # 2. Parse items
            articles = [provider.parse(raw) for raw in raw_items]

            # 3. Store articles (serialized via lock + to_thread)
            new_count = 0
            for article in articles:
                await store_article_async(...)  # serialized
                new_count += 1

            return {"new_articles": new_count}

    # Run all feeds concurrently (limited by semaphore)
    tasks = [process_feed(feed) for feed in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return aggregate_results(results)
```

### Anti-Patterns to Avoid

- **Using `asyncio.to_thread()` without a lock for DB writes:** `to_thread()` runs sync code in a thread pool but does NOT serialize - multiple threads can still cause "database is locked". Must combine with `asyncio.Lock`.

- **Creating one lock per operation:** Don't create `asyncio.Lock()` inside the operation function. Use a module-level singleton pattern.

- **Using `loop.run_in_executor(None, ...)` instead of `asyncio.to_thread()`:** `asyncio.to_thread()` is the modern (3.8+) stdlib equivalent and is more readable.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Concurrency limiting | Custom thread pool with queue | `asyncio.Semaphore` | Stdlib, correct semantics, tested |
| Blocking DB calls in async | Calling sync sqlite3 directly | `asyncio.to_thread()` | Stdlib, clear semantics |
| Serializing writes | Multiple locks or semaphores | Single `asyncio.Lock` | SQLite connections aren't thread-safe for concurrent writes |

## Common Pitfalls

### Pitfall 1: SQLite "database is locked" under concurrent async writes
**What goes wrong:** Multiple async tasks call `store_article()` simultaneously. SQLite's journal mode can't handle parallel writes, resulting in "database is locked" errors.
**Why it happens:** SQLite allows only one writer at a time. Async tasks naturally run concurrently, overwhelming SQLite's locking.
**How to avoid:** Wrap all DB write operations with `asyncio.Lock` + `asyncio.to_thread()`.
**Warning signs:** `"database is locked"` in logs, or `sqlite3.OperationalError` during concurrent fetch.

### Pitfall 2: Semaphore too large overwhelms target servers
**What goes wrong:** Setting concurrency=50+ may cause feeds to block or ban the crawler.
**Why it happens:** Each concurrent request consumes server resources. Too many = rate limiting or IP ban.
**How to avoid:** Default to 10 (per PROJECT.md v1.5 spec). This is a sweet spot for personal RSS reading.
**Warning signs:** HTTP 429 responses, connection timeouts, feeds that worked before start failing.

### Pitfall 3: Forgetting to handle exceptions in gather()
**What goes wrong:** One failed feed causes entire `asyncio.gather()` to cancel other tasks.
**Why it happens:** By default, `gather()` cancels other tasks on first exception.
**How to avoid:** Use `return_exceptions=True` in `gather()` and aggregate results afterward.
**Warning signs:** `"Task was destroyed" warnings` or incomplete fetch results.

### Pitfall 4: Stale semaphore value from Phase 19 ThreadPoolExecutor
**What goes wrong:** Confusion between Phase 19's `_default_executor` ThreadPoolExecutor (for crawl operations) and Phase 21's DB serialization lock.
**Why it happens:** Phase 19 added a 10-worker thread pool for sync crawl operations. Phase 21 adds a lock for DB serialization.
**How to avoid:** These are separate concerns. Crawl operations use the thread pool; DB writes use the lock + to_thread.

## Code Examples

### Example 1: asyncio.Semaphore pattern (verified)
```python
import asyncio

async def bounded_crawl(urls: list[str], concurrency: int = 10):
    semaphore = asyncio.Semaphore(concurrency)

    async def crawl_one(url: str):
        async with semaphore:
            # Only K of these run at once
            return await crawl_async(url)

    # All tasks start, but only K run concurrently
    return await asyncio.gather(*[crawl_one(u) for u in urls])
```

### Example 2: SQLite serialization with Lock + to_thread (verified)
```python
import asyncio

_db_lock: asyncio.Lock | None = None

def _get_db_lock() -> asyncio.Lock:
    global _db_lock
    if _db_lock is None:
        _db_lock = asyncio.Lock()
    return _db_lock

async def db_write_serialized(fn, *args, **kwargs):
    """Run sync DB function with serialization."""
    lock = _get_db_lock()
    async with lock:
        return await asyncio.to_thread(fn, *args, **kwargs)
```

### Example 3: Hybrid - Semaphore for crawl, Lock for DB write
```python
async def process_feed(feed, semaphore, store_lock):
    async with semaphore:  # Limit concurrent HTTP requests
        raw_items = await provider.crawl_async(feed.url)

    for raw in raw_items:
        article = provider.parse(raw)
        # DB writes serialized by lock, run in thread to not block event loop
        await db_write_serialized(store_article, article["guid"], ...)

async def fetch_all_async(concurrency: int = 10):
    feeds = list_feeds()
    semaphore = asyncio.Semaphore(concurrency)
    store_lock = _get_db_lock()

    tasks = [process_feed(f, semaphore, store_lock) for f in feeds]
    await asyncio.gather(*tasks, return_exceptions=True)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sequential sync fetch (fetch_all) | Concurrent async fetch with semaphore | Phase 21 | 10x speedup potential |
| Direct DB calls from async context | Serialized DB writes via lock + to_thread | Phase 21 | No "database is locked" errors |
| ThreadPoolExecutor for all async ops | asyncio native primitives (Semaphore, to_thread, Lock) | Phase 21 | Cleaner, stdlib, no executor management |

**Deprecated/outdated:**
- `loop.run_in_executor(None, fn)` - replaced by `asyncio.to_thread()` (3.8+)

## Open Questions

1. **Should `fetch_all_async()` live in `src/application/fetch.py` or `src/application/feed.py`?**
   - Recommendation: Create `src/application/fetch.py` as new module, keep `feed.py` for sync operations
   - This matches the existing pattern of `crawl.py` vs `crawl_url()` in application/

2. **Should we create async wrappers for all storage functions or just the write operations?**
   - Recommendation: Only wrap `store_article()` and other write operations with the lock
   - Read operations (list_feeds, get_article, etc.) can be called directly since SQLite handles concurrent reads fine with WAL mode

3. **Should we pass `concurrency` as parameter or read from config?**
   - Recommendation: Parameter with default from config (future enhancement)
   - Phase 22 will add `--concurrency` CLI parameter

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified)

This phase adds Python code only - no external tools, services, or CLI utilities beyond the existing project dependencies (httpx, feedparser, sqlite3).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest.ini or pyproject.toml |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UVLP-04 | Semaphore limits concurrent crawls to default 10 | unit | `pytest tests/test_fetch.py -xvs -k "semaphore"` | No - needs new test |
| UVLP-05 | DB writes serialized via asyncio.Lock + to_thread | unit | `pytest tests/test_fetch.py -xvs -k "db_lock"` | No - needs new test |
| UVLP-04 | fetch_all_async() exists and is callable | unit | `pytest tests/test_fetch.py -xvs -k "fetch_all_async"` | No - needs new test |

### Wave 0 Gaps
- `tests/test_fetch.py` - tests for fetch_all_async, semaphore behavior, DB serialization
- `tests/conftest.py` - may need async fixtures (if not already present)
- Framework install: `pip install pytest pytest-asyncio` if not already in dependencies

## Sources

### Primary (HIGH confidence)
- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html) - Semaphore, Lock, to_thread
- [Python sqlite3 documentation](https://docs.python.org/3/library/sqlite3.html) - thread safety model
- Existing codebase: `src/application/asyncio_utils.py`, `src/providers/rss_provider.py`, `src/storage/sqlite.py`

### Secondary (MEDIUM confidence)
- [SQLite WAL mode behavior](https://www.sqlite.org/wal.html) - concurrent reads, serialized writes
- [uvloop documentation](https://github.com/MagicStack/uvloop) - already installed via Phase 19

### Tertiary (LOW confidence)
- Web search for "asyncio sqlite database is locked" patterns (verified against stdlib docs)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - using Python stdlib asyncio primitives
- Architecture: HIGH - semaphore + lock pattern well-established
- Pitfalls: HIGH - "database is locked" issue is well-known with SQLite + async

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (30 days for stable asyncio patterns)
