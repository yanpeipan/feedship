# Quick Task: BatchClassifyChain - Research

**Task:** 创建BatchClassifyChain类，聚合batch classify相关代码
**Output:** `.planning/quick/260412-r0m-batchclassifychain-batch-classify/260412-r0m-RESEARCH.md`

**Researched:** 2026-04-12
**Domain:** LCEL Runnable + asyncio concurrency pattern
**Confidence:** HIGH (verified against existing codebase patterns)

## Summary

This is a refactoring task to extract batch classify logic from `report_generation.py` into a dedicated `BatchClassifyChain` class. The class wraps `get_classify_translate_chain` with batching, semaphore-based concurrency, and error handling. Implementation should follow the `AsyncLLMWrapper` pattern already in `chains.py`.

## Standard Stack

| Library | Version | Purpose |
|---------|---------|---------|
| langchain-core | 0.3.84 | LCEL Runnable interface |
| asyncio (stdlib) | — | Semaphore concurrency |

## Architecture Patterns

### Pattern: LCEL Runnable with Custom I/O Types

`BatchClassifyChain` deviates from typical LCEL usage (where inputs are prompt values/dicts). It takes `list[ArticleListItem]` and returns `list[ClassifyTranslateItem]`. This is acceptable — Runnable interface is a contract, not a constraint on I/O types.

```python
# Pattern from src/llm/chains.py lines 52-154
class AsyncLLMWrapper(Runnable):
    def invoke(self, input: Any, config: Any = None) -> str:
        """Sync invoke — avoid asyncio.run() in running loop."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self._ainvoke_raw(input, config))
        finally:
            loop.close()

    async def ainvoke(self, input: Any, config: Any = None) -> str:
        return await self._ainvoke_raw(input, config)

    async def abatch(self, inputs: list[Any], config: Any = None) -> list[str]:
        return [await self._ainvoke_raw(i, config) for i in inputs]  # sequential, not concurrent!
```

**Key insight:** `AsyncLLMWrapper.abatch` is sequential (each awaits the previous). This is a limitation — the semaphore should be at the outer `ainvoke` level for true concurrency.

### Pattern: BatchClassifyChain.ainvoke with Semaphore

Based on current implementation in `report_generation.py` lines 118-132:

```python
async def ainvoke(self, input: list[ArticleListItem], config=None) -> list[ClassifyTranslateItem]:
    semaphore = asyncio.Semaphore(self.max_concurrency)

    async def run_with_semaphore(batch: dict) -> list[ClassifyTranslateItem]:
        async with semaphore:
            return await self._run_single_batch(batch)

    results = await asyncio.gather(*[run_with_semaphore(b) for b in batches])
```

**Key insight:** The semaphore limits concurrent batches, not concurrent chains within a batch. Each batch is one LLM call processing 50 articles.

### Pattern: Sync invoke Using new_event_loop

For `invoke()` (sync), use `asyncio.new_event_loop()` pattern (avoids "RuntimeError: asyncio.run() cannot be called from a running event loop"):

```python
def invoke(self, input: list[ArticleListItem], config=None) -> list[ClassifyTranslateItem]:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(self.ainvoke(input, config))
    finally:
        loop.close()
```

## Don't Hand-Roll

| Problem | Use | Source |
|---------|-----|--------|
| Async event loop in sync context | `asyncio.new_event_loop()` + `run_until_complete()` | `src/llm/chains.py:132-136` |
| Concurrency limiting | `asyncio.Semaphore` | `src/application/report/report_generation.py:118` |

## Common Pitfalls

### Pitfall 1: Semaphore in abatch is Ineffective
**What goes wrong:** `abatch` awaits sequentially; semaphore is acquired/released per item, providing no concurrency control across items.
**How to avoid:** Use semaphore at `ainvoke` level (which processes the full batch list), not inside `abatch`.

### Pitfall 2: asyncio.run() in Sync Runnable Methods
**What goes wrong:** `RuntimeError: asyncio.run() cannot be called from a running event loop` when sync `invoke()` is called from async context.
**How to avoid:** Use `asyncio.new_event_loop()` + `run_until_complete()` instead of `asyncio.run()`.

### Pitfall 3: Callable vs Runnable in batch/abatch
**What goes wrong:** `batch([list1, list2])` means "process list1 and list2 as separate inputs", not "process list1 and list2 as a single batch".
**How to avoid:** Document clearly that primary usage is `ainvoke(list_of_articles)`. `batch([[art1, art2], [art3, art4]])` would process two separate article lists.

### Pitfall 4: Semaphore Not Shared Across Invocations
**What goes wrong:** Creating `semaphore = asyncio.Semaphore(MAX_CONCURRENT)` inside `ainvoke` means each invocation has its own semaphore (no cross-call limiting).
**How to avoid:** For true cross-call concurrency limiting, the semaphore should be stored on `self`. However, for this use case (batch-per-report), per-invocation semaphore is acceptable.

## Code Examples

### From report_generation.py (current implementation)
```python
# Lines 42-67: _run_classify_batch
async def _run_classify_batch(
    batch: dict,
    tag_list: str,
    target_lang: str,
) -> list[ClassifyTranslateItem]:
    batch_articles: list[ArticleListItem] = batch["batch_articles"]
    news_list = _build_news_list(batch_articles)
    chain = get_classify_translate_chain(tag_list=tag_list, news_list=news_list, target_lang=target_lang)
    output = await chain.ainvoke({...})
    return output.items

# Lines 105-132: concurrency pattern
BATCH_SIZE = 50
MAX_CONCURRENT = 5
semaphore = asyncio.Semaphore(MAX_CONCURRENT)
async def run_with_semaphore(batch: dict) -> list[ClassifyTranslateItem]:
    async with semaphore:
        return await _run_classify_batch(batch, tag_list, target_lang)
batch_results = await asyncio.gather(*[run_with_semaphore(b) for b in batches])
```

## Integration Points

| Caller | Method | Purpose |
|--------|--------|---------|
| `_entity_report_async` | Calls `cluster_articles_for_report` which calls `_entity_report_async` | The batch classify logic currently inline in `_entity_report_async` will be replaced by `BatchClassifyChain.ainvoke` |

**Refactoring impact:** After this change, `_entity_report_async` (in `report_generation.py`) will:
1. Create `BatchClassifyChain(tag_list, target_lang)` instance
2. Call `chain.ainvoke(filtered)` instead of the inline batching logic
3. Use returned `list[ClassifyTranslateItem]` for tag grouping

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `batch` and `abatch` are optional for this use case | Architecture | `ainvoke` is the primary interface; batch methods follow LCEL convention but may not be used |
| A2 | Semaphore per-invocation is acceptable | Common Pitfalls | No cross-report concurrency limiting needed; each report run is independent |

## Sources

### Primary (HIGH confidence)
- `src/llm/chains.py` lines 52-154 — `AsyncLLMWrapper` pattern (verified)
- `src/application/report/report_generation.py` lines 42-132 — current batching implementation (verified)
- `src/application/summarize.py` lines 224, 278 — asyncio.Semaphore usage (verified)
- `uv pip show langchain-core` — version 0.3.84 (verified)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against codebase
- Architecture: HIGH — based on verified existing patterns
- Pitfalls: HIGH — based on existing code review

**Research date:** 2026-04-12
**Valid until:** 2026-04-19 (30 days, stable domain)
