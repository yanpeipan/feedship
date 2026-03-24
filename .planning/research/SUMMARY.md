# Project Research Summary

**Project:** Personal Information System (RSS Reader)
**Domain:** CLI tool for RSS subscription and website crawling
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Executive Summary

The v1.5 milestone introduces uvloop-based async concurrency to the existing RSS reader CLI. The current `fetch --all` command processes feeds sequentially, creating a bottleneck when handling multiple feeds. This research confirms that adding concurrent fetching is technically straightforward: all necessary packages (uvloop, httpx with async support, anyio) are already installed, and the primary work is architectural - converting sync code paths to async patterns while maintaining SQLite write serialization.

The recommended approach is to add async variants to the provider protocol (crawl_async) with default executor-based implementations, then build async fetch functions in the application layer. This preserves backward compatibility for providers that have not yet been migrated. The key risk is blocking the event loop with synchronous libraries (feedparser) or mismanaging httpx AsyncClient lifecycle - both are well-documented pitfalls with clear prevention strategies.

## Key Findings

### Recommended Stack

The technology stack is well-established with HIGH confidence. Core components include feedparser 6.0.x for RSS parsing, httpx 0.27.x (with built-in AsyncClient) for HTTP, BeautifulSoup4 + lxml for HTML parsing, click 8.1.x for CLI, and sqlite3 (built-in) for storage. The project already has pluggy 1.5.0 installed for the plugin architecture from v1.3, and uvloop 0.22.1 is already installed for v1.5.

**v1.5 specific additions (all already installed):**
- uvloop 0.22.1: Event loop replacement providing 2-4x I/O improvement
- httpx 0.28.1: Built-in AsyncClient for concurrent HTTP requests
- anyio 4.7.0: Already installed as httpx dependency

Python minimum is 3.10 (required by scrapling 0.4.2 from v1.1 GitHub monitoring).

### Expected Features

**Must have (table stakes for v1.5):**
- uvloop event loop installation at app startup
- httpx.AsyncClient for async HTTP requests (drop-in replacement for httpx.get())
- asyncio.Semaphore for concurrency limiting (default 10 concurrent)
- Thread pool executor for feedparser.parse() to avoid blocking event loop
- SQLite writes remain serial via asyncio.to_thread() pattern

**Should have (differentiators for v1.6+):**
- Configurable concurrency via CLI argument --concurrency
- Per-feed progress reporting during concurrent fetch
- Batch SQLite writes with single transaction

**Defer (v2+):**
- Async generator for streaming article results
- Connection pooling with keep-alive across fetches
- Dynamic concurrency auto-tuning

### Architecture Approach

The architecture follows a provider plugin pattern (from v1.3) with clear layer separation: CLI -> Application -> Provider -> Storage. The v1.5 async refactor adds async variants to each layer while maintaining the existing sync code paths for backward compatibility.

**Major components:**
1. **CLI Layer (click):** Wraps async code with uvloop.run() to avoid click's async edge cases
2. **Application Layer:** New fetch_one_async() and fetch_all_async() functions with semaphore-controlled concurrency
3. **Provider Layer:** crawl_async() method added to ContentProvider protocol with default executor implementation
4. **Storage Layer:** No changes needed - existing store_article() called via asyncio.to_thread()

**Build order from architecture research:**
1. Phase 1: uvloop setup + crawl_async() protocol with default implementation
2. Phase 2: Async HTTP methods in RSSProvider using httpx.AsyncClient
3. Phase 3: Async fetch integration in application layer
4. Phase 4: crawl_url_async() for parallel URL arguments (if needed)

### Critical Pitfalls

1. **feedparser.parse() blocks event loop** — Must run in ThreadPoolExecutor via asyncio.to_thread(). Without this, concurrent fetches freeze during XML parsing.

2. **Provider crawl() methods are synchronous** — Calling sync provider.crawl(url) directly from async code blocks the event loop. Must either wrap in executor or add async variants.

3. **httpx.AsyncClient lifecycle mismanagement** — Connection leaks occur if AsyncClient is not properly closed. Must use context manager or ensure cleanup.

4. **uvloop cannot run in non-main thread** — ValueError occurs when uvloop.install() is called in non-main thread (e.g., certain Click invocations, IDE integrations). Guard with try/except.

5. **SQLite "database is locked" with async** — Concurrent writes cause locking errors even with WAL mode. Serialize all writes via asyncio.to_thread() or a write queue.

## Implications for Roadmap

Based on research, the v1.5 milestone should be structured in this order:

### Phase 1: uvloop Setup + Protocol Extension
**Rationale:** Foundation work that other phases depend on. Must establish async patterns before building async functionality.
**Delivers:** uvloop.install() at app startup, crawl_async() method on ContentProvider protocol with default executor-based implementation
**Avoids:** uvloop in non-main thread (Pitfall 4), missing await issues
**Research flag:** MEDIUM - uvloop behavior in Click subprocesses needs verification during implementation

### Phase 2: Provider Async HTTP Methods
**Rationale:** RSSProvider uses httpx directly for HTTP requests. Must convert to async before concurrent fetching works correctly.
**Delivers:** RSSProvider.crawl_async() using httpx.AsyncClient, GitHubReleaseProvider.crawl_async() wrapping sync calls in executor
**Avoids:** feedparser blocking event loop (Pitfall 1), httpx sync still used (Pitfall 8), provider crawl sync (Pitfall 2)

### Phase 3: Application Layer Async Integration
**Rationale:** Ties together providers with concurrency control and SQLite write serialization.
**Delivers:** fetch_one_async(), fetch_all_async() with semaphore-controlled concurrency, SQLite writes via asyncio.to_thread()
**Avoids:** SQLite locked errors (Pitfall 5), Click async commands not awaited (Pitfall 6)

### Phase 4: CLI Integration + Testing
**Rationale:** Final integration to expose async functionality via CLI and verify all pitfalls are addressed.
**Delivers:** fetch --all command uses uvloop.run(fetch_all_async()), error aggregation with summary output
**Avoids:** Progress indication gaps, silent failures

### Phase Ordering Rationale

- **Why Phase 1 first:** uvloop installation and protocol changes are foundational. Without crawl_async() on the protocol, providers cannot be called asynchronously.
- **Why Phase 2 before Phase 3:** The provider layer does the actual HTTP work. If RSSProvider still uses sync httpx.get(), async fetch in application layer will still block.
- **Why Phase 3 after providers are async:** The application layer coordinates providers and storage. Both must be async-ready before integration.
- **Why Phase 4 last:** CLI integration is the entry point. All async functionality should be working before wiring it to user-facing commands.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** uvloop in non-main thread edge cases with Click - may need testing to confirm compatibility
- **Phase 3:** SQLite write serialization performance under load - recommend stress testing with 50+ feeds

Phases with standard patterns (skip research-phase):
- **Phase 2:** httpx.AsyncClient is well-documented with clear patterns
- **Phase 4:** CLI async wrapping is a known pattern with established solutions

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified via PyPI JSON API. uvloop, httpx, anyio already installed. |
| Features | MEDIUM | Based on training data for async patterns; uvloop performance benchmarks not verified in project context |
| Architecture | MEDIUM-HIGH | Detailed integration points mapped; build order makes logical sense |
| Pitfalls | MEDIUM | Based on established Python async programming knowledge; uvloop edge cases may differ in practice |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Performance benchmarks:** uvloop 2-4x speedup claim is based on general benchmarks, not tested with actual RSS feeds in this project. Validate with real workloads after implementation.
- **feedparser thread pool sizing:** Thread pool workers (4-8 recommended) may need tuning based on CPU count and feed complexity. Default may not be optimal.
- **uvloop Windows fallback:** Project may run on Windows; verify default asyncio fallback works correctly if uvloop.install() fails.

## Sources

### Primary (HIGH confidence)
- [feedparser Documentation](https://feedparser.readthedocs.io/en/latest/) — RSS parsing library
- [httpx Async Client](https://www.python-httpx.org/async/) — AsyncClient usage patterns
- [Python asyncio official docs](https://docs.python.org/3/library/asyncio-sync.html#asyncio.Semaphore) — Semaphore, gather patterns
- [SQLite threading considerations](https://docs.python.org/3/library/sqlite3.html#sqlite3.threadsafety) — Write serialization
- [uvloop GitHub](https://github.com/MagicStack/uvloop) — Event loop installation, limitations
- [pluggy GitHub](https://github.com/pytest-dev/pluggy) — Plugin framework (v1.3)

### Secondary (MEDIUM confidence)
- [uvloop documentation](https://magicstack.github.io/uvloop/current/) — Performance claims, patterns
- [Click async issue](https://github.com/pallets/click/issues/2065) — async command limitations
- [rich documentation](https://rich.readthedocs.io/) — Terminal formatting (v1.2)
- [scrapling PyPI](https://pypi.org/project/scrapling/) — Changelog scraping (v1.1)

---
*Research completed: 2026-03-25*
*Ready for roadmap: yes*
