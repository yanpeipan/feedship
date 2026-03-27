# Phase: uvloop Best Practices Research

**Researched:** 2026-03-28
**Domain:** uvloop integration with asyncio-based Python CLI applications
**Confidence:** MEDIUM (training data + codebase analysis; no live docs access)

## Summary

The codebase already has uvloop integrated correctly. `deep_crawl.py` uses asyncio primitives that are fully compatible with uvloop. The primary refactor opportunity is **architectural alignment** - ensuring `deep_crawl` async patterns are consistent with the established uvloop usage pattern, rather than a fundamental rewrite.

**Primary recommendation:** The existing `install_uvloop()` pattern + `uvloop.run()` at CLI boundaries is correct. No changes needed to `deep_crawl.py` itself since it uses standard asyncio primitives that uvloop handles transparently.

## Current uvloop Integration

### Existing Pattern (Correct)

| Component | Implementation | Status |
|-----------|---------------|--------|
| Event loop install | `install_uvloop()` in `src/utils/asyncio_utils.py` | Correct - called at CLI startup |
| CLI entry point | `uvloop.run()` in `src/cli/discover.py` and `src/cli/feed.py` | Correct |
| Async primitives | `asyncio.Semaphore`, `asyncio.gather`, `asyncio.to_thread` | Correct - uvloop handles these transparently |
| Platform fallback | Windows check in `install_uvloop()` | Correct |

### deep_crawl.py Async Analysis

```python
# deep_crawl.py already uses uvloop-compatible patterns:
asyncio.Semaphore(5)        # uvloop handles this
asyncio.gather(*tasks)      # uvloop handles this
asyncio.to_thread()         # wraps blocking calls in thread pool (correct)
asyncio.sleep()             # uvloop handles this
```

## Key uvloop Facts

### How uvloop Works
- uvloop replaces the asyncio event loop policy with libuv (same as Node.js)
- `uvloop.install()` sets uvloop as the default event loop policy globally
- Once installed, all `asyncio.get_event_loop()` calls return a uvloop-backed loop
- `uvloop.run()` creates a new event loop and runs coroutines to completion

### Performance Characteristics
- 2-4x faster I/O-bound operations (HTTP, file I/O)
- Minimal improvement for CPU-bound work (stays in thread pool)
- `asyncio.to_thread()` calls go through thread pool regardless of event loop
- `loop.run_in_executor()` can use custom executor with uvloop

### Platform Constraints
- **Linux/macOS only** - Windows falls back to asyncio automatically
- Cannot run in non-main thread (certain Click invocations, IDE integrations)
- Already handled by `install_uvloop()` with try/except fallback

## Architecture Patterns

### Recommended Pattern (Already Implemented)

```python
# src/cli/__init__.py - app startup
from src.utils.asyncio_utils import install_uvloop
install_uvloop()  # Called once at application startup

# src/cli/discover.py - CLI command
import uvloop

@click.command()
def discover(url):
    feeds = uvloop.run(_discover_async(url))  # Entry point
```

### Why This Pattern Works

1. `install_uvloop()` sets the default policy before any async code runs
2. `uvloop.run()` creates a fresh event loop, runs the coroutine, closes loop
3. All async code inside (including deep_crawl.py) uses uvloop transparently
4. Standard asyncio primitives (`await`, `gather`, `Semaphore`) are handled by uvloop

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event loop setup | Custom loop creation | `uvloop.install()` + `uvloop.run()` | Handles edge cases, cross-platform |
| Thread pool for blocking I/O | Custom ThreadPoolExecutor | `asyncio.to_thread()` | Built-in, works with uvloop |
| Concurrent I/O | Sequential requests | `asyncio.gather()` + `Semaphore` | Already in deep_crawl.py |

## Common Pitfalls

### Pitfall 1: Mixing asyncio.run() with uvloop
**What goes wrong:** Creates a new standard asyncio loop, bypasses uvloop optimization.
**How to avoid:** Use only `uvloop.run()` at CLI entry points. Never call `asyncio.run()`.
**Verification:** `grep -r "asyncio\.run(" src/` returns no matches (confirmed - 0 matches)

### Pitfall 2: Blocking calls not in thread pool
**What goes wrong:** Blocks the event loop, defeats async benefits.
**How to avoid:** Wrap blocking calls with `asyncio.to_thread()`.
**deep_crawl.py status:** Uses `asyncio.to_thread(Fetcher.get, ...)` - correct.

### Pitfall 3: Calling install_uvloop() multiple times
**What goes wrong:** Second call may fail silently or create inconsistent state.
**How to avoid:** Call once at startup. Already handled by `install_uvloop()` implementation.

### Pitfall 4: Windows deployment
**What goes wrong:** uvloop not available on Windows.
**How to avoid:** `install_uvloop()` already checks `platform.system() == "Windows"`.
**Warning signs:** `uvloop not installed` log message on Windows.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `asyncio.run()` | `uvloop.run()` | v1.5 | 2-4x faster I/O |
| ThreadPoolExecutor manual | `asyncio.to_thread()` | Python 3.9+ | Cleaner API, same performance |
| Blocking `feedparser.parse()` | `asyncio.to_thread()` wrap | Already done | Non-blocking feed parsing |

**Deprecated/outdated:**
- `asyncio.new_event_loop()` + `asyncio.set_event_loop()` - replaced by `uvloop.run()`
- Manual `loop.run_until_complete()` - replaced by `uvloop.run()`

## Open Questions

1. **Should deep_crawl.py use `uvloop.run()` internally?**
   - No. `deep_crawl.py` is an async function meant to run inside an existing event loop.
   - It is called from `discover_feeds()` which is called via `uvloop.run()` at CLI boundary.
   - This is the correct pattern - one `uvloop.run()` at the entry point.

2. **Could `asyncio.to_thread()` be replaced with uvloop-specific API?**
   - Minimal benefit. `asyncio.to_thread()` is the modern Python API and works with any event loop.
   - `uvloop.run_in_executor()` is equivalent but less portable.

3. **Is there benefit to using `uvloop.Policy` directly?**
   - No. The `install_uvloop()` pattern is sufficient and handles all edge cases.

## Code Examples from Codebase

### Correct Pattern in src/cli/discover.py
```python
import uvloop

async def _discover_async(url: str, max_depth: int = 1) -> list[DiscoveredFeed]:
    return await discover_feeds(url, max_depth)  # Calls deep_crawl internally

@click.command("discover")
def discover(ctx, url, discover_depth):
    feeds = uvloop.run(_discover_async(url, discover_depth))  # Single entry point
```

### Correct Pattern in deep_crawl.py
```python
async def deep_crawl(start_url: str, max_depth: int = 1) -> list[DiscoveredFeed]:
    semaphore = asyncio.Semaphore(5)  # uvloop handles this
    # ...
    response = await asyncio.to_thread(Fetcher.get, url, headers=BROWSER_HEADERS)  # Correct
```

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `/Users/y3/radar/src/utils/asyncio_utils.py`, `/Users/y3/radar/src/cli/discover.py`, `/Users/y3/radar/src/discovery/deep_crawl.py`

### Secondary (MEDIUM confidence)
- Training data: uvloop 0.22.1 documentation and source code patterns

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - uvloop usage confirmed in codebase, docs not accessible for verification
- Architecture: HIGH - pattern is clearly correct and follows standard uvloop usage
- Pitfalls: MEDIUM - based on training data, not verified against live docs

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (uvloop API stable, unlikely to change)
