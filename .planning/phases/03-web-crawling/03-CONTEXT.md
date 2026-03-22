# Phase 3: Web Crawling - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

User can crawl websites and store extracted content as articles. Phase adds `crawl <url>` command with Readability-based extraction, respects robots.txt lazily, and stores content in the existing articles table with a system feed.

</domain>

<decisions>
## Implementation Decisions

### Content Extraction
- **D-01:** Use Readability algorithm for article content extraction
  - Firefox Reader View algorithm for high-quality extraction
  - Extracts full article text from HTML pages
  - Falls back gracefully if extraction fails

### robots.txt Handling
- **D-02:** Lazy mode — robots.txt is ignored by default
  - User must explicitly pass `--ignore-robots` flag to force crawling
  - This is different from Phase 2's conditional fetching approach but is a deliberate choice for web crawling

### Rate Limiting
- **D-03:** Fixed 2-second delay between requests to the same host
  - Meets CRAWL-04 requirement (1-2s delay)
  - Simple and reliable, avoids being blocked

### Content Scope
- **D-04:** Full text extraction
  - Extract all visible text from the page
  - Store in content field of articles table

### Error Handling
- **D-05:** Log and skip
  - Failed extractions are logged, not stored
  - Other URLs continue processing

### CLI Command
- **D-06:** `crawl <url>` with optional `--ignore-robots` flag
  - Single URL per invocation
  - `--ignore-robots` flag to force crawling (bypass lazy mode)

### Storage
- **D-07:** Store crawled content in articles table
  - Reuses existing article list and search functionality
  - No separate pages table needed

### Feed Source
- **D-08:** System feed "Crawled Pages"
  - feed_id = 'crawled'
  - Internal system feed, not shown in `feed list`
  - Source displayed as "Crawled Pages" in article list

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/PROJECT.md` — Project constraints: Python CLI, SQLite, local-first
- `.planning/REQUIREMENTS.md` — Phase 3 requirements: CRAWL-01, CRAWL-02, CRAWL-03, CRAWL-04, CLI-04
- `.planning/phases/01-foundation/01-CONTEXT.md` — Phase 1 decisions (click framework, output format, error handling)
- `.planning/phases/02-search-refresh/02-CONTEXT.md` — Phase 2 decisions (FTS5 shadow table approach)
- `src/feeds.py` — Existing patterns for fetch_feed_content(), refresh_feed(), error handling
- `src/db.py` — Database schema with articles table, init_db() function
- `src/articles.py` — ArticleListItem dataclass and list_articles() function
- `src/cli.py` — Click-based CLI with command groups

### Key Integration Points
- `src/cli.py` — Add `crawl` command with --ignore-robots option
- `src/db.py` — Ensure 'crawled' system feed exists (created on first crawl or in init_db)
- `src/articles.py` or new `src/crawl.py` — Add crawl_url() function using Readability
- `refresh_feed()` pattern — Reuse for single URL crawling with rate limiting
</canonical_refs>

<codebase_context>
## Existing Code Insights

### Reusable Assets
- Phase 1 established click-based CLI structure with hierarchical commands
- Phase 1 established httpx for HTTP requests
- Phase 1 established ANSI colors: green success, yellow warnings, red errors
- Phase 2 established FTS5 integration for search
- Database already has UNIQUE(feed_id, guid) constraint
- ArticleListItem dataclass in articles.py

### Established Patterns
- Per-feed error isolation: try/except per item, continue on failure
- ANSI colors for success/warning/error feedback
- Table/list output formats from Phase 1
- Rate limiting pattern can reuse httpx timeout infrastructure

### Integration Points
- New `crawl` command in cli.py (parallel to `feed` command group)
- Store crawled articles with feed_id = 'crawled' in articles table
- Need to create 'crawled' system feed if it doesn't exist
- Content goes to articles.content field (same as feed articles)
</codebase_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for implementation details.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>
