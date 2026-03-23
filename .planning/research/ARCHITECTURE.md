# Architecture Research: Plugin Provider System

**Domain:** RSS Reader CLI - Plugin-Based Provider Architecture
**Researched:** 2026-03-23
**Confidence:** MEDIUM-HIGH

## Executive Summary

Adding a plugin-based provider architecture to the existing RSS reader requires introducing a **Provider Interface**, a **Provider Registry** for discovery, and refactoring the existing `fetch` flow to iterate over providers generically. The primary architectural shift is treating GitHub repos as just another provider type alongside RSS/Atom feeds, both stored in the unified `feeds` table with provider-specific metadata in a JSON `metadata` column.

## Current Architecture Analysis

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer (click)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ feed.*   │  │ article.*│  │   tag.*  │  │  repo.*  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
├───────┴─────────────┴─────────────┴─────────────┴───────────┤
│                    Business Logic Layer                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ articles │  │  feeds   │  │   tags   │  │  github  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
├───────┴─────────────┴─────────────┴─────────────┴───────────┤
│                      Data Layer (SQLite)                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  feeds | articles | github_repos | github_releases   │   │
│  │  tags  | article_tags                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Current Component Responsibilities

| Component | Responsibility | Location | Issues |
|-----------|----------------|----------|--------|
| `cli.py` | Click commands, orchestrates fetch across feeds and repos | `src/cli.py` | Fetch command manually iterates both feeds and github_repos |
| `feeds.py` | RSS/Atom feed CRUD, refresh, parsing | `src/feeds.py` | Hardcoded to feedparser + httpx |
| `github.py` | GitHub API client, releases, changelog | `src/github.py` | Separate from feeds module, own refresh logic |
| `db.py` | SQLite connection, schema, CRUD | `src/db.py` | `github_repos` is separate from `feeds` table |
| `models.py` | Dataclass definitions | `src/models.py` | `GitHubRepo` is separate from `Feed` |

### Critical Integration Points

1. **`fetch --all` command** (`cli.py` line 536-608):
   - Iterates `list_feeds()` then `list_github_repos()`
   - Calls `refresh_feed()` for each feed
   - Calls `refresh_github_repo()` for each repo
   - Two separate code paths with similar structure

2. **`feed add` command** (`cli.py` line 77-94):
   - Calls `add_feed()` which internally detects GitHub blob URLs
   - But `repo add` is a separate command calling `add_github_repo()`

3. **Database** (`db.py`):
   - `feeds` table stores RSS/Atom feeds
   - `github_repos` table stores GitHub repositories
   - No common abstraction

## Recommended Plugin Architecture

### System Overview with Providers

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer (click)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ feed.*   │  │ article.*│  │   tag.*  │  │  repo.*  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
├───────┴─────────────┴─────────────┴─────────────┴─────────┤
│                    Business Logic Layer                     │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Provider Registry (NEW)                  │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │  │
│  │  │  RSS/   │  │ GitHub  │  │  Future │            │  │
│  │  │  Atom   │  │Provider │  │Providers│            │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘            │  │
│  └───────┴────────────┴────────────┴──────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ articles │  │  feeds   │  │   tags   │  │  github  │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
├───────┴─────────────┴─────────────┴─────────────┴───────────┤
│                      Data Layer (SQLite)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  feeds (with metadata JSON) | articles | tags       │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Provider Interface (Protocol)

```python
# src/providers/base.py
from abc import ABC, abstractmethod
from typing import Optional
from dataclasses import dataclass

@dataclass
class ProviderRefreshResult:
    """Result of a provider refresh operation."""
    new_items: int
    provider_name: str
    error: Optional[str] = None

class ContentProvider(ABC):
    """Abstract base class for content providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name (e.g., 'rss', 'github')."""
        pass

    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Unique identifier for this provider type."""
        pass

    @abstractmethod
    def add(self, url: str, metadata: dict) -> "Feed":
        """Add a new subscription. Returns created Feed object."""
        pass

    @abstractmethod
    def refresh(self, feed: "Feed") -> ProviderRefreshResult:
        """Refresh a feed and fetch new items. Returns result."""
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this provider can handle the given URL."""
        pass
```

### Provider Registry

```python
# src/providers/registry.py
from typing import Optional
from src.providers.base import ContentProvider

class ProviderRegistry:
    """Registry for content providers with discovery."""

    def __init__(self):
        self._providers: dict[str, ContentProvider] = {}

    def register(self, provider: ContentProvider) -> None:
        """Register a provider by its type name."""
        self._providers[provider.provider_type] = provider

    def get(self, provider_type: str) -> Optional[ContentProvider]:
        """Get provider by type name."""
        return self._providers.get(provider_type)

    def discover(self, url: str) -> Optional[ContentProvider]:
        """Discover which provider can handle a URL."""
        for provider in self._providers.values():
            if provider.can_handle(url):
                return provider
        return None

    def all_providers(self) -> list[ContentProvider]:
        """Return all registered providers."""
        return list(self._providers.values())

# Global registry instance
_registry: Optional[ProviderRegistry] = None

def get_registry() -> ProviderRegistry:
    """Get the global provider registry."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
        # Register built-in providers
        from src.providers.rss import RSSProvider
        from src.providers.github import GitHubProvider
        _registry.register(RSSProvider())
        _registry.register(GitHubProvider())
    return _registry
```

### Database Schema Changes

**Migration from `github_repos` to `feeds.metadata`:**

```sql
-- Add metadata column to feeds table
ALTER TABLE feeds ADD COLUMN metadata TEXT;

-- metadata stores JSON like:
-- {"provider": "github", "owner": "owner", "repo": "repo", "last_tag": "v1.0.0"}
-- or
-- {"provider": "rss"} -- RSS is the default/implicit provider
```

**After migration:**
- Drop `github_repos` table (or keep for v1.3 compatibility, deprecate later)
- All sources stored in `feeds` table
- `github_releases` remains separate (stores releases per feed)

## Integration with Existing Code

### New Components

| Component | Purpose | File |
|-----------|---------|------|
| `ContentProvider` | Abstract base class (protocol) | `src/providers/base.py` |
| `ProviderRegistry` | Provider discovery and management | `src/providers/registry.py` |
| `RSSProvider` | RSS/Atom feed handling | `src/providers/rss.py` |
| `GitHubProvider` | GitHub releases/changelog handling | `src/providers/github.py` |

### Modified Components

| Component | Change | Reason |
|-----------|--------|--------|
| `feeds.py` | REFACTOR into `RSSProvider` | Move RSS logic into provider |
| `github.py` | REFACTOR into `GitHubProvider` | Move GitHub logic into provider |
| `cli.py` | Use `ProviderRegistry` in fetch | Single loop over all feeds |
| `db.py` | Add `feeds.metadata` column | Store provider-specific data |
| `models.py` | Add `Feed.metadata` field | Access metadata from Feed |

### Unchanged Components

| Component | Reason |
|-----------|--------|
| `articles.py` | No changes needed |
| `tags.py`, `tag_rules.py` | Unaffected by provider architecture |

## Recommended Project Structure

```
src/
├── providers/                  # NEW: Provider plugin system
│   ├── __init__.py            # Exports registry, base classes
│   ├── base.py                # ContentProvider abstract class
│   ├── registry.py            # ProviderRegistry
│   ├── rss.py                 # RSS/Atom provider (from feeds.py)
│   └── github.py              # GitHub provider (from github.py)
├── cli.py                     # MODIFY: Use registry for fetch
├── feeds.py                   # MODIFY: Keep minimal, delegate to RSSProvider
├── github.py                  # MODIFY: Keep minimal, delegate to GitHubProvider
├── db.py                      # MODIFY: Add metadata column migration
├── models.py                  # MODIFY: Add Feed.metadata field
├── articles.py                # NO CHANGE
└── ...
```

### Structure Rationale

- **`providers/`:** New directory isolates plugin architecture, making it easy to add new providers
- **`providers/base.py`:** Defines the `ContentProvider` protocol - all providers implement this
- **`providers/registry.py`:** Singleton registry for provider discovery - the "plug" in "plugin"
- **`providers/*.py`:** Each provider in its own file, easy to locate and modify
- **Existing modules (`feeds.py`, `github.py`):** Initially kept as thin wrappers around providers for backward compatibility

## Data Flow with Provider Architecture

### Adding a New Source

```
User: feed add <url>
    │
    ▼
ProviderRegistry.discover(url)
    │
    ├── RSSProvider.can_handle(url) -> True/False
    ├── GitHubProvider.can_handle(url) -> True/False
    │
    ▼
SelectedProvider.add(url, metadata={})
    │
    ▼
Insert into feeds table with metadata
    │
    ▼
Return Feed object
```

### Fetching All Sources

```
User: fetch --all
    │
    ▼
ProviderRegistry.all_providers()
    │
    ▼
for each provider:
    │
    ▼
provider.refresh(feed) for all feeds with that provider_type
    │
    ▼
Aggregate results, report to user
```

### Unified Feed List

```
User: feed list
    │
    ▼
SELECT * FROM feeds
    │
    ▼
For each feed:
    │   Parse metadata JSON
    │   Get provider_type from metadata
    │
    ▼
Display: ID | Name | Provider | URL | Articles | Last Fetched
```

## Migration Strategy

### Phase 1: Introduce Provider Infrastructure (v1.3)

1. Add `providers/` directory with `base.py` and `registry.py`
2. Create `RSSProvider` class (moved from `feeds.py`)
3. Create `GitHubProvider` class (moved from `github.py`)
4. Add `feeds.metadata` column (JSON, nullable)
5. Register both providers in global registry

**Backward compatibility:** Existing `feeds.py` and `github.py` functions still work

### Phase 2: Migrate CLI to Use Registry (v1.4)

1. Modify `fetch --all` to use `ProviderRegistry`
2. Modify `feed add` to use `ProviderRegistry.discover()`
3. Keep `repo add` as alias but internally use registry

**Backward compatibility:** `repo add` still works via GitHub provider

### Phase 3: Deprecate Separate Tables (v1.5+)

1. Add migration script to copy `github_repos` data to `feeds` with metadata
2. Update `github_releases` to link via `feed_id` instead of `repo_id`
3. Eventually drop `github_repos` table

## Anti-Patterns to Avoid

### Anti-Pattern 1: Provider Instantiation Per Call

**What:** Creating new provider instance on each refresh
**Why bad:** Wasteful, breaks any connection-level caching
**Instead:** Providers are singletons in the registry

### Anti-Pattern 2: Provider Knows About Registry

**What:** Provider calling `ProviderRegistry.get()` to delegate
**Why bad:** Circular dependency, tight coupling
**Instead:** Provider only implements `ContentProvider`; registry handles discovery

### Anti-Pattern 3: Metadata as EAV (Entity-Attribute-Value)

**What:** Storing provider data as individual columns like `github_owner`, `github_repo`
**Why bad:** Schema explosion, hard to query
**Instead:** Single JSON `metadata` column with provider-specific keys

### Anti-Pattern 4: Plugin Loading from Filesystem

**What:** Dynamic import of `.py` files from a plugins directory at runtime
**Why bad:** Security risks, import errors, complexity
**Instead:** Use `entry_points` in `pyproject.toml` or simple registry for v1

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Personal use (< 100 feeds) | Single registry, no caching layer needed |
| 100-1000 feeds | Add provider-level result caching (1 hour TTL) |
| 1000+ feeds | Consider async refresh, provider-level parallelism |

### Scaling Priority

1. **First bottleneck:** Sequential refresh taking too long
   - **Fix:** Add `concurrent.futures` ThreadPoolExecutor for parallel refresh
2. **Second bottleneck:** Database writes becoming slow
   - **Fix:** Batch inserts, WAL mode already enabled

## Sources

- [Python pluggy documentation](https://pluggy.readthedocs.io/en/latest/) (plugin system standard)
- [Click plugin pattern](https://click.palletsprojects.com/en/stable/advanced/##plugins) (Click's own plugin recommendation)
- [Python entry_points for plugin discovery](https://packaging.python.org/en/latest/specifications/entry-points/) (official)

---

*Architecture research for: Plugin Provider System*
*Researched: 2026-03-23*
