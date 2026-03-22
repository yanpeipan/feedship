# Phase 1: Foundation - Research

**Researched:** 2026-03-23
**Domain:** RSS/Atom feed parsing, HTTP fetching, SQLite storage, CLI interface
**Confidence:** HIGH

## Summary

Phase 1 implements a personal RSS reader with feed subscription, article storage, and CLI access. The core stack is Python with feedparser for RSS/Atom parsing, httpx for HTTP requests, click for CLI, and sqlite3 for storage. The phase covers 16 requirements across feed management (FEED-01-04), content fetching (FETCH-01-04), storage (STOR-01-03), and CLI commands (CLI-01-03, CLI-05, CLI-07).

Key technical decisions: feedparser's bozo detection handles malformed XML, GUID-based deduplication with link+pubDate fallback, SQLite WAL mode for concurrency, and per-feed error isolation so one bad feed does not crash the system.

**Primary recommendation:** Use feedparser 6.0.x with bozo detection for feed parsing, httpx 0.28.x for HTTP, click 8.x for CLI, and sqlite3 with WAL mode for storage.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Use `click` framework for CLI
- **D-02:** Plain text output with ANSI colors
  - `feed list`: table format (name, URL, article count, last update)
  - `article list`: list format per line (title | source | date)
  - Default concise output, `-v` verbose mode for more info
- **D-03:** Single feed failure does not affect other feeds
  - Network errors: show error, continue next feed
  - Parse errors: use feedparser bozo detection, skip malformed feeds
  - Database errors: rollback transaction, fail entirely
- **D-04:** Standard normalized schema
  - `feeds` table: id, name, url, etag, last_modified, last_fetched, created_at
  - `articles` table: id, feed_id, title, link, guid, pub_date, description, content, created_at
  - UNIQUE(feed_id, guid) to prevent duplicates
  - Indexes: feed_id, pub_date, link
- **D-05:** Command structure
  - `feed add <url>` - Add feed
  - `feed list` - List all feeds
  - `feed remove <id>` - Delete feed
  - `feed refresh <id>` - Refresh single feed
  - `article list` - List recent articles (default 20)
  - `fetch --all` - Refresh all feeds

### Claude's Discretion

- Exact color scheme and format details
- Error log format and verbosity
- Article sorting rules (default date descending)

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **feedparser** | 6.0.12 | RSS/Atom parsing | Universal parser for RSS 0.9x-2.0, Atom, RDF. Bozo detection for malformed feeds. Active maintenance. |
| **httpx** | 0.28.1 | HTTP client | Modern async/sync HTTP client with requests-compatible API. HTTP/2 support. Timeout handling. |
| **click** | 8.3.1 (8.1.8 installed) | CLI framework | Decorator-based, automatic help generation, composable commands. Most popular modern Python CLI framework. |
| **sqlite3** | (built-in) | Database | No external dependencies. Sufficient for personal use cases. WAL mode for concurrency. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **beautifulsoup4** | 4.14.3 (4.12.3 installed) | HTML parsing | Extracting content from HTML pages. Use lxml parser backend. |
| **lxml** | 6.0.2 | Fast XML/HTML parser | C-based parser backend for BeautifulSoup. Faster than html.parser. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests | httpx has async support and HTTP/2. requests is fine if sync-only needed. |
| click | typer | Both are good. click has larger ecosystem and more examples. typer adds dependency on fastapi utilities. |
| beautifulsoup4 + lxml | lxml directly | BeautifulSoup provides more convenient navigation API. |
| sqlite3 | SQLAlchemy | sqlite3 is sufficient for personal use. SQLAlchemy adds complexity. |

**Installation:**
```bash
pip install feedparser httpx click beautifulsoup4 lxml
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── __init__.py
├── cli.py              # CLI entry point (click)
├── db.py               # SQLite connection, migrations
├── feeds.py            # Feed operations (fetch, parse, add, remove)
├── articles.py         # Article operations (list, deduplication)
├── models.py           # Data models (Feed, Article dataclasses)
└── utils/
    └── __init__.py
data/
└── .gitkeep            # SQLite database stored here
tests/
pyproject.toml
```

### Pattern 1: Repository Pattern for SQLite

Abstracts database behind repository interfaces.

```python
# Source: Python sqlite3 documentation
import sqlite3
from dataclasses import dataclass
from typing import Optional

@dataclass
class Feed:
    id: str
    name: str
    url: str
    etag: Optional[str]
    last_modified: Optional[str]
    last_fetched: Optional[str]
    created_at: str

class FeedRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def save(self, feed: Feed) -> str:
        with self.connect() as con:
            cur = con.cursor()
            cur.execute('''
                INSERT OR REPLACE INTO feeds
                (id, name, url, etag, last_modified, last_fetched, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (feed.id, feed.name, feed.url, feed.etag,
                  feed.last_modified, feed.last_fetched, feed.created_at))
        return feed.id
```

### Pattern 2: Per-Feed Error Isolation

Single feed failure does not affect other feeds.

```python
# Source: Common Python pattern for bulk operations
def refresh_all_feeds(feed_ids: list[str]) -> RefreshSummary:
    summary = RefreshSummary()
    for feed_id in feed_ids:
        try:
            result = refresh_single_feed(feed_id)
            summary.add_success(result)
        except FeedNotFoundError:
            summary.add_skipped(f"Feed {feed_id} not found")
        except NetworkError as e:
            summary.add_error(f"Network error for {feed_id}: {e}")
            continue  # Continue to next feed
        except ParseError as e:
            summary.add_error(f"Parse error for {feed_id}: {e}")
            continue  # Continue to next feed
    return summary
```

### Pattern 3: feedparser Bozo Detection

Handles malformed XML gracefully.

```python
# Source: feedparser documentation
import feedparser

def parse_feed(url: str) -> tuple[list[dict], bool]:
    feed = feedparser.parse(url)

    if feed.bozo:
        # Malformed XML detected - log but continue
        log.warning(f"Malformed feed at {url}: {feed.bozo_exception}")

    entries = []
    for entry in feed.entries:
        article = {
            'title': entry.get('title', ''),
            'link': entry.get('link', ''),
            'guid': entry.get('id') or entry.get('link', ''),
            'pub_date': parse_date(entry.get('published', '')),
            'description': entry.get('summary', ''),
            'content': entry.get('content', [{}])[0].get('value', ''),
        }
        entries.append(article)

    return entries, feed.bozo
```

### Anti-Patterns to Avoid

- **Don't ignore bozo flag:** feedparser sets `bozo=True` for malformed feeds. Skipping bozo feeds silently loses data.
- **Don't use link as primary GUID:** Many feeds lack `<guid>`. Fall back to link+pubDate hash when guid missing.
- **Don't use DELETE without LIMIT:** Large deletes lock the database. Use batched deletes.
- **Don't use OFFSET for pagination:** Linear cost. Use cursor-based pagination instead.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSS/Atom parsing | Custom XML parser | feedparser | Handles all RSS versions, namespaces, malformed XML, encoding issues |
| HTTP requests | urllib | httpx | Timeout handling, connection pooling, HTTP/2, async support |
| CLI help generation | manual --help | click | Auto-generates help, handles argument parsing, subcommands |
| SQLite WAL setup | ad-hoc | sqlite3 with WAL pragma | Proper concurrency, atomic writes, concurrent reads |
| Date parsing | strftime | feedparser date parsing + iso8601 | RFC 822 and Atom date formats handled correctly |

**Key insight:** RSS parsing is notoriously fragile - many feeds are not spec-compliant. feedparser handles ~96% of feeds correctly with bozo detection for the rest. Building a custom parser wastes time.

---

## Common Pitfalls

### Pitfall 1: Malformed RSS/XML Feed Parsing

**What goes wrong:** Feeds fail silently, items are missed, entire feed skipped.

**Why it happens:** Many feeds contain invalid XML characters, unescaped special characters, malformed entities, or wrong encoding declarations.

**How to avoid:** Always check `feed.bozo` flag. Log `feed.bozo_exception` for debugging. Sanitize HTML content before storage.

**Warning signs:** Feed consistently returns 0 items but no error.

### Pitfall 2: Missing or Unreliable GUID

**What goes wrong:** Duplicate items appear repeatedly, or items incorrectly marked as duplicates.

**Why it happens:** Only ~96.4% of feeds include `<guid>` per RSS Board analysis. Some use permalinks as GUID values.

**How to avoid:** Use GUID when present. Fall back to SHA256(link + pubDate) when missing. Log when falling back.

```python
def generate_article_id(entry: dict) -> str:
    guid = entry.get('id') or entry.get('link', '')
    if not guid:
        # Fallback to link + pubDate hash
        link = entry.get('link', '')
        pub_date = entry.get('published', '')
        guid = hashlib.sha256(f"{link}:{pub_date}".encode()).hexdigest()
    return guid
```

### Pitfall 3: SQLite Concurrent Write Contention

**What goes wrong:** "database is locked" errors, write failures.

**Why it happens:** SQLite allows only ONE writer. Multiple CLI invocations compete for lock.

**How to avoid:** Enable WAL mode, set busy_timeout, batch writes.

```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
PRAGMA cache_size=-4000;  -- 4MB
```

### Pitfall 4: Date/Time Parsing Chaos

**What goes wrong:** Items sorted incorrectly, future dates appear, timezone confusion.

**Why it happens:** RSS uses RFC 822 with ambiguous timezones. Atom uses ISO 8601 with varying precision.

**How to avoid:** Always normalize to UTC internally. Use feedparser's date parsing. Default to crawl time if no valid date.

### Pitfall 5: CLI Interactive Prompts in Scripts

**What goes wrong:** Scripts hang waiting for input, cron jobs fail.

**Why it happens:** CLI waits for confirmation when run non-interactively.

**How to avoid:** Provide `--yes` or `--force` flags. Detect TTY with `sys.stdin.isatty()` and fail fast without interactive input. Default to "no" for non-interactive contexts.

---

## Code Examples

### feedparser Parsing with Error Handling

```python
# Source: feedparser documentation + best practices
import feedparser

def fetch_and_parse_feed(url: str, etag: str = None, last_modified: str = None):
    """Fetch and parse a feed with conditional request support."""
    headers = {}
    if etag:
        headers['If-None-Match'] = etag
    if last_modified:
        headers['If-Modified-Since'] = last_modified

    # httpx for the HTTP request (sync version shown)
    import httpx
    response = httpx.get(url, headers=headers, timeout=30.0)

    if response.status_code == 304:
        return None  # Not modified

    # feedparser parses the content
    feed = feedparser.parse(response.text)

    # Check bozo flag for malformed feeds
    if feed.bozo:
        log.warning(f"Malformed feed {url}: {feed.bozo_exception}")

    return feed
```

### SQLite Connection with WAL Mode

```python
# Source: sqlite3 documentation
import sqlite3
from pathlib import Path

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get a SQLite connection with proper configuration."""
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA cache_size=-4000")
    con.row_factory = sqlite3.Row
    return con

def init_db(db_path: str):
    """Initialize database schema."""
    with get_db_connection(db_path) as con:
        con.execute('''
            CREATE TABLE IF NOT EXISTS feeds (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                etag TEXT,
                last_modified TEXT,
                last_fetched TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        con.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
                title TEXT,
                link TEXT,
                guid TEXT NOT NULL,
                pub_date TEXT,
                description TEXT,
                content TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(feed_id, guid)
            )
        ''')
        # Indexes
        con.execute('CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles(feed_id)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_articles_pub_date ON articles(pub_date)')
```

### Click CLI with Subcommands

```python
# Source: click documentation
import click
from feed import add_feed, list_feeds, remove_feed, refresh_feed
from articles import list_articles

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Personal Information System CLI."""
    pass

@cli.command()
@click.argument('url')
def feed_add(url):
    """Add a new RSS/Atom feed."""
    feed = add_feed(url)
    click.echo(f"Added: {feed.name} ({feed.url})")

@cli.command()
def feed_list():
    """List all subscribed feeds."""
    feeds = list_feeds()
    for feed in feeds:
        click.echo(f"{feed.id}\t{feed.name}\t{feed.url}\t{feed.article_count}")

@cli.command()
@click.argument('feed_id')
def feed_remove(feed_id):
    """Remove a feed."""
    remove_feed(feed_id)
    click.echo(f"Removed feed {feed_id}")

@cli.command()
@click.argument('feed_id', required=False)
def feed_refresh(feed_id):
    """Refresh one or all feeds."""
    if feed_id:
        result = refresh_feed(feed_id)
        click.echo(f"Refreshed: {result.new_articles} new articles")
    else:
        # Refresh all - already handled by fetch --all

@cli.command()
@click.option('--limit', default=20, help='Number of articles to show')
def article_list(limit):
    """List recent articles."""
    articles = list_articles(limit=limit)
    for article in articles:
        click.echo(f"{article.title} | {article.feed_name} | {article.pub_date}")

@cli.command()
@click.option('--all', 'refresh_all', is_flag=True, help='Refresh all feeds')
def fetch(refresh_all):
    """Fetch new articles from feeds."""
    if refresh_all:
        from feed import refresh_all_feeds
        summary = refresh_all_feeds()
        click.echo(f"Fetched {summary.new_count} new articles from {summary.success_count} feeds")
        if summary.error_count > 0:
            click.echo(f"Errors: {summary.error_count}", err=True)

cli()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| urllib.request | httpx | 2020s | Async support, HTTP/2, better timeouts |
| xml.etree | feedparser | 2000s | Handles all RSS versions, malformed feeds, namespaces |
| raw sqlite3 | sqlite3 + WAL pragma | 2010s | Better concurrent read/write without locking |
| argparse | click | 2015+ | Decorator syntax, automatic help, subcommands |

**Deprecated/outdated:**
- **requests library:** Still fine for sync-only, but httpx is the modern successor with async support
- **feedparser 5.x:** Legacy version; 6.x has Python 3.6+ support and better encoding handling

---

## Open Questions

1. **Should we implement feed discovery (auto-detect feed URL from website)?**
   - What we know: Phase 1 scope is adding feeds by direct URL
   - What's unclear: Whether to add website-to-feed discovery in Phase 1 or defer
   - Recommendation: Defer to Phase 2 (search and conditional fetching)

2. **Where should the SQLite database be stored?**
   - What we know: CONTEXT.md suggests `$HOME/.config/rss-reader/` or project directory
   - What's unclear: Cross-platform path handling (Windows uses AppData)
   - Recommendation: Use `platformdirs` library for proper cross-platform paths

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.13.5 | — |
| pip | Package install | Yes | 25.0.1 | — |
| sqlite3 | Database | Yes (built-in) | 3.46.1 | — |

**Missing dependencies with no fallback:**
- None identified - all required tools are available

**Missing dependencies with fallback:**
- None - the core dependencies are all available

---

## Sources

### Primary (HIGH confidence)
- [feedparser Documentation](https://feedparser.readthedocs.io/) - Bozo detection, encoding handling, date parsing
- [Click Documentation](https://click.palletsprojects.com/en/8.1.x/) - CLI framework, subcommands
- [Python sqlite3 Documentation](https://docs.python.org/3/library/sqlite3.html) - Connection handling, pragmas
- [httpx Documentation](https://www.python-httpx.org/) - HTTP client, timeout handling

### Secondary (MEDIUM confidence)
- [RSS 2.0 Specification](https://www.rssboard.org/rss-specification) - RSS standard, GUID requirements
- [PITFALLS.md](../PITFALLS.md) - Common mistakes documented from research

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified versions via pip, libraries are well-documented
- Architecture: HIGH - patterns from official docs and established Python practices
- Pitfalls: HIGH - based on RSS Board analysis and feedparser documentation

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days - stable domain)
