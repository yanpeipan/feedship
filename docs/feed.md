# Feed Provider Architecture

## Overview

Feed fetch is powered by a **plugin-based provider system**. Each URL type (RSS, GitHub, etc.) has its own provider that handles fetching, parsing, and tagging. All content (RSS articles, GitHub releases) is stored in the unified `articles` table. Tagging uses the `article_tags` table for all content types.

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
