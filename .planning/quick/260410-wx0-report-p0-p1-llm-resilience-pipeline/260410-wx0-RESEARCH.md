# Quick Task Research: Report P0/P1 - LLM Resilience + Pipeline Unification

**Researched:** 2026-04-10
**Domain:** Report generation pipeline (NER/EntityTopic chains, pipeline architecture)
**Confidence:** HIGH (code-based)

## Summary

Two problems need addressing in the report pipeline:

**P0 - LLM Resilience:** The NER and EntityTopic chains silently swallow failures without retry. The fix from last night (title translation) shows the pattern: catch exceptions, return sensible fallback, improve output parsing. Need to apply similar resilience to NER/entity_topic chains.

**P1 - Pipeline Unification:** The entity pipeline (`_entity_report_async`) is the intended path; thematic pipeline (`_cluster_articles_async`) should be deprecated. The migration path is straightforward: entity pipeline already handles failure gracefully by falling back to thematic.

## P0: LLM Resilience

### Current Error Handling State

| Chain | Location | Current Behavior | Has Retry |
|-------|----------|-----------------|-----------|
| NER | `ner.py:51` | Silent fallback to empty entities | No |
| EntityTopic | `entity_cluster.py:101` | Returns fallback EntityTopic (entity name only) | No |
| Title Translation | `report_generation.py` | Robust parsing, skips prompt text | Yes (title fix) |
| Litellm Router | `core.py:296` | `num_retries=2` per provider | Yes (provider-level) |

### Title Translation Fix Pattern (commit 9e94ac4)

The title translation resilience shows the target pattern:
1. **Increase max_tokens** from 80 to 300 for better output capacity
2. **Robust output parsing** - skip quoted strings containing English letters (prompt text detection)
3. **Skip short quotes** - `"直接翻译成中文，不要解释"` (len=10) is skipped
4. **Fix dict unpacking bugs** - correct handling of async return values
5. **Fix cache miss handling** - synchronous call path was missing async invocation

### Recommended Fix for NER Chain

**Current (ner.py:50-68):**
```python
try:
    raw = await chain.ainvoke({"articles_block": articles_block})
    parsed = json_mod.loads(raw) if isinstance(raw, str) else raw
except Exception:
    return [ArticleEnriched(...entities=[]) for a in batch]
```

**Problems:**
- No retry on transient failures
- Silent data loss (all entities for entire batch lost on any error)
- No logging of failure

**Recommended (per-item fallback + retry):**
```python
MAX_NER_RETRIES = 2

async def process_batch(batch, retries=MAX_NER_RETRIES):
    for attempt in range(retries):
        try:
            raw = await chain.ainvoke({"articles_block": articles_block})
            parsed = json_mod.loads(raw) if isinstance(raw, str) else raw
            # validate structure before breaking
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, KeyError) as e:
            if attempt == retries - 1:
                logger.warning(f"NER failed after {retries} attempts: {e}")
                break
            await asyncio.sleep(1 * (attempt + 1))  # backoff
    # Fallback: return batch with empty entities (not whole batch lost)
    return [{"id": a["id"], "entities": []} for a in batch]
```

**Key insight:** Per-item fallback (return empty entities for that batch) is better than whole-batch failure. The batch structure is preserved; articles still appear in report with no entities.

### Recommended Fix for EntityTopic Chain

**Current (entity_cluster.py:101-122):**
```python
try:
    result = await chain.ainvoke({...})
except Exception:
    return EntityTopic(entity_id=entity_id, entity_name=entity_name,
        layer="AI应用", headline=entity_name[:30], ...)
```

This is actually the correct pattern - graceful degradation to entity name only. The issue is there is **no retry** before falling back. Adding one retry would improve quality:

```python
for attempt in range(2):
    try:
        result = await chain.ainvoke({...})
        break
    except Exception as e:
        if attempt == 1:
            logger.warning(f"EntityTopic failed for {entity_name}: {e}")
            return fallback_entity_topic(entity_id, entity_name, entity_articles)
        await asyncio.sleep(0.5)
```

### LCEL Resilience Options

| Pattern | When to Use | Implementation |
|---------|-------------|----------------|
| Per-item fallback | Transient failures, partial data OK | try/except with fallback value |
| Batch retry with backoff | Transient failures, need full data | loop with sleep backoff |
| Circuit breaker | Repeated failures on same endpoint | litellm Router already handles |
| Pipeline-level fallback | Complete failure needs alternative | `_entity_report_async` falls back to `_cluster_articles_async` |

**Litellm Router already has `num_retries=2`** - so provider-level failures are already retried. The issue is **application-level errors** (JSON parsing, bad output format) that don't trigger Router retries.

## P1: Pipeline Unification

### Pipeline Comparison

| Feature | Thematic (`_cluster_articles_async`) | Entity (`_entity_report_async`) |
|---------|--------------------------------------|-------------------------------|
| Clustering | `_cluster_articles_into_topics` (semantic) | EntityClusterer (entity-based) |
| NER | No | Yes (LLM batch) |
| Headline generation | topic_title chain | entity_topic chain |
| Signal classification | Rule-based (leverage/business/creation) | No (computed differently) |
| TLDR | No | Yes (top 10) |
| Rendered output | Jinja2 template | `render_entity_report` |
| ChromaDB usage | Level 3 dedup (optional) | None (dedup done earlier) |
| Failure fallback | None | Falls back to thematic |

### Features Unique to Thematic Pipeline

1. **Signal sections** (`leverage`, `business`, `creation`) - rule-based classification not present in entity pipeline
2. **Creation clustering** (`creation_sections`) - separate clustering for creation-themed articles
3. **feed_id grouping fallback** - when ChromaDB fails, groups by `feed_id` instead

### Features Unique to Entity Pipeline

1. **NER extraction** - entities are extracted and stored
2. **Dimension classification** - `release`, `funding`, `research`, `ecosystem`, `policy`
3. **Entity grouping** - articles grouped by normalized entity name
4. **Top-10 TLDR** - single LLM call generates TLDR for top 10 entities
5. **Better failure handling** - falls back to thematic on any exception

### ChromaDB Usage Differences

**Thematic pipeline:**
- Uses ChromaDB for Level 3 embedding-based deduplication (`deduplicate_articles` -> `_level3_embedding_dedup`)
- Falls back to feed_id grouping if ChromaDB unavailable

**Entity pipeline:**
- No ChromaDB usage in the pipeline itself
- Assumes dedup already done before pipeline (via `deduplicate_articles` at caller)

### Migration Path

The entity pipeline is the intended direction. Deprecating thematic:

1. **Keep entity pipeline as primary** - already handles failures gracefully
2. **Remove `_cluster_articles_async` fallback** - once entity pipeline is stable, the fallback is unnecessary
3. **Add signal classification to entity pipeline** - if leverage/business signals are needed, add as post-processing step
4. **Optionally add creation detection** - can be done via dimension classification (policy dimension catches regulation)

**Simplest approach:** The entity pipeline already produces equivalent output structure (`layers`, `signals`, `creation`). The only missing piece is signal classification. Add rule-based signal classification as post-processing step after entity clustering:

```python
# After entity_topics are generated
for topic in entity_topics:
    topic.signals = classify_signals(topic)  # leverage/business
```

## Common Pitfalls

### Pitfall 1: Silent Data Loss
**What:** NER chain returns empty entities on failure, article appears in report without entities
**How to avoid:** Log warnings when fallback is triggered, add metrics for fallback rate

### Pitfall 2: Batch-Level Retry Without Per-Item Fallback
**What:** Retrying entire batch wastes LLM quota when transient failures affect one item
**How to avoid:** Per-item fallback is better than per-batch retry

### Pitfall 3: Pipeline Coupling
**What:** `_entity_report_async` imports from `src.application.entity_report` which imports from `src.application.report` packages
**How to avoid:** The current structure is fine - just ensure failures are handled gracefully at pipeline boundary

## Open Questions

1. **Should NER failures be retried?** Currently returns empty entities (graceful). Adding 1 retry might improve quality without risking long waits.

2. **Are signal sections (`leverage`, `business`, `creation`) used by templates?** If not used, no need to add to entity pipeline.

3. **Should the thematic pipeline be removed entirely?** If entity pipeline is stable, removing thematic reduces maintenance burden.

## Sources

- `src/llm/chains.py` - AsyncLLMWrapper and LCEL chain definitions
- `src/llm/core.py` - LLMClient with litellm Router (num_retries=2)
- `src/application/report/ner.py` - NERExtractor with current error handling
- `src/application/report/entity_cluster.py` - EntityClusterer with fallback pattern
- `src/application/report_generation.py` - Both pipelines, title translation fix
- `src/application/entity_report/__init__.py` - Entity pipeline exports
