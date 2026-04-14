# Quick Task Research: Extend ArticleListItem and Replace Dict Intermediate

**Researched:** 2026-04-12
**Confidence:** HIGH

## Summary

The report pipeline starts with typed `ArticleListItem` objects from `list_articles()`, but immediately converts them to `dict` at the boundary of `cluster_articles_for_report()` (line 488-507 in `report_generation.py`). From that point on, every layer -- dedup, filter, classification, enrichment, TLDR -- operates on `dict`. This conversion is unnecessary because `ArticleListItem` already contains all fields the pipeline needs.

The primary refactoring opportunity is removing the dict conversion in `cluster_articles_for_report()` and propagating `ArticleListItem` through all layers, ultimately building `ArticleEnriched` directly from `ArticleListItem` rather than from a dict.

## User Constraints

This is a quick-task-research with a clear directive: extend `ArticleListItem` fields and propagate the typed object downward instead of converting to `dict`. No locked decisions from prior phases constrain this work.

## Phase Requirements

Not applicable (quick task, not a planned phase with IDs).

---

## 1. ArticleListItem Definition

**Location:** `src/application/articles.py` lines 53-88

```python
@dataclass
class ArticleListItem:
    id: str
    feed_id: str
    feed_name: str
    title: str | None
    link: str | None
    guid: str
    published_at: str | None
    description: str | None
    vec_sim: float = 0.0
    bm25_score: float = 0.0
    freshness: float = 0.0
    source_weight: float = 0.3
    ce_score: float = 0.0
    score: float = 0.0
    quality_score: float | None = None
    content: str | None = None
    summary: str | None = None
    feed_weight: float | None = None
    feed_url: str | None = None
    content_hash: str | None = None
    minhash_signature: bytes | None = None
```

**Assessment:** This dataclass already contains all fields needed by the report pipeline. No field additions are strictly required, but see Section 4 for discussion of `entities` and `dimensions`.

---

## 2. Data Flow Map

### Entry Point
```
list_articles()  →  list[ArticleListItem]  (src/storage/sqlite/articles.py line 417)
```

### Boundary: dict conversion happens here
```
cluster_articles_for_report()  (src/application/report/report_generation.py line 470)
    │
    └─ Converts ArticleListItem[] → dict[] at lines 488-507:
       article_dicts = [
           {
               "id": a.id, "feed_id": a.feed_id, "feed_name": a.feed_name,
               "feed_weight": a.feed_weight, "title": a.title, "link": a.link,
               "published_at": a.published_at, "description": a.description,
               "content": a.content, "summary": a.summary,
               "quality_score": a.quality_score, "feed_url": a.feed_url,
               "content_hash": a.content_hash, "minhash_signature": a.minhash_signature,
           }
           for a in articles
       ]
    │
    └─ asyncio.run(_entity_report_async(article_dicts, ...))
```

### Layer 0: Deduplication
```
deduplicate_articles(pre_fetched_articles: list[dict])  (src/application/dedup.py line 209)
    │
    ├─ _level1_exact_dedup(): uses article.get("content_hash")
    ├─ _level2_minhash_dedup(): uses article.get("minhash_signature"), article.get("content_hash")
    └─ _level3_embedding_dedup(): uses article["id"]
```
**Note:** All three dedup levels access fields by key name. Since `ArticleListItem` is a dataclass, `.get()` will fail. Need to either (a) make ArticleListItem dict-like, (b) add dict-conversion at the dedup boundary only, or (c) change dedup to access attributes.

### Layer 1: Signal Filter
```
SignalFilter.filter(articles: list[dict[str, Any]])  (src/application/report/filter.py line 59)
    │
    └─ _passes_all_rules(): uses article.get("content"), .get("description"), .get("title"), .get("quality_score"), .get("feed_weight")
```
**Note:** Same issue -- `ArticleListItem` has all these fields but as attributes, not dict keys.

### Layer 2: Classify + Translate
```
Filtered dicts → batched → ClassifyTranslateItem[] (LLM chain)
    │
    └─ Lines 249-318: Maps items back to filtered[] by index (item.id - 1)
       Creates tag_groups: dict[str, list[tuple[int, dict]]]
```

### Layer 3: ArticleEnriched creation
```
Lines 334-347: ArticleEnriched built from dict art:
    ae = ArticleEnriched(
        id=art.get("id", ""),
        title=art.get("title", ""),
        link=art.get("link", ""),
        summary=art.get("summary", ""),
        quality_score=art.get("quality_score", 0.0),
        feed_weight=art.get("feed_weight", 0.0),
        published_at=art.get("published_at", ""),
        feed_id=art.get("feed_id", ""),
        entities=[],  # always empty - from classify_translate has no entities
        dimensions=_classify_dim(art),
    )
```
**Key observation:** `entities=[]` is hardcoded. This is because `classify_translate` does not extract entities -- that would require a separate NER step. The `dimensions` field is computed by `_classify_dim()` which inspects title + summary text.

### Layer 3: EntityTopic creation
```
Lines 330-376: EntityTopic built from ArticleEnriched[]
    entity_topics.append(EntityTopic(
        entity_id=tag,
        entity_name=tag,
        layer="AI应用",
        headline=headline,
        dimensions=by_dim,  # dict[str, list[ArticleEnriched]]
        articles_count=len(arts),
        signals=[],
        tldr="",
        quality_weight=sum(a.get("quality_score", 0.0) for a in arts) * len(arts),
    ))
```

### Layer 3: TLDR Generation
```
TLDRGenerator.generate_top10(entity_topics: list[EntityTopic], ...)  (tldr.py)
    │  (EntityTopic is already a typed dataclass)
```

### Layer 4: Render
```
render_entity_report(entity_topics: list, ...)  (render.py line 46)
    │  Receives EntityTopic[] (typed), but then at lines 389-422:
    │
    └─ Converts EntityTopic.sources to dicts for template:
       for dim_arts in topic.dimensions.values():
           for art in dim_arts:
               sources.append({
                   "id": art.id, "title": art.title, "link": art.link,
                   "summary": art.summary, "quality_score": art.quality_score,
                   "feed_weight": art.feed_weight, "published_at": art.published_at,
                   "feed_id": art.feed_id,
                   "entities": [{"name": e.name, "type": e.type, "normalized": e.normalized} for e in art.entities],
               })
```

---

## 3. All Dict-Intermediate Locations

| Location | Line | Dict Type | Accesses |
|----------|------|-----------|----------|
| `cluster_articles_for_report()` | 488-507 | `list[dict]` from ArticleListItem | all fields via `.get()` |
| `deduplicate_articles()` | 209 | `list[dict]` | `content_hash`, `minhash_signature`, `id` |
| `SignalFilter.filter()` | 59 | `list[dict[str, Any]]` | `content`, `description`, `title`, `quality_score`, `feed_weight` |
| `_classify_signal_leverage()` | 106 | `dict` | `title`, `summary`, `description` |
| `_classify_signal_business()` | 118 | `dict` | `title`, `summary`, `description` |
| `_classify_creation()` | 130 | `dict` | `title`, `summary`, `description` |
| `_classify_dim()` | 294 | `dict` | `title`, `summary` |
| `ArticleEnriched` creation | 334-347 | `dict` | all fields via `.get()` |
| `entity_topic_dicts` creation | 389-422 | `dict` from ArticleEnriched | all fields |

---

## 4. Fields Analysis: What Would Need to Be Added to ArticleListItem?

### Fields currently on ArticleListItem that the report pipeline needs:
| Field | Used By | Already on ArticleListItem? |
|-------|---------|--------|
| `id` | dedup, enrich | Yes |
| `title` | classify, enrich | Yes |
| `link` | enrich | Yes |
| `summary` | classify, enrich | Yes |
| `description` | filter, classify | Yes |
| `content` | filter, dedup (via content[:500]) | Yes |
| `quality_score` | filter, enrich | Yes |
| `feed_weight` | filter, enrich | Yes |
| `published_at` | enrich | Yes |
| `feed_id` | enrich | Yes |
| `feed_name` | (available in dict but not used in enrich) | Yes |
| `feed_url` | (available in dict but not used in enrich) | Yes |
| `content_hash` | dedup | Yes |
| `minhash_signature` | dedup | Yes |
| `entities` | enrich (currently always `[]`) | **No -- would need to add** |
| `dimensions` | enrich (computed by `_classify_dim()`) | **No -- computed at enrich time** |

### New fields potentially needed on ArticleListItem:

1. **`entities: list[EntityTag]`** -- Currently always `[]` in report pipeline because classify_translate does not extract entities. If NER is to be added to the report pipeline, this would be needed. However, this is a separate feature from the dict-replacement task.

2. **`dimensions: list[str]`** -- Currently computed at enrich time by `_classify_dim()` which does rule-based classification on title + summary text. Could be precomputed and stored on ArticleListItem, but that would require updating `list_articles()` SQL and all callers. Better to keep it computed at report time.

**Conclusion for ArticleListItem extension:** No new fields are strictly required to replace the dict intermediate. `ArticleListItem` already has all fields used by the report pipeline. The `entities=[]` is a deliberate placeholder (NER not in report pipeline), and `dimensions` is computed per-report.

---

## 5. Breaking Changes Analysis

### Breaking Change 1: `deduplicate_articles()` signature

**Current:** `def deduplicate_articles(articles: list[dict], ...)`
**Impact:** All callers would need to pass `list[ArticleListItem]` or the function would need to accept both.

**Affected callers:**
- `report_generation.py` line 180: `deduplicate_articles(pre_fetched_articles)` -- `pre_fetched_articles` comes from `cluster_articles_for_report()` output, which is dict. If we stop converting to dict, this becomes ArticleListItem[].

**Approach:** Keep `deduplicate_articles()` internal to `_entity_report_async()`. Since it only accesses `content_hash`, `minhash_signature`, and `id`, and these are all fields on `ArticleListItem`, we can either:
- (a) Change it to accept `list[ArticleListItem]` and use `getattr(a, 'content_hash')` or a helper
- (b) Add a `to_dict()` method to `ArticleListItem` and convert only at the dedup boundary
- (c) Use duck typing -- check if object has `.get` method, otherwise use `getattr`

**Recommended:** Option (a) -- change dedup to work with `ArticleListItem` directly. It's in `src/application/dedup.py` and not part of a public storage API.

### Breaking Change 2: `SignalFilter.filter()` signature

**Current:** `def filter(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]`
**Impact:** Would need to accept `list[ArticleListItem]`.

**Approach:** Same as dedup -- change to work with `ArticleListItem`. `SignalFilter` is in `src/application/report/filter.py`.

### Breaking Change 3: Classification functions

**Current:** `_classify_signal_leverage(article: dict)` etc.
**Impact:** Change to accept `ArticleListItem` or a protocol.

**Approach:** These are module-level functions in `report_generation.py`. They use `.get()` to access `title`, `summary`, `description`. Since `ArticleListItem` has all three as attributes, change to `ArticleListItem` and use `getattr` or add a `to_dict()` convenience method.

### Breaking Change 4: `_classify_dim()`

**Current:** `def _classify_dim(article: dict) -> list[str]:`
**Same approach as classification functions.**

### Breaking Change 5: `ArticleEnriched` creation

**Current:** Lines 334-347 build `ArticleEnriched` from dict `art` using `.get()`.
**Impact:** Would build directly from `ArticleListItem` using attribute access.

### Breaking Change 6: `entity_topic_dicts` flattening

**Current:** Lines 389-422 flatten `EntityTopic.dimensions` (which contains `ArticleEnriched`) to dicts for template rendering.
**Impact:** Templates expect dicts. Either:
- (a) Change templates to use `ArticleEnriched` attributes directly
- (b) Keep the flattening but do it in the template layer (Jinja2 can access attributes)
- (c) Keep dict conversion only at the template boundary

**Recommended:** Option (b) -- Jinja2 templates can access both dict keys and object attributes. If `art.id` works for dicts, it also works for `ArticleEnriched` in Jinja2.

### Breaking Change 7: Storage API `list_articles()` return type

**Current:** `list_articles()` returns `list[ArticleListItem]` -- this is already typed and should NOT change. The breaking change is only in the report pipeline's internal handling.

---

## 6. Recommended Implementation Approach

1. **Keep `ArticleListItem` unchanged** -- it already has all required fields.

2. **Add a helper method on `ArticleListItem`:**
   ```python
   def to_dict(self) -> dict:
       return {
           "id": self.id,
           "feed_id": self.feed_id,
           # ... all fields
       }
   ```
   Use this ONLY at boundaries where dict is required (e.g., template rendering or external APIs).

3. **Change `deduplicate_articles()`** to accept `list[ArticleListItem]`. Replace `article.get("content_hash")` with `article.content_hash` (with None handling). Same for `minhash_signature` and `id`.

4. **Change `SignalFilter.filter()`** to accept `list[ArticleListItem]`. Replace dict `.get()` calls with attribute access.

5. **Change classification functions** (`_classify_signal_leverage`, etc.) to accept `ArticleListItem`.

6. **Change `_classify_dim()`** to accept `ArticleListItem`.

7. **Change `ArticleEnriched` creation** (lines 334-347) to build from `ArticleListItem` attributes directly.

8. **Update template rendering** to work with `ArticleEnriched` attributes instead of dict keys (Jinja2 supports both, but existing templates likely use dict access).

9. **Remove the dict conversion** in `cluster_articles_for_report()` (lines 488-507). Instead, pass `articles` directly to `_entity_report_async()`.

---

## 7. Confidence and Risks

| Area | Confidence | Risk |
|------|-----------|------|
| ArticleListItem fields completeness | HIGH | Verified by reading source -- has all fields needed |
| Dedup layer compatibility | HIGH | Only accesses `content_hash`, `minhash_signature`, `id` -- all on ArticleListItem |
| SignalFilter compatibility | HIGH | Only accesses fields on ArticleListItem |
| Classification functions | HIGH | Only accesses `title`, `summary`, `description` -- all on ArticleListItem |
| Template rendering | MEDIUM | Jinja2 supports attribute access but templates may need updates |
| LLM chain output (ClassifyTranslateItem) | N/A | Not changed in this refactor |

**Main risk:** Jinja2 templates currently use dict access (e.g., `article.title` works for both `dict["title"]` and `obj.title`). This should be template-compatible, but actual template content needs verification.

---

## 8. Open Questions

1. **Are there other callers of `deduplicate_articles()` besides the report pipeline?** If so, they would need to be updated too. Currently only called from `report_generation.py`.

2. **Do the Jinja2 templates use dict access or attribute access for `ArticleEnriched` objects?** Jinja2 supports both, but if templates use `article['title']` syntax they would break. Templates are in `~/.config/feedship/templates/` (user config) -- need to check actual template content.

3. **Is `entities=[]` intentional placeholder or missing feature?** Current pipeline never populates entities for report. If entities are needed in reports, a separate NER step would need to be added, which is beyond the scope of this dict-replacement task.

---

## Sources

- `src/application/articles.py` -- ArticleListItem definition (lines 53-88)
- `src/storage/sqlite/articles.py` -- list_articles() returns list[ArticleListItem] (lines 417-532)
- `src/application/report/report_generation.py` -- dict conversion at lines 488-507, all downstream dict usage
- `src/application/dedup.py` -- deduplicate_articles() works with list[dict]
- `src/application/report/filter.py` -- SignalFilter.filter() works with list[dict]
- `src/application/report/models.py` -- ArticleEnriched, EntityTopic dataclasses
- `src/application/report/tldr.py` -- TLDRGenerator works with EntityTopic (typed)
- `src/application/report/render.py` -- render_entity_report() receives EntityTopic[], template flattening at lines 389-422
