# Architecture Research: GitHub Monitoring Integration

**Domain:** CLI personal资讯系统 - GitHub releases and changelog monitoring
**Researched:** 2026-03-23
**Confidence:** HIGH

## Executive Summary

GitHub releases and changelog monitoring integrates cleanly with the existing architecture by treating GitHub repos as a special feed type. The existing `feeds` and `articles` tables can be reused with a `feed_type` column to distinguish between RSS, crawled pages, and GitHub sources. GitHub API provides structured release data (tag_name, body, published_at) that maps directly to article fields. Scrapling handles changelog HTML fetching with its adaptive parsing capabilities.

## Integration with Existing Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                             │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ feed add │  │  crawl   │  │  fetch   │  │ article  │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │             │            │
├───────┴─────────────┴─────────────┴─────────────┴────────────┤
│                    Service Layer                              │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │ feeds.py │  │ crawl.py │  │ github.py│  │changelog │     │
│  │ (exist) │  │ (exist)  │  │  (NEW)   │  │  .py NEW │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │             │            │
├───────┴─────────────┴─────────────┴─────────────┴────────────┤
│                    Data Layer                                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │    feeds table      │  │      articles table          │  │
│  │  (extend with type) │  │   (reusable for releases)     │  │
│  └─────────────────────┘  └─────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              FTS5 articles_fts                       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Implementation |
|-----------|----------------|----------------|
| `feeds.py` (existing) | Generic feed CRUD | Extend with feed_type detection |
| `crawl.py` (existing) | URL content extraction | Unchanged for GitHub integration |
| `github.py` (NEW) | GitHub API releases | httpx client with Bearer auth |
| `changelog.py` (NEW) | CHANGELOG.md fetching | Scrapling adaptive parser |
| `db.py` (existing) | SQLite with WAL | Add feed_type column migration |

## Recommended Project Structure

```
src/
├── __init__.py           # Package marker
├── cli.py                # CLI commands (extend with github subcommands)
├── db.py                 # Database schema (add feed_type)
├── feeds.py              # Feed operations (add github_refresh)
├── articles.py           # Article operations (unchanged)
├── crawl.py              # URL crawling (unchanged)
├── github.py             # GitHub API client (NEW)
└── changelog.py           # Changelog fetcher (NEW)
```

### Structure Rationale

- **`github.py`:** Separates GitHub API logic from generic feed logic. Handles auth, rate limiting, release parsing.
- **`changelog.py`:** Separates Scrapling-based changelog fetching from generic crawling. Handles raw markdown file fetching and change detection.
- **`feeds.py` changes minimal:** Add `refresh_github_release()` that calls github.py, keep existing patterns.

## Architectural Patterns

### Pattern 1: Feed Type Discrimination

**What:** Extend feeds table with a `feed_type` column to handle different source types uniformly in UI but differently in refresh logic.

**When to use:** When multiple data sources share storage but need different fetch strategies.

**Trade-offs:**
- Pros: Single table, simple queries, unified article listing
- Cons: Type checking scattered in refresh logic

**Example:**
```python
# feeds table extension
cursor.execute("ALTER TABLE feeds ADD COLUMN feed_type TEXT DEFAULT 'rss'")

# In refresh logic
def refresh_feed(feed_id: str) -> dict:
    feed = get_feed(feed_id)
    if feed.feed_type == 'github_release':
        return refresh_github_release(feed)
    elif feed.feed_type == 'github_changelog':
        return refresh_github_changelog(feed)
    else:
        return refresh_rss_feed(feed)  # existing logic
```

### Pattern 2: GitHub API as Feed Fetcher

**What:** Treat GitHub releases endpoint as a structured feed with known fields mapping to article schema.

**When to use:** When API provides machine-readable feed-like data.

**Trade-offs:**
- Pros: Direct mapping, no HTML parsing needed, structured data
- Cons: API rate limits (5000/hour authenticated), requires auth token

**Example:**
```python
# GitHub release -> article mapping
article_id = f"github:{owner}/{repo}:{release['tag_name']}"
cursor.execute("""
    INSERT OR IGNORE INTO articles
    (id, feed_id, title, link, guid, pub_date, description, content)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (
    article_id,
    feed_id,
    release['name'] or release['tag_name'],
    release['html_url'],
    release['tag_name'],
    release['published_at'],
    release['body'],  # description = release notes summary
    release['body'],  # content = full release notes
))
```

### Pattern 3: Changelog as Single Article

**What:** Store each CHANGELOG.md fetch as a single article, with content hash for change detection.

**When to use:** When monitoring file changes rather than discrete entries.

**Trade-offs:**
- Pros: Simple storage, easy change detection via content hash
- Cons: No per-version granularity, need content comparison for diff

**Example:**
```python
def fetch_changelog(repo_url: str) -> Optional[dict]:
    changelog_url = f"{repo_url.rstrip('/')}/blob/main/CHANGELOG.md"
    page = StealthyFetcher.fetch(changelog_url)
    content = page.css('pre[data-testid="code"]::text', first=True) or page.text()

    return {
        'content': content,
        'hash': hashlib.sha256(content.encode()).hexdigest(),
    }
```

## Data Flow

### GitHub Releases Flow

```
[User adds GitHub repo]
    ↓
[Parse owner/repo from URL] → [Store in feeds table with feed_type='github_release']
    ↓
[fetch --all calls refresh_github_release]
    ↓
[github.py: fetch_releases(owner, repo, token)]
    ↓
[GitHub API: GET /repos/{owner}/{repo}/releases]
    ↓
[Parse releases, map to articles] → [INSERT OR IGNORE into articles]
    ↓
[Sync to FTS5] → [Update feed.last_fetched]
```

### Changelog Monitoring Flow

```
[User adds GitHub repo for changelog]
    ↓
[Store in feeds table with feed_type='github_changelog']
    ↓
[fetch calls refresh_github_changelog]
    ↓
[changelog.py: fetch_raw_changelog(owner, repo)]
    ↓
[Scrapling fetches raw CHANGELOG.md content]
    ↓
[Compute content hash, compare with previous]
    ↓
[If changed: INSERT OR REPLACE article with new content]
    ↓
[Update feed.last_fetched]
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|-------------------------|
| 0-100 feeds | Current architecture sufficient |
| 100-1000 feeds | Add batch rate limiting, consider async fetching |
| 1000+ feeds | Consider job queue, parallel refresh with backoff |

### Scaling Priorities

1. **First bottleneck:** GitHub API rate limits (5000/hour). Mitigation: Implement per-repo backoff, track rate limit headers.
2. **Second bottleneck:** Sequential fetching on `fetch --all`. Mitigation: asyncio parallelization for independent feeds.

## Anti-Patterns

### Anti-Pattern 1: Ignoring GitHub Rate Limits

**What people do:** Blindly fetch GitHub API on every refresh without checking rate limit headers.

**Why it's wrong:** Exhausts rate limit quickly, causes 429 responses, potential IP ban.

**Do this instead:**
```python
def fetch_with_rate_limit_handling(url: str, headers: dict) -> httpx.Response:
    response = httpx.get(url, headers=headers)
    remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
    if remaining < 10:
        reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
        sleep_duration = max(reset_time - time.time(), 0) + 5
        time.sleep(sleep_duration)
    return response
```

### Anti-Pattern 2: Storing Raw HTML Instead of Content

**What people do:** Store raw HTML from GitHub pages instead of extracting actual content.

**Why it's wrong:** Wastes storage, FTS5 indexes HTML noise, article listing shows garbled content.

**Do this instead:** Use Scrapling's text extraction or raw markdown fetching for CHANGELOG.md.

### Anti-Pattern 3: No Auth Token for GitHub API

**What people do:** Using unauthenticated GitHub API requests.

**Why it's wrong:** 60 requests/hour limit vs 5000/hour authenticated. Will hit rate limits immediately with multiple repos.

**Do this instead:** Require GH_TOKEN environment variable, show clear error if missing.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| GitHub API | REST over HTTPS with Bearer token | Rate limit: 5000/hour authenticated, 60/hour anonymous |
| GitHub raw content | Raw file URLs for CHANGELOG.md | URL: `https://raw.githubusercontent.com/{owner}/{repo}/main/CHANGELOG.md` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| cli.py -> github.py | Function call | `add_github_feed(url)` -> `github.py:validate_repo()` |
| feeds.py -> github.py | Function call | `refresh_feed()` dispatches to `refresh_github_release()` |
| changelog.py -> cli.py | Function call | `refresh_github_changelog()` calls `changelog.py:fetch_raw_changelog()` |

## Database Schema Changes

### Migration: Add feed_type

```sql
ALTER TABLE feeds ADD COLUMN feed_type TEXT DEFAULT 'rss';

-- Optional: add index for type queries
CREATE INDEX IF NOT EXISTS idx_feeds_feed_type ON feeds(feed_type);
```

### New Columns for GitHub-specific Metadata (Optional Enhancement)

```sql
-- Only needed if storing per-repo GitHub metadata separately from articles
ALTER TABLE feeds ADD COLUMN gh_owner TEXT;
ALTER TABLE feeds ADD COLUMN gh_repo TEXT;
ALTER TABLE feeds ADD COLUMN gh_last_tag TEXT;
```

### Article Storage for GitHub Releases

Releases map directly to existing article schema:

| Article Field | GitHub Release Field | Notes |
|---------------|---------------------|-------|
| id | `github:{owner}/{repo}:{tag_name}` | Unique per release |
| feed_id | feeds.id | Foreign key |
| title | release.name or release.tag_name | Display name |
| link | release.html_url | Release page URL |
| guid | release.tag_name | Version identifier |
| pub_date | release.published_at | ISO timestamp |
| description | release.body (first 500 chars) | Release notes preview |
| content | release.body | Full release notes (Markdown) |

### Article Storage for Changelog

| Article Field | Changelog Value | Notes |
|---------------|-----------------|-------|
| id | `changelog:{owner}/{repo}:{hash}` | Hash of content |
| feed_id | feeds.id | Foreign key |
| title | `{repo} Changelog` | Static |
| link | `https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md` | Raw URL |
| guid | `changelog:{hash}` | Hash as identifier |
| pub_date | last_fetched timestamp | Update time |
| description | First 500 chars of changelog | Content preview |
| content | Full changelog content | Full Markdown |

## Suggested Build Order

### Phase 1: GitHub API Client (`src/github.py`)
- Implement `fetch_releases(owner, repo, token)` function
- Handle pagination (per_page=100, iterate pages)
- Rate limit handling with header inspection
- Return structured release data

### Phase 2: Release Refresh Integration
- Add `feed_type='github_release'` to feeds table
- Implement `refresh_github_release(feed_id)` in feeds.py
- Store releases as articles using existing schema
- Test with single repo

### Phase 3: Changelog Fetcher (`src/changelog.py`)
- Implement `fetch_raw_changelog(owner, repo)` using raw GitHub URL
- Use httpx (not Scrapling) for raw file fetching - simpler for raw markdown
- Content hash computation for change detection
- Return content and hash

### Phase 4: Changelog Refresh Integration
- Add `feed_type='github_changelog'` handling
- Implement `refresh_github_changelog(feed_id)`
- Store as single article per changelog
- Detect changes via content hash

### Phase 5: CLI Integration
- Add `github` subcommand group
- `github add <repo-url>` - adds repo for release monitoring
- `github add-changelog <repo-url>` - adds repo for changelog monitoring
- Integrate with `fetch --all` for unified refresh

## Sources

- [GitHub REST API - Releases](https://docs.github.com/en/rest/releases/releases) (HIGH confidence)
- [GitHub REST API - Rate Limits](https://docs.github.com/en/rest/rate-limit/rate-limit) (HIGH confidence)
- [Scrapling Documentation](https://scrapling.readthedocs.io/) (HIGH confidence)
- [Existing codebase: src/feeds.py, src/crawl.py, src/db.py] (HIGH confidence - internal)
