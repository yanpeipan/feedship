# Application Structure

## Directory Layout

```
src/
├── cli/               # CLI entry points
├── application/       # Business logic
├── providers/         # Plugin providers
├── storage/           # Storage (SQLite, Vector DB)
├── discovery/         # Auto-discovery system
├── utils/            # Utilities
├── models.py         # Dataclasses
├── feed.py           # (to be split)
└── __init__.py
```

## Source Files

| File | Responsibility |
|------|----------------|
| `cli/__init__.py` | cli() entry point |
| `cli/__main__.py` | CLI bootstrap |
| `cli/feed.py` | feed add/list/remove/refresh |
| `cli/article.py` | article list/view/open/tag |
| `cli/discover.py` | discover command |
| `cli/ui.py` | TUI interface |
| `application/feed.py` | add_feed, list_feeds, remove_feed, fetch |
| `application/articles.py` | Article CRUD |
| `application/search.py` | Search (FTS + semantic) |
| `application/fetch.py` | Fetch orchestration |
| `application/related.py` | Related articles |
| `application/config.py` | Config |
| `providers/__init__.py` | Provider registry |
| `providers/base.py` | ContentProvider protocol |
| `providers/rss_provider.py` | RSS/Atom (priority 50) |
| `providers/default_provider.py` | Default fallback |
| `providers/github_release_provider.py` | GitHub releases |
| `storage/sqlite/impl.py` | SQLite data access |
| `storage/vector.py` | ChromaDB semantic search |
| `discovery/` | Auto-discovery (models, fetcher, parser) |
| `models.py` | Dataclasses (Feed, Article, Tag) |

## Structural Rules

1. **DB via context manager** - `with get_db() as conn:` not bare `get_connection()`
2. **No circular imports** - shared logic in base.py
3. **CLI is thin** - business logic in application/
4. **feed_meta() ≠ crawl()** - metadata separate from content
5. **Single DAL** - storage/ owns all SQL
