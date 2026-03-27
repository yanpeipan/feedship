# Phase 39: uvloop Best Practices Review - Context

**Gathered:** 2026-03-28 (--auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Review async code patterns to ensure uvloop is used correctly, remove dead code from `asyncio_utils.py`, and verify all CLI entry points follow uvloop best practices.

</domain>

<decisions>
## Implementation Decisions

### Dead Code Removal (D-01)
The following are **unused** and must be removed from `src/utils/asyncio_utils.py`:
- `_default_executor` global variable (line 20)
- `_main_loop` global variable (line 23)
- `_get_default_executor()` function (lines 26-35)
- `run_in_executor_crawl()` function (lines 72-92)
- Lines 62-63: `_main_loop = asyncio.new_event_loop()` and `asyncio.set_event_loop(_main_loop)`

**Why safe to remove:** None of these are referenced by any caller. `run_in_executor_crawl` was designed as a default `crawl_async()` implementation but no provider ever used it — each provider implements its own `crawl_async()`. Phase 20 research confirmed RSSProvider uses true async httpx.AsyncClient.

### install_uvloop() Simplification (D-02)
Simplify `install_uvloop()` to only:
1. Check Windows → return False (skip)
2. Try import uvloop → return False if not installed
3. Try `uvloop.install()` → return False on failure

**Do NOT create/store an event loop.** `uvloop.run()` creates its own loop. The `_main_loop = asyncio.new_event_loop()` + `asyncio.set_event_loop()` pattern is unnecessary — it creates a loop that's never used.

### uvloop Usage Verification (D-03)
Confirmed correct across codebase:
- `uvloop.run()` at all CLI entry points: `src/cli/feed.py`, `src/cli/discover.py`
- `install_uvloop()` called once at CLI startup: `src/cli/__init__.py` line 25
- No `asyncio.run()` in `src/`
- No custom event loop creation in async code
- All async primitives use standard library: `asyncio.Semaphore`, `asyncio.gather`, `asyncio.to_thread`

### Resulting File Size (D-04)
After cleanup, `src/utils/asyncio_utils.py` should be ~40 lines (down from 93).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### uvloop Integration
- `src/utils/asyncio_utils.py` — target file for dead code removal
- `src/cli/__init__.py` — where `install_uvloop()` is called at startup
- `src/cli/feed.py` — `uvloop.run()` usage at lines 147, 319, 328, 345
- `src/cli/discover.py` — `uvloop.run()` usage at line 94

### Async Providers
- `src/providers/base.py` — ContentProvider protocol with `crawl_async()` stub
- `src/providers/rss_provider.py` — overrides `crawl_async()` with true async httpx.AsyncClient (Phase 20)
- `src/providers/default_provider.py` — `crawl_async()` raises NotImplementedError
- `src/providers/github_release_provider.py` — `crawl_async()` raises NotImplementedError

### Prior Research
- `.planning/quick/260328-1xu-uvloop/260328-1xu-RESEARCH.md` — existing uvloop best practices research
- `.planning/quick/260328-1xu-uvloop/260328-1xu-PLAN.md` — existing plan for asyncio_utils cleanup
- `.planning/phases/phase-19-uvloop-setup-crawl-async-protocol/19-CONTEXT.md` — Phase 19 context (uvloop foundation)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing `install_uvloop()` pattern in `src/cli/__init__.py` — correct, keep as-is
- All async providers already implement their own `crawl_async()` — no dependency on dead code

### Integration Points
- `install_uvloop()` called at `cli()` group creation — single point of initialization
- All async operations flow through `uvloop.run()` at CLI boundaries

</code_context>

<specifics>
## Specific Ideas

### Dead Code Evidence
`run_in_executor_crawl` docstring says "Use this as the default crawl_async() implementation" but grep shows **zero callers** in the codebase. It was written as infrastructure but never adopted.

The Phase 20 research confirms: "RSSProvider must override this with true async" — meaning `run_in_executor_crawl` was always intended to be replaced, not used.

</specifics>

<deferred>
## Deferred Ideas

None — code review phase with clear findings.

</deferred>
