# Stack Research: pytest Testing Framework

**Domain:** Python CLI Testing Framework
**Project:** 个人资讯系统 (RSS reader CLI with async, SQLite, Click)
**Researched:** 2026-03-25
**Confidence:** HIGH

## Recommended Stack

### Core Testing Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **pytest** | 9.0.2 | Test framework | De facto standard for Python testing. Auto-discovery, rich assertion introspection, fixture system. Python 3.10+ required. |
| **pytest-asyncio** | 1.3.0 | Async code testing | Required for testing `fetch.py`, `asyncio_utils.py`, and async provider methods. Supports `asyncio_mode = "auto"` for asyncio-only projects. |
| **pytest-cov** | 7.1.0 | Code coverage | Integrates with pytest for `--cov` reporting. Essential for TEST-01 coverage goals. |
| **pytest-mock** | 3.15.1 | Mocking/patching | Provides `mocker` fixture with automatic cleanup. Better than raw `unittest.mock` for pytest integration. |
| **pytest-click** | 1.1.0 | CLI testing | Provides `cli_runner` fixture for Click's CliRunner. Stable, covers TEST-04 CLI integration testing needs. |
| **pytest-httpx** | 0.36.0 | HTTP mocking | Provides `httpx_mock` fixture to mock httpx requests. Critical for provider tests without network calls. |
| **pytest-xdist** | 3.8.0 | Parallel execution | Enables `pytest -n auto` for faster test runs. Useful as project grows. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **pytest-asyncio** | 1.3.0 | Async fixtures | For fixtures that need `async def` (e.g., async DB setup) |
| **pytest-timeout** | (latest) | Test timeout | Prevent hung tests. Add `pytest --timeout=30` or per-test `@pytest.mark.timeout(30)` |
| **pytest-xvfb** | (latest) | X display | Only if GUI testing needed (not required for this CLI-only project) |

## Installation

```bash
# Core testing dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-click pytest-httpx pytest-xdist

# Or as dev dependencies (if using requirements-dev.txt)
pip install -r requirements-dev.txt
```

**requirements-dev.txt content:**
```
pytest==9.0.2
pytest-asyncio==1.3.0
pytest-cov==7.1.0
pytest-mock==3.15.1
pytest-click==1.1.0
pytest-httpx==0.36.0
pytest-xdist==3.8.0
```

## Recommended Project Structure

```
tests/
├── conftest.py                 # Root fixtures (temp DB, app config)
├── unit/
│   ├── conftest.py           # Unit-specific fixtures
│   ├── test_providers/
│   │   ├── conftest.py       # Provider fixtures
│   │   ├── test_rss_provider.py
│   │   ├── test_github_release_provider.py
│   │   └── test_provider_registry.py
│   ├── test_storage/
│   │   ├── conftest.py       # Storage fixtures
│   │   └── test_sqlite.py
│   └── test_tag_parsers.py
└── integration/
    ├── conftest.py           # Integration fixtures
    └── test_cli/
        ├── conftest.py       # CLI runner fixtures
        ├── test_feed.py
        ├── test_article.py
        └── test_tag.py
```

## conftest.py Design

### Root conftest.py (tests/conftest.py)

```python
# tests/conftest.py
import pytest
import tempfile
import os
from pathlib import Path

@pytest.fixture(scope="session")
def temp_db_path():
    """Create a temporary database file for the test session."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)
    # Also clean up WAL files
    wal_path = db_path + "-wal"
    shm_path = db_path + "-shm"
    if os.path.exists(wal_path):
        os.unlink(wal_path)
    if os.path.exists(shm_path):
        os.unlink(shm_path)

@pytest.fixture(scope="function")
def mock_db(temp_db_path, monkeypatch):
    """Patch storage to use temp DB path for each test."""
    # Patch platformdirs to return temp location
    import platformdirs
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda *args, **kwargs: str(Path(temp_db_path).parent))
```

### Provider conftest.py (tests/unit/test_providers/conftest.py)

```python
# tests/unit/test_providers/conftest.py
import pytest
from unittest.mock import Mock, MagicMock
from src.providers.base import ContentProvider, Article, Raw

@pytest.fixture
def mock_provider():
    """Create a mock ContentProvider for testing."""
    provider = Mock(spec=ContentProvider)
    provider.match.return_value = True
    provider.priority.return_value = 50
    return provider

@pytest.fixture
def sample_raw_feed_entry():
    """Sample feedparser entry dict."""
    return {
        "title": "Test Article",
        "link": "https://example.com/article",
        "id": "https://example.com/article#1",
        "published": "2026-03-25T10:00:00Z",
        "summary": "Test description",
    }

@pytest.fixture
def sample_article():
    """Sample Article dict from provider.parse()."""
    return Article(
        title="Test Article",
        link="https://example.com/article",
        guid="https://example.com/article#1",
        pub_date="2026-03-25T10:00:00Z",
        description="Test description",
        content="<p>Full content</p>",
    )
```

### CLI conftest.py (tests/integration/test_cli/conftest.py)

```python
# tests/integration/test_cli/conftest.py
import pytest
from click.testing import CliRunner
from src.cli import cli

@pytest.fixture
def cli_runner():
    """Provide a CliRunner for CLI tests."""
    return CliRunner()

@pytest.fixture
def isolated_cli_runner(cli_runner):
    """Provide a CliRunner with isolated filesystem."""
    return cli_runner.isolated_filesystem()

@pytest.fixture
def invoke_cli(cli_runner):
    """Factory fixture to invoke CLI commands."""
    def _invoke(command, *args, **kwargs):
        return cli_runner.invoke(cli, [command] + list(args), **kwargs)
    return _invoke
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Test Framework | pytest | unittest, nose2 | pytest has better fixtures, auto-discovery, assertion introspection |
| Async Testing | pytest-asyncio | anyio | pytest-asyncio is the standard for pytest projects; anyio is for anyio-based projects |
| Mocking | pytest-mock | unittest.mock directly | pytest-mock provides pytest-integrated `mocker` fixture with auto-cleanup |
| HTTP Mocking | pytest-httpx | responses, requests-mock | pytest-httpx is designed for httpx specifically (used by this project) |
| CLI Testing | pytest-click | raw CliRunner | pytest-click provides `cli_runner` fixture; CliRunner is from Click itself |
| Coverage | pytest-cov | coverage.py CLI | pytest-cov integrates coverage with pytest's `-v` output |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **unittest** | Verbose, no fixtures, no auto-discovery | pytest |
| **nose2** | In maintenance mode, less community support | pytest |
| **pytest-django** | This project uses SQLite, not Django | N/A - not needed |
| **factory_boy** | Overkill for SQLite testing | Simple fixtures with `tempfile` |
| **hypothesis** | Property-based testing adds complexity | Traditional unit tests sufficient for MVP |
| **selenium** | Browser automation for web apps | This is a CLI tool; CliRunner suffices |
| **pytest-bdd** | Gherkin syntax adds overhead | Standard pytest for now |

## Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
minversion = "9.0"
testpaths = ["tests"]
asyncio_mode = "auto"           # For asyncio-only project
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
]
markers = [
    "asyncio: mark test as async",
    "integration: integration test requiring full app",
    "slow: tests that take significant time",
]
filterwarnings = [
    "ignore::DeprecationWarning",
]
```

## Key Integration Points

### 1. Async Testing with uvloop

The project uses `uvloop.install()` at CLI startup. For testing, pytest-asyncio handles event loop management:

```python
# In pytest-asyncio auto mode (configured above), this works automatically:
@pytest.mark.asyncio
async def test_fetch_one_async():
    result = await fetch_one_async(feed)
    assert result["new_articles"] >= 0
```

**Important:** `asyncio_mode = "auto"` automatically marks all async functions with `@pytest.mark.asyncio`.

### 2. SQLite Testing

The storage layer uses module-level `get_db()` context manager. Tests should:

```python
def test_store_article(temp_db_path, monkeypatch):
    # Patch the DB path before importing storage
    import src.storage.sqlite as sqlite_module
    monkeypatch.setattr(sqlite_module, "_DB_PATH", Path(temp_db_path))

    # Now init and test
    from src.storage.sqlite import init_db, store_article
    init_db()
    article_id = store_article(guid="test", title="Test", content="...", link="...")
    assert article_id is not None
```

### 3. HTTP Request Mocking

```python
def test_rss_provider_crawl(httpx_mock):
    # Register a mock response
    httpx_mock.add_response(
        url="https://example.com/feed.xml",
        content=b"""<?xml version="1.0"?>
        <rss><channel><item><title>Test</title><link>https://example.com</link></item></channel></rss>""",
        headers={"content-type": "application/rss+xml"}
    )

    provider = RSSProvider()
    entries = provider.crawl("https://example.com/feed.xml")
    assert len(entries) == 1
    assert entries[0]["title"] == "Test"
```

### 4. Provider Protocol Testing

The project uses `@runtime_checkable` protocols. Test protocol conformance:

```python
def test_rss_provider_is_content_provider():
    from src.providers.rss_provider import RSSProvider
    from src.providers.base import ContentProvider

    provider = RSSProvider()
    assert isinstance(provider, ContentProvider)  # @runtime_checkable allows this
```

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| pytest | 9.0.2 | Python 3.10+ | Requires Python >= 3.10 |
| pytest-asyncio | 1.3.0 | pytest >= 7.0 | Use `asyncio_mode = "auto"` for asyncio-only projects |
| pytest-cov | 7.1.0 | pytest >= 7.0 | Works with pytest-asyncio |
| pytest-mock | 3.15.1 | All pytest versions | Thin wrapper around unittest.mock |
| pytest-click | 1.1.0 | Click >= 7.0 | Last updated 2022, but stable |
| pytest-httpx | 0.36.0 | pytest >= 7.0 | Requires httpx >= 0.25 |

## Sources

- [pytest 9.0.2 - PyPI](https://pypi.org/project/pytest/9.0.2/) — HIGH confidence
- [pytest-asyncio 1.3.0 - PyPI](https://pypi.org/project/pytest-asyncio/1.3.0/) — HIGH confidence
- [pytest-cov 7.1.0 - PyPI](https://pypi.org/project/pytest-cov/7.1.0/) — HIGH confidence
- [pytest-mock 3.15.1 - PyPI](https://pypi.org/project/pytest-mock/3.15.1/) — HIGH confidence
- [pytest-click 1.1.0 - PyPI](https://pypi.org/project/pytest-click/1.1.0/) — HIGH confidence
- [pytest-httpx 0.36.0 - PyPI](https://pypi.org/project/pytest-httpx/0.36.0/) — HIGH confidence
- [pytest-xdist 3.8.0 - PyPI](https://pypi.org/project/pytest-xdist/3.8.0/) — HIGH confidence
- [Click Testing Documentation](https://click.palletsprojects.com/en/stable/testing/) — HIGH confidence
- [pytest-asyncio Auto Mode](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html) — HIGH confidence

---

*Stack research for: pytest testing framework*
*Researched: 2026-03-25*
