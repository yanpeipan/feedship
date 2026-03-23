# Phase 09: Enhanced Article List - Research

**Researched:** 2026-03-23
**Domain:** Python CLI terminal table formatting, SQLite N+1 query optimization
**Confidence:** HIGH

## Summary

Phase 9 requires enhancing the `article list` command to display article IDs and tags as separate columns. The current implementation has an N+1 query problem where `get_article_tags()` is called per article. The solution involves using the `rich` library for table formatting and fixing the N+1 issue by batching tag queries.

**Primary recommendation:** Use `rich.Table` for formatted output and batch-fetch tags in a single query with `GROUP BY` aggregation.

## User Constraints (from CONTEXT.md)

This phase has no CONTEXT.md - the decisions come from ROADMAP.md and STATE.md.

### Locked Decisions

- Using `rich` library for terminal table formatting (from STATE.md v1.2 decisions)
- Truncated ID (8 chars) for display, full ID (32 chars) for commands (from STATE.md Technical Notes)
- N+1 fix via JOIN or batch query in `list_articles_with_tags()` (from STATE.md Technical Notes)

### Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ARTICLE-01 | Article list ID column | Add column to table output, truncate to 8 chars |
| ARTICLE-02 | Tags in separate column | Add dedicated Tags column to table |
| ARTICLE-03 | Fix N+1 query performance | Batch query with GROUP BY aggregation |
| ARTICLE-04 | `--verbose` shows full IDs | Pass verbose flag to control ID truncation |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **rich** | 13.x | Terminal table formatting | Decision from STATE.md v1.2. Rich is the de-facto standard for rich output in Python CLI. Used in Phase 10 (detail view) and Phase 11 as well. |

**Installation:**
```bash
pip install rich
```

### No New Dependencies Required

The existing codebase already has all required components:
- `click` 8.1.x for CLI framework
- `sqlite3` built-in for database access

## Architecture Patterns

### Recommended Project Structure

No structural changes needed - modifying existing files:

```
src/
├── cli.py              # Modify article_list command
├── articles.py         # Add batch tag fetching
└── db.py               # No changes needed
```

### Pattern 1: Rich Table for Article List

**What:** Replace plain text output with `rich.table.Table`

**When to use:** For `article list` command output

**Example:**
```python
# Source: .planning/research/STACK.md
from rich.console import Console
from rich.table import Table

console = Console()

table = Table(show_header=True, header_style="bold magenta")
table.add_column("ID", style="dim", width=8)
table.add_column("Tags", max_width=15)
table.add_column("Title")
table.add_column("Source", max_width=20)
table.add_column("Date", max_width=10)

for article in articles:
    tags = ",".join(article.tags) or "-"  # Pre-fetched tags
    table.add_row(
        article.id[:8],
        tags,
        article.title or "No title",
        article.feed_name[:20],
        (article.pub_date or "")[:10]
    )

console.print(table)
```

### Pattern 2: Batch Tag Fetching to Fix N+1

**What:** Fetch all tags for articles in a single query using `GROUP BY` and aggregate function

**When to use:** Before rendering article list to avoid N+1 queries

**SQL Pattern:**
```sql
-- Fetch article IDs and their tags in one query
SELECT at.article_id, GROUP_CONCAT(t.name) as tags
FROM article_tags at
JOIN tags t ON at.tag_id = t.id
WHERE at.article_id IN (?, ?, ?, ...)
GROUP BY at.article_id
```

**Why this fixes N+1:** Instead of N queries for N articles, we make 1 query for all tags.

### Pattern 3: Verbose Flag for Full IDs

**What:** Conditionally truncate IDs based on verbosity level

**When to use:** In article list output

**Example:**
```python
id_display = article.id if verbose else article.id[:8]
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal table formatting | Custom ASCII art tables | `rich.table.Table` | Handles column sizing, overflow, colors, borders automatically |
| Batch tag fetching | N individual queries | SQL GROUP_CONCAT or JOIN | SQLite handles aggregation efficiently |

**Key insight:** Rich table handles terminal width, overflow, and styling that would be error-prone to implement manually.

## Common Pitfalls

### Pitfall 1: N+1 Query Persists After Refactor

**What goes wrong:** Adding `rich` table output without fixing tag fetching doesn't solve the performance issue.

**Why it happens:** The N+1 is in `get_article_tags()` called per article in the loop at cli.py line 210.

**How to avoid:** Batch-fetch tags before the rendering loop and attach to article objects.

**Warning signs:** `article list --limit 50` takes >2 seconds.

### Pitfall 2: Verbose Flag Not Passed Through

**What goes wrong:** `article list --verbose` doesn't show full IDs because verbosity isn't propagated to tag fetching.

**Why it happens:** The `verbose` flag is captured in CLI context but not passed to `list_articles_with_tags()`.

**How to avoid:** Add `verbose: bool` parameter to `list_articles_with_tags()` and use it in display logic.

### Pitfall 3: Tags Column Overflow

**What goes wrong:** Long tag lists break table formatting.

**Why it happens:** Rich table `max_width` truncates but may not wrap gracefully.

**How to avoid:** Use `overflow="ellipsis"` for Tags column or limit tags display to first 3 with "+N more".

## Code Examples

### Fix N+1: Batch Query in articles.py

```python
def get_articles_with_tags(article_ids: list[str]) -> dict[str, list[str]]:
    """Batch fetch tags for multiple articles.

    Args:
        article_ids: List of article IDs to fetch tags for.

    Returns:
        Dict mapping article_id -> list of tag names.
    """
    if not article_ids:
        return {}

    conn = get_connection()
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" * len(article_ids))
        cursor.execute(f"""
            SELECT at.article_id, t.name
            FROM article_tags at
            JOIN tags t ON at.tag_id = t.id
            WHERE at.article_id IN ({placeholders})
            ORDER BY at.article_id, t.name
        """, article_ids)

        result: dict[str, list[str]] = {aid: [] for aid in article_ids}
        for row in cursor.fetchall():
            result[row["article_id"]].append(row["name"])
        return result
    finally:
        conn.close()
```

### Updated ArticleListItem with Tags

```python
@dataclass
class ArticleListItem:
    # ... existing fields ...
    tags: list[str] = field(default_factory=list)  # Add this
```

### CLI with Verbose and Tags

```python
@article.command("list")
@click.option("--limit", default=20)
@click.option("--verbose", is_flag=True, help="Show full article IDs")
# ... other options ...
def article_list(ctx, limit, verbose, ...):
    articles = list_articles_with_tags(limit=limit, ...)

    # Pre-fetch tags for all articles (fixes N+1)
    article_ids = [a.id for a in articles]
    tags_map = get_articles_with_tags(article_ids)

    # Attach tags to articles
    for article in articles:
        article.tags = tags_map.get(article.id, [])

    # Rich table output
    table = Table(show_header=True)
    table.add_column("ID", style="dim", width=8 if not verbose else 36)
    table.add_column("Tags", max_width=12)
    table.add_column("Title")
    # ...

    for article in articles:
        id_display = article.id if verbose else article.id[:8]
        tags_str = ",".join(article.tags) if article.tags else "-"
        # ... add row ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Plain text `click.secho` output | `rich.table.Table` | Phase 9 | Structured columns, proper overflow handling |
| Per-article `get_article_tags()` | Batch `GROUP BY` query | Phase 9 | O(1) vs O(N) queries |

## Open Questions

None identified - all requirements have clear implementation paths.

## Environment Availability

Step 2.6: SKIPPED (no external dependencies - code/config-only changes)

The `rich` library is not yet in `pyproject.toml` dependencies. It must be added:
```bash
pip install rich
```

And `pyproject.toml` must be updated:
```toml
dependencies = [
    ...
    "rich>=13.0.0",
]
```

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pytest.ini or pyproject.toml |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File |
|--------|----------|-----------|-------------------|------|
| ARTICLE-01 | ID column shows truncated ID | Unit | `pytest tests/test_cli.py -k test_article_list -x` | tests/test_cli.py |
| ARTICLE-02 | Tags in separate column | Unit | Same as above | tests/test_cli.py |
| ARTICLE-03 | N+1 fix via batch query | Performance | Manual timing with `time python -m src.cli article list --limit 50` | N/A |
| ARTICLE-04 | --verbose shows full ID | Unit | `pytest tests/test_cli.py -k test_article_list_verbose -x` | tests/test_cli.py |

### Wave 0 Gaps

- [ ] `tests/test_cli.py::test_article_list` - verify ID and tags columns
- [ ] `tests/test_cli.py::test_article_list_verbose` - verify full IDs
- [ ] `tests/test_articles.py::test_get_articles_with_tags` - verify batch query
- Framework install: Already present (pytest in optional-dependencies)

## Sources

### Primary (HIGH confidence)

- Rich library table documentation - established Python library, well-documented
- Existing codebase patterns in src/cli.py, src/articles.py

### Secondary (MEDIUM confidence)

- `.planning/research/STACK.md` - project research with code examples
- `.planning/STATE.md` - locked decisions for v1.2

### Tertiary (LOW confidence)

- N/A

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - `rich` library is the clear choice per STATE.md
- Architecture: HIGH - batch query fix is straightforward SQL pattern
- Pitfalls: MEDIUM - N+1 fix pattern is well-known but must be carefully implemented

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days for stable topic)
