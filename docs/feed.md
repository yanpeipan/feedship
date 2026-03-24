# Feed Provider Architecture

## Overview

Feed fetch is powered by a **plugin-based provider system**. Each URL type (RSS, GitHub, etc.) has its own provider that handles fetching, parsing, and tagging. All content (RSS articles, GitHub releases) is stored in the unified `articles` table. Tagging uses the `article_tags` table for all content types.

## Target Application Structure

```
src/
├── cli/
│   ├── __init__.py              # cli() 主入口
│   ├── feed.py                  # feed add/list/remove/refresh
│   ├── article.py               # article list/view/open/tag
│   └── tag.py                  # tag add/list/remove + rule commands
├── application/
│   ├── feed.py                 # add_feed, list_feeds, remove_feed, fetch_one, fetch_all
│   └── article.py              # search, get_article, tagging orchestration
├── providers/
│   ├── __init__.py             # Provider registry (discover, discover_or_default)
│   ├── base.py                 # ContentProvider, TagParser protocols
│   ├── rss_provider.py         # RSS/Atom feeds (priority 50)
│   └── github_release_provider.py # GitHub releases (priority 200)
├── db.py                       # DB connection, schema init, ALL data access
├── models.py                   # Dataclasses (Feed, Article, Tag)
├── tags/
│   ├── __init__.py             # TagParser registry
│   ├── default_tag_parser.py   # Keyword/regex tag parser
│   └── release_tag_parser.py    # GitHub release tag parser
└── utils/
    ├── github.py               # GitHub API client
    └── id.py                   # ID generation utilities
```

### Structural Rules (Anti-屎山)

1. **DB via context manager** - `with get_db() as conn:` 代替裸 `get_connection()` + 手动 close
2. **No circular imports** - providers don't import each other, shared logic in base.py
3. **CLI is a thin shell** - all business logic in application/
4. **feed_meta() doesn't crawl()** - metadata fetch is separate from content fetch
5. **Single data access layer** - `db.py` owns all SQL, application modules call db functions

## Fetch Flow

```
fetch --all
  └─ fetch_all()
       │
       ├─ feeds = list_feeds()
       │
       └─ for each feed:
            │
            └─ fetch_one(feed)
                 │
                 ├─ discover_or_default(feed.url) → provider (highest priority match)
                 │    └─ if no match: default RSS provider
                 │
                 ├─ raw_items = provider.crawl(feed.url)
                 │
                 ├─ articles = provider.parse(raw) for raw in raw_items
                 │
                 ├─ for article in articles:
                 │    ├─ INSERT OR IGNORE into articles (dedup by guid)
                 │    └─ if new: INSERT into articles_fts (FTS5 sync)
                 │
                 └─ apply tag_rules to new articles (post-commit, avoids DB lock)
```

```
feed refresh <feed_id>
  └─ fetch_one(feed_id)
       └─ (same as above, single feed)
```

**FTS5 sync:** New articles are synced to `articles_fts` shadow table immediately after INSERT. Tag rules run after commit to avoid "database is locked" from nested connections.

**No feed_rules stage:** Unlike the old flow, tagging is not provider-driven. All new articles after INSERT get `apply_rules_to_article()` called post-commit.

## Provider Interface

```python
class ContentProvider(Protocol):
    def match(self, url: str) -> bool:
        """Return True if this provider handles the URL."""

    def priority(self) -> int:
        """Higher = tried first. Default RSS returns 50."""

    def crawl(self, url: str) -> List[Raw]:
        """Fetch raw content from URL. Return list of raw items (may be empty)."""

    def parse(self, raw: Raw) -> Article:
        """Convert raw item to Article dict."""

    def feed_meta(self, url: str) -> FeedMeta:
        """Fetch feed metadata (title, etag) WITHOUT crawling full content. Raises if unavailable."""

    def tag_parsers(self) -> List[TagParser]:
        """Return tag parsers for articles from this provider."""
```

**Key improvement:** `feed_meta()` must NOT call `crawl()` - it should only fetch headers or a lightweight HEAD request to get metadata.

**Article dict shape:**
```python
{
    "title": str,
    "link": str,
    "guid": str,
    "pub_date": str | None,   # ISO 8601
    "description": str | None,
    "content": str | None,
}
```

## TagParser Interface

```python
class TagParser(Protocol):
    def parse_tags(self, article: Article) -> List[str]:
        """Return tags for this article."""
```

Tag merging: union of all tags from all tag parsers, deduplicated.
`['a', 'b'] + ['a', 'c'] = ['a', 'b', 'c']`

## Provider Registration

Providers register themselves by appending to `PROVIDERS` list in `src/providers/__init__.py`. Each provider class is instantiated once at module load time.

**Rule: Providers must not import each other** (avoid circular deps). Shared logic goes in `src/providers/base.py`.

## Database Schema

### feeds table

```sql
feeds (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  url TEXT NOT NULL UNIQUE,
  etag TEXT,
  last_modified TEXT,
  last_fetched TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### articles table

```sql
articles (
  id TEXT NOT NULL,
  feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
  title TEXT,
  link TEXT,
  guid TEXT NOT NULL,
  pub_date TEXT,
  description TEXT,
  content TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(feed_id, id)
)
```

### articles_fts (FTS5 virtual table)

Full-text search shadow table for articles. Sync handled by db.py's store functions.

### tags table

```sql
tags (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### article_tags table

```sql
article_tags (
  article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  tag_id TEXT NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (article_id, tag_id)
)
```

## CLI Structure

| Command | Module | Behavior |
|---------|--------|----------|
| `feed add <url>` | cli/feed.py | Detects provider type, adds feed |
| `feed list` | cli/feed.py | List all subscribed feeds |
| `feed remove <id>` | cli/feed.py | Remove feed by ID |
| `feed refresh <id>` | cli/feed.py | Fetch new articles for one feed |
| `fetch --all` | cli/feed.py | Fetch all feeds |
| `crawl <url>` | cli/crawl.py | Crawl arbitrary URL |
| `article list` | cli/article.py | List articles with tags |
| `article view <id>` | cli/article.py | View full article |
| `article open <id>` | cli/article.py | Open in browser |
| `article tag <id> <tag>` | cli/article.py | Manual tagging |
| `article tag --auto` | cli/article.py | AI clustering |
| `article tag --rules` | cli/article.py | Apply keyword/regex rules |
| `tag add <name>` | cli/tag.py | Create tag |
| `tag list` | cli/tag.py | List tags with counts |
| `tag remove <name>` | cli/tag.py | Remove tag |
| `tag rule add <tag>` | cli/tag.py | Add tag rule |
| `tag rule list` | cli/tag.py | List rules |
| `tag rule edit <tag>` | cli/tag.py | Edit rule |
| `tag rule remove <tag>` | cli/tag.py | Remove rule |

## Refactoring Status

### Phase 1 ✅ DONE
- Provider plugin system
- RSS provider with conditional fetching
- FTS5 search
- Basic tagging with rules

### Phase 2 🔄 NEXT
- [ ] `cli.py` (798 lines) → split into `cli/` package with command groups
- [ ] `provider.feed_meta()` → 轻量级 HEAD 请求，不调用 `crawl()`
- [ ] DB context manager → `with get_db() as conn:` 代替裸 `get_connection()`

### Phase 3 📋 LATER
- GitHub releases unified into articles table
- AI tagging as proper TagParser plugin
- Async provider support

## Default RSS Provider

- `match(url)` returns `False` (only matched as fallback)
- When no provider matches: `discover_or_default` returns `[default_rss_provider]`
- `priority()` returns `50` (lowest; providers with higher priority are tried first)
- `feed_meta()` does lightweight HEAD request only, NOT full crawl()
