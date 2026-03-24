# Pitfalls Research: uvloop Async Concurrency

**Domain:** Adding uvloop/async concurrency to Python CLI with httpx sync and SQLite
**Researched:** 2026-03-25
**Confidence:** MEDIUM

*Note: Web search was unavailable during research. Findings are based on established Python async programming knowledge and known library behaviors.*

---

## Critical Pitfalls

### Pitfall 1: feedparser.parse() Blocks the Event Loop

**What goes wrong:**
The event loop stalls while `feedparser.parse()` processes XML. With 10 concurrent feeds, the entire async pipeline freezes during each parse operation, eliminating concurrency benefits.

**Why it happens:**
`feedparser.parse()` is a CPU-bound synchronous function. It performs XML parsing in the calling thread. Async/await cannot yield control during the parse operation.

**How to avoid:**
Run feedparser in a thread pool executor:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=4)

async def parse_feed_async(content: bytes, url: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, feedparser.parse, content)
```

**Warning signs:**
- Event loop appears frozen during feed parsing
- High CPU on single core during concurrent fetches
- "slow callback" warnings from uvloop

**Phase to address:**
Phase 1 (uvloop setup + executor pool for feedparser)

---

### Pitfall 2: Provider crawl() Methods Are Synchronous

**What goes wrong:**
`ContentProvider.crawl()` and all concrete implementations (RSSProvider, GitHubReleaseProvider) are synchronous. Calling `provider.crawl(url)` directly from async code blocks the event loop for the entire duration of the HTTP request.

**Why it happens:**
The Provider protocol was designed for synchronous execution. Each provider's `crawl()` method internally calls `httpx.get()` (blocking) and `feedparser.parse()` (blocking).

**How to avoid:**
Either:
1. Wrap all provider calls in executor: `await loop.run_in_executor(None, provider.crawl, url)`
2. Or refactor providers to async methods (breaking change to protocol)

Option 1 is less invasive for existing code.

**Warning signs:**
- Sequential behavior despite asyncio.gather() usage
- Concurrent fetches taking longer than sequential would

**Phase to address:**
Phase 2 (Provider wrapper for async execution)

---

### Pitfall 3: httpx.AsyncClient Lifecycle Mismanagement

**What goes wrong:**
Connection leaks, "Unclosed client session" warnings, or socket exhaustion. The AsyncClient is created but never properly closed, or closed too early.

**Why it happens:**
`httpx.AsyncClient` requires explicit lifecycle management. Unlike the sync `httpx.get()` which handles connections internally, AsyncClient maintains a connection pool that must be closed.

**How to avoid:**
Always use context manager or ensure proper cleanup:
```python
async with httpx.AsyncClient() as client:
    results = await asyncio.gather(*[fetch_one(client, url) for url in urls])
# Client automatically closed here

# For shared client across module:
_client: httpx.AsyncClient | None = None

async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient()
    return _client
```

**Warning signs:**
- "Unclosed client session" in logs
- Socket/file descriptor exhaustion
- Connection reset errors

**Phase to address:**
Phase 1 (httpx async client setup)

---

### Pitfall 4: uvloop Cannot Run in Non-Main Thread

**What goes wrong:**
`ValueError: uvloop can only be installed in the main thread` when running certain Click command invocations, especially with subprocess execution or certain IDE integrations.

**Why it happens:**
uvloop uses low-level threading APIs that only work in the Python main thread. Click may invoke commands in ways that are not the main thread.

**How to avoid:**
Guard uvloop installation:
```python
import asyncio
import uvloop
import sys

def main():
    if sys.platform != 'win32' and sys.implementation.name == 'cpython':
        # Only install uvloop in main thread on CPython (not PyPy)
        try:
            uvloop.install()
        except ValueError:
            pass  # Already in non-main thread or uvloop unavailable

    # Rest of CLI setup
    cli()
```

**Warning signs:**
- `ValueError: uvloop can only be installed in the main thread` crashes
- Works in direct CLI execution but fails in tests or IDE

**Phase to address:**
Phase 1 (uvloop installation)

---

### Pitfall 5: SQLite "database is locked" with Async Access

**What goes wrong:**
`sqlite3.OperationalError: database is locked` errors occur when multiple async tasks attempt to write to SQLite simultaneously, even with WAL mode.

**Why it happens:**
SQLite uses file-level locking. WAL mode allows concurrent readers but serialized writers. When 10 async tasks try to `store_article()` concurrently, SQLite's busy_timeout (5s) is exceeded on some connections.

**How to avoid:**
Serialize all SQLite writes through a single async queue:
```python
import asyncio
from collections.abc import Callable

_write_queue: asyncio.Queue[Callable] = asyncio.Queue()
_write_lock = asyncio.Lock()

async def serialized_db_operation(func: Callable, *args, **kwargs):
    """Queue a synchronous DB operation to run serially."""
    result = await _write_lock.acquire()
    try:
        return func(*args, **kwargs)
    finally:
        _write_lock.release()

# Or use a dedicated writer task:
async def _db_writer():
    while True:
        func, args, kwargs, future = await _write_queue.get()
        try:
            result = func(*args, **kwargs)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)
        finally:
            _write_queue.task_done()
```

The project plan explicitly keeps SQLite writes serial. Implementation must enforce this.

**Warning signs:**
- `database is locked` errors during concurrent fetches
- `PRAGMA busy_timeout` being exceeded

**Phase to address:**
Phase 3 (SQLite write serialization)

---

### Pitfall 6: Click Commands Cannot Be Async Directly

**What goes wrong:**
Defining a click command with `async def` leaves the coroutine unawaited. The function runs but returns a coroutine object that is never executed.

**Why it happens:**
Click's decorator-based command system expects synchronous functions. It calls the decorated function and does not await coroutines.

**How to avoid:**
Wrap async code in `asyncio.run()`:
```python
@cli.command("fetch")
@click.option("--all", is_flag=True)
@click.pass_context
def fetch(ctx, all):
    """Fetch feeds - async internally."""
    asyncio.run(_fetch_async(all))

async def _fetch_async(all):
    # All async code here
    pass
```

Or use a library like `click-asyncio` that handles this.

**Warning signs:**
- Functions with `async def` that don't execute
- "Coroutine was never awaited" warnings (in Python 3.7+)

**Phase to address:**
Phase 1 (CLI async wrapper pattern)

---

### Pitfall 7: Missing await on Async Function Calls

**What goes wrong:**
An async function is called but not awaited, resulting in a coroutine being created but never executed. The code appears to run but produces no results.

**Why it happens:**
Common mistake when converting sync to async code:
```python
# WRONG
async def fetch_feed(url):
    client = httpx.AsyncClient()
    response = client.get(url)  # Missing await!

# CORRECT
async def fetch_feed(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
```

**How to avoid:**
- Use `await` on all async calls
- Enable linting rules for `misc Rule: await` in Ruff
- Check for "coroutine was never awaited" warnings

**Warning signs:**
- No results but no errors
- "Coroutine was never awaited" warnings
- Code that appears to run but produces nothing

**Phase to address:**
Phase 1 (code review checklist)

---

### Pitfall 8: httpx Sync Client Still Used in Providers

**What goes wrong:**
Providers still use `httpx.get()` (synchronous) instead of async client, causing blocking HTTP calls despite async infrastructure.

**Why it happens:**
Existing code in RSSProvider uses sync patterns:
```python
def fetch_feed_content(url, etag=None, last_modified=None):
    response = httpx.get(url, ...)  # Sync!
```

**How to avoid:**
Replace with async client usage:
```python
async def fetch_feed_content_async(client: httpx.AsyncClient, url, etag=None, last_modified=None):
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified
    response = await client.get(url, headers=headers, timeout=30.0)
    return response
```

**Warning signs:**
- Sync `httpx.get` or `httpx.post` calls in provider code
- "Blocking HTTP call in async context" warnings

**Phase to address:**
Phase 2 (Provider async HTTP methods)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Using `asyncio.to_thread()` instead of executor pool | Simpler code | Less control over thread pool size | MVP only, must refactor before production |
| Creating new AsyncClient per request | Simpler lifecycle | Socket exhaustion at scale | Never - reuse client |
| Wrapping all DB ops in single lock | Serialization without queue | Blocks all reads during write | MVP only |
| Ignoring "Unclosed client session" | Faster development | Resource leaks, eventual crashes | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| httpx + uvloop | Not setting `http2=True` for HTTP/2 | HTTP/2 support in httpx requires explicit `http2=True` if needed |
| feedparser + async | Calling parse() directly | Wrap in `run_in_executor()` |
| SQLite + asyncio | Multiple connections for writes | Single serialized connection or queue |
| Click + asyncio | `async def` command without wrapper | Wrap in `asyncio.run()` |
| Provider protocol + async | Assuming crawl() is awaitable | It's sync - wrap in executor |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Thread pool exhaustion | Slow requests despite concurrency | Size thread pool appropriately (4-8 workers for I/O) | At 50+ concurrent feeds |
| Connection pool too small | HTTP 429 rate limiting | Set `limits` on AsyncClient | At high concurrency |
| Serial DB writes bottleneck | Async fetch completes but storage lags | Profile with actual workloads | At 20+ feeds with many articles |
| No backpressure | Memory growth | Use bounded queue with `maxsize` | With large feed lists |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Sharing AsyncClient across processes | Connection state contamination | One client per process |
| Not limiting concurrent requests | DoS on upstream servers | Semaphore to limit concurrency |
| Storing credentials in async client | Credentials in memory longer | Use context manager, minimize lifetime |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress indication during concurrent fetch | User thinks app hung | Progress bar updates even during concurrent operations |
| Errors cause silent failures | User doesn't know some feeds failed | Aggregate errors, show summary at end |
| Concurrent fetch is too fast | Rate limit bans from servers | Respect `UVLP-04` serial writes as backpressure signal |

---

## "Looks Done But Isn't" Checklist

- [ ] **uvloop installed:** App actually uses uvloop - verify with `asyncio.get_event_loop().__class__`
- [ ] **AsyncClient lifecycle:** All clients properly closed on exit
- [ ] **feedparser in executor:** Parsing does not block event loop - test with mock slow parse
- [ ] **SQLite serialization:** Writes truly serial under concurrent load - stress test
- [ ] **Provider crawl wrapped:** No sync HTTP calls in async context
- [ ] **await on all async calls:** No coroutines left unawaited
- [ ] **Error isolation:** One feed failure doesn't crash entire fetch

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Coroutine never awaited | LOW | Add missing `await`, often caught by linter |
| Database locked | LOW | Wait for timeout, retry serial operation |
| Connection leak | MEDIUM | Restart app, fix client lifecycle |
| Event loop blocked by feedparser | MEDIUM | Add executor wrapper, restart |
| Click async not awaited | LOW | Wrap command in `asyncio.run()` |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| uvloop in non-main thread | Phase 1: uvloop setup | Test in subprocess, IDE execution |
| httpx client lifecycle | Phase 1: httpx async client | Check for unclosed warnings |
| feedparser blocking | Phase 1: executor pool | Mock slow parse, verify concurrency |
| Click async commands | Phase 1: CLI async wrapper | Commands with `--all` actually async |
| Provider sync methods | Phase 2: Provider async wrapper | Wrap crawl() in executor, verify non-blocking |
| SQLite write serialization | Phase 3: Serial DB writes | Stress test with concurrent writes |
| Missing await | All phases | Enable Ruff await rule, run mypy |

---

## Sources

- [uvloop GitHub - Known Limitations](https://github.com/MagicStack/uvloop) (MEDIUM confidence - known project limitation)
- [httpx AsyncClient Documentation](https://www.python-httpx.org/async/) (MEDIUM confidence - official docs)
- [Python asyncio best practices](https://docs.python.org/3/library/asyncio-dev.html) (HIGH confidence - official docs)
- [SQLite threading considerations](https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety) (HIGH confidence - official docs)
- [Click issue: async support](https://github.com/pallets/click/issues/2065) (MEDIUM confidence - GitHub issue)

---

*Pitfalls research for: uvloop async concurrency feature*
*Researched: 2026-03-25*
