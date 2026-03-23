# Phase 14: CLI Integration - Research

**Researched:** 2026-03-24
**Domain:** Click CLI framework, Provider Registry integration
**Confidence:** HIGH (codebase analysis)

## Summary

Phase 14 wires the existing CLI commands to use the Provider Registry architecture. The primary changes are:
1. `fetch --all` must iterate feeds via ProviderRegistry and call provider.crawl() + parse()
2. `feed add <url>` must auto-detect provider type via ProviderRegistry.discover()
3. `repo` command group (add/list/remove/refresh) must be deleted
4. `feed list` must show provider_type column

**Key finding:** The feeds table schema in db.py does NOT have a `metadata` TEXT column, and `github_repos` table still exists. Phase 12/13 requirements DB-01, DB-02, DB-03 appear to not have been fully implemented in the database schema. This is a blocking gap - the CLI integration assumes feeds.metadata works but the column doesn't exist yet.

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for this phase. All decisions are in REQUIREMENTS.md and PROJECT.md.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | fetch --all uses Registry | ProviderRegistry.discover_or_default(url) returns matching provider; provider.crawl() + parse() returns articles |
| CLI-02 | feed add auto-routes | ProviderRegistry.discover_or_default(url) handles provider selection automatically |
| CLI-03 | Delete repo commands | repo add/list/remove/refresh defined in cli.py lines 646-788; delete entire @repo group |
| CLI-04 | feed list shows provider_type | feeds table needs metadata column to store provider_type; list_feeds() must query it |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | 8.1.x | CLI framework | Project standard (CLAUDE.md) |

### Project-Specific
| Library | Purpose | Location |
|---------|---------|----------|
| ProviderRegistry | Provider discovery | src/providers/__init__.py |
| ContentProvider | Provider interface protocol | src/providers/base.py |
| feeds.py | Feed CRUD operations | src/feeds.py |
| github.py | GitHub API client | src/github.py |

## Architecture Patterns

### Recommended CLI Integration Pattern

The CLI should delegate to providers rather than having separate code paths for RSS vs GitHub:

```
feed add <url>
  -> ProviderRegistry.discover_or_default(url)[0]  # highest priority match
  -> provider.crawl(url)       # fetch raw content
  -> provider.parse(raw)       # convert to article
  -> store_article()           # save to DB (via feeds table)
  -> store metadata with provider name

fetch --all
  -> list_feeds()
  -> for each feed:
     -> ProviderRegistry.discover_or_default(feed.url)[0]
     -> provider.crawl(feed.url)
     -> provider.parse(raw)
     -> store any new articles
```

### Key Interface: ProviderRegistry

**Location:** `src/providers/__init__.py`

```python
def discover(url: str) -> List[ContentProvider]:
    """Find providers matching a URL, sorted by priority descending."""

def discover_or_default(url: str) -> List[ContentProvider]:
    """Find providers or return default RSS provider as fallback."""

def get_all_providers() -> List[ContentProvider]:
    """Return all loaded providers sorted by priority."""
```

### Key Interface: ContentProvider Protocol

**Location:** `src/providers/base.py`

```python
@runtime_checkable
class ContentProvider(Protocol):
    def match(self, url: str) -> bool: ...
    def priority(self) -> int: ...
    def crawl(self, url: str) -> List[Raw]: ...
    def parse(self, raw: Raw) -> Article: ...
```

## Current CLI Structure (cli.py)

### feed group (lines 70-174)
- `feed add <url>` -> calls `add_feed(url)` from feeds.py
- `feed list` -> calls `list_feeds()` from feeds.py
- `feed remove <feed_id>` -> calls `remove_feed(feed_id)`
- `feed refresh <feed_id>` -> calls `refresh_feed(feed_id)`

### repo group (lines 646-788) - TO BE DELETED
- `repo add <url>` -> calls `add_github_repo(url)` from github.py
- `repo list` -> calls `list_github_repos()` from github.py
- `repo remove <repo_id>` -> calls `remove_github_repo(repo_id)`
- `repo refresh [repo_id]` -> calls `refresh_github_repo(repo_id)`
- `repo changelog [repo_id] --refresh` -> calls `refresh_changelog()` / `get_repo_changelog()`

### fetch command (lines 536-608)
- `fetch --all` currently:
  1. Calls `list_feeds()` and iterates calling `refresh_feed()` for each
  2. Calls `list_github_repos()` and iterates calling `refresh_github_repo()` for each

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Provider discovery | Custom URL matching | ProviderRegistry.discover() | Built-in priority-based matching already exists |
| Feed type routing | if/else on URL patterns | Provider.match() | Providers self-identify via match() method |
| Provider iteration | Hardcoded provider list | get_all_providers() | Providers auto-discovered at import time |

## Common Pitfalls

### Pitfall 1: Missing metadata column
**What goes wrong:** feeds table in db.py schema has no `metadata` column. Feed model has `metadata: Optional[str]` but DB schema does not include it.
**Why it happens:** DB-01 requirement (add feeds.metadata column) was not implemented in the actual database schema
**How to avoid:** Check database schema before assuming metadata exists. May need to add migration step.
**Warning signs:** `metadata` column not found when querying feeds table

### Pitfall 2: github_repos table still exists
**What goes wrong:** github_repos table still defined in db.py (lines 122-133) when DB-03 says it should be dropped
**Why it happens:** Phase 12/13 migrations may not have been fully implemented
**How to avoid:** The CLI integration should work regardless - github repos will be migrated to feeds.metadata

### Pitfall 3: Mixing old and new code paths
**What goes wrong:** feeds.py still has `is_github_blob_url()` checks and direct github.py imports
**Why it happens:** Legacy code not cleaned up after provider architecture
**How to avoid:** Refactor feeds.py to use providers exclusively, remove github.py imports from cli.py

### Pitfall 4: Provider returns different data shape than expected
**What goes wrong:** RSSProvider.parse() returns Article dict with specific fields, but feeds.py insert expects different shape
**Why it happens:** Provider architecture uses dicts, feeds.py uses parameterized inserts
**How to avoid:** The CLI integration should use store_article() which handles the dict format

## Code Examples

### Current fetch --all (needs refactor)
```python
# Current: separate handling for feeds and github repos
for feed_obj in feeds:
    result = refresh_feed(feed_obj.id)  # Uses feeds.py which has its own RSS parsing

github_repos = list_github_repos()
for r in github_repos:
    result = refresh_github_repo(r.id)  # Uses github.py directly
```

### New fetch --all (via ProviderRegistry)
```python
from src.providers import ProviderRegistry

feeds = list_feeds()
for feed in feeds:
    providers = ProviderRegistry.discover_or_default(feed.url)
    provider = providers[0]  # highest priority
    raw_items = provider.crawl(feed.url)
    for raw in raw_items:
        article = provider.parse(raw)
        store_article(
            guid=article['guid'],
            title=article['title'],
            content=article.get('content'),
            link=article.get('link'),
            feed_id=feed.id,
            pub_date=article.get('pub_date'),
        )
```

### Current feed list output
```
ID  | Name | URL | Articles | Last Fetched
--------------------------------------------
abc | Tech News | https://... | 10 | 2024-01-01
```

### New feed list output (with provider_type)
```
ID  | Name | URL | Type | Articles | Last Fetched
-------------------------------------------------
abc | Tech News | https://... | RSS | 10 | 2024-01-01
def | owner/repo | https://github.com/... | GitHub | 5 | 2024-01-02
```

## Database Schema Gap Analysis

**Current feeds table (db.py lines 77-87):**
```sql
CREATE TABLE IF NOT EXISTS feeds (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    etag TEXT,
    last_modified TEXT,
    last_fetched TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**Missing:** `metadata TEXT` column (per DB-01 requirement)

**Current github_repos table (db.py lines 122-133):**
```sql
CREATE TABLE IF NOT EXISTS github_repos (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    last_fetched TEXT,
    last_tag TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(owner, repo)
)
```

**Should be:** Deleted (per DB-03 requirement), data migrated to feeds.metadata

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies - code/config changes only)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest.ini or pyproject.toml |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|------------------|--------------|
| CLI-01 | fetch --all iterates providers via Registry | integration | `pytest tests/test_cli.py::test_fetch_all_uses_registry -x` | NO |
| CLI-02 | feed add auto-detects provider type | integration | `pytest tests/test_cli.py::test_feed_add_auto_discovers -x` | NO |
| CLI-03 | repo commands deleted | unit | `pytest tests/test_cli.py::test_repo_commands_removed -x` | NO |
| CLI-04 | feed list shows provider_type | unit | `pytest tests/test_cli.py::test_feed_list_shows_type -x` | NO |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- `tests/test_cli.py` — covers CLI-01 through CLI-04
- `tests/conftest.py` — shared fixtures (if needed)
- Framework install: `pip install pytest` — if not detected

*(Note: No existing test infrastructure detected in project)*

## Sources

### Primary (HIGH confidence)
- src/cli.py - Current CLI implementation
- src/providers/__init__.py - ProviderRegistry implementation
- src/providers/base.py - ContentProvider protocol
- src/providers/rss_provider.py - RSS provider example
- src/providers/github_provider.py - GitHub provider example
- src/feeds.py - Current feed management
- src/github.py - Current GitHub integration
- src/db.py - Database schema (identified gap: missing metadata column)
- src/models.py - Data models (Feed has metadata field but DB doesn't)

### Secondary (MEDIUM confidence)
- CLAUDE.md - Project tech stack recommendations
- REQUIREMENTS.md - Phase requirements (DB-01/02/03 marked complete but schema doesn't reflect)

## Open Questions

1. **Database migration gap:** The feeds table lacks `metadata` column and github_repos table still exists. Should Phase 14 include these database schema fixes, or is it a separate issue?
   - What we know: db.py schema was not updated; Feed model has metadata field
   - What's unclear: Whether migrations were run separately or not implemented
   - Recommendation: Add `metadata TEXT` column to feeds table as part of Phase 14, since CLI-04 depends on it

2. **Backward compatibility:** When migrating github_repos to feeds.metadata, what happens to existing github_releases table entries?
   - What we know: github_releases table has repo_id foreign key
   - What's unclear: If github_repos is deleted, what happens to github_releases entries?
   - Recommendation: Keep github_releases table but add feed_id column for dual reference

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Click is project standard, Provider Registry already implemented
- Architecture: HIGH - Clear pattern: CLI delegates to providers via discover()
- Pitfalls: MEDIUM - Database schema gaps identified via code analysis

**Research date:** 2026-03-24
**Valid until:** 2026-04-23 (30 days - stable domain)
