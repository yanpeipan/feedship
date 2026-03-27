# Summary: Optimize fetch <feed_id> Response Speed

## Completed Tasks

### Task 1: Add fetch_one_async_by_id to fetch.py
- **File**: `src/application/fetch.py`
- **Changes**:
  - Added `get_feed` to imports (line 14)
  - Added `fetch_one_async_by_id(feed_id)` function (lines 234-247) that:
    - Uses `get_feed()` to resolve feed_id to Feed object
    - Raises `FeedNotFoundError` if feed not found
    - Calls `fetch_one_async(feed)` for async-native path
- **Verification**: `python -m py_compile src/application/fetch.py` passed

### Task 2: Use fetch_one_async_by_id in CLI for single ID
- **File**: `src/cli/feed.py`
- **Changes**:
  - Added `get_feed` to imports from `src.application.feed` (line 11)
  - Added `fetch_one_async_by_id` to imports from `src.application.fetch` (line 17)
  - Modified `fetch()` command (lines 188-205):
    - Single ID case (`len(ids) == 1`): Uses `fetch_one_async_by_id()` directly
    - Multi-ID case: Uses `fetch_ids_async()` with semaphore concurrency (unchanged)
- **Verification**: `python -m py_compile src/cli/feed.py` passed

### Task 3: Multi-ID and --all cases preserved
- **Multi-ID case**: Still uses `fetch_ids_async` with `asyncio.Semaphore` for concurrency
- **--all case**: Unchanged, still uses `fetch_all_async` with semaphore

## Key Changes

| File | Line(s) | Change |
|------|---------|--------|
| `src/application/fetch.py` | 14 | Added `get_feed` to imports |
| `src/application/fetch.py` | 234-247 | Added `fetch_one_async_by_id()` |
| `src/cli/feed.py` | 11 | Added `get_feed` to imports |
| `src/cli/feed.py` | 17 | Added `fetch_one_async_by_id` to imports |
| `src/cli/feed.py` | 188-205 | Branch for single vs multi-ID handling |

## Performance Improvement

**Before**: Single feed fetch used `asyncio.to_thread(fetch_one, id)` which wrapped sync HTTP/SQLite in a thread.

**After**: Single feed fetch uses `fetch_one_async()` which calls:
- `provider.crawl_async()` - true async HTTP
- `store_article_async()` - async SQLite via asyncio.Lock + to_thread
- `add_article_embedding()` - already async via `asyncio.to_thread`

This eliminates unnecessary thread context switches for single-feed fetches.

## Verification Status
- [x] Syntax check: `python -m py_compile` passed for both files
- [x] Runtime verification not possible (torch unavailable in test env)
- [ ] Functional verification pending: requires full environment
