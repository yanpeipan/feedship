# Phase Quick: Report P1 - Pipeline Unification: Deprecate Thematic Clustering

**Researched:** 2026-04-10
**Domain:** Report generation pipeline architecture (thematic vs entity-based)
**Confidence:** HIGH (code-based verification)

## Summary

The thematic pipeline (`_cluster_articles_async`) and entity pipeline (`_entity_report_async`) are two competing report generation paths. The entity pipeline is the intended direction but is currently missing three features that only thematic provides: `signals.leverage`, `signals.business`, and `signals.creation` (Section B and C in templates). The entity pipeline returns these as empty lists, so Section B and C always render as "暂无数据". The migration is straightforward: copy the three rule-based classification functions from the thematic pipeline into the entity pipeline as a post-processing step, then remove `_cluster_articles_async`.

**Primary recommendation:** Add `_classify_signal_leverage`, `_classify_signal_business`, and `_classify_creation` as post-processing steps in `_entity_report_async` (after entity clustering, before building return dict). Remove `_cluster_articles_async` and its fallback in `_entity_report_async`.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Entity-based pipeline (`_entity_report_async`) is the intended path
- Thematic pipeline (`_cluster_articles_async`) should be deprecated
- Migration path: add rule-based signal classification to entity pipeline, then deprecate thematic

### Claude's Discretion
- Minimal change vs full rewrite approach
- How to handle `creation` section (currently thematic does re-clustering for creation articles)

### Deferred Ideas (OUT OF SCOPE)
- Removing ChromaDB entirely
- New template design

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| REQ-P1-01 | Add rule-based signal classification (leverage/business) to entity pipeline | Functions `_classify_signal_leverage` and `_classify_signal_business` exist in thematic; need to port as post-processing step |
| REQ-P1-02 | Add creation classification to entity pipeline | Function `_classify_creation` exists in thematic; thematic does re-clustering of creation articles |
| REQ-P1-03 | Remove `_cluster_articles_async` and its fallback | Only called from `_entity_report_async` exception handler; removing fallback simplifies code |
| REQ-P1-04 | Verify template rendering works correctly | Both `default.md` and `v2.md` templates exist; v2.md has template bug for `signals.business` |

## Standard Stack

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| sklearn KMeans | (existing) | Semantic clustering in thematic pipeline | `src/application/report_generation.py:195` |
| ChromaDB | (existing) | Embedding storage; used in `_cluster_articles_into_topics` | `get_chroma_collection()` call |
| Jinja2 | (existing) | Template rendering | `render_report()`, `render_entity_report()` |
| rule-based keywords | (existing) | Signal classification | `_LEVERAGE_KEYWORDS`, `_BUSINESS_KEYWORDS`, `_CREATION_KEYWORDS` |

## Architecture Patterns

### Two Pipeline Architecture

```
CLI: report.py
  └─ cluster_articles_for_report()  [sync wrapper]
       └─ _entity_report_async()     [ALWAYS called]
            ├─ SignalFilter.filter()  [Layer 0: quality filter]
            ├─ NERExtractor.extract_batch()  [Layer 1: NER]
            ├─ EntityClusterer.cluster()     [Layer 2: entity grouping]
            ├─ TLDRGenerator.generate_top10() [Layer 3: TLDR]
            └─ render_entity_report()         [Layer 4: render]
            └─ [exception] → _cluster_articles_async()  [DEPRECATED fallback]

_cluster_articles_async()  [DEPRECATED - thematic pipeline]
  ├─ deduplicate_articles() [Level 1/2/3 dedup]
  ├─ batch_summarize_articles() [LLM summarize]
  ├─ _cluster_articles_into_topics() [semantic clustering via ChromaDB]
  │   └─ ChromaDB embedding lookup → KMeans → merge small clusters
  ├─ _classify_signal_leverage() [rule-based]
  ├─ _classify_signal_business() [rule-based]
  ├─ _classify_creation() [rule-based]
  └─ re-cluster creation articles
```

### Call Sites

| Function | Called By | File |
|----------|-----------|------|
| `_cluster_articles_async` | `_entity_report_async` exception handler only (line 1044) | `src/application/report_generation.py` |
| `_entity_report_async` | `cluster_articles_for_report` (line 1069) | `src/application/report_generation.py` |
| `cluster_articles_for_report` | `report.py` CLI (line 71) | `src/cli/report.py` |

**Key finding:** `_cluster_articles_async` is NEVER called directly from CLI. It is ONLY a fallback when `_entity_report_async` raises an exception. This means the thematic pipeline is effectively dead code unless the entity pipeline throws.

## Signal Sections Detail

### What Are the "Signal Sections"?

The thematic pipeline computes three additional sections beyond the 5-layer taxonomy:

| Section | Function | Keywords | Output Structure |
|---------|----------|----------|-----------------|
| Section B.1 (leverage) | `_classify_signal_leverage` | tool, platform, api, framework, open source, library, sdk, model, release, launch, github, npm, pypi, runtime, compiler, assistant, agent, claude, gpt, gemini, openai, anthropic | Flat list of articles |
| Section B.2 (business) | `_classify_signal_business` | startup, funding, raise, series, ipo, business model, revenue, unicorn, vc, venture, investor, seed round, acquisition, merger, profit | Flat list of articles |
| Section C (creation) | `_classify_creation` | how to, tutorial, review, top, best, vs, comparison, guide, introduction, beginner, getting started, 101, cheat sheet, tips, master, learn, course, workshop | Topics (re-clustered creation articles) |

### Template Usage

**`~/.config/feedship/templates/default.md`** (used by CLI `report` command):
- `signals.leverage[:20]` — renders `s.title`, `s.link` (flat article list) — WORKS
- `signals.business[:20]` — renders `s.title`, `s.link` (flat article list) — WORKS
- `creation` — renders `section.name`, `section.topics` — WORKS

**`~/.config/feedship/templates/v2.md`** (for `render_report` with `template_name="v2"`):
- `signals.leverage[:5]` — renders `topic.title`, `topic.insight`, `topic.sources` — WORKS
- `signals.business[:5]` — expects `topic.case`, `topic.demand`, `topic.tech_stack`, `topic.mvp_sop` — **NEVER POPULATED** in either pipeline
- `creation` — renders `section.topics` — WORKS

**Template bug in v2.md:** Section B.2 (商业逆向工程) in `v2.md` expects topic objects with `case`, `demand`, `tech_stack`, `mvp_sop` fields. Neither pipeline produces these. The thematic pipeline passes flat articles (no such fields). This section will always render broken or empty in v2 template.

### Current State in Entity Pipeline

In `_entity_report_async` (line 1026-1028):
```python
# Entity pipeline doesn't compute signals/creation separately
signals_data: dict[str, list] = {"leverage": [], "business": []}
creation_data: list[dict] = []
```

Result: When entity pipeline is used, Section B and C always show "暂无数据".

### ChromaDB Usage Comparison

| Pipeline | ChromaDB Used? | Where | Purpose |
|----------|---------------|-------|---------|
| Thematic | YES | `_cluster_articles_into_topics` line 165 | Semantic clustering via embedding lookup |
| Thematic | YES | `deduplicate_articles` | Level 3 embedding dedup (called before clustering) |
| Entity | NO | Never | Assumes dedup done before pipeline |

Both pipelines call `deduplicate_articles` at their start. ChromaDB in entity pipeline is only needed for the pre-deduplication step (already done before `_entity_report_async` is called).

## Don't Hand-Roll

| Problem | Use Instead | Source |
|---------|-------------|--------|
| Semantic clustering | `_cluster_articles_into_topics` (KMeans + ChromaDB) | `report_generation.py:139` |
| Rule-based signal classification | `_classify_signal_leverage/business/creation` | `report_generation.py:419-452` |
| Embedding storage | ChromaDB via `get_chroma_collection()` | `report_generation.py:165` |

## Common Pitfalls

### Pitfall 1: Template Field Mismatch
**What:** `v2.md` template Section B.2 expects `topic.case`, `topic.demand`, `topic.tech_stack`, `topic.mvp_sop` which neither pipeline produces.
**How to avoid:** Either fix the v2.md template to use flat article fields, or populate these fields in thematic pipeline.
**Status:** This is a pre-existing bug unrelated to the P1 unification task.

### Pitfall 2: ChromaDB Availability for Thematic Pipeline
**What:** `_cluster_articles_into_topics` falls back to `feed_id` grouping when ChromaDB is unavailable (line 175-179). If ChromaDB goes down, thematic pipeline degrades gracefully but entity pipeline (which never uses ChromaDB in the pipeline itself) is unaffected.
**How to avoid:** Entity pipeline is already ChromaDB-independent for the main flow.

### Pitfall 3: Duplicate Clustering for Creation
**What:** Thematic pipeline re-runs `_cluster_articles_into_topics` on creation-filtered articles (line 901). This is a second LLM call. If ported naively, it would add latency to entity pipeline.
**How to avoid:** Creation section is lower priority. Can skip re-clustering and just return flat list (like leverage/business), matching what `default.md` template actually needs.

## Code Examples

### Rule-Based Classification Functions (to port)

```python
# Keywords for Section B (signals) rule-based classification
_LEVERAGE_KEYWORDS = [
    "tool", "platform", "api", "framework", "open source",
    "library", "sdk", "model", "release", "launch", "github",
    "npm", "pypi", "runtime", "compiler", "assistant", "agent",
    "claude", "gpt", "gemini", "openai", "anthropic",
]
_BUSINESS_KEYWORDS = [
    "startup", "funding", "raise", "series", "ipo", "business model",
    "revenue", "unicorn", "vc", "venture", "investor", "seed round",
    "acquisition", "merger", "profit",
]
_CREATION_KEYWORDS = [
    "how to", "tutorial", "review", "top", "best", "vs",
    "comparison", "guide", "introduction", "beginner",
    "getting started", "101", "cheat sheet", "tips", "master",
    "learn", "course", "workshop",
]

def _classify_signal_leverage(article: dict) -> bool:
    text = (article.get("title", "") + " " +
            article.get("summary", "") + " " +
            article.get("description", "")).lower()
    return any(kw in text for kw in _LEVERAGE_KEYWORDS)

def _classify_signal_business(article: dict) -> bool:
    text = (article.get("title", "") + " " +
            article.get("summary", "") + " " +
            article.get("description", "")).lower()
    return any(kw in text for kw in _BUSINESS_KEYWORDS)

def _classify_creation(article: dict) -> bool:
    text = (article.get("title", "") + " " +
            article.get("summary", "") + " " +
            article.get("description", "")).lower()
    return any(kw in text for kw in _CREATION_KEYWORDS)
```

### Where to Add in Entity Pipeline

In `_entity_report_async` after line 1024 (after `layers_data` is built, before `signals_data`):

```python
# After layers_data is built, compute signals via rule-based classification
# Flatten all sources from entity topics for signal matching
all_sources = []
for topic_dict in entity_topic_dicts:
    all_sources.extend(topic_dict.get("sources", []))

leverage_articles = [a for a in all_sources if _classify_signal_leverage(a)]
business_articles = [a for a in all_sources if _classify_signal_business(a)]
creation_articles = [a for a in all_sources if _classify_creation(a)]

signals_data = {
    "leverage": leverage_articles,
    "business": business_articles,
}
creation_data = [{"name": "创作选题", "topics": []}] if creation_articles else []
```

**Note:** For creation, the thematic pipeline re-clusters using `_cluster_articles_into_topics`. This adds a second LLM call. If minimal change is preferred, a flat list (like leverage/business) works with both `default.md` and `v2.md` templates.

## Migration Steps

1. **Port classification functions** — Move `_classify_signal_leverage`, `_classify_signal_business`, `_classify_creation`, and their keyword lists from `report_generation.py` (lines 59-125) to a shared location (e.g., `src/application/report/signal_classifier.py`)

2. **Add signal computation in entity pipeline** — After `entity_topic_dicts` is built (line 1024), add flat article collection and rule-based filtering to populate `signals_data` and `creation_data`

3. **Remove thematic fallback** — Delete the `except Exception` block in `_entity_report_async` (lines 1041-1046) that falls back to `_cluster_articles_async`

4. **Remove `_cluster_articles_async` and `_cluster_articles_into_topics`** — Delete both functions and all their helpers (`_LEVERAGE_KEYWORDS`, `_BUSINESS_KEYWORDS`, `_CREATION_KEYWORDS`, `_classify_signal_*`, `_classify_creation`, `_keyword_overlap`, `_lang_name`, etc.)

5. **Verify `report.py` CLI** — No changes needed; `cluster_articles_for_report` already calls `_entity_report_async`

6. **Verify `render_report`** — No changes needed; it already handles `signals` and `creation` keys in data dict

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `_cluster_articles_async` is only called as fallback from `_entity_report_async` | Architecture | If there are other call sites not found by grep, removing it would break those |
| A2 | `default.md` template's `signals.leverage` and `signals.business` expect flat article lists | Template Usage | Verified in code — templates use `s.title`, `s.link` |
| A3 | Rule-based signal functions use title+summary+description for classification | Code | Verified — functions concat title, summary, description |
| A4 | Entity pipeline dedup is done before `_entity_report_async` is called | Architecture | `cluster_articles_for_report` calls `list_articles_for_llm` then passes to `_entity_report_async`; `deduplicate_articles` is NOT called inside entity pipeline |

## Open Questions

1. **Should creation articles be re-clustered (2nd LLM call) or returned as flat list?**
   - Thematic: re-clusters via `_cluster_articles_into_topics` (extra LLM call)
   - `default.md` template: treats creation like leverage/business (flat list of articles)
   - `v2.md` template: expects `section.topics` structure
   - Recommendation: For minimal change, use flat list. For feature parity, re-cluster.

2. **Should the v2.md template bug (Section B.2 expecting non-existent fields) be fixed?**
   - Not in scope for P1, but it will cause Section B.2 to always show "暂无数据" even after migration

3. **What happens to ChromaDB if thematic pipeline is removed?**
   - ChromaDB is still used by `deduplicate_articles` (called before entity pipeline)
   - ChromaDB is still used by `src/application/report/dedup.py` for embedding-based dedup
   - No change to ChromaDB usage

## Environment Availability

Step 2.6: SKIPPED (no external dependencies identified — pure code refactor)

## Sources

- `src/application/report_generation.py` — `_cluster_articles_async`, `_entity_report_async`, `_cluster_articles_into_topics`, signal classification functions (lines 59-125, 139-450, 742-1046)
- `src/application/report/filter.py` — `SignalFilter` (Layer 0 of entity pipeline)
- `src/application/report/models.py` — `EntityTopic`, `ArticleEnriched` dataclasses
- `src/application/report/render.py` — `render_entity_report` (entity pipeline rendering)
- `src/cli/report.py` — CLI entry point, calls `cluster_articles_for_report`
- `~/.config/feedship/templates/default.md` — main template used by CLI
- `~/.config/feedship/templates/v2.md` — alternate template with template bug
