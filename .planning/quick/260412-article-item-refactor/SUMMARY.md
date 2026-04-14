# Quick Task Summary: ArticleListItem Typed Pipeline

**Completed:** 2026-04-12

## Changes Made

1. **`src/application/articles.py`** — Added `to_dict()` method to `ArticleListItem` dataclass for boundaries that require dict (template rendering).

2. **`src/application/dedup.py`** — Changed `_level1_exact_dedup`, `_level2_minhash_dedup`, `_level3_embedding_dedup`, and `deduplicate_articles()` to accept `list[ArticleListItem]` instead of `list[dict]`. All `a.get("field")` calls replaced with `a.field` attribute access.

3. **`src/application/report/filter.py`** — Changed `SignalFilter.filter()` and `_passes_all_rules()` to accept `list[ArticleListItem]`. All `article.get("field")` replaced with `article.field` attribute access.

4. **`src/application/report/report_generation.py`** — Multiple changes:
   - Removed dict conversion in `cluster_articles_for_report()` — passes `ArticleListItem[]` directly to `_entity_report_async()`
   - `_entity_report_async()` signature updated to `list[ArticleListItem]`
   - `process_batch()` uses `art.title or ''` instead of `art.get('title', '')`
   - `tag_groups` type changed to `dict[str, list[tuple[int, ArticleListItem]]]`
   - ArticleEnriched creation uses `art.id or ""` etc. instead of `art.get("id", "")`
   - `best_art` and `quality_weight` calculations use attribute access
   - `_classify_signal_leverage`, `_classify_signal_business`, `_classify_creation`, `_classify_dim` accept `ArticleListItem | ArticleEnriched` via `getattr` with fallback
   - Signal classification builds `all_sources` from `ArticleEnriched` directly (typed, not via dict flattening)

5. **`tests/test_report.py`** — Updated `TestDedupArticles` to use `ArticleListItem` instead of dict.

## Key Design Decisions

- Used `getattr(article, 'field', '') or ''` pattern in classification functions to accept both `ArticleListItem` and `ArticleEnriched` (both have same needed fields: title, summary, description)
- Kept `entity_topic_dicts` as dicts for template compatibility — Jinja2 can access dict keys as attributes
- `to_dict()` on `ArticleListItem` available for any future boundaries needing dict

## Pre-existing Failures (not introduced by this change)

- `test_report_end_to_end` — references `src.application.summarize` which was removed in a prior dead-code cleanup session
- `test_entity_cluster.py` import error — `entity_cluster.py` was moved to `entity_report/` in a prior session, test file still references old location
