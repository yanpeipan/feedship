# Quick Execute Summary: 260411-1rz

## Objective
Merge `list_articles_for_llm` into `list_articles`. Remove `unsummarized_only` param. Update all callers.

## Tasks Completed

### Task 1: Extend `list_articles` SELECT (articles.py)
- Extended SELECT to include `f.weight as feed_weight`, `a.content`, `a.summary`, `f.url as feed_url`
- Updated `_compute_article_item` to populate all four new fields on `ArticleListItem`

### Task 2: Extend `ArticleListItem` dataclass (articles.py application layer)
- Added four new fields: `content`, `summary`, `feed_weight`, `feed_url` (all with `None` defaults)

### Task 3: Remove `list_articles_for_llm` (llm.py)
- Deleted `list_articles_for_llm` function (lines 111-205)
- Removed unused imports (`_date_to_str`, `_date_to_str_end`, `_published_at_to_timestamp`)

### Task 4: Update re-exports and imports
- `src/storage/__init__.py`: removed `list_articles_for_llm` from impl imports
- `src/storage/sqlite/__init__.py`: removed from llm imports and `__all__`
- `src/storage/sqlite/impl.py`: removed from llm imports
- `src/cli/summarize.py`: changed import to `list_articles`, updated 3 call sites (`a["id"]` -> `a.id`)
- `src/application/report/report_generation.py`: changed import to `list_articles`, removed `unsummarized_only` arg, added dict conversion for ArticleListItem objects

## Verification
- `grep -r "list_articles_for_llm" src/` → No matches
- All 8 modified files pass `python3 -m py_compile`

## Truths Met
- `list_articles_for_llm` removed from entire codebase
- `list_articles` extended with `content`, `summary`, `feed_weight`, `feed_url` fields
- All callers updated to use `list_articles` (with dict conversion where needed)
