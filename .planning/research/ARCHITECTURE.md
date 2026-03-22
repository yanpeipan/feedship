# Architecture Research: Personal Information System

**Domain:** Feed aggregator with web crawling and SQLite storage
**Researched:** 2026-03-22
**Confidence:** MEDIUM (limited external verification due to search tool issues)

## Executive Summary

A personal information system that subscribes to RSS feeds, crawls websites, and stores data in SQLite requires a modular architecture with clear component boundaries. The system needs a fetcher layer for HTTP operations, a parser layer for feed normalization, a storage layer for SQLite persistence, and a CLI layer for user interaction.

The recommended architecture follows a pipeline pattern: sources (feeds/URLs) -> fetcher -> parser -> storage -> CLI/API. Each component has a single responsibility and communicates through well-defined interfaces.

## Component Architecture

### High-Level Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                           │
│  (add, remove, list, fetch, crawl, search, export, stats)  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│  (FeedService, CrawlService, ArticleService, SearchService) │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌────────────────┐
│    Fetcher       │ │   Parser     │ │    Storage     │
│  (HTTP Client)   │ │ (Feed+HTML)  │ │   (SQLite)     │
└──────────────────┘ └──────────────┘ └────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Public API |
|-----------|---------------|------------|
| **Fetcher** | HTTP requests, rate limiting, robots.txt compliance | `fetch(url): Promise<Response>` |
| **FeedParser** | Normalize RSS/Atom/RDF to unified format | `parse(xml): Promise<NormalizedFeed>` |
| **HtmlParser** | Extract content from HTML pages | `parse(html, url): Promise<ExtractedContent>` |
| **Storage** | SQLite operations, migrations, queries | `save(type, data)`, `query(sql, params)` |
| **FeedService** | Manage feed lifecycle, scheduling | `addFeed()`, `refreshFeed()`, `removeFeed()` |
| **CrawlService** | Website crawling, link extraction | `crawl(url, depth)`, `discoverLinks()` |
| **ArticleService** | Article CRUD, deduplication | `saveArticle()`, `getArticles()`, `markRead()` |
| **SearchService** | FTS5 full-text search | `search(query)`, `indexArticle()` |
| **CLI** | User interaction, argument parsing | Commands and flags |

### Data Flow

```
RSS URL or Crawl Target
         │
         ▼
┌─────────────────┐
│     Fetcher     │ ──► Rate limiter, robots.txt
└─────────────────┘
         │
         ▼
┌─────────────────┐
│     Parser      │ ──► Feed (RSS/Atom) OR HtmlParser
└─────────────────┘
         │
         ▼
┌─────────────────┐
│    Storage     │ ──► SQLite with FTS5
└─────────────────┘
         │
         ▼
┌─────────────────┐
│   CLI/Output   │
└─────────────────┘
```

## Recommended Architecture Patterns

### 1. Repository Pattern for Storage

Abstracts SQLite behind a repository interface, enabling future database changes.

```typescript
interface ArticleRepository {
  save(article: Article): Promise<string>;
  findById(id: string): Promise<Article | null>;
  findByFeedId(feedId: string, limit?: number): Promise<Article[]>;
  search(query: string): Promise<Article[]>;
  markAsRead(id: string): Promise<void>;
}

class SQLiteArticleRepository implements ArticleRepository {
  constructor(private db: Database) {}
  // SQLite-specific implementation
}
```

### 2. Service Layer Pattern

Business logic encapsulated in services, keeping components loosely coupled.

```typescript
class FeedService {
  constructor(
    private fetcher: Fetcher,
    private feedParser: FeedParser,
    private articleRepo: ArticleRepository,
    private feedRepo: FeedRepository
  ) {}

  async refreshFeed(feedId: string): Promise<RefreshResult> {
    const feed = await this.feedRepo.findById(feedId);
    const response = await this.fetcher.fetch(feed.url);
    const parsed = await this.feedParser.parse(response.body);
    // ... business logic
  }
}
```

### 3. Event-Driven Updates

Components emit events that other components can subscribe to.

```typescript
// Emitter
class FeedService {
  private emitter = new EventEmitter();

  onArticleSaved(handler: (article: Article) => void) {
    this.emitter.on('article:saved', handler);
  }

  private async saveArticle(article: Article) {
    await this.articleRepo.save(article);
    this.emitter.emit('article:saved', article);
  }
}
```

### 4. Scheduler with node-cron

```typescript
import cron from 'node-cron';

class Scheduler {
  private tasks: Map<string, cron.ScheduledTask> = new Map();

  scheduleFeedRefresh(feedId: string, expression: string, handler: () => Promise<void>) {
    const task = cron.schedule(expression, handler, {
      scheduled: true,
      timezone: 'UTC'
    });
    this.tasks.set(feedId, task);
  }

  cancelFeedRefresh(feedId: string) {
    this.tasks.get(feedId)?.stop();
    this.tasks.delete(feedId);
  }
}
```

## Database Schema Design

### Core Tables

```sql
-- Feeds table: stores RSS/Atom feed subscriptions
CREATE TABLE feeds (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL UNIQUE,
  title TEXT,
  description TEXT,
  site_url TEXT,
  feed_url TEXT,
  etag TEXT,
  last_modified TEXT,
  last_fetched_at TEXT,
  fetch_interval TEXT DEFAULT '1 hour',
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Articles table: stores parsed articles/items from feeds
CREATE TABLE articles (
  id TEXT PRIMARY KEY,
  feed_id TEXT NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
  guid TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT,
  description TEXT,
  content TEXT,
  author TEXT,
  published_at TEXT,
  is_read INTEGER DEFAULT 0,
  is_bookmarked INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(feed_id, guid)
);

-- Authors table: normalize author information
CREATE TABLE authors (
  id TEXT PRIMARY KEY,
  name TEXT,
  email TEXT,
  url TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Article-Author junction table
CREATE TABLE article_authors (
  article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  author_id TEXT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
  PRIMARY KEY (article_id, author_id)
);

-- Categories/tags for articles
CREATE TABLE categories (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

-- Article-Category junction table
CREATE TABLE article_categories (
  article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  category_id TEXT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  PRIMARY KEY (article_id, category_id)
);

-- Crawl history for website crawling
CREATE TABLE crawl_history (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  status TEXT NOT NULL,
  status_code INTEGER,
  error_message TEXT,
  pages_visited INTEGER DEFAULT 0,
  links_found INTEGER DEFAULT 0,
  started_at TEXT NOT NULL,
  completed_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Discovered URLs from crawling
CREATE TABLE discovered_urls (
  id TEXT PRIMARY KEY,
  crawl_id TEXT NOT NULL REFERENCES crawl_history(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  source_url TEXT,
  is_processed INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_articles_feed_id ON articles(feed_id);
CREATE INDEX idx_articles_published_at ON articles(published_at);
CREATE INDEX idx_articles_is_read ON articles(is_read);
CREATE INDEX idx_discovered_urls_crawl_id ON discovered_urls(crawl_id);
CREATE INDEX idx_discovered_urls_is_processed ON discovered_urls(is_processed);
```

### Full-Text Search (FTS5)

```sql
-- FTS5 virtual table for article search
CREATE VIRTUAL TABLE articles_fts USING fts5(
  title,
  description,
  content,
  author,
  content='articles',
  content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER articles_fts_insert AFTER INSERT ON articles BEGIN
  INSERT INTO articles_fts(rowid, title, description, content, author)
  VALUES (NEW.rowid, NEW.title, NEW.description, NEW.content, NEW.author);
END;

CREATE TRIGGER articles_fts_delete AFTER DELETE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, title, description, content, author)
  VALUES('delete', OLD.rowid, OLD.title, OLD.description, OLD.content, OLD.author);
END;

CREATE TRIGGER articles_fts_update AFTER UPDATE ON articles BEGIN
  INSERT INTO articles_fts(articles_fts, rowid, title, description, content, author)
  VALUES('delete', OLD.rowid, OLD.title, OLD.description, OLD.content, OLD.author);
  INSERT INTO articles_fts(rowid, title, description, content, author)
  VALUES (NEW.rowid, NEW.title, NEW.description, NEW.content, NEW.author);
END;
```

### SQLite Configuration Recommendations

```sql
-- Enable WAL mode for better concurrency
PRAGMA journal_mode = WAL;

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Synchronous mode (NORMAL is good balance of safety and speed)
PRAGMA synchronous = NORMAL;

-- Cache size (negative = KB, here ~64MB)
PRAGMA cache_size = -64000;

-- Memory-mapped I/O (256MB)
PRAGMA mmap_size = 268435456;

-- Temp store in memory
PRAGMA temp_store = MEMORY;
```

## CLI Command Design

### Command Structure

```
info-system <command> [options]

Commands:
  feed add <url>           Add a new RSS/Atom feed
  feed list                List all subscribed feeds
  feed remove <id>         Remove a feed
  feed refresh [id]        Refresh one or all feeds
  feed status <id>         Show feed details and status

  crawl <url> [options]    Crawl a website
    --depth <n>            Crawl depth (default: 2)
    --concurrency <n>      Parallel requests (default: 3)

  article list             List recent articles
    --feed <id>            Filter by feed
    --unread               Show only unread
    --limit <n>            Limit results (default: 20)
  article read <id>        Mark article as read
  article bookmark <id>     Bookmark an article
  article search <query>   Search articles

  export [format]          Export data (json, csv, html)
    --feed <id>            Export specific feed
    --from <date>          Start date
    --to <date>            End date

  stats                    Show system statistics

Global options:
  --format <fmt>           Output format (text, json, csv)
  --verbose                Enable verbose logging
  --quiet                  Suppress non-error output
  --help                   Show help
  --version                Show version
```

### Usage Examples

```bash
# Add a feed
info-system feed add https://example.com/feed.xml
info-system feed add https://news.ycombinator.com/rss

# List and manage feeds
info-system feed list
info-system feed refresh
info-system feed refresh abc123

# Crawl a website
info-system crawl https://example.com --depth 3 --concurrency 5

# Read articles
info-system article list --unread --limit 50
info-system article list --feed abc123
info-system article search "typescript"

# Export data
info-system export json --from 2026-01-01 > articles.json
info-system export csv --feed abc123 > feed.csv

# Stats
info-system stats
```

## Error Handling Strategy

### Error Categories

| Category | Examples | Handling Strategy |
|----------|----------|-------------------|
| **Network** | Timeout, DNS failure, Connection reset | Retry with exponential backoff |
| **HTTP** | 404, 500, 403, Rate limited | Log, skip, notify user |
| **Parse** | Malformed XML, Invalid HTML | Log to failed_parses table, skip |
| **Storage** | Constraint violation, Disk full | Rollback, alert user |
| **Validation** | Invalid URL, Missing fields | Fail fast with clear message |

### Retry Logic

```typescript
class RetryHandler {
  async withRetry<T>(
    operation: () => Promise<T>,
    options: {
      maxAttempts?: number;
      baseDelay?: number;
      maxDelay?: number;
      shouldRetry?: (error: Error) => boolean;
    } = {}
  ): Promise<T> {
    const {
      maxAttempts = 3,
      baseDelay = 1000,
      maxDelay = 30000,
      shouldRetry = this.defaultShouldRetry
    } = options;

    let lastError: Error;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        if (attempt === maxAttempts || !shouldRetry(lastError)) {
          throw error;
        }
        const delay = Math.min(baseDelay * Math.pow(2, attempt - 1), maxDelay);
        await this.sleep(delay);
      }
    }
    throw lastError!;
  }

  private defaultShouldRetry(error: Error): boolean {
    if (error instanceof NetworkError) return true;
    if (error instanceof HTTPError && error.statusCode >= 500) return true;
    return false;
  }
}
```

### Logging Architecture

```typescript
import pino from 'pino';

// Structured logging with levels
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  transport: process.env.NODE_ENV === 'development'
    ? { target: 'pino-pretty' }
    : undefined,
  base: { pid: process.pid },
  timestamp: pino.stdTimeFunctions.isoTime
});

// Usage
logger.info({ feedId: 'abc123' }, 'Refreshing feed');
logger.warn({ url: 'https://...' }, 'Feed returned 404, skipping');
logger.error({ error, feedId: 'abc123' }, 'Failed to refresh feed');
```

### Error Storage

```sql
CREATE TABLE errors (
  id TEXT PRIMARY KEY,
  operation TEXT NOT NULL,
  entity_type TEXT,
  entity_id TEXT,
  error_code TEXT,
  error_message TEXT,
  stack_trace TEXT,
  context TEXT,  -- JSON for additional context
  occurred_at TEXT DEFAULT CURRENT_TIMESTAMP,
  resolved_at TEXT,
  resolved_by TEXT
);

CREATE INDEX idx_errors_occurred_at ON errors(occurred_at);
CREATE INDEX idx_errors_resolved ON errors(resolved_at) WHERE resolved_at IS NULL;
```

## Scalability Considerations

| Scale | Feeds | Articles | Approach |
|-------|-------|----------|----------|
| **Personal** | < 100 | < 100K | Single SQLite file, no special optimization |
| **Power user** | < 500 | < 1M | FTS5 indexes, WAL mode, connection pooling |
| **Multi-user** | N/A | N/A | Consider separate database per user, or PostgreSQL migration |

### Performance Optimizations

1. **Batch inserts** for article imports
2. **Partial indexes** for common queries (unread articles per feed)
3. **Async writes** with write-ahead logging
4. **Connection pooling** for concurrent requests

## Technology Recommendations

| Layer | Library | Rationale |
|-------|---------|-----------|
| **HTTP Fetcher** | `undici` | Built-in, fast, modern HTTP client with connection pooling |
| **Feed Parser** | `feedparser` | Handles RSS/Atom/RDF, namespace extensions |
| **HTML Parser** | `cheerio` | Fast jQuery-like DOM parsing |
| **SQLite** | `better-sqlite3` | Synchronous, fast, WAL support |
| **CLI** | `meow` | Lightweight, zero dependencies |
| **Logging** | `pino` | Structured JSON logging, fast |
| **Scheduling** | `node-cron` | Familiar cron syntax |
| **ID Generation** | `nanoid` | Compact, URL-safe IDs |

## Project Structure

```
src/
├── index.ts              # CLI entry point
├── commands/             # CLI command handlers
│   ├── feed.ts
│   ├── article.ts
│   ├── crawl.ts
│   ├── export.ts
│   └── stats.ts
├── services/             # Business logic
│   ├── FeedService.ts
│   ├── CrawlService.ts
│   ├── ArticleService.ts
│   └── SearchService.ts
├── fetcher/              # HTTP operations
│   ├── Fetcher.ts
│   ├── robotsTxt.ts
│   └── rateLimiter.ts
├── parser/               # Parsing logic
│   ├── FeedParser.ts
│   ├── HtmlParser.ts
│   └── ContentExtractor.ts
├── storage/              # Data persistence
│   ├── database.ts
│   ├── migrations/
│   └── repositories/
│       ├── FeedRepository.ts
│       ├── ArticleRepository.ts
│       └── CrawlRepository.ts
├── models/               # Type definitions
│   ├── Feed.ts
│   ├── Article.ts
│   └── Crawl.ts
├── utils/                # Utilities
│   ├── logger.ts
│   ├── retry.ts
│   └── scheduler.ts
└── types/                # TypeScript types
    └── index.ts

test/
├── unit/
└── integration/

package.json
tsconfig.json
```

## Sources

- node-feedparser GitHub: https://github.com/danmactough/node-feedparser
- node-cron GitHub: https://github.com/ncb000gt/node-cron
- Meow CLI GitHub: https://github.com/sindresorhus/meow
- SQLite Documentation: https://sqlite.org/docs.html
- Datasette: https://github.com/simonw/datasette
- better-sqlite3: Synchronous SQLite for Node.js with WAL support
