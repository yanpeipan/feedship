# VERIFICATION: quick-260409-uo1

**Task goal:** 优化LLM调用从730次降至~150次
**Plan:** 260409-uo1-01
**Date:** 2026/04/09

## Status: FAILED

---

## Dimension 1: Must-Haves Artifact Verification

| Must Have (Plan) | Expected | Actual | Status |
|------------------|---------|--------|--------|
| `batch_summarize_articles()` in `src/llm/core.py` | `BATCH_SUMMARIZE_PROMPT` constant + `batch_summarize_articles()` function exported | NOT PRESENT in `src/llm/core.py` | FAIL |
| `_cluster_articles_async` uses `batch_summarize_articles()` | Calls batch function with batch_size=3 | Still calls `summarize_article_content()` per-article (line 720) | FAIL |
| Semaphore changed from 1 to 5 | `asyncio.Semaphore(5)` at line ~748 | `asyncio.Semaphore(1)` at line 748 | FAIL |
| Fallback to `summarize_article_content()` | On batch failure | N/A (batch not used) | N/A |
| `pending_writes_v2` post-gather DB writes | Plan mentions Fix #3 (DB after gather) | PRESENT at lines 706, 726, 766 | PASS |

---

## Dimension 2: Code Evidence

### Finding 1: `batch_summarize_articles` absent from core.py

```bash
$ grep -n "batch_summarize_articles\|BATCH_SUMMARIZE_PROMPT" src/llm/core.py
# (no results)
```

### Finding 2: Per-article summarization still in use

In `_cluster_articles_async` (line 720):
```python
summary, _, quality, _ = await summarize_article_content(
    content, title
)
```
This is a **per-article LLM call**. For 200 articles with `feed_weight >= 0.7`, this alone = ~200 LLM calls. The plan claimed batch_size=3 would reduce this to ~67 calls.

### Finding 3: Semaphore still 1, not 5

```python
# Line 748 in _cluster_articles_async:
semaphore = asyncio.Semaphore(1)  # NOT Semaphore(5)
```

### Finding 4: `_translate_titles_batch_async` has Semaphore(1) not (5)

Line 501:
```python
semaphore = asyncio.Semaphore(1)  # max 2 concurrent LLM calls  # comment is wrong, it's 1
```

---

## Dimension 3: Goal Achievement Analysis

**Plan's claimed reduction:**
- 200 articles / 3 batch_size = 67 calls (vs 600 per-article)
- + 30 cluster calls + 100 title translation = ~197 total

**Actual state (no batch implemented):**
- Summarize: ~200 calls (per-article, unchanged)
- Cluster into topics: ~20-30 calls (unchanged)
- Title translation: batched but Semaphore(1) limits concurrency
- **Total: ~250+ calls** — far from the ~150 goal

**Gap:** The primary optimization (`batch_summarize_articles` with batch_size=3) was never implemented. The LLM call count remains near original levels.

---

## Dimension 4: Scope Sanity

The plan had 2 tasks, both unexecuted. This is not a scope problem — the execution never happened.

---

## Summary

| Dimension | Status |
|-----------|--------|
| Must-haves artifacts | FAIL — `batch_summarize_articles()` not created |
| Core optimization | FAIL — per-article LLM calls unchanged |
| Semaphore concurrency | FAIL — still 1, not 5 |
| Goal achievement | FAIL — calls reduced ~0, not ~580 |

**Recommendation:** Return to planner. Tasks 1 and 2 of plan 01 were not executed. Before re-verification, execute the planned changes or revise the plan to match current codebase state.
