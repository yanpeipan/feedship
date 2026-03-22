# Milestones

## v1.0 MVP (Shipped: 2026-03-22)

**Phases completed:** 3 phases, 9 plans, 12 tasks

**Key accomplishments:**

- SQLite database with WAL mode, Feed/Article dataclasses, and project dependencies configured
- Feed CRUD operations with RSS/Atom parsing, bozo detection, and article deduplication via GUID/UNIQUE constraint
- Click-based CLI with feed management and article listing commands with ANSI colors and per-feed error isolation
- Commit:
- Article search subcommand added to CLI with FTS5-powered full-text search via search_articles() function
- One-liner:
- crawl_url() function with Readability extraction, robots.txt lazy compliance, and 2-second per-host rate limiting
- `crawl` CLI command with --ignore-robots flag wrapping crawl_url() for web content extraction

---
