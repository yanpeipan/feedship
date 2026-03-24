# Phase 18: Storage Layer Enforcement - Context

**Gathered:** 2026-03-25 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Make `get_db()` internal to `src/storage/` — all SQL operations must live in `src/storage/sqlite.py`. Application/CLI layers use storage functions only, never direct `cursor.execute()` calls. This enforces the storage layer abstraction established in Phase 17.

</domain>

<decisions>
## Implementation Decisions

### Storage Layer Boundary
- **D-01:** All SQL operations belong in `src/storage/` — application/CLI layers use storage functions only
- **D-02:** `get_db()` stays in `src/storage/sqlite.py` as the ONLY place exposing database connections
- **D-03:** `src/storage/__init__.py` exports the public storage API — modules import from `src.storage`, not `src.storage.sqlite`

### Scope: Article Operations (from `src/application/articles.py`)
- **D-04:** Move `list_articles()` to `src/storage/sqlite.py` — returns `list[ArticleListItem]`
- **D-05:** Move `get_article()` to `src/storage/sqlite.py` — returns `Optional[ArticleListItem]`
- **D-06:** Move `get_article_detail()` to `src/storage/sqlite.py` — returns `dict` with tags
- **D-07:** Move `search_articles()` to `src/storage/sqlite.py` — returns `list[ArticleListItem]`
- **D-08:** Move `list_articles_with_tags()` to `src/storage/sqlite.py` — returns `list[ArticleListItem]`
- **D-09:** Move `get_articles_with_tags()` to `src/storage/sqlite.py` — returns `dict[str, list[str]]`

### Scope: Feed Operations (from `src/application/feed.py`)
- **D-10:** Move `add_feed()` to `src/storage/sqlite.py` — returns `Feed`
- **D-11:** Move `list_feeds()` to `src/storage/sqlite.py` — returns `list[Feed]` with article counts
- **D-12:** Move `get_feed()` to `src/storage/sqlite.py` — returns `Optional[Feed]`
- **D-13:** Move `remove_feed()` to `src/storage/sqlite.py` — returns `bool`

### Scope: Crawl Operations (from `src/application/crawl.py`)
- **D-14:** Move `ensure_crawled_feed()` to `src/storage/sqlite.py` — no return value

### Scope: CLI Operations (from `src/cli/article.py`)
- **D-15:** Create `get_untagged_articles()` in `src/storage/sqlite.py` to replace direct SQL in `article_tag --rules`

### Scope: AI Tagging (from `src/tags/ai_tagging.py`)
- **D-16:** Move `store_embedding()`, `get_embedding()`, `_ensure_embeddings_table()` to `src/storage/sqlite.py`
- **D-17:** `src/tags/ai_tagging.py` imports embedding functions from `src.storage` only

### API Design
- **D-18:** Storage functions return domain objects (`ArticleListItem`, `Feed`, etc.) — not raw dicts/rows
- **D-19:** Storage functions handle their own connection management via `get_db()` context manager

### What Stays
- **D-20:** `src/models.py` stays — `ArticleListItem`, `Feed`, `Article` dataclasses remain shared types
- **D-21:** `src/application/articles.py` and `src/application/feed.py` remain — but become thin wrappers calling storage functions

### Import Structure
- **D-22:** All modules import storage functions from `src.storage` (public API), not `src.storage.sqlite` (internal)
- **D-23:** No module outside `src/storage/` should call `get_db()` directly

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Storage Layer (current state)
- `src/storage/__init__.py` — Public storage API exports
- `src/storage/sqlite.py` — Current storage implementation with `get_db()`, `store_article()`, tag operations

### Application Layer (operations to move)
- `src/application/articles.py` — `list_articles()`, `get_article()`, `get_article_detail()`, `search_articles()`, `list_articles_with_tags()`, `get_articles_with_tags()` (lines 39-381)
- `src/application/feed.py` — `add_feed()`, `list_feeds()`, `get_feed()`, `remove_feed()` (lines 25-184)
- `src/application/crawl.py` — `ensure_crawled_feed()` (lines 179-195)

### CLI Layer (operations to fix)
- `src/cli/article.py` — `apply_rules` section with direct SQL (lines 246-276)

### Tags Layer (operations to move)
- `src/tags/ai_tagging.py` — `store_embedding()`, `get_embedding()`, `_ensure_embeddings_table()` (lines 81-127)

### Models
- `src/models.py` — `ArticleListItem`, `Feed`, `Tag` dataclasses

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/storage/sqlite.py` already has correct patterns: `get_db()` context manager, `store_article()`, tag operations
- `ArticleListItem` dataclass in `src/application/articles.py` — natural return type
- `Feed` model in `src/models.py` — already used by feed operations

### Established Patterns
- `get_db()` context manager pattern: `with get_db() as conn: cursor = conn.cursor()`
- Storage functions return domain objects, not raw rows
- `src/storage/__init__.py` is the public API entry point

### Integration Points
- `src/application/articles.py` → imports from `src.storage.sqlite` (line 11)
- `src/application/feed.py` → imports from `src.storage.sqlite` (line 11)
- `src/application/crawl.py` → imports from `src.storage.sqlite` (line 26)
- `src/cli/article.py` → imports from `src.storage.sqlite` (line 249)
- `src/tags/ai_tagging.py` → imports from `src.storage.sqlite` (line 17)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — analysis stayed within phase scope

</deferred>
