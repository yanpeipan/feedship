# Architecture Research: pytest Test Organization

**Domain:** Python CLI Application Testing (RSS Reader)
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH (based on established pytest patterns and project structure analysis)

## Executive Summary

This project uses a Python CLI application with Click framework, SQLite storage, and a Provider plugin architecture. The existing tests are minimal (4 test files with basic fixtures). The v1.7 milestone requires expanding to cover Providers, Storage layer, and CLI integration tests.

The recommended approach is:
- **Single root conftest.py** for project-wide fixtures (database, temp files)
- **Flat test file structure** mirroring `src/` modules: `test_providers.py`, `test_storage.py`, `test_cli.py`
- **Fixture scope decisions** based on resource cost and isolation needs
- **Click CliRunner** for CLI integration testing

## Standard pytest Project Structure

### Recommended Directory Layout

```
tests/
├── __init__.py              # Makes tests a package
├── conftest.py              # Root fixtures: temp_db, sample_feed, sample_article, cli_runner
├── test_fetch.py            # Existing: async fetch tests
├── test_config.py           # Existing: config tests
├── test_ai_tagging.py       # Existing: AI tagging tests
├── test_providers.py        # NEW: Provider plugin tests (RSSProvider, GitHubReleaseProvider)
├── test_storage.py          # NEW: SQLite storage layer tests
└── test_cli.py              # NEW: CLI command integration tests
```

### Alternative Considered: Per-Module Conftest

```
tests/
├── conftest.py              # Common fixtures (temp_db, sample_article)
├── providers/
│   ├── conftest.py          # Provider-specific fixtures
│   └── test_rss_provider.py
├── storage/
│   ├── conftest.py          # Storage-specific fixtures
│   └── test_sqlite.py
└── cli/
    ├── conftest.py          # CLI-specific fixtures
    └── test_commands.py
```

**Why NOT this approach** for this project:
- Adds unnecessary nesting for a project with ~10 source modules
- Session-scoped fixtures (like temp_db) cannot be easily shared across nested conftest.py files
- Increases complexity without proportional benefit for a personal CLI tool

## Recommended Fixtures

### Root conftest.py Fixtures

```python
"""Root pytest fixtures for radar tests."""
import pytest
import tempfile
import os
from pathlib import Path

# --- Database Fixtures ---

@pytest.fixture(scope="session")
def temp_db_path():
    """Session-scoped temp database path (shared across all tests in session)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    os.unlink(db_path)


@pytest.fixture(scope="function")
def temp_db(temp_db_path):
    """Function-scoped database connection pointing to temp path.

    Tests should patch src.storage.sqlite.get_db_path() to return this path.
    """
    # Patch the module-level _DB_PATH or use monkeypatch
    pass


@pytest.fixture(scope="function")
def initialized_db(temp_db_path):
    """Database that has been initialized with schema (tables created)."""
    from src.storage.sqlite import init_db, _get_connection
    # Override get_db_path temporarily and init
    import src.storage.sqlite as storage_module
    original_path = storage_module._DB_PATH
    storage_module._DB_PATH = Path(temp_db_path)
    init_db()
    yield temp_db_path
    storage_module._DB_PATH = original_path


# --- Sample Data Fixtures ---

@pytest.fixture
def sample_feed():
    """Sample feed for testing."""
    from src.models import Feed
    return Feed(
        id="test-feed-1",
        name="Test Feed",
        url="https://example.com/feed.xml",
        etag=None,
        last_modified=None,
        last_fetched=None,
        created_at="2024-01-01T00:00:00+00:00",
    )


@pytest.fixture
def sample_article():
    """Sample article data for testing."""
    return {
        "id": "test-article-1",
        "title": "Test Article Title",
        "url": "https://example.com/article",
        "description": "This is a test article description",
        "content": "<p>Full article content here</p>",
        "source": "test",
        "pub_date": "2024-01-15T10:30:00+08:00",
    }


# --- CLI Fixtures ---

@pytest.fixture
def cli_runner():
    """Click CliRunner for testing CLI commands."""
    from click.testing import CliRunner
    return CliRunner()


@pytest.fixture
def isolated_cli_env(cli_runner):
    """CliRunner with isolated filesystem (for testing file operations)."""
    return CliRunner(mix_stderr=False, isolate_internationalization=True)
```

### Fixture Scope Decisions

| Fixture | Scope | Rationale |
|---------|-------|-----------|
| `temp_db_path` | session | Expensive to create (file I/O), safe to share |
| `initialized_db` | function | Tests may modify schema/data, need isolation |
| `sample_feed` | function | Stateless, cheap to create |
| `sample_article` | function | Stateless, cheap to create |
| `cli_runner` | session | CliRunner is stateless, reusable |
| `isolated_cli_env` | function | Filesystem isolation per test |

## Test File Organization

### test_providers.py

Tests for `src/providers/` module:
- RSSProvider.match() URL matching
- RSSProvider.crawl() and crawl_async() with mocked httpx
- GitHubReleaseProvider.match() and priority ordering
- ProviderRegistry.discover() and discover_or_default()
- TagParser chain integration

```python
"""Tests for Provider plugin architecture."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.providers import discover, discover_or_default, get_all_providers


class TestProviderDiscovery:
    """Test provider URL matching and discovery."""

    def test_rss_provider_matches_feed_url(self):
        """RSS provider should match RSS feed URLs."""
        from src.providers.rss_provider import RSSProvider
        provider = RSSProvider()
        assert provider.match("https://example.com/feed.xml")

    def test_github_release_provider_matches_github_releases(self):
        """GitHubReleaseProvider should match github.com/*/releases URLs."""
        from src.providers.github_release_provider import GitHubReleaseProvider
        provider = GitHubReleaseProvider()
        assert provider.match("https://github.com/example/repo/releases")

    def test_discover_returns_matching_providers(self):
        """discover() returns providers sorted by priority."""
        providers = discover("https://github.com/example/repo/releases")
        assert len(providers) >= 1
        # GitHubReleaseProvider (priority 200) should be first
        assert providers[0].priority() >= 200

    def test_discover_or_default_falls_back_to_rss(self):
        """Unknown URL falls back to RSS provider."""
        providers = discover_or_default("https://unknown-site.com/feed")
        assert len(providers) == 1
        assert providers[0].__class__.__name__ == "RSSProvider"
```

### test_storage.py

Tests for `src/storage/sqlite.py`:
- init_db() creates correct schema
- store_article() inserts and updates
- list_articles(), search_articles() queries
- Tag operations (add_tag, tag_article, etc.)
- Feed operations (add_feed, list_feeds, etc.)

```python
"""Tests for SQLite storage layer."""
import pytest
from src.storage.sqlite import (
    init_db, store_article, list_articles, add_feed, list_feeds,
    tag_article, get_article_tags
)


@pytest.fixture
def storage_db(initialized_db):
    """Initialized database for storage tests."""
    return initialized_db


class TestArticleStorage:
    """Test article CRUD operations."""

    def test_store_article_inserts_new(self, storage_db):
        """store_article creates new article with generated ID."""
        article_id = store_article(
            guid="test-guid-1",
            title="Test Title",
            content="Test content",
            link="https://example.com/article1",
            feed_id="test-feed",
        )
        assert article_id is not None
        assert len(article_id) > 0

    def test_store_article_updates_existing_by_guid(self, storage_db):
        """store_article with existing guid updates rather than inserts."""
        # Insert first
        id1 = store_article(
            guid="same-guid",
            title="Original Title",
            content="Original content",
            link="https://example.com/original",
            feed_id="test-feed",
        )
        # Same guid should return same ID
        id2 = store_article(
            guid="same-guid",
            title="Updated Title",
            content="Updated content",
            link="https://example.com/updated",
            feed_id="test-feed",
        )
        assert id1 == id2


class TestFeedStorage:
    """Test feed operations."""

    def test_add_and_list_feeds(self, storage_db, sample_feed):
        """Feeds can be added and listed."""
        added = add_feed(sample_feed)
        feeds = list_feeds()
        assert len(feeds) == 1
        assert feeds[0].name == "Test Feed"
```

### test_cli.py

Integration tests for CLI commands using Click CliRunner:
- feed add/list/remove commands
- article list/detail/search commands
- tag add/list commands
- fetch --all command

```python
"""Integration tests for CLI commands."""
import pytest
from click.testing import CliRunner
from src.cli import cli


@pytest.fixture
def cli_runner():
    return CliRunner(mix_stderr=False)


@pytest.fixture
def invoke(cli_runner):
    """Helper to invoke CLI commands."""
    def _invoke(*args, **kwargs):
        return cli_runner.invoke(cli, args, **kwargs)
    return _invoke


class TestFeedCommands:
    """Test feed management commands."""

    def test_feed_list_empty(self, invoke):
        """feed list shows no feeds initially."""
        result = invoke("feed", "list")
        assert result.exit_code == 0
        # May show empty state message

    def test_feed_add_rss(self, invoke):
        """feed add accepts RSS URL."""
        result = invoke("feed", "add", "https://example.com/feed.xml")
        assert result.exit_code == 0


class TestArticleCommands:
    """Test article display commands."""

    def test_article_list(self, invoke):
        """article list shows articles."""
        result = invoke("article", "list")
        assert result.exit_code == 0

    def test_article_list_with_limit(self, invoke):
        """article list accepts --limit flag."""
        result = invoke("article", "list", "--limit", "5")
        assert result.exit_code == 0
```

## Module-Specific conftest.py (Optional Enhancement)

For larger projects, a conftest.py per source module provides better organization:

```
tests/
├── conftest.py                    # Common fixtures only
├── test_providers.py
├── providers/
│   ├── conftest.py                # RSS feed samples, mock httpx client
│   └── test_rss_provider.py
├── storage/
│   ├── conftest.py                # DB fixtures with schema
│   └── test_sqlite.py
└── cli/
    ├── conftest.py                # CliRunner fixture
    └── test_article.py
```

**Rule:** Fixtures that are ONLY used by one module's tests belong in that module's conftest.py.

## Test Categorization

### Unit Tests (fast, no I/O)
- Provider.match() logic
- Storage function logic (string manipulation, query building)
- Tag parser chain
- Data model validation

### Integration Tests (slower, with I/O)
- CLI command execution (uses CliRunner but still exercises real code paths)
- Database operations (even with temp DB, still I/O)
- Provider crawl() with mocked HTTP responses

### Async Tests
- Use `@pytest.mark.asyncio` for async test functions
- Existing `test_fetch.py` shows the pattern with `AsyncMock` and `patch`
- For true async tests, use `pytest-asyncio` plugin

## Anti-Patterns to Avoid

### Anti-Pattern 1: Global State in Fixtures

**Bad:**
```python
# conftest.py
db_connection = None  # Shared mutable state!

@pytest.fixture
def temp_db():
    global db_connection
    db_connection = create_db()
    yield db_connection
    db_connection.close()
```

**Why bad:** Tests can pollute each other's state, causing flaky tests.

**Good:** Use function-scoped fixtures with explicit setup/teardown.

### Anti-Pattern 2: Importing Application Code in conftest

**Bad:**
```python
# conftest.py
from src.storage.sqlite import init_db  # Init at import time!
init_db()
```

**Why bad:** Initializes production database or creates side effects at test collection time.

**Good:** Initialize fixtures inside the fixture function, not at module level.

### Anti-Pattern 3: Testing Implementation Details

**Bad:**
```python
def test_provider_uses_correct_regex():
    # Testing internal _url_pattern attribute
    assert provider._url_pattern.match("...")
```

**Why bad:** Refactoring internal implementation breaks tests.

**Good:** Test public behavior (match() returns correct bool for given URLs).

## CLI Testing with Click

### CliRunner Best Practices

```python
from click.testing import CliRunner

@pytest.fixture
def cli_runner():
    return CliRunner(mix_stderr=False)


def test_cli_with_isolated_filesystem(cli_runner):
    """Use CliRunner's isolated filesystem for file operations."""
    with cli_runner.isolated_filesystem():
        result = cli_runner.invoke(cli, ["feed", "export", "OPML"])
        assert result.exit_code == 0
```

### Testing Async CLI Commands

For `fetch --all` which uses uvloop.run():
```python
@pytest.mark.asyncio
async def test_fetch_all_cli():
    """Test fetch --all command."""
    with patch("src.application.fetch.storage_list_feeds", return_value=[]):
        result = cli_runner.invoke(cli, ["fetch", "--all"])
        assert result.exit_code == 0
```

## Sources

- [pytest Documentation: Fixtures](https://docs.pytest.org/en/latest/reference/fixtures.html) (HIGH)
- [pytest Documentation: Writing hooks](https://docs.pytest.org/en/latest/reference/reference.html#hooks) (HIGH)
- [Click Documentation: Testing Cli](https://click.palletsprojects.com/en/latest/testing/) (HIGH)
- [Python Testing with pytest: fixtures and scopes](https://docs.pytest.org/en/latest/how-to/fixtures.html#scope-sharing-fixtures) (MEDIUM)

---

*Architecture research for: pytest test organization*
*Researched: 2026-03-25*
