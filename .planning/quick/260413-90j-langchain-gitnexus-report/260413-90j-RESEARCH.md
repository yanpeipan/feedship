# Quick Task 260413-90j: LangChain Best Practices Research

**Task:** Research LangChain LCEL best practices and optimize feedship report module using GitNexus

## LangChain LCEL Best Practices

### 1. RunnableLambda vs Custom Chains

**Best Practice:** Prefer standard LCEL components (RunnableLambda, RunnableGenerator) over custom Chain classes.

- `RunnableLambda` — sync/async functions wrapped as Runnables
- `RunnableGenerator` — for generator-based streaming
- **Anti-pattern:** Subclassing `Chain` class directly (like the current `BatchClassifyChain`, `TLDRChain`, `BuildReportDataChain`)

### 2. LCEL Composition Pattern

```python
# Recommended factory pattern
from langchain_core.runnables import RunnableLambda

def make_classify_runnable(tag_list: str, target_lang: str) -> Runnable:
    async def classify_fn(articles: list) -> list:
        # async logic here
        return articles
    return RunnableLambda(classify_fn)

# Chain composition
chain = (
    make_classify_runnable(...)
    | make_build_report_runnable(...)
    | make_tldr_runnable(...)
)
```

### 3. Streaming with RunnableGenerator

For streaming output, use `RunnableGenerator`:

```python
from langchain_core.runnables import RunnableGenerator

def streaming_fn(input):
    for item in input:
        yield item

RunnableLambda(streaming_fn)  # sync
RunnableGenerator(streaming_fn)  # async generator
```

### 4. Event Loop Management

**Critical Bug Found:** `asyncio.new_event_loop()` + `loop.run_until_complete()` + `loop.close()` in sync `invoke()` methods causes event loop leaks.

**Correct Pattern:**
```python
def invoke(self, input, config=None):
    try:
        loop = asyncio.get_running_loop()
        return loop.run_until_complete(self.ainvoke(input, config))
    except RuntimeError:
        return asyncio.run(self.ainvoke(input, config))
```

### 5. Retry Configuration

Use `.with_retry()` on LCEL chains:

```python
chain = (prompt | llm | parser).with_retry(
    stop_after_attempt=2,
    retry_on=["RateLimitError", "APITimeoutError"]
)
```

### 6. Streaming Dedup Pattern

For memory-efficient deduplication in streaming pipelines:

```python
def dedup_streaming(articles):
    seen = {}
    for a in articles:
        if a.content_hash not in seen:
            seen[a.content_hash] = a
            yield a
```

## GitNexus Analysis Findings

### Report Module Hot Paths (from GitNexus)
- `cluster_articles_for_report` — main entry
- `_entity_report_async` — 5-layer pipeline
- `BatchClassifyChain.invoke/ainvoke` — LLM batching
- `SignalFilter.filter` — quality gating

### Critical Issues Identified

1. **Event loop leak** — `BatchClassifyChain`, `TLDRChain`, `BuildReportDataChain` all use `asyncio.new_event_loop()` in `invoke()`
2. **Write lock duplication** — `_get_db_write_lock` defined in both `conn.py` and `articles.py`
3. **Freshness computation waste** — `_compute_article_item` always computes `freshness` even when not needed
4. **Streaming dedup missing** — dedup stores all articles in memory before filtering

## Integration Points

| Component | Role | File |
|-----------|------|------|
| `src/llm/chains.py` | Factory functions for LCEL runnables | Factory registry |
| `src/application/report/classify.py` | `BatchClassifyChain` → RunnableLambda | To refactor |
| `src/application/report/tldr.py` | `TLDRChain` → RunnableLambda | To refactor |
| `src/application/report/models.py` | `BuildReportDataChain` → RunnableLambda | To refactor |
| `src/application/report/generator.py` | Pipeline composition | Already uses LCEL |
| `src/application/dedup.py` | Streaming dedup functions | Needs new functions |
| `src/application/report/filter.py` | SHA256 dedup (to be removed) | Deduplicated |
| `src/storage/sqlite/conn.py` | Write lock (single source) | Already fixed |
| `src/storage/sqlite/articles.py` | Write lock import, freshness opt | Already fixed |

## Risks

1. LCEL migration may change error handling behavior
2. Streaming dedup must maintain exact dedup guarantees
3. Retry wrapper may change failure modes
4. Removing dedup from SignalFilter requires full integration testing
