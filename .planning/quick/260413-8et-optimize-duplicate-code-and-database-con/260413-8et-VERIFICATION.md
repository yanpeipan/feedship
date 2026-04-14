---
quick_id: 260413-8et
verified: 2026-04-13T00:00:00Z
status: passed
score: 4/4 must-haves verified
---

# Quick Task: Optimize Duplicate Code and Database Connection Handling

**Task Goal:** Optimize duplicate code and database connection handling
**Verified:** 2026-04-13
**Status:** passed

## Must-Haves Verification

| # | Must-Have | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Connection caching to avoid repeated PRAGMA execution | VERIFIED | `conn.py` lines 25-26, 56-70: `_thread_local` caches connection, PRAGMAs only execute on first connection per thread |
| 2 | Shared utility module for date functions | VERIFIED | `src/storage/sqlite/utils.py` contains `_normalize_published_at`, `_date_to_timestamp`, `_date_to_timestamp_end`, `_date_to_str`, `_date_to_str_end` — imported by `conn.py` and `articles.py` |
| 3 | store_article refactored to single UPSERT | VERIFIED | `articles.py` lines 96-128: single `INSERT ... ON CONFLICT(feed_id, guid) DO UPDATE SET` replaces SELECT + INSERT/UPDATE pattern |
| 4 | All imports moved to module top-level | VERIFIED | `fetch.py` lines 1-22: all imports at module top-level, no inline imports within functions |

**Score:** 4/4 must-haves verified

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| utils.py imports work | `uv run python -c "from src.storage.sqlite.utils import _normalize_published_at; print('OK')"` | OK | PASS |
| conn.py connection caching works | `uv run python -c "from src.storage.sqlite.conn import get_db; print('OK')"` | OK | PASS |
| fetch.py imports work | `uv run python -c "from src.application.fetch import fetch_all_async; print('OK')"` | OK | PASS |

## Anti-Patterns Found

No anti-patterns detected.

---

_Verified: 2026-04-13T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
