# Quick Task 260411-0sg: Report Pipeline LLM Call Analysis & Optimization

**Researched:** 2026-04-11
**Confidence:** MEDIUM-HIGH

## Summary

Current pipeline for 3333 articles uses ~85 LLM calls total, with NER (34 calls) and Entity Clustering (50 calls) dominating. The architecture is already well-optimized with batching, concurrency control, and retry logic. The primary optimization opportunity is NER batch_size tuning (10 -> 20-30), which can cut NER calls from 34 to 12-17. Secondary gains exist in pre-NER quality filtering and title translation deduplication (already implemented).

## Current Pipeline Architecture

```
3333 articles (input)
    |
[Layer 0: SignalFilter]
    | quality>=0.6 + feed_weight>=0.5 + dedup by SHA256
    v
~300 articles (after filter)
    |
[Layer 1: NERExtractor] -- batch_size=10, concurrency=3
    | "Articles: [id, title]" each batch
    v
~300 enriched articles with entities
    |
[Layer 2: EntityClusterer] -- max_entities=50, concurrency=5
    | groups articles by entity, LLM call per entity
    v
50 entity topics
    |
[Layer 3: TLDRGenerator] -- top 10 by quality_weight
    | 1 batch call
    v
10 TLDRs
    |
[Layer 4: Title Translation] -- deduplicated, 1 batch
    v
```

## LLM Call Count: 3333 Articles

| Stage | Formula | Calls | Notes |
|-------|---------|-------|-------|
| SignalFilter | 0 (rules) | 0 | No LLM |
| NERExtractor | ceil(300 / 10) | **34** | concurrency=3 |
| EntityClusterer | max_entities=50 | **50** | concurrency=5 |
| TLDRGenerator | 1 | **1** | top 10 entities |
| Title Translation | 1 | **1** | deduplicated unique titles |
| **Total** | | **86** | |

SignalFilter reduces 3333 -> ~300 (10% pass rate). Source: `src/application/report/filter.py` with `quality_threshold=0.6, feed_weight_threshold=0.5`.

### NER Concurrency vs Call Count
- `batch_size=10`, `concurrency=3` = 34 calls (sequential batches in groups of 3)
- Actual concurrency = 3 simultaneous batches of 10 articles
- Time: ~12 batches * ~[LLM latency] / 3 = ~4x faster than sequential

## Optimization Opportunities

### 1. NER Batch Size Tuning (HIGH impact, LOW risk)

**Current:** `batch_size=10`
**Proposal:** `batch_size=20-30`

| batch_size | NER calls | Reduction |
|-------------|-----------|-----------|
| 10 (current) | 34 | baseline |
| 20 | 17 | -50% |
| 30 | 12 | -65% |

**Constraint:** NER chain uses `max_tokens=200` (from `chains.py` line 354). Each batch sends:
```
Article 1 (id=xxx): [title truncated to 200 chars]
Article 2 (id=xxx): [title truncated to 200 chars]
...
```
With `batch_size=30` and average title 15 tokens, total input ~450 tokens + prompt overhead ~100 tokens = ~550 tokens, well within context limits of any model.

**Risk:** Accuracy may degrade with larger batches if articles are heterogeneous. Recommend A/B testing with `batch_size=20` as safe middle ground.

**Implementation:** Change `NERExtractor(batch_size=10)` to `NERExtractor(batch_size=20)` in `src/application/report_generation.py` line 314.

### 2. Entity Clustering Batch (MEDIUM impact, LOW risk)

**Current:** 1 LLM call per entity (50 calls)
**Observation:** Each entity cluster already contains 1-10 articles. The `EntityTopicChain` uses `max_tokens=150` and processes article list as markdown links. Batching multiple entities into one call is architecturally complex since each entity needs a distinct response.

**Status:** Already optimized — entity grouping is the batching mechanism here. 50 entities = 50 calls is near-optimal.

### 3. Pre-NER Quality Filter (MEDIUM impact, MEDIUM risk)

**Current:** SignalFilter runs first, reducing 3333 -> ~300 before NER.
**Opportunity:** Tighten `quality_threshold` from 0.6 to 0.65-0.7, or add a lightweight rule-based pre-filter that skips NER for articles with no entity signals.

**Risk:** May filter valid articles. The current 10% pass rate (~300/3333) is already aggressive.

### 4. Title Translation Deduplication (already done)

Title translation uses in-memory cache (`_title_translate_cache`) and deduplicates via `dict.fromkeys(unique_titles)` before batch call. No action needed.

### 5. TLDR Batch Size (LOW impact)

**Current:** 1 call for top 10 entities.
**Status:** Already optimal. Cannot merge further without losing entity-specific context.

## Optimized Call Count Projection

| Change | Before | After |
|--------|--------|-------|
| NER batch_size 10 -> 20 | 34 calls | 17 calls |
| EntityClusterer (unchanged) | 50 calls | 50 calls |
| TLDRGenerator (unchanged) | 1 call | 1 call |
| Title Translation (unchanged) | 1 call | 1 call |
| **Total** | **86** | **69** |

**Net reduction:** 17 calls (-20%)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Title caching | Custom Redis/cache | In-memory dict (`_title_translate_cache`) |
| Retry logic | Custom exponential backoff | Existing `delays = [2, 4, 8]` in NER, `[1, 2]` in EntityClusterer |
| Concurrency control | Thread pool manually | `asyncio.Semaphore` in NER (3) and EntityClusterer (5) |
| JSON parsing | Manual try/except | `JsonOutputParser` from langchain |

## Common Pitfalls

### 1. NER Batch Size Too Large
**What goes wrong:** Accuracy drops if heterogeneous articles batched together.
**Why it happens:** LLM processes all articles in one context; similar entities may get confused.
**How to avoid:** Test at `batch_size=20` before going to 30. Monitor entity extraction completeness.

### 2. Semaphore Concurrency Mismatch
**What goes wrong:** Setting `concurrency=10` but model rate limits cause cascading retries.
**Current setting:** NER=3, EntityClusterer=5. These are conservative and should not be increased without rate limit testing.
**How to avoid:** Current values are safe. If increasing, test with `--dry-run` first.

### 3. SignalFilter Over-Filtering
**What goes wrong:** Raising threshold too aggressively loses valid articles.
**Current:** `quality_threshold=0.6, feed_weight_threshold=0.5` reduces 3333 -> ~300 (10%).
**How to avoid:** Do not raise quality_threshold above 0.7 without manual review of filtered articles.

## Integration Points

| File | Line | Current Value | Change To |
|------|------|---------------|-----------|
| `src/application/report_generation.py` | 314 | `NERExtractor(batch_size=10)` | `NERExtractor(batch_size=20)` |

## Assumptions Log

| # | Claim | Confidence |
|---|-------|------------|
| A1 | SignalFilter reduces 3333 -> ~300 (10% pass rate) | MEDIUM — depends on actual article quality distribution |
| A2 | NER `max_tokens=200` is the bottleneck, not context window | LOW — not verified with actual token count |

## Sources

- `src/application/report_generation.py` — pipeline orchestration, NER/Clusterer/TLDR instantiation
- `src/application/report/ner.py` — NERExtractor with batch_size and semaphore=3
- `src/application/report/entity_cluster.py` — EntityClusterer with max_entities=50, semaphore=5
- `src/application/report/filter.py` — SignalFilter with quality_threshold=0.6, feed_weight_threshold=0.5
- `src/llm/chains.py` — max_tokens per chain (NER=200, EntityTopic=150, TLDR=300)

## Metadata

**Research date:** 2026-04-11
**Valid until:** 2026-04-18 (pipeline architecture stable)
**Confidence breakdown:** Architecture=High, Call counts=High, Optimization impact=Medium
