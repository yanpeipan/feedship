# Quick 260409-ty1: Reorder Deduplication Before LLM Summarize

## Summary

Moved `deduplicate_articles()` to execute BEFORE the `asyncio.gather()` that calls LLM summarize, preventing wasted LLM API calls on duplicate articles.

## Changes

**File:** `src/application/report.py`

| Location | Before | After |
|----------|--------|-------|
| Line ~744 | `all_processed = deduplicate_articles(all_processed)` (after gather) | `articles = deduplicate_articles(articles)` (before gather) |

## Flow Comparison

**Before (WRONG - wasted LLM calls):**
```
articles = list_articles_for_llm()
all_processed = await asyncio.gather(*[bounded_process(a) for a in articles])  # LLM called on ALL articles including duplicates
all_processed = deduplicate_articles(all_processed)  # TOO LATE!
```

**After (CORRECT):**
```
articles = list_articles_for_llm()
articles = deduplicate_articles(articles)  # Remove duplicates FIRST
all_processed = await asyncio.gather(*[bounded_process(a) for a in articles])  # LLM called only on unique articles
```

## Verification

```bash
uv run feedship --debug report --since 2026-04-07 --until 2026-04-10 --language zh
```

## Commit

```
ff01c9e refactor(report): deduplicate before LLM summarize to avoid wasted calls
```

## Self-Check: PASSED

- Module imports correctly
- Deduplication moved before gather
- `pending_writes_v2` batch DB write pattern preserved
- `process_one()` logic unchanged
