# Verification: Optimize fetch <feed_id> Response Speed

**Date:** 2026-03-27
**Task:** `.planning/quick/260327-jju-python-m-src-cli-fetch-feed-id/PLAN.md`

---

## Must-Have Checks

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | `fetch_one_async_by_id` exists in `src/application/fetch.py` and calls `fetch_one_async` | **PASS** | Lines 234-249: `async def fetch_one_async_by_id(feed_id: str) -> dict` calls `await fetch_one_async(feed)` |
| 2 | `src/cli/feed.py` uses `fetch_one_async_by_id` for single ID case (len(ids) == 1) | **PASS** | Lines 190-203: `if len(ids) == 1:` branch calls `uvloop.run(fetch_one_async_by_id(feed_id))` |
| 3 | Multi-ID case still uses `fetch_ids_async` with semaphore | **PASS** | Lines 204-209: `else:` branch calls `fetch_ids_async(ids, concurrency)` with semaphore concurrency |
| 4 | `python -m py_compile` passes for both files | **PASS** | Both `src/application/fetch.py` and `src/cli/feed.py` compile without errors |

---

## Implementation Summary

**Problem (from plan):** Single feed fetch (`python -m src.cli fetch <feed_id>`) was using `asyncio.to_thread(fetch_one, id)` via `fetch_ids_async`, incurring thread overhead with zero concurrency benefit.

**Solution implemented:**
- Added `fetch_one_async_by_id(feed_id)` at `src/application/fetch.py:234-249` that uses async-native `fetch_one_async(feed)` path
- Updated `src/cli/feed.py:190-203` to call `fetch_one_async_by_id` directly for single ID case
- Multi-ID case (`fetch_ids_async`) unchanged with semaphore concurrency

**Key code paths:**

```
Single ID:  fetch_one_async_by_id(feed_id) -> fetch_one_async(feed) -> provider.crawl_async() + store_article_async()
Multi-ID:   fetch_ids_async(ids, concurrency) -> asyncio.to_thread(fetch_one) [unchanged]
All:        fetch_all_async(concurrency) -> asyncio.Semaphore + fetch_one_async [unchanged]
```

---

## Verification Commands Run

```bash
python -m py_compile src/application/fetch.py  # OK
python -m py_compile src/cli/feed.py           # OK
```

---

**Result:** All must-haves verified. Task goal achieved.
