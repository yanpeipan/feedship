# Research: LangChain LCEL Optimization for BatchClassifyChain

**Date:** 2026-04-13
**Focus:** LCEL RunnableLambda factory, 529 overload retry, streaming patterns
**Confidence:** MEDIUM-HIGH (verified against langchain-core 1.2.28, litellm exceptions)

## Summary

The existing optimization plan is mostly sound but has one critical API error: the `retry_on` parameter in Task 11 does not exist in langchain-core 1.2.28. The correct parameter is `retry_if_exception_type`. The current `LLMWrapper` implementation already handles 529 errors correctly via `InternalServerError` in `_RETRY_TYPES`, so no changes are needed there.

**Primary recommendation:** Fix the plan's retry syntax, keep the current `LLMWrapper.with_retry()` approach, and clarify that `dedup_streaming` is not true streaming but a memory-efficient in-memory pass.

---

## Finding 1: LCEL RunnableLambda Factory Pattern

### Correct Pattern (langchain-core 1.2.28)

```python
from langchain_core.runnables import RunnableLambda

async def classify_fn(articles: list) -> list:
    # async logic here
    return articles

runnable = RunnableLambda(classify_fn)
```

You pass the async function **directly** to `RunnableLambda()` - no `.from_lambda()` or wrapper needed. The `afunc` parameter exists in `__init__` but passing the async function positionally works.

### Key Verification

```python
# Verified working in langchain-core 1.2.28:
async def async_fn(x):
    return x * 2

rl = RunnableLambda(async_fn)
result = asyncio.run(rl.ainvoke([1, 2, 3]))  # Works
```

### Plan Assessment

The factory functions proposed in Tasks 5-7 are syntactically correct. The pattern:
```python
def make_classify_runnable(...) -> Runnable:
    async def classify_fn(articles: list) -> list:
        ...
    return RunnableLambda(classify_fn)
```

This is the standard LCEL pattern. **No issues found.**

---

## Finding 2: 529 Overload Retry Strategy

### Critical Fix Needed

**Plan has an API error.** The plan (Task 11) suggests:
```python
.with_retry(stop_after_attempt=2, retry_on=["RateLimitError", "APITimeoutError"])
```

**But `retry_on` does not exist in langchain-core 1.2.28.** The correct API is:

```python
.with_retry(
    stop_after_attempt=2,
    retry_if_exception_type=(RateLimitError, APITimeoutError),
    wait_exponential_jitter=True,  # default
)
```

Verified via inspection:
```
with_retry(self, *, retry_if_exception_type, wait_exponential_jitter,
            exponential_jitter_params, stop_after_attempt)
```

### Current Implementation Status

The `LLMWrapper` in `src/llm/core.py` already handles 529 correctly:

```python
_RETRY_TYPES = (
    RateLimitError,
    APIConnectionError,
    Timeout,
    JSONSchemaValidationError,
    InternalServerError,  # ← Covers 529 Service Unavailable
)
```

And the retry config:
```python
_retry_config = {
    "stop_after_attempt": 2,
    "retry_if_exception_type": self._RETRY_TYPES,
}
```

**The Router has `num_retries=0`** to avoid double-retry (Router + LLMWrapper both retry would worsen overload cascading).

**The Router has `default_max_parallel_requests=3`** to limit concurrency and reduce 529 errors proactively.

### Conclusion

The retry logic is already correct in `core.py`. Task 11 of the plan should be **skipped or corrected** to use `retry_if_exception_type` instead of `retry_on`.

---

## Finding 3: Streaming with Generator

### Current `dedup_streaming` is NOT True Streaming

```python
def dedup_streaming(articles: list[ArticleListItem]) -> list[ArticleListItem]:
    """Streaming-friendly Level 1 (exact) dedup..."""
    seen: dict[str, ArticleListItem] = {}
    for a in articles:
        ...
    return list(seen.values())  # ← Returns list, not generator
```

This function takes a list, processes in a single pass (memory-efficient), and returns a list. It is **not** a generator and does not yield. The docstring is misleading - it says "Yields" but the implementation returns a list.

### True Streaming with RunnableGenerator

For actual streaming (generator in, generator out), LangChain uses:

```python
from langchain_core.runnables import RunnableGenerator

def my_generator(input):
    for item in input:
        yield processed_item

runnable = RunnableGenerator.from_generator(my_generator)
```

Or with async:

```python
async def my_async_generator(input):
    for item in input:
        yield processed_item

runnable = RunnableGenerator.from_generator(my_async_generator)
```

### Recommendation for This Project

True streaming through the entire LCEL chain would require significant re-architecture. The current in-memory pass approach (`dedup_streaming` → `filter` → `chain.ainvoke`) is appropriate for this use case because:

1. Articles are already in memory (fetched from SQLite)
2. The dedup is a single-pass, O(n) operation
3. Changing to true generators would complicate the chain composition significantly

**Suggested fix:** Rename `dedup_streaming` to `dedup_inmem` or fix the docstring to match the implementation. The function does NOT yield despite what the docstring claims.

---

## Integration Points with Existing Codebase

### Files That Need Changes (Based on Plan)

| File | Changes | Risk |
|------|---------|------|
| `src/llm/chains.py` | Add 3 factory functions | LOW - additive |
| `src/application/report/classify.py` | Deprecate BatchClassifyChain | LOW - class kept for compat |
| `src/application/report/generator.py` | Update chain composition | MEDIUM - replace class with factory |
| `src/application/dedup.py` | Add streaming dedup functions | LOW - additive |
| `src/application/report/filter.py` | Remove dedup from SignalFilter | MEDIUM - behavioral change |

### No Changes Needed

- `src/llm/core.py` - Retry logic already correct
- `src/application/report/tldr.py` - Can be deprecated after migration
- `src/application/report/models.py` - BuildReportDataChain can be deprecated

---

## Potential Issues

### Issue 1: Plan's Retry Syntax Will Fail at Runtime

If Task 11 is implemented as written, it will raise a `TypeError` because `retry_on` is not a valid parameter for `with_retry()` in langchain-core 1.2.28.

**Fix:** Use `retry_if_exception_type` instead.

### Issue 2: `dedup_streaming` Docstring Mismatch

The function claims to yield but actually returns a list. This could confuse future maintainers.

**Fix:** Either make it a true generator (yield-based) or fix the docstring.

### Issue 3: Factory Functions Lose Type Information

When you wrap async logic in `RunnableLambda`, the resulting `Runnable` loses the specific return type hints. This is standard LCEL behavior but means downstream code must rely on duck typing.

**Mitigation:** The existing code already does this (all chains return `list[ArticleListItem]` or `ReportData`), so no change needed.

---

## Recommendations

1. **Fix Task 11** to use `retry_if_exception_type=(RateLimitError, APITimeoutError)` instead of `retry_on=[...]`

2. **Skip Task 11 entirely** since `LLMWrapper` already has correct retry logic

3. **Clarify `dedup_streaming`** - either fix docstring or make it a true generator

4. **Keep BatchClassifyChain/TLDRChain/BuildReportDataChain classes** as deprecated but functional - they provide backward compatibility

---

## Verified Behavior

| Check | Result | Source |
|-------|--------|--------|
| `RunnableLambda(async_fn)` works | Verified | `uv run python -c "..."` |
| `with_retry` params in 1.2.28 | `retry_if_exception_type`, not `retry_on` | Inspected via `inspect.signature` |
| `InternalServerError` covers 529 | Verified | litellm exception hierarchy |
| `default_max_parallel_requests=3` | Reduces 529 | Plan docs |

---

## Sources

- langchain-core 1.2.28 (verified via `uv pip show` and `inspect.signature`)
- litellm exceptions (verified via `uv run python -c "..."`)
- Existing codebase: `src/llm/core.py`, `src/application/report/classify.py`, `src/application/dedup.py`
