# Quick Task 260414-nda: 增加约束：UNIQUE(link) 删除feed 里的link重复文章

**Completed:** 2026-04-14
**Commit:** 2251307

## Summary

Added UNIQUE constraint on `articles.link` to prevent duplicate articles:

1. **Migration script** (`scripts/migrate_add_article_link_unique.py`):
   - Deleted 223 duplicate articles from existing database
   - Created UNIQUE index `idx_articles_link_unique` on `articles.link`
   - Verified 0 duplicates remain

2. **Schema update** (`src/storage/sqlite/init.py`):
   - Replaced `CREATE INDEX idx_articles_link` with `CREATE UNIQUE INDEX idx_articles_link_unique`
   - New installations will have the UNIQUE constraint from initialization

## Results

| Metric | Value |
|--------|-------|
| Duplicates deleted | 223 |
| Articles before | 4306 |
| Articles after | 4083 |
| Constraint created | idx_articles_link_unique |

## Files Changed

- `scripts/migrate_add_article_link_unique.py` (new)
- `src/storage/sqlite/init.py`
