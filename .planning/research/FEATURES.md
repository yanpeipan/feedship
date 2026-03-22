# Feature Landscape: Personal RSS Reader and Website Crawler

**Domain:** CLI tool for RSS subscription and website crawling
**Researched:** 2026-03-22
**Confidence:** MEDIUM (limited verification due to search tool issues; supplemented with known project documentation)

## Table of Contents

1. [Core Features (Table Stakes)](#table-stakes)
2. [Differentiating Features](#differentiators)
3. [Anti-Features](#anti-features)
4. [Feature Dependencies](#feature-dependencies)
5. [MVP Recommendation](#mvp-recommendation)

---

## Table Stakes

Features users expect. Missing these makes the product feel incomplete.

### Feed Management

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Add feed by URL | Basic subscription workflow | Low | Must handle RSS, Atom, RDF auto-detection |
| List subscribed feeds | View all subscriptions | Low | Should show feed title, article count, last updated |
| Remove feed | Unsubscribe workflow | Low | Cascade delete articles or keep them |
| OPML import/export | Migration from other readers | Low | Standard format for feed subscriptions |
| Refresh single/all feeds | Manual update trigger | Low | Show fetch status, article count |

### Content Fetching

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Parse RSS 2.0 | Most common feed format | Low | Universally supported |
| Parse Atom | Standard alternative | Low | Often used by newer sites |
| Extract article title | Core reading information | Low | Handle missing titles gracefully |
| Extract article URL | Primary link to source | Low | Required for opening articles |
| Extract article content | Main reading body | Medium | Handle HTML, plain text, CDATA |
| Store publication date | Chronological sorting | Low | Handle missing/invalid dates |
| Handle feed errors | Real-world robustness | Medium | 404, timeout, malformed XML |

### Data Storage

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| SQLite persistence | Keep data between sessions | Low | Single-file database |
| Store feed metadata | Title, description, site URL | Low | Avoid re-fetching on every run |
| Store articles | Enable offline reading | Low | Full content or description only |
| Mark articles read/unread | Track reading state | Low | Persist state across sessions |
| Bookmark articles | Save for later | Low | "Read it later" functionality |

### CLI Interface

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Help command | Discoverability | Low | List all commands |
| List command | View feeds/articles | Low | Paginated output |
| Add command | Subscribe to feed | Low | Single URL argument |
| Remove command | Unsubscribe | Low | By feed ID or URL |
| Fetch/refresh command | Update feeds | Low | Manual trigger |
| Output formats | Different use cases | Medium | Text (default), JSON, CSV |

### Search

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Full-text search | Find articles by keyword | Medium | SQLite FTS5 |
| Filter by feed | Narrow results | Low | Feed ID or name |
| Filter by date range | Time-based queries | Low | From/to dates |
| Filter by read status | Unread-only view | Low | Read/unread/all |

---

## Differentiators

Features that set products apart. Not expected, but valued when present.

### Advanced Feed Management

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Query feeds (meta-feeds) | Aggregate across feeds with filters | Medium | "All articles from past week" |
| Feed categories/folders | Organize large subscriptions | Low | Group related feeds |
| Keyboard-driven UI | Power-user efficiency | Low | vi-like bindings common |
| Custom refresh intervals | Per-feed fetch timing | Medium | Some feeds hourly, others daily |
| Feed validation | Detect broken feeds | Medium | Check before adding |

### Web Scraping / Crawling

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Website crawling | Discover content without RSS | High | Extract articles from sites without feeds |
| XPath-based scraping | Custom content extraction | High | For sites without proper feeds |
| JavaScript rendering | SPA support | High | Playwright for rendered content |
| robots.txt compliance | Ethical crawling | Medium | Respect site rules |
| Depth-limited crawling | Scope control | Medium | Prevent runaway crawls |
| Discovered URL storage | Build feed from site | Medium | Find RSS feeds on crawled sites |

### Automation

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Scheduled fetching | Hands-free updates | Medium | Cron-like scheduling |
| Auto-refresh on interval | Keep data fresh | Medium | Background process |
| Deduplication | Avoid repeated articles | Medium | By GUID or URL hash |
| Automatic read marking | Based on rules | Medium | Mark old articles read |
| ETag/Last-Modified support | Conditional requests | Medium | Avoid re-fetching unchanged |
| WebSub/PubSubHubbub | Real-time push | High | Instant feed updates |

### Content Enhancement

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Content extraction | Strip ads/boilerplate | High | Readability algorithms |
| Readability mode | Clean article view | High | Focus on content |
| Media extraction | Pull images/audio | Medium | Enrich article presentation |
| Author extraction | Normalize author data | Medium | Handle multiple formats |
| Tag/category extraction | Organize by topic | Medium | Map to structured data |

### Advanced Search & Organization

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Saved searches | Re-run queries | Low | Store search queries |
| Search within feed | Feed-specific search | Low | Filter results |
| Bulk operations | Batch mark/read/delete | Medium | Efficiency for power users |
| Article filtering rules | Auto-categorize | Medium | By keyword, author, feed |
| Killfiles | Hide matching articles | Medium | Block unwanted content |

### Data Portability

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Export to JSON | Machine-readable backup | Low | Full data export |
| Export to CSV | Spreadsheet analysis | Low | Tabular format |
| Export to HTML | Static archive | Medium | Browseable offline |
| Article-per-file | Granular storage | Medium | One file per article |
| Import from other readers | Migration path | Medium | Fever, Google Reader API |

### Monitoring & Notifications

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Feed change detection | Alert on updates | Medium | Track website changes |
| Article count notifications | Know when new content | Medium | CLI output or desktop notif |
| Health monitoring | Feed uptime tracking | Medium | Detect dead feeds |
| Statistics dashboard | Usage insights | Low | Article counts, feed health |

### API & Extensibility

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| REST API | External integrations | High | Programmatic access |
| Google Reader API compatibility | Mobile app support | High | Use existing apps |
| Webhooks | Event-driven integrations | High | Trigger on new articles |
| Plugin/extension system | Custom behavior | High | User-extensible |
| Custom scripts | Transform feeds | Low | External program filters |

### User Experience

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multiple output formats | Different consumers | Medium | Text, JSON, CSV, HTML |
| Color-coded output | Visual hierarchy | Low | Read vs unread, feed colors |
| Pagination | Handle large result sets | Low | Limit and offset |
| Progress indicators | Feedback during long ops | Low | Fetch status |
| Interactive mode | TUI for browsing | High | Ncurses-style interface |
| Vim-like navigation | Keyboard-centric | Low | j/k for up/down |

---

## Anti-Features

Features to explicitly NOT build (at least initially).

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Multi-user support | Adds auth, isolation complexity | Single-user, local SQLite |
| User authentication | Not needed for personal tool | File system permissions |
| Social/sharing features | Outside scope | Export and share manually |
| Built-in sync (Dropbox, etc.) | Scope creep | Use file-based sync |
| Cloud hosting | Opposite of self-hosted | Local-only by default |
| Recommendation engine | AI overreach | Manual subscription |
| Commenting/discussion | Not an RSS reader | Use source site |
| Podcast support | Separate use case | Focus on articles |
| Email newsletter parsing | Different problem | Separate tool later |

---

## Feature Dependencies

```
Feed Management
  Add feed URL
    Validate URL format → Low
    Check feed is valid RSS/Atom → Medium
    Save to database → Low
  Remove feed
    Delete articles (or mark deleted) → Low
    Remove from database → Low

Content Fetching
  Fetch feed
    HTTP GET with timeout → Low
    Parse XML → Low
    Handle parse errors → Medium
    Store articles → Low
    Detect duplicates (by guid) → Medium

Search
  Full-text search (FTS5)
    Create FTS virtual table → Low
    Index on insert/update → Low
    Query with ranking → Medium

Crawling (if implemented)
  Fetch page
    Respect robots.txt → Medium
    Rate limiting → Medium
    Extract links → Medium
    Follow linked pages (depth-limited) → High
    Detect RSS feeds on crawled pages → High

Automation
  Scheduled refresh
    Cron-like scheduler → Medium
    Background process management → Medium
    Per-feed intervals → Medium
```

---

## MVP Recommendation

For a personal RSS reader and website crawler CLI tool, prioritize in this order:

### Phase 1: Core (Table Stakes)

1. **Feed subscription** - Add feed by URL, list feeds, remove feed
2. **Feed refresh** - Fetch and parse RSS/Atom, extract articles
3. **Article listing** - View articles with pagination, show title/date/link
4. **Read state** - Mark articles as read/unread, filter by status
5. **Basic search** - Full-text search across articles
6. **SQLite storage** - Persist feeds, articles, read state between sessions
7. **OPML export** - Backup subscriptions

### Phase 2: Enhancement (Commonly Valued)

1. **OPML import** - Restore from backup or migrate from other readers
2. **Bookmarking** - Save articles for later, bookmark-only view
3. **Multiple output formats** - JSON, CSV export
4. **Better search** - Filter by feed, date range, read status
5. **Error handling** - Graceful handling of broken feeds, retry logic
6. **Feed metadata** - Store and display feed title, description, site URL

### Phase 3: Differentiation (If Time Permits)

1. **Website crawling** - Scrape sites without RSS, discover feeds
2. **XPath scraping** - Custom extraction rules for problematic sites
3. **Scheduled fetching** - Automatic refresh on interval
4. **Deduplication** - Detect and skip duplicate articles
5. **Content extraction** - Strip boilerplate, extract main content
6. **ETag/Last-Modified** - Conditional requests to reduce bandwidth

### Defer Indefinitely

- Multi-user support
- User authentication
- Social features
- Cloud sync
- Podcast support
- Built-in AI/recommendations
- Plugin system

---

## Sources

- FreshRSS documentation and GitHub (HIGH confidence)
- CommaFeed features (MEDIUM confidence)
- Inoreader feature list (MEDIUM confidence)
- Newsboat/Newsbeuter documentation (HIGH confidence)
- GitHub Topics - RSS (MEDIUM confidence)
- GitHub Topics - Web Crawler (MEDIUM confidence)
- Common RSS reader feature patterns (MEDIUM confidence)

---

## Confidence Assessment

| Category | Confidence | Notes |
|----------|------------|-------|
| Table stakes features | HIGH | Core features well-documented across all major RSS readers |
| Differentiating features | MEDIUM | Varies by reader; some features are niche |
| Anti-features | MEDIUM | Based on scope analysis, not external validation |
| Dependencies | MEDIUM | General patterns, not implementation-verified |
| MVP recommendation | MEDIUM | Based on research synthesis, not user testing |
