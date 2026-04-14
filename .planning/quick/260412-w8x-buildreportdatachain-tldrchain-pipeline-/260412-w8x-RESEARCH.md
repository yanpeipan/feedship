# Phase Quick: BuildReportDataChain + TLDRChain pipeline refactor - Research

**Researched:** 2026/04/12
**Domain:** LangChain Runnable implementation + recursive cluster tree traversal
**Confidence:** HIGH

## Summary

Two new async LCEL Runnable chains are needed in the report generation pipeline:

1. **BuildReportDataChain (Layer 3)** wraps `ReportData.add_articles() + build()` as a LangChain Runnable. These are sync CPU operations with no I/O, so the chain simply calls them inline within `ainvoke`.

2. **TLDRChain (Layer 4)** traverses all clusters recursively (including `cluster.children`), batches entities with articles into calls to `get_tldr_chain`, and writes results to `cluster.summary`.

**Primary recommendation:** Follow `BatchClassifyChain` pattern exactly for both chains — `ainvoke`/`invoke`/`abatch`/`batch` interface, semaphore concurrency for TLDR.

## Standard Stack

| Library | Version | Purpose |
|---------|---------|---------|
| langchain-core | latest | `Runnable` base class |
| asyncio | stdlib | Semaphore concurrency |

**Installation:** No new packages — all dependencies already in project.

## Architecture Patterns

### Pattern 1: BuildReportDataChain as Runnable

**What:** Sync CPU ops (`add_articles`, `build`) wrapped as async LCEL Runnable.

**When to use:** Layer 3, after `BatchClassifyChain` mutates articles with tags/translation.

**Implementation:**

```python
class BuildReportDataChain(Runnable):
    """Input: (filtered_articles, heading_tree). Output: ReportData."""

    def __init__(self, target_lang: str = "zh"):
        self.target_lang = target_lang

    async def ainvoke(self, input: tuple[list[ArticleListItem], HeadingNode | None], config=None) -> ReportData:
        filtered, heading_tree = input
        report_data = ReportData(
            clusters={},
            date_range={},
            target_lang=self.target_lang,
            heading_tree=heading_tree,
        )
        report_data.add_articles(filtered, lambda a: a.tags[0] if a.tags else "unknown")
        report_data.build(heading_tree)
        return report_data

    def invoke(self, input, config=None) -> ReportData:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.ainvoke(input, config))
        finally:
            loop.close()

    async def abatch(self, inputs: list, config=None) -> list[ReportData]:
        return [await self.ainvoke(inp, config) for inp in inputs]

    def batch(self, inputs: list, config=None) -> list[ReportData]:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.abatch(inputs, config))
        finally:
            loop.close()
```

**Key insight:** No I/O — just CPU ops. No semaphore needed. Just wraps sync calls in async signature.

### Pattern 2: TLDRChain with recursive cluster traversal

**What:** Traverses ALL clusters (including `cluster.children`) recursively, batches entities per call to `get_tldr_chain`, writes to `cluster.summary`.

**When to use:** Layer 4, after `ReportData` is built.

**Recursive traversal helper:**

```python
def collect_all_clusters(
    clusters: dict[str, list[ReportCluster]]
) -> list[ReportCluster]:
    """Flatten all clusters including nested children into a single list."""
    all_clusters = []
    for cluster_list in clusters.values():
        all_clusters.extend(_flatten_cluster_list(cluster_list))
    return all_clusters

def _flatten_cluster_list(cluster_list: list[ReportCluster]) -> list[ReportCluster]:
    result = []
    for cluster in cluster_list:
        result.append(cluster)
        if cluster.children:
            result.extend(_flatten_cluster_list(cluster.children))
    return result
```

**Batching per call to `get_tldr_chain`:**

The `get_tldr_chain` batches multiple entities per call via `topics_block` string. The chain expects JSON output with `entity_id` and `tldr` fields per `TLDRItem`.

```python
async def _generate_tldr_for_batch(
    clusters: list[ReportCluster],
    target_lang: str,
    batch_size: int = 20,
) -> None:
    """Build topics_block string, call get_tldr_chain, write to cluster.summary."""
    import json

    topics_block = "\n".join(
        f"Entity {i + 1} ({c.name}): {c.articles[0].translation or c.articles[0].title or ''}"
        for i, c in enumerate(clusters)
    )
    chain = get_tldr_chain()
    try:
        raw = await chain.ainvoke({"topics_block": topics_block, "target_lang": target_lang})
        # raw is already parsed as list[TLDRItem] due to JsonOutputParser
        tldr_map = {item.entity_id: item.tldr for item in raw}
        for cluster in clusters:
            cluster.summary = tldr_map.get(cluster.name, "")
    except Exception as e:
        logger.warning("TLDR batch failed: %s", e)
```

**Full TLDRChain class:**

```python
class TLDRChain(Runnable):
    def __init__(self, top_n: int = 100, target_lang: str = "zh", batch_size: int = 20):
        self.top_n = top_n
        self.target_lang = target_lang
        self.batch_size = batch_size

    async def ainvoke(self, input: ReportData, config=None) -> ReportData:
        all_clusters = collect_all_clusters(input.clusters)
        # Filter clusters that have articles
        clusters_with_articles = [c for c in all_clusters if c.articles]
        # Optionally limit to top_n
        clusters_with_articles = clusters_with_articles[:self.top_n]

        # Process in batches
        for i in range(0, len(clusters_with_articles), self.batch_size):
            batch = clusters_with_articles[i:i + self.batch_size]
            await self._generate_tldr_for_batch(batch, input.target_lang)

        return input

    def invoke(self, input: ReportData, config=None) -> ReportData:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.ainvoke(input, config))
        finally:
            loop.close()
```

## Integration Points

### In `_entity_report_async`:

Current code (lines 71-79):
```python
# Layer 3: Build clusters incrementally via add_articles
report_data = ReportData(...)
report_data.add_articles(filtered, lambda a: a.tags[0] if a.tags else "unknown")
report_data.build(heading_tree)
```

Refactored to use chains:
```python
# Layer 3: BuildReportDataChain
build_chain = BuildReportDataChain(target_lang=target_lang)
report_data = await build_chain.ainvoke((filtered, heading_tree))

# Layer 4: TLDRChain (after Layer 3 completes)
tldr_chain = TLDRChain(top_n=100, target_lang=target_lang)
report_data = await tldr_chain.ainvoke(report_data)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async Runnable interface | Custom async class without proper LCEL methods | Subclass `Runnable`, implement `ainvoke/invoke/abatch/batch` | LCEL integration, proper config passthrough |
| Recursive cluster traversal | Multiple loops without handling children | `_flatten_cluster_list` helper | Children can nest to arbitrary depth |
| Event loop in sync wrapper | `asyncio.run()` in sync invoke | `asyncio.new_event_loop()` pattern from BatchClassifyChain | Avoids "cannot run from running loop" error |
| TLDR batching | One call per cluster | Batch multiple entities via `topics_block` string | `get_tldr_chain` already designed for batching |

## Common Pitfalls

### Pitfall 1: Using old TLDRGenerator with wrong model fields

**What goes wrong:** `TLDRGenerator.generate_top10()` references `t.entity_name`, `t.headline`, `topic.tldr`, and `quality_weight` — none of which exist on `ReportCluster`.

**How to avoid:** The new `TLDRChain` uses `cluster.name` (entity_id) and `cluster.summary` (tldr output target). Article title/translation comes from `cluster.articles[0].translation` or `.title`.

**Warning signs:** `AttributeError` on `entity_name` or `headline` when running TLDR.

### Pitfall 2: Recursive traversal misses children

**What goes wrong:** Iterating only `clusters.values()` top-level dict misses clusters inside `cluster.children`.

**How to avoid:** Use `_flatten_cluster_list` which recurses into `cluster.children`.

### Pitfall 3: `asyncio.run()` inside async context

**What goes wrong:** `invoke()` sync wrapper using `asyncio.run()` will crash if called from within an already-running event loop.

**How to avoid:** Use `asyncio.new_event_loop()` pattern (see `BatchClassifyChain.invoke` lines 130-134).

### Pitfall 4: TLDR batch too large

**What goes wrong:** `get_tldr_chain` has implicit limits — sending 100+ entities in one `topics_block` may cause prompt overflow or degraded output.

**How to avoid:** Batch size of 20 (default) keeps prompt manageable. `top_n=100` means 5 batches at most.

### Pitfall 5: Empty cluster summary on error

**What goes wrong:** `get_tldr_chain` call fails silently (caught exception), `cluster.summary` remains `""`.

**How to avoid:** Log warning with batch offset (matching `BatchClassifyChain` pattern). Consider partial results — one bad batch should not affect others.

## Code Examples

### Wiring TLDRChain after BuildReportDataChain in `_entity_report_async`

```python
# After Layer 2 (BatchClassifyChain) completes — filtered has .tags and .translation

# Layer 3
build_chain = BuildReportDataChain(target_lang=target_lang)
report_data = await build_chain.ainvoke((filtered, heading_tree))

# Layer 4
tldr_chain = TLDRChain(top_n=100, target_lang=target_lang)
await tldr_chain.ainvoke(report_data)

# report_data.clusters now has cluster.summary populated for clusters with articles
return report_data
```

### Collect all clusters recursively (verified pattern)

```python
def _collect_clusters_recursive(
    clusters: dict[str, list[ReportCluster]]
) -> list[ReportCluster]:
    """Flatten all clusters including nested children."""
    result = []
    for cluster_list in clusters.values():
        result.extend(_flatten_list(cluster_list))
    return result

def _flatten_list(cluster_list: list[ReportCluster]) -> list[ReportCluster]:
    flat = []
    for cluster in cluster_list:
        flat.append(cluster)
        if cluster.children:
            flat.extend(_flatten_list(cluster.children))
    return flat
```

### TLDR input format from cluster

```python
# Use first article's translation (or title fallback) as the "headline" for the cluster
article = cluster.articles[0]
headline = article.translation or article.title or ""
# entity_id = cluster.name (unique within report)
# tldr output → cluster.summary
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `get_tldr_chain` output is `list[TLDRItem]` (JsonOutputParser parses automatically) | TLDRChain batching | Medium — if parser returns raw string, need `json.loads()` |
| A2 | `ReportCluster.summary` is the correct field for TLDR output | TLDRChain | Low — matches `ReportCluster` model |
| A3 | `cluster.articles[0].translation` is populated when TLDR runs | TLDRChain | Low — Layer 2 populates it before Layer 3 |

## Open Questions

1. **Should `top_n` limit apply before or after filtering clusters with articles?**
   - Current design: filter to clusters with articles first, then slice top_n
   - Clarify: if a cluster has no articles, should it even appear in the report?

2. **Should TLDR failures leave `cluster.summary` empty string or preserve previous value?**
   - Current design (following `BatchClassifyChain`): silent failure → empty string
   - Could add retry logic for partial failures

3. **What about clusters with zero articles after `build()`?**
   - They get created as empty clusters from `heading_tree` matching
   - `TLDRChain` filters them out via `if c.articles`
   - Is this correct behavior?

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest.ini (existing) |
| Quick run | `pytest tests/ -x -q` |
| Full suite | `pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Command |
|--------|----------|-----------|---------|
| QK-01 | BuildReportDataChain.ainvoke returns ReportData with clusters | unit | `pytest tests/test_report.py -k "test_build_report_data_chain" -x` |
| QK-02 | TLDRChain recursively visits all clusters including children | unit | `pytest tests/test_report.py -k "test_tldr_chain_traverses_children" -x` |
| QK-03 | TLDRChain batches entities per get_tldr_chain call | unit | `pytest tests/test_report.py -k "test_tldr_chain_batching" -x` |
| QK-04 | TLDRChain writes to cluster.summary | unit | `pytest tests/test_report.py -k "test_tldr_chain_writes_summary" -x` |

### Wave 0 Gaps
- [ ] `tests/test_report_chains.py` — unit tests for BuildReportDataChain and TLDRChain
- [ ] `tests/conftest.py` — shared fixtures (sample ReportData, ReportCluster tree)

## Sources

### Primary (HIGH confidence)
- `src/application/report/classify.py` — BatchClassifyChain pattern (lines 21-154)
- `src/application/report/models.py` — ReportCluster, ReportData models (lines 69-184)
- `src/llm/chains.py` — get_tldr_chain, TLDR_PROMPT (lines 220-247)
- `src/llm/output_models.py` — TLDRItem pydantic model (lines 10-14)

### Secondary (MEDIUM confidence)
- `src/application/report/generator.py` — _entity_report_async integration point (lines 23-84)
- `src/application/report/tldr.py` — old TLDRGenerator (reference for what NOT to use)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — uses existing project patterns
- Architecture: HIGH — directly follows BatchClassifyChain
- Pitfalls: HIGH — identified from codebase patterns and known async patterns

**Research date:** 2026/04/12
**Valid until:** 60 days (async Runnable pattern is stable)
