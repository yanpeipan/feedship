# Phase 17: Anti-屎山 Refactoring - Research

**Researched:** 2026-03-24
**Domain:** Python refactoring patterns, SQLite context managers, Click CLI architecture
**Confidence:** HIGH (internal codebase analysis, no external dependencies)

## Summary

Phase 2 of the Anti-屎山 refactoring addresses three concrete problems: (1) cli.py at 798 lines needs splitting into a `cli/` package with command groups, (2) `RSSProvider.feed_meta()` incorrectly calls `crawl()` instead of doing a lightweight HEAD request, and (3) all database functions use bare `get_connection()` + manual `conn.close()` instead of a context manager.

**Primary recommendation:** Add a `get_db()` context manager to `db.py`, migrate all bare `get_connection()` calls, then split cli.py into the `src/cli/` package structure defined in docs/feed.md. The `feed_meta()` fix should use `httpx.head()` in `RSSProvider.feed_meta()` rather than full content fetch.

## User Constraints (from docs/feed.md)

### Locked Decisions
- **DB via context manager** - `with get_db() as conn:` replaces bare `get_connection()` + manual close
- **No circular imports** - providers don't import each other, shared logic in base.py
- **CLI is a thin shell** - all business logic in application/
- **feed_meta() doesn't crawl()** - metadata fetch is separate from content fetch
- **Single data access layer** - `db.py` owns all SQL, application modules call db functions

### Target CLI Structure
| Command | Module |
|---------|--------|
| `feed add/list/remove/refresh` | cli/feed.py |
| `fetch --all` | cli/feed.py |
| `crawl <url>` | cli/crawl.py |
| `article list/view/open/tag` | cli/article.py |
| `tag add/list/remove` | cli/tag.py |
| `tag rule add/list/edit/remove` | cli/tag.py |

## Standard Stack

### Core Technologies
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | 8.1.x | CLI framework | Decorator-based, automatic help, nested command groups |
| sqlite3 | built-in | Database | No external deps, DB-API 2.0 compliant |
| httpx | 0.27.x | HTTP client | Async/sync, HTTP/2, head() support for metadata-only requests |

### No Changes Needed For
- feedparser 6.0.x - already working, not part of this refactor
- BeautifulSoup4 4.12.x - not affected
- rich - already in use by cli.py

## Architecture Patterns

### 1. DB Context Manager Pattern
**Current (anti-pattern):**
```python
conn = get_connection()
try:
    cursor = conn.cursor()
    cursor.execute(...)
    conn.commit()
finally:
    conn.close()
```

**Target (context manager):**
```python
with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute(...)
    conn.commit()
# Connection auto-closed on exit
```

**Implementation in db.py:**
```python
from contextlib import contextmanager

@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
```

### 2. cli.py Split Pattern
**Target structure:**
```
src/cli/
├── __init__.py      # Imports all commands, re-exports cli()
├── feed.py          # feed group + feed add/list/remove/refresh + fetch --all
├── article.py       # article group + article list/view/open/tag
├── tag.py           # tag group + tag add/list/remove + rule sub-group
└── crawl.py        # crawl command
```

**Entry point in __init__.py:**
```python
"""CLI package - re-exports cli() from src.cli."""
from src.cli import cli

if __name__ == "__main__":
    cli()
```

**pyproject.toml update needed:**
```toml
[project.scripts]
rss-reader = "src.cli:cli"  # Change from "src.cli:cli"
```

### 3. feed_meta() Lightweight Pattern
**Current (wrong - calls crawl()):**
```python
def feed_meta(self, url: str) -> Feed:
    entries = self.crawl(url)  # Expensive - fetches full content!
    if not entries:
        raise ValueError(f"No entries in feed {url}")
    return Feed(name=_feed_title_var.get() or url, ...)
```

**Target (HEAD only):**
```python
def feed_meta(self, url: str) -> Feed:
    """Fetch feed metadata via lightweight HEAD request."""
    response = httpx.head(url, timeout=10.0, follow_redirects=True)
    # Extract title from Content-Type or headers
    # Return Feed with name from URL or headers, no full content fetch
```

**For RSS feeds specifically:** Parse the feed with a timeout and limited bytes, since RSS feeds don't support true HEAD responses for metadata. Use `httpx.get(..., timeout=5.0)` with `follow_redirects=True` but only read minimal content to get the feed title. Alternative: use a shorter timeout and catch exceptions.

### 4. Duplicate _store_article
**Found in two places:**
- `db.py:store_article()` (lines 283-354)
- `application/feed.py:_store_article()` (lines 310-361)

**Resolution:** Keep `db.py:store_article()`, update `application/feed.py` to call `db.store_article()` instead of its own `_store_article()`.

## Bare get_connection() Inventory

| File | Function | Line | Pattern |
|------|----------|------|---------|
| db.py | add_tag | 151 | `conn = get_connection()` |
| db.py | list_tags | 169 | `conn = get_connection()` |
| db.py | remove_tag | 180 | `conn = get_connection()` |
| db.py | get_tag_article_counts | 202 | `conn = get_connection()` |
| db.py | tag_article | 219 | `conn = get_connection()` |
| db.py | untag_article | 249 | `conn = get_connection()` |
| db.py | get_article_tags | 269 | `conn = get_connection()` |
| db.py | store_article | 310 | `conn = get_connection()` |
| db.py | init_db | 67 | `conn = get_connection()` (OK - no close in finally) |
| application/feed.py | add_feed | 65, 79 | Two calls, both need migration |
| application/feed.py | list_feeds | 118 | Single call |
| application/feed.py | get_feed | 159 | Single call |
| application/feed.py | remove_feed | 191 | Single call |
| application/feed.py | _store_article | 322 | Single call |
| articles.py | list_articles | 49 | Single call |
| articles.py | get_article | 108 | Single call |
| articles.py | get_article_detail | 148 | Single call |
| articles.py | search_articles | 222 | Single call |
| articles.py | list_articles_with_tags | 302 | Single call |
| articles.py | get_articles_with_tags | 381 | Single call |
| cli.py | article_tag | 452-453 | Inline bare usage in apply_rules section |
| crawl.py | crawl_url | 185 | Single call |
| ai_tagging.py | multiple | 93, 110, 126, 188, 266 | Multiple functions |

**Total: ~22 call sites need migration**

## feed_meta() Implementation Analysis

**RSSProvider.feed_meta() (lines 300-328):**
```python
def feed_meta(self, url: str) -> "Feed":
    from src.models import Feed
    from src.config import get_timezone
    from datetime import datetime

    # WRONG: calls crawl() which fetches full content
    entries = self.crawl(url)
    if not entries:
        raise ValueError(f"No entries in feed {url}")

    now = datetime.now(get_timezone()).isoformat()

    return Feed(
        id="",  # ID not assigned - this is metadata only
        name=_feed_title_var.get() or url,
        url=url,
        etag=None,
        last_modified=None,
        last_fetched=now,
        created_at=now,
    )
```

**Problem:** `crawl()` is expensive - it fetches full feed content, parses all entries, and sets `_feed_title_var`. For `feed_meta()`, we only need the feed title.

**Solution:** Use `httpx.get()` with limited content parsing:
```python
def feed_meta(self, url: str) -> "Feed":
    from src.models import Feed
    from src.config import get_timezone
    from datetime import datetime

    try:
        # Lightweight fetch with short timeout
        response = httpx.get(url, headers=BROWSER_HEADERS, timeout=5.0, follow_redirects=True)
        response.raise_for_status()

        # Parse just enough to get feed title
        parsed = feedparser.parse(response.content)
        title = parsed.feed.get("title") if parsed.feed else url

        # Get headers for future conditional requests
        etag = response.headers.get("etag")
        last_modified = response.headers.get("last-modified")

        now = datetime.now(get_timezone()).isoformat()

        return Feed(
            id="",
            name=title,
            url=url,
            etag=etag,
            last_modified=last_modified,
            last_fetched=now,
            created_at=now,
        )
    except Exception as e:
        raise ValueError(f"Failed to fetch feed metadata: {e}")
```

**GitHubReleaseProvider.feed_meta()** (lines 168-197) is already correct - it uses GitHub API directly without calling `crawl()`.

## Circular Import Risks

**When splitting cli.py, watch for:**

1. `cli/__init__.py` imports `cli.feed`, `cli.article`, `cli.tag`, `cli.crawl`
2. Each sub-module imports from `application/`, `db.py`, `providers/`
3. `providers/__init__.py` loads all providers at import time via `load_providers()`
4. `application/feed.py` imports from `providers`

**Safe import order:**
```
cli/__init__.py
  └── cli.feed (imports application.feed, db, providers)
  └── cli.article (imports articles, db, providers)
  └── cli.tag (imports db, tag_rules)
  └── cli.crawl (imports crawl module)
```

**Avoid:**
- cli submodules importing from each other
- application modules importing from cli

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DB connection management | Custom connection pooling | Context manager with `get_db()` | Simple, Pythonic, auto-cleanup |
| CLI command groups | Multiple script files | Click nested command groups | Proper help, tab completion, consistent UX |
| Feed metadata | Custom HTTP headers parsing | httpx head/get + feedparser | Already in stack |

## Common Pitfalls

### Pitfall 1: Forgetting to Update pyproject.toml
**What goes wrong:** `rss-reader` CLI command breaks after splitting cli.py.
**How to avoid:** Update entry point to `src.cli:cli` after creating `src/cli/__init__.py`.

### Pitfall 2: Duplicate _store_article
**What goes wrong:** Two different store functions cause inconsistent behavior.
**How to avoid:** Consolidate to `db.store_article()`, remove `_store_article()` from `application/feed.py`.

### Pitfall 3: feed_meta() Still Calls crawl()
**What goes wrong:** Expensive full fetch on every `feed add` command.
**How to avoid:** Use lightweight `httpx.get()` with short timeout + feedparser for title only.

### Pitfall 4: Missing Context Manager Migration
**What goes wrong:** Some functions still use bare `get_connection()`, causing connection leaks.
**How to avoid:** Audit all 22 call sites after adding `get_db()`.

### Pitfall 5: Circular Import After Split
**What goes wrong:** `cli.feed` imports `application.feed`, which imports `providers`, which triggers `load_providers()` which imports `cli` modules.
**How to avoid:** Ensure cli submodules don't import application modules that might trigger circular loading. Keep application layer clean of CLI imports.

## Code Examples

### Adding get_db() Context Manager to db.py
```python
from contextlib import contextmanager

@contextmanager
def get_db():
    """Context manager for database connections.

    Yields a configured connection and ensures it is closed on exit.

    Usage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(...)
            conn.commit()
    """
    conn = _get_connection()
    try:
        yield conn
    finally:
        conn.close()

# Rename existing get_connection to _get_connection (internal)
def _get_connection() -> sqlite3.Connection:
    """Internal: create database connection with optimized settings."""
    # ... existing implementation ...
```

### Migrating a Function
**Before:**
```python
def list_tags() -> list[Tag]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM tags ORDER BY name")
        return [Tag(...) for row in cursor.fetchall()]
    finally:
        conn.close()
```

**After:**
```python
def list_tags() -> list[Tag]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, created_at FROM tags ORDER BY name")
        return [Tag(...) for row in cursor.fetchall()]
```

## Open Questions

1. **crawl.py module location:** The `crawl` command in cli.py calls `src.crawl.crawl_url()`. After splitting, should `src/cli/crawl.py` import from `src.crawl` or should the crawl logic move into `src/cli/`?
   - Recommendation: Keep `src.crawl` as the business logic module, `src/cli/crawl.py` as the thin CLI wrapper.

2. **ai_tagging.py scope:** `ai_tagging.py` has 5 bare `get_connection()` calls. Should these also be migrated, or is ai_tagging planned for Phase 3?
   - Recommendation: Migrate all bare connections in this phase per the anti-屎山 rules.

3. **_store_article consolidation:** `application/feed.py` has its own `_store_article()` that does FTS5 sync. `db.store_article()` also does FTS5 sync. Are they identical?
   - Verified: Both do identical FTS5 sync. Consolidate to `db.store_article()`.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies - pure refactoring phase)

## Sources

### Primary (HIGH confidence - internal codebase)
- `docs/feed.md` - Target architecture specification
- `src/cli.py` (798 lines) - CLI commands to split
- `src/db.py` (355 lines) - DB functions needing context manager
- `src/providers/rss_provider.py` - feed_meta() issue at lines 300-328
- `src/application/feed.py` (362 lines) - _store_article duplicate
- `src/articles.py` (400 lines) - bare get_connection() calls

### Secondary (MEDIUM confidence - established patterns)
- Click documentation for nested command groups (standard pattern)
- Python contextlib.contextmanager documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no changes to dependencies
- Architecture: HIGH - based on docs/feed.md specification
- Pitfalls: HIGH - derived from codebase analysis

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (refactoring patterns don't expire)
