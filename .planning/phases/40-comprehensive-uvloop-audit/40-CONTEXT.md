# Phase 40: Comprehensive uvloop Audit - Context

**Gathered:** 2026-03-28 (--auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Full audit of all async code to identify uvloop anti-patterns, ensure no `asyncio.run()` usage, verify blocking calls are wrapped in `asyncio.to_thread()`, and confirm all async code flows through `uvloop.run()` at CLI boundaries.

</domain>

<decisions>
## Implementation Decisions

### Audit Scope (D-01)
**Files to audit** (all files containing async code in `src/`):
- `src/cli/feed.py` — CLI entry point with `uvloop.run()` calls
- `src/cli/discover.py` — CLI entry point with `uvloop.run()` calls
- `src/application/fetch.py` — async fetch orchestration
- `src/discovery/deep_crawl.py` — async BFS crawler
- `src/storage/sqlite.py` — async DB wrapper with `asyncio.Lock` + `to_thread`
- `src/providers/rss_provider.py` — async HTTP via `httpx.AsyncClient`
- `src/providers/github_release_provider.py` — async via `to_thread` wrapping sync
- `src/providers/base.py` — ContentProvider protocol with `crawl_async()` stub
- `src/utils/asyncio_utils.py` — simplified `install_uvloop()` (Phase 39 result)

**Why these files:** All contain `async def` or `asyncio.*` primitives. Phase 39 only audited `asyncio_utils.py`.

### Anti-pattern Checks (D-02)
Verify zero occurrences of each:
1. `asyncio.run()` — should NEVER appear in `src/`
2. `asyncio.new_event_loop()` — custom loop creation
3. `get_event_loop()` outside proper context — avoid orphaned loops
4. `time.sleep()` — blocking sleep, should use `asyncio.sleep()`
5. `requests.get` / `urllib.request` — blocking HTTP, should use `httpx`

### Blocking Call Wrapping (D-03)
Confirm all blocking operations use `asyncio.to_thread()`:
- SQLite writes: `store_article_async` uses `asyncio.to_thread(store_article, ...)`
- feedparser.parse: `RSSProvider.crawl_async` uses `loop.run_in_executor(None, feedparser.parse, ...)`
- PyGithub calls: `GitHubReleaseProvider.crawl_async` uses `asyncio.to_thread(self.crawl, url)`

### Provider Async Patterns (D-04)
- **RSSProvider**: True async via `httpx.AsyncClient` — CORRECT
- **GitHubReleaseProvider**: Wraps sync `crawl()` in `asyncio.to_thread()` — ACCEPTABLE (PyGithub is sync-only)
- **DefaultProvider**: `crawl_async` raises `NotImplementedError` — correct stub

### SQLite Lock Pattern (D-05)
**Pattern**: `_db_write_lock: asyncio.Lock | None = None` created lazily via `_get_db_write_lock()`.

**Assessment**: This is a lazy initialization pattern. The lock is created when first needed within async context (via `uvloop.run()`). `asyncio.Lock()` creation does not require a running loop. The lock is only used within `async with` context, which always has an event loop. **No fix needed.**

### Fix vs Defer Criteria (D-06)
- **Fix immediately**: Any `asyncio.run()`, `time.sleep()`, or blocking HTTP (`requests.*`, `urllib.*`)
- **Fix immediately**: Any `asyncio.new_event_loop()` or `set_event_loop()` outside proper startup
- **Defer**: Complex patterns that work but could be improved (document as technical debt)
- **Document**: Findings summary for each file audited

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### uvloop Integration (Phase 39 foundation)
- `src/utils/asyncio_utils.py` — Phase 39 cleaned version (~44 lines)
- `src/cli/__init__.py` — `install_uvloop()` called once at startup (line 25)
- `src/cli/feed.py` — `uvloop.run()` at lines 147, 319, 328, 345
- `src/cli/discover.py` — `uvloop.run()` at line 94

### Async Code Files
- `src/application/fetch.py` — async fetch with `asyncio.Semaphore`, `asyncio.to_thread`
- `src/discovery/deep_crawl.py` — async BFS with `asyncio.gather`, `asyncio.Semaphore`, `asyncio.to_thread`
- `src/storage/sqlite.py` — async DB wrapper with `asyncio.Lock`, `asyncio.to_thread`
- `src/providers/rss_provider.py` — true async via `httpx.AsyncClient` + `run_in_executor` for feedparser
- `src/providers/github_release_provider.py` — `asyncio.to_thread` wrapping PyGithub sync calls
- `src/providers/base.py` — ContentProvider protocol

### Prior Research
- `.planning/phases/39-uvloop-best-practices/39-CONTEXT.md` — Phase 39 context (dead code removal, install_uvloop simplification)
- `.planning/phases/phase-19-uvloop-setup-crawl-async-protocol/19-CONTEXT.md` — Phase 19 context (uvloop foundation)

</canonical_refs>

<codebase_context>
## Existing Code Insights

### Async Architecture Summary
The async code follows a layered pattern:
1. **CLI boundary**: `uvloop.run()` wraps all async entry points
2. **Async orchestration**: `fetch.py`, `deep_crawl.py` use `asyncio.Semaphore` + `asyncio.gather`
3. **Blocking wrappers**: `asyncio.to_thread()` or `run_in_executor()` for sync operations
4. **Providers**: RSS uses true async HTTP; GitHub uses thread pool for sync PyGithub

### Verified Clean Patterns
- `uvloop.run()` at all 5 CLI entry points ✓
- `asyncio.Semaphore(default=10)` for concurrency limiting ✓
- `asyncio.to_thread()` for SQLite writes ✓
- `asyncio.Lock` singleton for write serialization ✓
- No `asyncio.run()` in `src/` ✓
- No `time.sleep()` in `src/` ✓

### Potential Pattern to Verify
- `asyncio.Lock` lazy initialization in `sqlite.py` — works because it's always accessed within `uvloop.run()` context

</codebase_context>

<specifics>
## Specific Ideas

### Audit Evidence
Initial grep shows:
- `asyncio.run()`: **0 matches** ✓
- `asyncio.new_event_loop()`: **0 matches** ✓
- `time.sleep()`: **0 matches** ✓
- `requests.get|urllib.request`: **0 matches** ✓
- `uvloop.run()`: 5 matches (CLI boundaries) ✓
- `asyncio.to_thread()`: Multiple uses for SQLite, feedparser, PyGithub ✓

### Phase 39 Context Applied
Phase 39 already verified and cleaned `asyncio_utils.py`. Phase 40 extends the audit to all other async files in `src/`.

</specifics>

<deferred>
## Deferred Ideas

None — audit phase with clear findings from initial grep.

</deferred>
