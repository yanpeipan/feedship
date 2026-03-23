# Phase 12: Provider Core Infrastructure - Research

**Researched:** 2026-03-23
**Domain:** Python Plugin Architecture / Provider Protocol / SQLite Migrations
**Confidence:** HIGH (standard library patterns, well-established)

## Summary

Phase 12 implements the plugin architecture foundation for the RSS reader's provider system. The core challenge is designing a dynamic plugin loading system with error isolation, a Protocol-based interface for providers, and SQLite schema migrations for the `feeds.metadata` field while migrating data from `github_repos`.

Key decisions:
1. Use `@runtime_checkable Protocol` for the `ContentProvider` interface (not ABC) - allows structural typing checks
2. Use `glob.glob()` + `importlib.import_module()` for provider discovery (simple, effective)
3. Provider registration via `PROVIDERS` dict in each module, discovered at import time
4. SQLite migration uses `ALTER TABLE ADD COLUMN` with existence checks (standard pattern)
5. Error isolation via try/except per provider, logging, and continuing to next

**Primary recommendation:** Implement `src/providers/__init__.py` with `ProviderRegistry` singleton that loads providers at import time, sorted by priority. Each provider module registers itself via a `PROVIDERS` dict. The default RSS provider is a fallback (match returns False, priority=0).

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Plugin directory: `src/providers/` and `src/tags/`
- Discovery: `glob()` + dynamic import, alphabetical order
- Rule: Providers must not import each other (avoid circular deps)
- Provider interface: match/priority/crawl/parse/tag_parsers/parse_tags
- Crawl failure: log.error and continue to next provider
- Tag merging: union of all tag parsers, deduplicated
- Default RSS: match() returns False, only used as fallback
- Database: feeds.metadata JSON field for provider-specific data
- github_repos table to be dropped after migration

### Claude's Discretion
- Exact implementation details for Protocol definitions (method signatures, type hints)
- Migration script implementation details
- Error message wording
- Internal module organization within `src/providers/`

### Deferred Ideas (OUT OF SCOPE)
- Async parallel refresh
- External plugin discovery
- Plugin hot-reload
- Per-feed tag rules

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROVIDER-01 | Provider Registry - dynamic load from src/providers/, priority sorted, ProviderRegistry singleton | Section: Dynamic Loading Pattern |
| PROVIDER-02 | Provider Protocol - @runtime_checkable Protocol with match/priority/crawl/parse/tag_parsers/parse_tags | Section: Protocol Implementation |
| PROVIDER-03 | Error Isolation - single provider failure logs error and continues | Section: Error Isolation Pattern |
| PROVIDER-04 | Provider Fallback - default RSS provider (match=False, priority=0) | Section: Default RSS Provider |
| DB-01 | feeds.metadata field - ALTER TABLE ADD COLUMN metadata TEXT | Section: SQLite Migration |
| DB-02 | github_repos data migration to feeds.metadata JSON | Section: Data Migration Strategy |
| DB-03 | github_releases table retained unchanged | Already satisfied - github_releases not touched |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typing.Protocol` | built-in (3.8+) | Runtime-checkable interface | Standard Python for structural typing, preferred over ABC for this use case |
| `importlib.import_module` | built-in | Dynamic module loading | Standard Python module import |
| `glob.glob` | built-in | File discovery | Standard Python pathname expansion |
| `sqlite3` | built-in | Database | Already in use, standard library |
| `logging` | built-in | Error logging | Already in use, standard library |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `feedparser` | 6.0.x | RSS/Atom parsing | RSS Provider crawl/parse |
| `httpx` | 0.27.x | HTTP client | Already in feeds.py, used for fetching |
| `click` | 8.1.x | CLI framework | Already in use for CLI |

**Installation:**
No new packages required. All patterns use Python standard library.

**Version verification:** N/A - all standard library.

## Architecture Patterns

### Recommended Project Structure

```
src/
├── providers/
│   ├── __init__.py          # ProviderRegistry singleton, loads all providers
│   ├── base.py               # Base Protocol definitions (ContentProvider, TagParser)
│   ├── rss_provider.py       # RSS/Atom provider (priority=50)
│   ├── github_provider.py     # GitHub provider (priority=100)
│   └── default_rss_provider.py # Fallback only (match=False, priority=0)
├── tags/
│   ├── __init__.py
│   └── default_tag_parser.py  # AI-powered tagging (Phase 13)
└── (existing modules unchanged)
```

### Pattern 1: ContentProvider Protocol

**What:** A `@runtime_checkable` Protocol defining the provider interface.

**When to use:** For all content providers (RSS, GitHub, etc.)

**Example:**
```python
# src/providers/base.py
from typing import List, Protocol, runtime_checkable

@runtime_checkable
class ContentProvider(Protocol):
    def match(self, url: str) -> bool:
        """Return True if this provider handles the URL."""
        ...

    def priority(self) -> int:
        """Higher = tried first. Default RSS returns 0."""
        ...

    def crawl(self, url: str) -> List["Raw"]:
        """Fetch raw content from URL."""
        ...

    def parse(self, raw: "Raw") -> "Article":
        """Convert Raw to Article."""
        ...

    def tag_parsers(self) -> List["TagParser"]:
        """Return tag parsers for articles from this provider."""
        return []

    def parse_tags(self, article: "Article") -> List["Tag"]:
        """Parse tags for an article."""
        return []
```

**Note on @runtime_checkable:** When using `@runtime_checkable` with Protocol:
- Instance checks like `isinstance(provider, ContentProvider)` become possible
- All methods must be defined (even if returning empty/default values)
- The Protocol methods should NOT raise NotImplementedError in default implementations - they should just return empty values

### Pattern 2: TagParser Protocol

**What:** A Protocol for tag parsing plugins.

**When to use:** For tag parser implementations that can be chained.

**Example:**
```python
# src/providers/base.py
@runtime_checkable
class TagParser(Protocol):
    def parse_tags(self, article: "Article") -> List["Tag"]:
        """Return tags for this article."""
        ...
```

### Pattern 3: Dynamic Provider Loading

**What:** Discover and load providers from `src/providers/` directory at startup.

**When to use:** During application initialization (CLI startup, db init).

**Example:**
```python
# src/providers/__init__.py
import glob
import importlib
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

# Discovered providers, populated at import time
PROVIDERS: List["ContentProvider"] = []

def load_providers() -> None:
    """Load all providers from src/providers/ directory."""
    providers_dir = Path(__file__).parent
    provider_files = sorted(providers_dir.glob("*_provider.py"))

    for filepath in provider_files:
        module_name = filepath.stem  # e.g., "rss_provider"
        full_module = f"src.providers.{module_name}"

        try:
            importlib.import_module(full_module)
            logger.debug("Loaded provider module: %s", full_module)
        except Exception as e:
            logger.error("Failed to load provider %s: %s", full_module, e)

    # Sort providers by priority descending
    PROVIDERS.sort(key=lambda p: p.priority(), reverse=True)

def discover(url: str) -> List["ContentProvider"]:
    """Find providers matching a URL, or return default RSS provider."""
    matched = [p for p in PROVIDERS if p.match(url)]
    if not matched:
        # Return default RSS provider (should be last after sorting)
        matched = [p for p in PROVIDERS if p.__class__.__name__ == "DefaultRSSProvider"]
    return matched

# Load providers at module import
load_providers()
```

### Pattern 4: Provider Self-Registration

**What:** Each provider module registers itself by appending to PROVIDERS list.

**When to use:** In each provider module's initialization.

**Example:**
```python
# src/providers/rss_provider.py
from typing import List
from src.providers.base import ContentProvider, TagParser
# ... imports

class RSSProvider:
    def match(self, url: str) -> bool:
        return url.startswith("http://") or url.startswith("https://")

    def priority(self) -> int:
        return 50

    def crawl(self, url: str) -> List[Raw]:
        # ... existing feeds.py logic
        pass

    def parse(self, raw: Raw) -> Article:
        # ... existing feeds.py logic
        pass

    def tag_parsers(self) -> List[TagParser]:
        return []

    def parse_tags(self, article: Article) -> List[Tag]:
        return []

# Register this provider
from src.providers import PROVIDERS
PROVIDERS.append(RSSProvider())
```

**Anti-pattern to avoid:** Providers should NOT import each other. Shared logic goes in `src/providers/base.py` or `src/plugins/base.py`.

### Pattern 5: Error Isolation Per Provider

**What:** Wrap each provider's crawl/parse in try/except, log error, continue to next.

**When to use:** When iterating over matched providers for a feed.

**Example:**
```python
# In ProviderRegistry or fetch logic
matched_providers = registry.discover(feed.url)

for provider in matched_providers:
    try:
        raws = provider.crawl(feed.url)
    except Exception as e:
        logger.error("Provider %s failed to crawl %s: %s",
                      provider.__class__.__name__, feed.url, e)
        continue  # Try next provider

    try:
        for raw in raws:
            article = provider.parse(raw)
            # ... store article
    except Exception as e:
        logger.error("Provider %s failed to parse %s: %s",
                     provider.__class__.__name__, feed.url, e)
        continue  # Try next provider
```

### Pattern 6: SQLite Column Addition with Existence Check

**What:** Add a column to a table only if it doesn't exist.

**When to use:** During database schema migration.

**Example:**
```python
def migrate_add_metadata_column() -> None:
    """Add metadata TEXT column to feeds table if it doesn't exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Check if column exists
        cursor.execute("PRAGMA table_info(feeds)")
        columns = [row[1] for row in cursor.fetchall()]
        if "metadata" not in columns:
            cursor.execute("ALTER TABLE feeds ADD COLUMN metadata TEXT")
            conn.commit()
            logger.info("Added metadata column to feeds table")
    finally:
        conn.close()
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Interface checking | Custom metaclass or duck typing | `@runtime_checkable Protocol` | Standard, tested, allows `isinstance()` checks |
| Plugin discovery | Custom import hooks | `glob.glob()` + `importlib.import_module()` | Simple, reliable, standard pattern |
| Error isolation | Custom exception handling framework | Simple try/except per provider | Simple is sufficient here |
| Priority sorting | Custom sort key | Built-in `list.sort(key=..., reverse=True)` | Simple and efficient |

**Key insight:** The plugin system requirements are straightforward - no need for complex frameworks like pluggy or stevedore. Standard library is sufficient.

## Runtime State Inventory

> This section is for rename/refactor/migration phases only. Since this is primarily a new code phase (adding provider infrastructure, not renaming existing strings), the runtime state inventory is minimal. However, DB-02 involves data migration.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `github_repos` table: rows with owner/repo/token | DB-02: Migrate to feeds.metadata JSON, then DROP table |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | GITHUB_TOKEN env var (referenced in github.py) | Not changed by this phase |
| Build artifacts | None | None |

**Migration action for DB-02:**
1. Add `metadata` column to `feeds` table (DB-01)
2. For each `github_repos` row with no corresponding `feeds` row: create `feeds` row with `metadata = {"github_token": "...", "repo": "...", "owner": "..."}`
3. For `github_repos` rows with corresponding `feeds` row: update `feeds.metadata` with token info
4. Delete all `github_repos` rows (or DROP table after confirming migration)

## Common Pitfalls

### Pitfall 1: Circular Imports Between Providers

**What goes wrong:** Provider A imports Provider B, Provider B imports Provider A -> ImportError.

**Why it happens:** If providers need to reference each other, or if base.py imports from provider modules.

**How to avoid:**
- Providers must NOT import each other (enforced rule)
- `src/providers/__init__.py` imports provider modules AFTER they define themselves
- Base Protocol definitions in `base.py` should have NO provider-specific imports
- Each provider module imports only from `base.py` and standard library / existing src modules

**Warning signs:** `ImportError` or `AttributeError` during provider loading.

### Pitfall 2: Protocol with NotImplementedError in Default Methods

**What goes wrong:** `isinstance(provider, ContentProvider)` returns False for concrete providers due to `@runtime_checkable` strictness.

**Why it happens:** If a Protocol method raises `NotImplementedError` instead of returning a valid value, the runtime check fails.

**How to avoid:** Default methods should return empty values (empty list, False, etc.) rather than raising exceptions.

**Warning signs:** `isinstance()` checks failing for valid provider instances.

### Pitfall 3: Missing Default RSS Provider in PROVIDERS List

**What goes wrong:** `discover()` returns empty list for unknown URLs -> error instead of fallback.

**Why it happens:** Default RSS provider not loaded or not registered.

**How to avoid:** Ensure default RSS provider is always in PROVIDERS list, loaded last (lowest priority).

**Warning signs:** `discover()` returns empty list for non-RSS URLs.

### Pitfall 4: SQLite ALTER TABLE on Pre-existing Schema

**What goes wrong:** `ALTER TABLE ADD COLUMN` fails if column already exists in some SQLite versions.

**Why it happens:** SQLite doesn't support `IF NOT EXISTS` for `ADD COLUMN` in older versions.

**How to avoid:** Always check `PRAGMA table_info(table_name)` before adding column.

**Warning signs:** `OperationalError: duplicate column name` on fresh install with existing DB.

### Pitfall 5: Forgetting to Sort Providers After Loading

**What goes wrong:** Providers tried in load order (alphabetical) instead of priority order.

**Why it happens:** Forgetting to call `PROVIDERS.sort()` after loading all providers.

**How to avoid:** Sort immediately after all providers loaded in `load_providers()`.

**Warning signs:** Higher priority provider not being tried first.

## Code Examples

### Example 1: ProviderRegistry Singleton

```python
# src/providers/__init__.py (final structure)
import logging
from pathlib import Path
from typing import List, Optional

import importlib

from src.providers.base import ContentProvider

logger = logging.getLogger(__name__)

PROVIDERS: List[ContentProvider] = []


def load_providers() -> None:
    """Load all providers from src/providers/ directory.

    Discovers *_provider.py files, imports each module,
    then sorts providers by priority descending.
    """
    providers_dir = Path(__file__).parent

    # Find all provider modules (exclude __init__ and base)
    provider_files = sorted(providers_dir.glob("*_provider.py"))

    for filepath in provider_files:
        module_name = filepath.stem
        if module_name in ("__init__", "base"):
            continue

        full_module = f"src.providers.{module_name}"
        try:
            importlib.import_module(full_module)
            logger.debug("Loaded provider module: %s", full_module)
        except Exception:
            logger.exception("Failed to load provider %s", full_module)

    # Sort by priority descending (higher priority first)
    PROVIDERS.sort(key=lambda p: p.priority(), reverse=True)
    logger.info("Loaded %d providers", len(PROVIDERS))


def discover(url: str) -> List[ContentProvider]:
    """Find providers matching a URL.

    Args:
        url: URL to match against providers.

    Returns:
        List of matching providers sorted by priority (descending).
        Empty list if no match and no default provider.
    """
    matched = [p for p in PROVIDERS if p.match(url)]
    return matched


def discover_or_default(url: str) -> List[ContentProvider]:
    """Find providers matching a URL, or return default RSS provider.

    Args:
        url: URL to match against providers.

    Returns:
        List with single default RSS provider if no matches.
    """
    matched = discover(url)
    if not matched:
        # Find default RSS provider
        for p in PROVIDERS:
            if p.__class__.__name__ == "DefaultRSSProvider":
                matched = [p]
                break
    return matched


# Load providers at module import
load_providers()
```

### Example 2: Default RSS Provider (Fallback Only)

```python
# src/providers/default_rss_provider.py
"""Default RSS provider - fallback only, never matches directly."""
from typing import List

from src.providers.base import ContentProvider, Raw, Article, Tag, TagParser


class DefaultRSSProvider:
    """Fallback RSS provider for unknown URL types.

    This provider never matches URLs directly (match() returns False).
    It is only used when no other provider matches a URL.
    """

    def match(self, url: str) -> bool:
        """Never matches - only used as fallback."""
        return False

    def priority(self) -> int:
        """Lowest priority - only tried when all else fails."""
        return 0

    def crawl(self, url: str) -> List[Raw]:
        """Not implemented - should not be called."""
        raise NotImplementedError("Default RSS provider is fallback only")

    def parse(self, raw: Raw) -> Article:
        """Not implemented - should not be called."""
        raise NotImplementedError("Default RSS provider is fallback only")

    def tag_parsers(self) -> List[TagParser]:
        return []

    def parse_tags(self, article: Article) -> List[Tag]:
        return []


# Register this provider
from src.providers import PROVIDERS
PROVIDERS.append(DefaultRSSProvider())
```

### Example 3: SQLite Migration for metadata Column

```python
# src/db_migrations.py (new file)
"""Database migrations for v1.3 provider architecture."""

import json
import logging
from typing import Optional

from src.db import get_connection

logger = logging.getLogger(__name__)


def migrate_feeds_metadata_column() -> bool:
    """Add metadata TEXT column to feeds table if it doesn't exist.

    Returns:
        True if column was added or already exists.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(feeds)")
        columns = [row[1] for row in cursor.fetchall()]

        if "metadata" not in columns:
            cursor.execute("ALTER TABLE feeds ADD COLUMN metadata TEXT")
            conn.commit()
            logger.info("Added metadata column to feeds table")
            return True
        else:
            logger.debug("metadata column already exists")
            return True
    finally:
        conn.close()


def migrate_github_repos_to_feeds() -> int:
    """Migrate github_repos data to feeds.metadata JSON.

    For each github_repos row:
    - If corresponding feeds row exists (by owner/repo URL): update feeds.metadata
    - If no corresponding feeds row: create feeds row with metadata

    Returns:
        Number of github_repos rows migrated.
    """
    conn = get_connection()
    migrated = 0

    try:
        cursor = conn.cursor()

        # Get all github_repos rows
        cursor.execute("SELECT * FROM github_repos")
        repos = cursor.fetchall()

        for repo in repos:
            repo_id = repo["id"]
            owner = repo["owner"]
            repo_name = repo["repo"]

            # Build GitHub URL
            github_url = f"https://github.com/{owner}/{repo_name}"

            # Check if feeds row exists for this URL
            cursor.execute("SELECT id, metadata FROM feeds WHERE url = ?", (github_url,))
            existing_feed = cursor.fetchone()

            # Prepare metadata JSON
            metadata = {
                "github_token": repo.get("name"),  # Note: 'name' field stores token per current schema
                "repo": repo_name,
                "owner": owner,
            }

            if existing_feed:
                # Update existing feeds row
                existing_metadata = {}
                if existing_feed["metadata"]:
                    try:
                        existing_metadata = json.loads(existing_feed["metadata"])
                    except json.JSONDecodeError:
                        pass
                existing_metadata.update(metadata)
                cursor.execute(
                    "UPDATE feeds SET metadata = ? WHERE id = ?",
                    (json.dumps(existing_metadata), existing_feed["id"])
                )
            else:
                # Create new feeds row
                import uuid
                from datetime import datetime, timezone
                feed_id = str(uuid.uuid4())
                now = datetime.now(timezone.utc).isoformat()

                cursor.execute(
                    """INSERT INTO feeds (id, name, url, metadata, created_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (feed_id, f"{owner}/{repo_name}", github_url, json.dumps(metadata), now)
                )

            migrated += 1

        conn.commit()
        logger.info("Migrated %d github_repos rows to feeds.metadata", migrated)
        return migrated
    finally:
        conn.close()


def migrate_drop_github_repos() -> bool:
    """Drop github_repos table after successful migration.

    Returns:
        True if table was dropped or didn't exist.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='github_repos'"
        )
        if not cursor.fetchone():
            logger.debug("github_repos table doesn't exist, nothing to drop")
            return True

        cursor.execute("DROP TABLE github_repos")
        conn.commit()
        logger.info("Dropped github_repos table")
        return True
    except Exception:
        logger.exception("Failed to drop github_repos table")
        return False
    finally:
        conn.close()
```

### Example 4: Full Migration Runner

```python
# Migrations should be called during init_db() or a dedicated migration function

def run_v13_migrations() -> None:
    """Run all v1.3 provider architecture migrations."""
    # DB-01: Add metadata column
    migrate_feeds_metadata_column()

    # DB-02: Migrate github_repos data
    migrated_count = migrate_github_repos_to_feeds()
    if migrated_count > 0:
        # DB-03: Drop github_repos table (only after successful migration)
        migrate_drop_github_repos()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| github_repos separate table | Unified feeds table with metadata JSON | Phase 12 | Simpler schema, provider-specific data in one place |
| Hardcoded feed type detection | Dynamic provider discovery via match() | Phase 12 | Extensible, pluggable providers |
| Single provider per feed | Multiple providers per URL (tried by priority) | Phase 12 | Better fallback handling |

**Deprecated/outdated:**
- `github_repos` table: Replaced by `feeds.metadata` JSON (DB-02/DB-03)
- Direct `repo_*` CLI commands: Replaced by unified `feed` commands (Phase 14)

## Open Questions

1. **What is the `name` field in `github_repos` table?**
   - What we know: `github_repos.name` stores some value that becomes `github_token` in metadata
   - What's unclear: Is `name` actually a display name or is it the token? Looking at `add_github_repo()`, `name` is set to `f"{owner}/{repo}"` which is NOT a token.
   - Recommendation: Check actual usage. If `name` is just display name, metadata should store token differently (perhaps from a different source or environment variable).

2. **How to handle existing feeds that came from GitHub blob URLs?**
   - What we know: Some feeds may have GitHub blob URLs (from `add_github_blob_feed`)
   - What's unclear: Should these have metadata indicating they're GitHub-sourced?
   - Recommendation: Add `metadata = {"source": "github_blob", "owner": "...", "repo": "..."}` for these feeds during migration.

3. **Provider discovery order tiebreaking**
   - What we know: Alphabetical order for same-priority providers
   - What's unclear: Is this deterministic enough?
   - Recommendation: Within same priority, sort by class name for consistency.

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified beyond Python standard library)

All requirements for Phase 12 are satisfied by Python 3.13 standard library and existing project dependencies (feedparser, httpx, click, etc. already installed).

## Validation Architecture

> Skip this section since `workflow.nyquist_validation` is explicitly set to `false` in `.planning/config.json`.

## Sources

### Primary (HIGH confidence)
- Python `typing.Protocol` documentation - built-in, stable since 3.8
- Python `importlib` documentation - built-in, stable
- Python `glob` documentation - built-in, stable
- SQLite `ALTER TABLE` documentation - standard SQL, widely supported
- Existing codebase patterns (feeds.py, github.py, db.py) - already in use

### Secondary (MEDIUM confidence)
- N/A for this phase - all standard library patterns

### Tertiary (LOW confidence)
- N/A for this phase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all standard library, well-established patterns
- Architecture: HIGH - straightforward plugin loading, no novel patterns
- Pitfalls: HIGH - common pitfalls with known solutions

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (standard library patterns stable indefinitely)
