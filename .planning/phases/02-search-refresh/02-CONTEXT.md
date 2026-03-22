# Phase 2: search-refresh - Context

**Gathered:** 2026-03-23 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

User can search articles by keyword and refresh feeds efficiently with conditional fetching. This phase adds full-text search capability and completes conditional fetching implementation.
</domain>

<decisions>
## Implementation Decisions

### FTS5 Implementation
- **D-01:** Shadow FTS5 virtual table approach
  - Separate `articles_fts` FTS5 table indexes title, description, content
  - Manual sync in `refresh_feed()` after INSERT loop
  - Avoids complex trigger management, keeps articles schema unchanged

- **D-02:** Index title, description, and content fields for FTS5
  - Ensures comprehensive search across all article text fields

### Search Query Interface
- **D-03:** Expose FTS5 query syntax directly to users
  - Simple keyword matching (space-separated = AND)
  - Quoted phrases for exact match: `"machine learning"`
  - AND/OR operators for advanced users

- **D-04:** Multiple keywords default to AND behavior (all must match)
  - Intuitive default, reduces noise in results

### Search Results Display
- **D-05:** Same format as `article list` command (title | feed | date columns)
  - Consistency with established UX patterns

- **D-06:** Sort search results by FTS5 bm25 ranking (relevance)
  - Relevance-based results, not date-based

### CLI Command Structure
- **D-07:** `article search` subcommand with `--limit` and `--feed-id` filter options
  - Follows established `article` command group pattern
  - Options parallel to `article list`

### Conditional Fetching (FETCH-05)
- **D-08:** Already implemented in Phase 1
  - `fetch_feed_content()` sends ETag/Last-Modified headers
  - `refresh_feed()` handles 304 Not Modified responses
  - No additional implementation needed
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/01-foundation/01-CONTEXT.md` — Phase 1 decisions (CLI: click, output format, error handling)
- `src/feeds.py` — Already implements conditional fetching (lines 39-75 fetch, lines 326-348 refresh with 304 handling)
- `src/db.py` — Database schema with feeds/articles tables, init_db() function
- `src/articles.py` — Article listing with ArticleListItem dataclass
- `src/cli.py` — Click-based CLI with article command group

### Key Integration Points
- `init_db()` in `src/db.py` — Add FTS5 table creation
- `refresh_feed()` in `src/feeds.py` — Sync new articles to FTS5
- `src/articles.py` — Add `search_articles()` function using FTS5 MATCH
- `src/cli.py` — Add `article search` subcommand
</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 established click-based CLI structure with hierarchical commands
- articles.py already has ArticleListItem dataclass and list_articles()
- feeds.py already extracts title, description, content from entries
- Database already has UNIQUE(feed_id, guid) constraint

### Established Patterns
- Per-feed error isolation: try/except per feed, continue on failure
- ANSI colors: green success, yellow warnings, red errors
- Table/list output formats from Phase 1

### Integration Points
- FTS5 table needs creation in init_db()
- FTS5 sync after article INSERT in refresh_feed()
- New search_articles() function in articles.py
- New search subcommand in cli.py
</codebase_context>

<specifics>
## Specific Ideas

- FTS5 highlight() and snippet() functions for UX enhancement (nice-to-have)
- Handle special characters and empty queries gracefully
</specifics>

<deferred>
## Deferred Ideas

None — analysis stayed within phase scope

</deferred>
