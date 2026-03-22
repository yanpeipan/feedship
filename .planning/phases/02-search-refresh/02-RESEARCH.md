# Phase 2: search-refresh - Research

**Researched:** 2026-03-23
**Domain:** SQLite FTS5 full-text search, CLI search commands
**Confidence:** HIGH

## Summary

Phase 2 implements full-text search capability using SQLite FTS5 virtual tables and a CLI search command. The shadow table approach is used where articles_fts indexes title, description, and content fields, with manual synchronization after article inserts in refresh_feed(). Search results are returned ranked by FTS5 bm25 scoring. CLI follows existing click patterns with `article search` subcommand.

**Primary recommendation:** Create `articles_fts` FTS5 virtual table in init_db(), sync new articles after INSERT in refresh_feed(), add search_articles() in articles.py, and add `article search` subcommand in cli.py.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Shadow FTS5 virtual table approach
  - Separate `articles_fts` FTS5 table indexes title, description, content
  - Manual sync in `refresh_feed()` after INSERT loop
  - Avoids complex trigger management, keeps articles schema unchanged

- **D-02:** Index title, description, and content fields for FTS5
  - Ensures comprehensive search across all article text fields

- **D-03:** Expose FTS5 query syntax directly to users
  - Simple keyword matching (space-separated = AND)
  - Quoted phrases for exact match: `"machine learning"`
  - AND/OR operators for advanced users

- **D-04:** Multiple keywords default to AND behavior (all must match)
  - Intuitive default, reduces noise in results

- **D-05:** Same format as `article list` command (title | feed | date columns)
  - Consistency with established UX patterns

- **D-06:** Sort search results by FTS5 bm25 ranking (relevance)
  - Relevance-based results, not date-based

- **D-07:** `article search` subcommand with `--limit` and `--feed-id` filter options
  - Follows established `article` command group pattern
  - Options parallel to `article list`

- **D-08:** FETCH-05 (conditional fetching) already implemented in Phase 1
  - No additional implementation needed

### Claude's Discretion

- Exact highlighting/markup in search results (bold/colors)
- Empty query handling

### Deferred Ideas (OUT OF SCOPE)

None - analysis stayed within phase scope

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-04 | FTS5 virtual table for full-text search | FTS5 creation schema, sync strategy, query syntax documented |
| CLI-06 | `article search <query>` - Search articles via FTS5 | CLI patterns from Phase 1, FTS5 MATCH syntax |
| FETCH-05 | Conditional fetching (ETag/Last-Modified) | Already implemented in Phase 1 - no research needed |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **sqlite3** | 3.45.3 (built-in) | Database + FTS5 | FTS5 is built into SQLite, no extra dependency |
| **click** | 8.3.1 | CLI framework | Already used in Phase 1 |

### No New Dependencies

FTS5 is built into Python's sqlite3 module (SQLite 3.9.0+ required, 3.45.3 installed).

---

## Architecture Patterns

### Recommended Project Structure

```
src/
├── __init__.py
├── cli.py              # Add article search subcommand
├── db.py               # Add FTS5 table creation in init_db()
├── feeds.py            # Add FTS5 sync after INSERT in refresh_feed()
├── articles.py         # Add search_articles() function
└── models.py
```

### Pattern 1: Shadow FTS5 Virtual Table

Create separate FTS5 table that indexes article text fields.

```sql
-- Source: SQLite FTS5 documentation (https://www.sqlite.org/fts5.html)
CREATE VIRTUAL TABLE articles_fts USING fts5(
    title,
    description,
    content,
    tokenize='porter ascii'
);
```

**Why shadow approach:**
- No triggers required (manual sync in refresh_feed())
- articles table schema unchanged
- Simpler than content=external content table approach
- Tradeoff: must manually sync on inserts/deletes

### Pattern 2: Manual FTS5 Sync After INSERT

After inserting new articles in refresh_feed(), sync to FTS5 table.

```python
# Source: Based on Phase 1 patterns + FTS5 documentation
def refresh_feed(feed_id: str) -> dict:
    # ... existing article INSERT loop ...

    # Sync new articles to FTS5
    for article_id, title, description, content_val in new_articles_data:
        cursor.execute(
            """
            INSERT OR REPLACE INTO articles_fts(rowid, title, description, content)
            SELECT id, title, description, content FROM articles WHERE id = ?
            """,
            (article_id,),
        )

    conn.commit()
```

### Pattern 3: FTS5 Search with bm25 Ranking

Query FTS5 table and sort by relevance.

```python
# Source: SQLite FTS5 documentation
def search_articles(query: str, limit: int = 20, feed_id: Optional[str] = None) -> list[ArticleListItem]:
    """Search articles using FTS5 full-text search.

    Args:
        query: FTS5 query string (space-separated = AND, use quotes for phrases)
        limit: Maximum number of results
        feed_id: Optional feed ID to filter by specific feed

    Returns:
        List of ArticleListItem objects ordered by bm25 relevance
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # FTS5 MATCH with bm25 ranking
        if feed_id:
            cursor.execute(
                """
                SELECT a.id, a.feed_id, f.name as feed_name, a.title, a.link,
                       a.guid, a.pub_date, a.description,
                       bm25(articles_fts) as rank
                FROM articles_fts
                JOIN articles a ON articles_fts.rowid = a.id
                JOIN feeds f ON a.feed_id = f.id
                WHERE articles_fts MATCH ?
                  AND a.feed_id = ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, feed_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT a.id, a.feed_id, f.name as feed_name, a.title, a.link,
                       a.guid, a.pub_date, a.description,
                       bm25(articles_fts) as rank
                FROM articles_fts
                JOIN articles a ON articles_fts.rowid = a.id
                JOIN feeds f ON a.feed_id = f.id
                WHERE articles_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            )

        rows = cursor.fetchall()
        return [ArticleListItem(...) for row in rows]
    finally:
        conn.close()
```

### Pattern 4: Click Search Subcommand

Add search subcommand following existing article command pattern.

```python
# Source: Phase 1 cli.py patterns
@cli.command("search")
@click.argument("query")
@click.option("--limit", default=20, help="Maximum number of results")
@click.option("--feed-id", default=None, help="Filter by feed ID")
@click.pass_context
def article_search(ctx: click.Context, query: str, limit: int, feed_id: Optional[str]) -> None:
    """Search articles by keyword using full-text search."""
    verbose = ctx.parent and ctx.parent.obj.get("verbose") if ctx.parent else False
    try:
        articles = search_articles(query=query, limit=limit, feed_id=feed_id)
        if not articles:
            click.echo("No articles found matching your search.")
            return

        click.echo("Title | Feed | Date")
        click.echo("-" * 80)

        for article in articles:
            title = article.title or "No title"
            feed_name = article.feed_name or "Unknown"
            pub_date = article.pub_date or "No date"
            click.echo(f"{title[:50]} | {feed_name[:20]} | {pub_date[:10]}")
    except Exception as e:
        click.echo(f"Error: Failed to search articles: {e}", err=True, fg="red")
        logger.exception("Failed to search articles")
        sys.exit(1)
```

### Anti-Patterns to Avoid

- **Don't use FTS5 content=external without triggers:** Shadow table approach avoids complex trigger management
- **Don't sync entire table on every refresh:** Only sync new articles (track which were inserted)
- **Don't forget to handle empty/None text fields:** FTS5 handles NULL gracefully but empty strings need care

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Full-text search | Custom inverted index | SQLite FTS5 | Built into SQLite, optimized, bm25 ranking |
| Query parsing | Custom query language | FTS5 query syntax | Supports AND/OR/NOT, phrases, prefixes |
| Relevance ranking | naive match count | bm25() | Standard IR ranking, considers term frequency and document length |

**Key insight:** FTS5 is the standard SQLite full-text search solution. It is battle-tested, supports bm25 ranking, and requires no external dependencies.

---

## Common Pitfalls

### Pitfall 1: FTS5 Sync After Delete

**What goes wrong:** FTS5 index contains deleted articles.

**Why it happens:** Shadow table is not automatically updated when articles are deleted.

**How to avoid:** When removing a feed (ON DELETE CASCADE), the article rowids change. Consider rebuilding FTS5 periodically or using content=external with proper triggers.

**Warning signs:** Search returns articles that no longer exist in articles table.

### Pitfall 2: Tokenizer Issues with Non-ASCII

**What goes wrong:** Chinese/Japanese/Arabic text not searchable.

**Why it happens:** Default tokenizer does not handle CJK well.

**How to avoid:** Use `tokenize='unicode61'` or dedicated tokenizer for CJK. However, porter ascii is fine for English-heavy content.

```sql
CREATE VIRTUAL TABLE articles_fts USING fts5(
    title,
    description,
    content,
    tokenize='unicode61'
);
```

### Pitfall 3: Query Injection in FTS5

**What goes wrong:** Malicious FTS5 query crashes or extracts data.

**Why it happens:** FTS5 query syntax includes special characters that could be exploited.

**How to avoid:** Pass query as parameterized argument (already safe with sqlite3), but validate empty queries.

---

## Code Examples

### FTS5 Table Creation with Porter Stemmer

```python
# Source: SQLite FTS5 documentation
def init_db() -> None:
    """Initialize database schema including FTS5."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # ... existing feeds/articles tables ...

        # FTS5 virtual table for full-text search
        # Uses porter tokenizer for English stemming
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title,
                description,
                content,
                tokenize='porter ascii'
            )
        """)

        # Index for common query patterns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles(feed_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_articles_pub_date ON articles(pub_date)")

        conn.commit()
    finally:
        conn.close()
```

### FTS5 Sync After Article Insert

```python
# Source: Pattern from Phase 1 refresh_feed() + FTS5 docs
def refresh_feed(feed_id: str) -> dict:
    # ... existing fetch and parse logic ...

    new_article_ids = []  # Track new articles for FTS5 sync

    for entry in entries:
        # ... existing INSERT logic ...
        cursor.execute(
            """
            INSERT OR IGNORE INTO articles (id, feed_id, title, link, guid, pub_date, description, content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (article_id, feed_id, title, link, guid, pub_date, description, content_val, now),
        )
        if cursor.rowcount > 0:
            new_articles += 1
            new_article_ids.append(article_id)

    # Sync new articles to FTS5
    for article_id in new_article_ids:
        cursor.execute(
            """
            INSERT INTO articles_fts(rowid, title, description, content)
            SELECT id, title, description, content FROM articles WHERE id = ?
            """,
            (article_id,),
        )

    conn.commit()
```

### Search with Optional Feed Filter

```python
# Source: articles.py list_articles() pattern adapted for FTS5
def search_articles(
    query: str,
    limit: int = 20,
    feed_id: Optional[str] = None
) -> list[ArticleListItem]:
    """Search articles using FTS5 full-text search.

    Args:
        query: FTS5 query (space-separated = AND, use "quotes" for phrases)
        limit: Maximum results to return
        feed_id: Optional feed ID to filter results

    Returns:
        List of ArticleListItem sorted by bm25 relevance
    """
    if not query or not query.strip():
        return []

    conn = get_connection()
    try:
        cursor = conn.cursor()

        if feed_id:
            cursor.execute(
                """
                SELECT a.id, a.feed_id, f.name as feed_name, a.title, a.link,
                       a.guid, a.pub_date, a.description
                FROM articles_fts
                JOIN articles a ON articles_fts.rowid = a.id
                JOIN feeds f ON a.feed_id = f.id
                WHERE articles_fts MATCH ?
                  AND a.feed_id = ?
                ORDER BY bm25(articles_fts)
                LIMIT ?
                """,
                (query, feed_id, limit),
            )
        else:
            cursor.execute(
                """
                SELECT a.id, a.feed_id, f.name as feed_name, a.title, a.link,
                       a.guid, a.pub_date, a.description
                FROM articles_fts
                JOIN articles a ON articles_fts.rowid = a.id
                JOIN feeds f ON a.feed_id = f.id
                WHERE articles_fts MATCH ?
                ORDER BY bm25(articles_fts)
                LIMIT ?
                """,
                (query, limit),
            )

        rows = cursor.fetchall()
        articles = []
        for row in rows:
            articles.append(
                ArticleListItem(
                    id=row["id"],
                    feed_id=row["feed_id"],
                    feed_name=row["feed_name"],
                    title=row["title"],
                    link=row["link"],
                    guid=row["guid"],
                    pub_date=row["pub_date"],
                    description=row["description"],
                )
            )
        return articles
    finally:
        conn.close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LIKE %query% | FTS5 MATCH | 2014+ (SQLite 3.9) | 10-100x faster, relevance ranking |
| External search index | Built-in FTS5 | SQLite 3.9+ | No external dependencies |

**Deprecated/outdated:**
- **FTS3/FTS4:** FTS5 is the current standard, better performance and features

---

## Open Questions

None identified for this phase based on CONTEXT.md locked decisions.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.13.5 | — |
| sqlite3 (FTS5) | Database search | Yes | 3.45.3 | — |
| click | CLI | Yes | 8.3.1 | — |

**Missing dependencies with no fallback:**
- None identified - all required tools are available

**Missing dependencies with fallback:**
- None - the core dependencies are all available

---

## Sources

### Primary (HIGH confidence)
- [SQLite FTS5 Documentation](https://www.sqlite.org/fts5.html) - FTS5 virtual table creation, query syntax, bm25 ranking, highlight/snippet functions
- [Phase 1 01-RESEARCH.md](../01-foundation/01-RESEARCH.md) - Existing patterns, CLI structure, database schema
- [Phase 2 02-CONTEXT.md](./02-CONTEXT.md) - Locked decisions on shadow table approach

### Secondary (MEDIUM confidence)
- Phase 1 source code (src/db.py, src/articles.py, src/cli.py, src/feeds.py) - Existing patterns verified

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - sqlite3 FTS5 is built-in, verified working
- Architecture: HIGH - shadow table approach is standard pattern
- Pitfalls: HIGH - based on SQLite documentation and common FTS5 issues

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days - stable domain)
