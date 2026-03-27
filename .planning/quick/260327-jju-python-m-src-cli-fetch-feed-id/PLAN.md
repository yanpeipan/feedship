---
must_haves:
  - truth: "fetch_ids_async calls asyncio.to_thread(fetch_one, id) for sync fetch_one - wastes thread overhead"
  - truth: "fetch_one_async properly uses crawl_async + store_article_async (async-native)"
  - truth: "Single feed fetch should use async-native path, not asyncio.to_thread"
  - artifact: "src/application/fetch.py - add fetch_one_async_by_id"
  - artifact: "src/cli/feed.py - use fetch_one_async_by_id for single ID case"
  - artifact: "Multi-ID case continues using fetch_ids_async with semaphore"
gsd_type: quick
quick_mode: true
---

# Plan: Optimize fetch <feed_id> Response Speed

## Problem

When running `python -m src.cli fetch ee4914f0-5aac-437d-b210-c2d8cb39afa2` (single feed ID):

1. `fetch_ids_async` at line 190 calls `asyncio.to_thread(fetch_one, id)`
2. `fetch_one` (sync) does `provider.crawl()` (sync HTTP) + `store_article()` (sync SQLite)
3. Thread overhead with zero concurrency benefit for single feed

## Solution

Create `fetch_one_async_by_id` that uses the async-native `fetch_one_async` path:
- `provider.crawl_async()` - true async HTTP
- `store_article_async()` - async SQLite writes
- `add_article_embedding` - already async via `asyncio.to_thread`

## Tasks

### Task 1: Add fetch_one_async_by_id to fetch.py

```python
async def fetch_one_async_by_id(feed_id: str) -> dict:
    """Fetch one feed by ID using async-native path."""
    feed = get_feed(feed_id)
    if not feed:
        raise FeedNotFoundError(f"Feed not found: {feed_id}")
    return await fetch_one_async(feed)
```

**Files:** `src/application/fetch.py`
**Action:** Add `fetch_one_async_by_id` function before `fetch_ids_async`
**Verify:** `grep -n "fetch_one_async_by_id" src/application/fetch.py`
**Done:** When function is added and imports are correct

### Task 2: Use fetch_one_async_by_id in CLI for single ID

**Files:** `src/cli/feed.py`
**Action:**
- Import `fetch_one_async_by_id` from `src.application.fetch`
- In `fetch()` command (line 187-197), replace `fetch_ids_async([id], concurrency)` with `fetch_one_async_by_id(id)` for single ID case
- The result format differs: `fetch_one_async_by_id` returns dict directly, `fetch_ids_async` is an async generator

**Verify:** `python -m src.cli fetch --help` shows correct usage
**Done:** When `python -m src.cli fetch <single_id>` uses async path without `asyncio.to_thread`

### Task 3: Verify multi-ID still works

**Action:** Ensure `--all` and multi-ID cases still use `fetch_ids_async` with semaphore concurrency
**Verify:** `python -m src.cli fetch --all` works correctly
**Done:** All existing fetch modes work correctly

## Key Files

| File | Change |
|------|--------|
| `src/application/fetch.py` | Add `fetch_one_async_by_id` |
| `src/cli/feed.py` | Use `fetch_one_async_by_id` for single ID case |

## Verification Commands

```bash
# Single ID - should use async-native path
python -m src.cli fetch ee4914f0-5aac-437d-b210-c2d8cb39afa2

# Multi-ID - should use semaphore concurrency
python -m src.cli fetch id1 id2 id3

# All feeds - should use semaphore concurrency
python -m src.cli fetch --all
```
