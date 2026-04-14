---
phase: quick
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/application/articles.py
  - src/application/dedup.py
  - src/application/report/filter.py
  - src/application/report/report_generation.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "cluster_articles_for_report() passes ArticleListItem[] directly without dict conversion"
    - "deduplicate_articles() operates on ArticleListItem attributes instead of dict.get()"
    - "SignalFilter.filter() operates on ArticleListItem attributes instead of dict.get()"
    - "Classification functions use ArticleListItem/ArticleEnriched attributes directly"
    - "ArticleEnriched creation uses ArticleListItem attributes directly"
  artifacts:
    - path: "src/application/articles.py"
      provides: "ArticleListItem.to_dict() method"
    - path: "src/application/dedup.py"
      provides: "deduplicate_articles() accepts list[ArticleListItem]"
    - path: "src/application/report/filter.py"
      provides: "SignalFilter.filter() accepts list[ArticleListItem]"
    - path: "src/application/report/report_generation.py"
      provides: "Classification functions, ArticleEnriched creation, cluster_articles_for_report() all use ArticleListItem"
  key_links:
    - from: "src/application/report/report_generation.py"
      to: "src/application/articles.py"
      via: "ArticleListItem type import"
    - from: "src/application/dedup.py"
      to: "src/application/articles.py"
      via: "ArticleListItem type import"
    - from: "src/application/report/filter.py"
      to: "src/application/articles.py"
      via: "ArticleListItem type import"
---

<objective>
Refactor the report pipeline to use `ArticleListItem` typed objects throughout instead of converting to dict intermediates. Eliminate the dict conversion at `cluster_articles_for_report()` boundary and propagate `ArticleListItem` through all layers (dedup, filter, classification, enrichment).
</objective>

<context>
@src/application/articles.py
@src/application/dedup.py
@src/application/report/filter.py
@src/application/report/report_generation.py
@src/application/report/models.py
</context>

<interfaces>
<!-- ArticleListItem — source of truth for the pipeline -->
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

<!-- ArticleEnriched — used downstream in render layer -->
@dataclass
class ArticleEnriched:
    id: str
    title: str
    link: str
    summary: str
    quality_score: float
    feed_weight: float
    published_at: str
    feed_id: str
    entities: list[EntityTag] = field(default_factory=list)
    dimensions: list[str] = field(default_factory=list)
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add to_dict() helper to ArticleListItem</name>
  <files>src/application/articles.py</files>
  <action>
Add a `to_dict()` method to the `ArticleListItem` dataclass. This is used ONLY at boundaries where dict is truly required (e.g., template flattening in render.py). Place it after line 88 (after `minhash_signature` field).

```python
def to_dict(self) -> dict:
    """Convert to dict for boundaries that require dict (e.g., template rendering)."""
    return {
        "id": self.id,
        "feed_id": self.feed_id,
        "feed_name": self.feed_name,
        "title": self.title,
        "link": self.link,
        "guid": self.guid,
        "published_at": self.published_at,
        "description": self.description,
        "vec_sim": self.vec_sim,
        "bm25_score": self.bm25_score,
        "freshness": self.freshness,
        "source_weight": self.source_weight,
        "ce_score": self.ce_score,
        "score": self.score,
        "quality_score": self.quality_score,
        "content": self.content,
        "summary": self.summary,
        "feed_weight": self.feed_weight,
        "feed_url": self.feed_url,
        "content_hash": self.content_hash,
        "minhash_signature": self.minhash_signature,
    }
```

Also add `from dataclasses import dataclass, field` import if not already present (it is present at line 11).
</action>
  <verify>
python -c "from src.application.articles import ArticleListItem; a = ArticleListItem(id='1', feed_id='f1', feed_name='Test', title='T', link='u', guid='g', published_at='2024-01-01', description='d'); print(a.to_dict()['id'])"
</verify>
  <done>ArticleListItem.to_dict() method exists and returns a dict with all fields</done>
</task>

<task type="auto">
  <name>Task 2: Change deduplicate_articles() to accept ArticleListItem[]</name>
  <files>src/application/dedup.py</files>
  <action>
Change the deduplication layer to work with `list[ArticleListItem]` instead of `list[dict]`.

**Import ArticleListItem** — add at top of file (after existing imports):
```python
from src.application.articles import ArticleListItem
```

**Change `_level1_exact_dedup`** (line 58): Change signature from `list[dict]` to `list[ArticleListItem]`. Replace:
- `a.get("content_hash")` → `a.content_hash`
- `a.get("id")` → `a.id`
- Return type is still `list[ArticleListItem]` (seen dict values become ArticleListItem values, stored by content_hash key)

**Change `_level2_minhash_dedup`** (line 77): Change signature from `list[dict]` to `list[ArticleListItem]`. Replace:
- `a.get("minhash_signature")` → `a.minhash_signature`
- `a.get("content_hash")` → `a.content_hash`
- `a.get("id")` → `a.id`

**Change `_level3_embedding_dedup`** (line 128): Change signature from `list[dict]` to `list[ArticleListItem]`. Replace:
- `a["id"]` → `a.id`
- `id_to_embedding.get(a["id"])` → `id_to_embedding.get(a.id)`

**Change `deduplicate_articles`** (line 209): Change signature from `list[dict]` to `list[ArticleListItem]`. Update docstring accordingly. Return type remains `list[ArticleListItem]`.

Note: The `signature_map` and `seen` dicts use article as value — this is fine since ArticleListItem is a dataclass and can be stored directly.
</action>
  <verify>
python -c "from src.application.dedup import deduplicate_articles; from src.application.articles import ArticleListItem; a = ArticleListItem(id='1', feed_id='f1', feed_name='Test', title='T', link='u', guid='g', published_at='2024-01-01', description='d', content_hash='abc'); print(len(deduplicate_articles([a])))"
</verify>
  <done>deduplicate_articles() accepts list[ArticleListItem] and returns list[ArticleListItem]</done>
</task>

<task type="auto">
  <name>Task 3: Change SignalFilter.filter() to accept ArticleListItem[]</name>
  <files>src/application/report/filter.py</files>
  <action>
Change `SignalFilter.filter()` and `_passes_all_rules()` to work with `ArticleListItem` instead of `dict`.

**Import ArticleListItem** — add at top of file:
```python
from src.application.articles import ArticleListItem
```

**Change `filter()` signature** (line 59): From `list[dict[str, Any]]` to `list[ArticleListItem]`. Return type remains `list[ArticleListItem]`.

**Change `_passes_all_rules()` signature** (line 77): From `article: dict` to `article: ArticleListItem`. Replace all `.get()` calls:
- `article.get("content", "") or article.get("description", "")` → `article.content or article.description or ""`
- `article.get("title", "")` → `article.title or ""`
- `article.get("quality_score") or 0.0` → `article.quality_score or 0.0`
- `article.get("feed_weight", 0.0)` → `article.feed_weight or 0.0`

Note: `feed_weight` and `quality_score` on ArticleListItem are `float | None`, so use `or 0.0` to handle None.
</action>
  <verify>
python -c "from src.application.report.filter import SignalFilter; from src.application.articles import ArticleListItem; sf = SignalFilter(); a = ArticleListItem(id='1', feed_id='f1', feed_name='Test', title='T', link='u', guid='g', published_at='2024-01-01', description='d', quality_score=0.8, feed_weight=0.6, content='test'); print(len(sf.filter([a])))"
</verify>
  <done>SignalFilter.filter() accepts list[ArticleListItem] and returns list[ArticleListItem]</done>
</task>

<task type="auto">
  <name>Task 4: Change classification functions to accept ArticleListItem</name>
  <files>src/application/report/report_generation.py</files>
  <action>
Change all four classification functions to accept `ArticleListItem` instead of `dict`.

**Import ArticleListItem** — add at top of file (around line 17):
```python
from src.application.articles import ArticleListItem
```

**Change `_classify_signal_leverage`** (line 106): Change `article: dict` to `article: ArticleListItem`. Replace `.get()` calls:
- `article.get("title", "")` → `article.title or ""`
- `article.get("summary", "")` → `article.summary or ""`
- `article.get("description", "")` → `article.description or ""`

**Change `_classify_signal_business`** (line 118): Same pattern as above.

**Change `_classify_creation`** (line 130): Same pattern as above.

**Change `_classify_dim`** (line 294): Change `article: dict` to `article: ArticleListItem`. Replace:
- `article.get("title", "") or ""` → `article.title or ""`
- `article.get("summary", "") or ""` → `article.summary or ""`
</action>
  <verify>
python -c "from src.application.report.report_generation import _classify_signal_leverage, _classify_signal_business, _classify_creation, _classify_dim; from src.application.articles import ArticleListItem; a = ArticleListItem(id='1', feed_id='f1', feed_name='Test', title='OpenAI releases GPT-5', link='u', guid='g', published_at='2024-01-01', description='desc', summary='sum'); print(_classify_signal_leverage(a), _classify_signal_business(a), _classify_creation(a), _classify_dim(a))"
</verify>
  <done>All four classification functions accept ArticleListItem and return correct bool/list[str]</done>
</task>

<task type="auto">
  <name>Task 5: Remove dict conversion in cluster_articles_for_report() and fix ArticleEnriched creation</name>
  <files>src/application/report/report_generation.py</files>
  <action>
This task has two sub-parts in the same file.

**Sub-part A: Remove dict conversion in cluster_articles_for_report()**

Lines 488-507 currently convert ArticleListItem[] to dict[]. Remove this conversion and pass ArticleListItem[] directly to `_entity_report_async()`.

Change lines 488-509 from:
```python
article_dicts = [
    {
        "id": a.id,
        "feed_id": a.feed_id,
        ...
    }
    for a in articles
]
return asyncio.run(
    _entity_report_async(article_dicts, since, until, auto_summarize, target_lang)
)
```
To:
```python
return asyncio.run(
    _entity_report_async(articles, since, until, auto_summarize, target_lang)
)
```

**Sub-part B: Update _entity_report_async() signature and ArticleEnriched creation**

Change `_entity_report_async()` signature (line 147): `pre_fetched_articles: list` → `pre_fetched_articles: list[ArticleListItem]`.

Update `process_batch()` (line 213): Change `batch_articles: list[dict]` to `batch_articles: list[ArticleListItem]`. Update news_list construction:
```python
news_list = "\n".join(
    f"{i + 1}. {art.title or ''}"
    for i, art in enumerate(batch_articles)
)
```

Update ArticleEnriched creation (lines 334-347): Replace `.get()` calls with attribute access:
```python
ae = ArticleEnriched(
    id=art.id or "",
    title=art.title or "",
    link=art.link or "",
    summary=art.summary or "",
    quality_score=art.quality_score or 0.0,
    feed_weight=art.feed_weight or 0.0,
    published_at=art.published_at or "",
    feed_id=art.feed_id or "",
    entities=[],  # No entities from classify_translate
    dimensions=_classify_dim(art),
)
```

Update best_art selection (line 356): Replace `a.get("quality_score", 0.0)` with `a.quality_score or 0.0` and `a.get("id")` with `a.id`.

Update quality_weight calculation (line 373): Replace `a.get("quality_score", 0.0)` with `a.quality_score or 0.0`.

Update primary_tag extraction (line 316): Replace `art.get("feed_id", "unknown")` with `art.feed_id or "unknown"`.

**Sub-part C: Update tag_groups and flatten**

Line 309: Change `tag_groups: dict[str, list[tuple[int, dict]]]` to `tag_groups: dict[str, list[tuple[int, ArticleListItem]]]`.

Line 314: Replace `art = filtered[item.id - 1]` — no change needed since filtered is now ArticleListItem[].
</action>
  <verify>
python -c "
from src.application.report.report_generation import cluster_articles_for_report
# Just verify the import works and function is callable (actual DB call not needed for verify)
print('cluster_articles_for_report imported successfully')
"
</verify>
  <done>cluster_articles_for_report() passes ArticleListItem[] directly to _entity_report_async() without dict conversion</done>
</task>

<task type="auto">
  <name>Task 6: Update signal classification on entity_topic_dicts</name>
  <files>src/application/report/report_generation.py</files>
  <action>
Lines 445-447 use classification functions on `all_sources` (which are dicts from entity_topic_dicts flattening). Since `all_sources` are built from `ArticleEnriched` objects (lines 391-414), they are dicts with keys like `id`, `title`, etc.

The `_classify_signal_*` functions now accept `ArticleListItem`, but `all_sources` are dicts built from ArticleEnriched. There are two options:

**Option A (preferred):** Keep all_sources as list of ArticleEnriched and pass to classification functions directly. Change lines 441-447 from:
```python
all_sources = []
for topic_dict in entity_topic_dicts:
    all_sources.extend(topic_dict.get("sources", []))
```
To:
```python
all_sources: list[ArticleEnriched] = []
for topic in entity_topics:
    for dim_arts in topic.dimensions.values():
        all_sources.extend(dim_arts)
```

Then change lines 445-447 from:
```python
leverage_articles = [a for a in all_sources if _classify_signal_leverage(a)]
business_articles = [a for a in all_sources if _classify_signal_business(a)]
creation_articles = [a for a in all_sources if _classify_creation(a)]
```
To pass ArticleEnriched. However, classification functions need `title`, `summary`, `description` which ArticleEnriched has. No change needed to classification calls since they now accept ArticleListItem-like objects. Wait — ArticleEnriched is NOT ArticleListItem. The classification functions were changed to accept ArticleListItem.

Actually, ArticleEnriched and ArticleListItem have the same fields needed for classification (`title`, `summary`, `description`). But they are different types. Options:
- Option A: Make classification functions accept a Protocol with those fields
- Option B: Use `to_dict()` on ArticleEnriched before passing to classification
- Option C: Update entity_topic_dicts to use ArticleEnriched directly and update templates

**Decision:** Use Option B — convert ArticleEnriched to dict using `to_dict()` when building `entity_topic_dicts`, so signal classification works unchanged. The `entity_topic_dicts` is only used for signals_data and template rendering, so this is the minimal change.

Wait — but `entity_topic_dicts` flattening (lines 389-414) builds dicts from ArticleEnriched. The signal classification at lines 445-447 operates on these dicts. Since classification functions now expect ArticleListItem, and ArticleEnriched has the same fields, we can either:

1. Change entity_topic_dicts to NOT flatten (keep ArticleEnriched objects)
2. Add a `to_dict()` method to ArticleEnriched
3. Change classification to accept ArticleEnriched

**Simplest approach:** Change lines 391-414 to build sources from ArticleEnriched directly (keep as objects), and change lines 445-447 to pass ArticleEnriched. The classification functions need `title`, `summary`, `description` which both types have. Update classification function signatures to accept `ArticleEnriched | ArticleListItem` via a Protocol.

Actually the cleanest approach: Add a simple duck-typed check in classification functions. Or just use `getattr` instead of `.get` on the article parameter. But changing from `.get()` to `getattr` is a larger change.

**Recommended:** Change entity_topic_dicts (lines 389-414) to keep sources as ArticleEnriched objects (not dicts). Templates can access ArticleEnriched attributes directly (Jinja2 supports this). Then change lines 445-447 to pass ArticleEnriched objects to classification functions.

But this changes the structure of entity_topic_dicts which templates may depend on. Let's check — templates use `sources` as a list of dicts with keys like `id`, `title`, etc. Changing to ArticleEnriched objects would break templates that use `source.title` vs `source['title']`.

**Safest approach for templates:** Keep entity_topic_dicts as dicts (use to_dict() or build manually). Then in signal classification (lines 445-447), convert dicts back to ArticleListItem-like objects or use getattr.

Actually the cleanest solution: Change `_classify_signal_*` functions to accept a protocol or use `getattr` with fallback. But the fastest path is to keep entity_topic_dicts as dicts and change the signal classification at 445-447 to work with dicts by using `.get()` instead of attribute access — but the functions now expect ArticleListItem.

**Final decision:** The entity_topic_dicts at lines 389-414 produce dicts that go to templates. For signal classification, we can reconstruct ArticleListItem-like objects from the dicts in lines 445-447. Since `_classify_signal_*` only use `title`, `summary`, `description`, we can use a simple approach:

Change lines 445-447 to use dict access directly since all_sources (from entity_topic_dicts) are dicts:
```python
# Create a simple wrapper that provides attribute access from dict
class _DictAttrWrapper:
    def __init__(self, d):
        self.__dict__.update(d)
    def __getitem__(self, k):
        return self.__dict__[k]

leverage_articles = [a for a in all_sources if _classify_signal_leverage(_DictAttrWrapper(a))]
```

OR simpler — change `_classify_signal_*` to use `getattr(article, 'title', '')` instead of `article.title` — but this requires the functions to accept any object with attributes.

**Simplest:** Just create a helper that creates an object with the needed attributes from the dict at the point of call. Do this inline.

Actually, looking at this more carefully — the cleanest solution is:

1. Keep entity_topic_dicts as dicts (for template compatibility)
2. For signal classification (lines 445-447), use a simple lambda that extracts the needed fields and calls the classification function with proper attribute access

But that's ugly. The REAL simplest fix: Change entity_topic_dicts to NOT be needed for signal classification. Build `all_sources` directly from `entity_topics` (which contains ArticleEnriched objects). Then pass ArticleEnriched to classification functions.

Change lines 441-447 to:
```python
# Build all_sources from ArticleEnriched directly (not from dicts)
all_sources: list[ArticleEnriched] = []
for topic in entity_topics:
    for dim_arts in topic.dimensions.values():
        all_sources.extend(dim_arts)

# Classification functions accept ArticleEnriched now
leverage_articles = [a for a in all_sources if _classify_signal_leverage(a)]
business_articles = [a for a in all_sources if _classify_signal_business(a)]
creation_articles = [a for a in all_sources if _classify_creation(a)]
```

Then update `_classify_signal_*` to accept `ArticleEnriched` in addition to `ArticleListItem`. Since both have `title`, `summary`, `description` as attributes, use `getattr(article, 'title', '') or ''` etc.

Actually, the classification functions were updated in Task 4 to use `article.title or ""`. This works for both ArticleListItem (where title is `str | None`) and ArticleEnriched (where title is `str`). So if we pass ArticleEnriched to them, it should work.

Wait — but `_classify_signal_leverage(article: dict)` was changed to accept ArticleListItem. Passing ArticleEnriched would fail type checking but work at runtime since both have the same fields.

**Final approach:**
1. Change `all_sources` construction (lines 441-447) to build from ArticleEnriched directly
2. Update `_classify_signal_*` signatures to accept `ArticleListItem | ArticleEnriched` (using Union type)
3. entity_topic_dicts (lines 389-414) stays as dicts for template compatibility
4. The templates that use `source.title` etc. will still work because Jinja2 can access dict keys as attributes

This is the minimal change that preserves template compatibility.
</action>
  <verify>
python -c "
from src.application.report.report_generation import _classify_signal_leverage
from src.application.report.models import ArticleEnriched
ae = ArticleEnriched(id='1', title='OpenAI releases GPT-5', link='u', summary='sum', quality_score=0.8, feed_weight=0.6, published_at='2024-01-01', feed_id='f1')
print(_classify_signal_leverage(ae))
"
</verify>
  <done>Signal classification works with ArticleEnriched objects from entity_topics</done>
</task>

</tasks>

<verification>
Run the full test suite to ensure no regressions:
```bash
cd /Users/y3/feedship && python -c "
from src.application.articles import ArticleListItem
from src.application.dedup import deduplicate_articles
from src.application.report.filter import SignalFilter
from src.application.report.report_generation import cluster_articles_for_report, _classify_signal_leverage

# Verify ArticleListItem.to_dict()
a = ArticleListItem(id='1', feed_id='f1', feed_name='Test', title='T', link='u', guid='g', published_at='2024-01-01', description='d', content='content', quality_score=0.8, feed_weight=0.6)
d = a.to_dict()
assert d['id'] == '1' and d['quality_score'] == 0.8, 'to_dict failed'

# Verify deduplicate_articles with ArticleListItem
deduped = deduplicate_articles([a])
assert len(deduped) == 1, 'dedup failed'

# Verify SignalFilter with ArticleListItem
sf = SignalFilter()
filtered = sf.filter([a])
assert len(filtered) == 1, 'filter failed'

# Verify classification with ArticleListItem
assert _classify_signal_leverage(a) == True, 'classification failed'

print('All basic checks passed')
"
```
</verification>

<success_criteria>
- ArticleListItem.to_dict() method exists and produces a complete dict
- deduplicate_articles() accepts list[ArticleListItem] and returns list[ArticleListItem]
- SignalFilter.filter() accepts list[ArticleListItem] and returns list[ArticleListItem]
- All four classification functions accept ArticleListItem (or ArticleEnriched) and work correctly
- cluster_articles_for_report() passes ArticleListItem[] directly to _entity_report_async() without dict conversion
- ArticleEnriched creation uses ArticleListItem attributes directly
- Signal classification on entity_topics uses ArticleEnriched objects directly
</success_criteria>

<output>
After completion, create `.planning/quick/260412-article-item-refactor/SUMMARY.md` with a brief summary of changes made.
</output>
