# Feature Research: pytest Testing Coverage

**Domain:** Python CLI RSS Reader App Testing
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Core Test Categories)

These are the essential test categories for a CLI RSS reader with SQLite storage and provider plugins. Missing any of these leaves significant coverage gaps.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Storage Layer Tests** | All data operations go through `src/storage/sqlite.py` | MEDIUM | Requires isolated temp DB per test, fixture for common operations |
| **Provider Plugin Tests** | Plugin architecture is core to extensibility | MEDIUM | Mock HTTP responses, test `discover()` and `fetch()` methods |
| **Tag Parser Tests** | Tag system affects article metadata quality | LOW | Pure functions with sample input/output |
| **CLI Command Tests** | User-facing interface must work correctly | MEDIUM | Use Click's `CliRunner` for invocation tests |
| **Integration Tests** | End-to-end workflows must function | MEDIUM | Test `fetch --all` with mocked providers |

### Differentiators (Advanced Testing Patterns)

Features that elevate test quality but are not strictly required.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Async Fetch Tests** | uvloop/httpx async path critical for performance | HIGH | Requires `pytest-asyncio` with proper event loop handling |
| **Provider Priority/Routing Tests** | Plugin routing determines which provider handles each URL | MEDIUM | Test `ProviderRegistry.discover_or_default()` behavior |
| **FTS5 Search Tests** | Full-text search is a key user feature | LOW | Test search queries against known article data |
| **Error Recovery Tests** | Network failures, malformed feeds, DB locked scenarios | MEDIUM | Verify graceful degradation and user-facing errors |
| **Concurrent Fetch Tests** | Semaphore limits concurrent crawls | HIGH | Test concurrency limits and SQLite write serialization |

### Anti-Features (Testing Patterns to Avoid)

| Anti-Pattern | Why Problematic | Alternative |
|--------------|-----------------|-------------|
| **Live network calls in CI** | Flaky, slow, rate-limited | Mock HTTP responses with `responses` or `httpx`'s `AsyncClient` mocking |
| **Shared SQLite DB across tests** | State leakage causes flaky tests | Use `tmp_path` fixture for per-test isolated DB |
| **Testing implementation details** | Brittle, refactoring breaks tests | Test behavior through public interfaces |
| **Mocking everything** | Loses integration value | Reserve mocks for external dependencies (HTTP, GitHub API) |

## Feature Dependencies

```
Storage Tests (tmp_path DB)
    └──requires──> Fixtures for common data (feeds, articles)

Provider Tests
    └──requires──> Mock HTTP responses (RSS XML, HTML pages)
    └──requires──> ProviderRegistry fixture

Tag Parser Tests
    └──requires──> Sample feeds with known tag outcomes

CLI Tests
    └──requires──> CliRunner invocation
    └──requires──> Isolated filesystem (Click's `isolated_filesystem`)
    └──requires──> In-memory or temp DB

Integration Tests (fetch --all)
    └──requires──> All of the above working together
    └──requires──> Async event loop setup (uvloop or standard asyncio)

Async Tests
    └──requires──> pytest-asyncio configuration
    └──requires──> Proper fixture scoping (function vs session)
```

## MVP Definition

### Launch With (v1.7)

Minimum viable test coverage for the milestone to be considered successful.

- [ ] **conftest.py fixtures**: temp DB (`tmp_path`), sample RSS feed data, mock HTTP responses
- [ ] **Storage tests**: `store_article()`, `get_articles()`, `search_articles()`, feed CRUD
- [ ] **Provider tests**: RSSProvider, GitHubProvider, GitHubReleaseProvider with mocked HTTP
- [ ] **Tag parser tests**: DefaultTagParser, ReleaseTagParser with sample inputs
- [ ] **CLI tests**: `feed add`, `feed list`, `article list`, `article detail` using CliRunner

### Add After Validation (v1.8+)

Features to add once basic coverage exists.

- [ ] **Async fetch tests**: Test `fetch --all` with mocked async providers
- [ ] **Error path tests**: Malformed feeds, network timeouts, DB locked scenarios
- [ ] **Provider priority tests**: Registry routing behavior with multiple matching providers
- [ ] **FTS search tests**: Verify search relevance and query handling

### Future Consideration (v2+)

Features to defer until core tests are stable.

- [ ] **Concurrent fetch stress tests**: Verify Semaphore limits under load
- [ ] **Performance benchmarks**: Track test execution time as a metric
- [ ] **Coverage targets**: Enforce minimum coverage percentages via tooling

## Test Categories Breakdown

### 1. Unit Tests (Pure Functions)

**Complexity:** LOW

| Module | What to Test | Approach |
|--------|--------------|----------|
| `src/tags/default_tag_parser.py` | Tag extraction from text | Sample inputs with expected outputs |
| `src/tags/release_tag_parser.py` | Semantic version parsing | Known version strings with expected tags |
| `src/tags/tag_rules.py` | Rule-based tag matching | Sample rules with test inputs |
| `src/storage/sqlite.py` | Individual functions | Isolated DB, single operation per test |

**Example test:**
```python
def test_default_tag_parser_extracts_keywords():
    parser = DefaultTagParser()
    result = parser.parse("Python 3.12 released with performance improvements")
    assert "python" in result
    assert "release" in result
```

### 2. Storage Layer Tests (SQLite Operations)

**Complexity:** MEDIUM

| Operation | What to Test |
|-----------|--------------|
| `store_feed()` | Insert feed, verify retrieval, handle duplicates |
| `store_article()` | Insert article, verify with different ID generators |
| `get_articles()` | Filtering by feed, pagination, ordering |
| `search_articles()` | FTS5 query matching, relevance ordering |
| `update_feed_metadata()` | Update fields, verify persistence |

**Key fixtures:**
- `empty_db` - Fresh DB for each test
- `db_with_feeds` - Pre-populated with sample feeds
- `db_with_articles` - Pre-populated with sample articles

**Example test:**
```python
def test_store_article_with_nanoid(db_with_feeds, sample_article_data):
    article_id = store_article(db_with_feeds, sample_article_data)
    assert len(article_id) == 21  # nanoid default length
    assert article_id.isalnum() or '-' in article_id  # URL-safe
```

### 3. Provider Tests (Plugin Architecture)

**Complexity:** MEDIUM

| Provider | What to Test | Mock Strategy |
|----------|--------------|---------------|
| `RSSProvider` | Parses RSS/Atom, returns articles | Mock httpx response with sample RSS XML |
| `GitHubProvider` | GitHub repo URL handling, API calls | Mock PyGithub responses |
| `GitHubReleaseProvider` | Release extraction, version parsing | Mock PyGithub release data |
| `DefaultProvider` | Fallback HTML scraping | Mock httpx response with HTML |

**Key fixtures:**
- `rss_feed_xml` - Sample RSS 2.0 and Atom 1.0 feeds
- `github_release_data` - Sample GitHub API responses
- `html_page_content` - Sample HTML for scraping

**Example test:**
```python
@responses.activate
def test_rss_provider_discovers_articles(sample_rss_feed):
    responses.add(responses.GET, 'https://example.com/feed.xml',
                  body=sample_rss_feed, status=200)
    provider = RSSProvider()
    articles = provider.discover('https://example.com/feed.xml')
    assert len(articles) > 0
    assert articles[0].title is not None
```

### 4. CLI Tests (Click Commands)

**Complexity:** MEDIUM

| Command | What to Test |
|---------|--------------|
| `feed add <url>` | Success, invalid URL, duplicate feed |
| `feed list` | Empty state, populated list, formatting |
| `article list` | Filters, pagination, search integration |
| `article detail <id>` | Found, not found, formatting |
| `fetch --all` | With mocked providers, concurrency handling |
| `tag <article_id> <tags>` | Success, invalid article |

**Key fixtures:**
- `cli_runner` - CliRunner instance
- `isolated_db` - DB isolated via tmp_path + CliRunner's filesystem
- `populated_db` - DB with sample data for list/detail tests

**Example test:**
```python
def test_feed_list_empty(cli_runner, empty_db):
    result = cli_runner.invoke(feed_list, [], obj={'db_path': empty_db})
    assert result.exit_code == 0
    assert 'No feeds found' in result.output
```

### 5. Integration Tests (End-to-End)

**Complexity:** MEDIUM-HIGH

| Workflow | What to Test |
|----------|--------------|
| `feed add` then `fetch --all` | Full add-and-fetch cycle |
| `article list` then `article detail` | List navigation |
| Search then tag | Search -> detail -> tag chain |
| `fetch --all` with concurrency | Multiple feeds fetched in parallel |

**Key fixtures:**
- `integration_env` - Full app environment with temp DB
- `mocked_providers` - All HTTP calls mocked

## Fixture Design

### conftest.py Structure

```python
# conftest.py - Root fixtures
import pytest
from click.testing import CliRunner

@pytest.fixture
def cli_runner():
    return CliRunner()

@pytest.fixture
def sample_rss_feed():
    """Valid RSS 2.0 feed XML string"""

@pytest.fixture
def sample_atom_feed():
    """Valid Atom 1.0 feed XML string"""

@pytest.fixture
def sample_github_release():
    """PyGithub Release object fixture"""

@pytest.fixture
def empty_db(tmp_path):
    """Fresh SQLite DB path per test"""
    db_path = tmp_path / "test.db"
    # Initialize schema
    yield str(db_path)
```

### Scoping Strategy

| Fixture | Scope | Reason |
|---------|-------|--------|
| `cli_runner` | function | Not thread-safe |
| `empty_db` | function | Per-test isolation |
| `sample_rss_feed` | session | Static data, no mutation |
| `mocked_providers` | function | May have state |

## Testing Tooling

### Required Packages

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | 8.x | Test framework |
| `pytest-asyncio` | 0.23.x | Async test support |
| `responses` | 0.25.x | Sync HTTP mocking |
| `pytest-httpx` | 0.30.x | Async HTTP mocking alternative |
| `pytest-cov` | 5.x | Coverage reporting |

### Optional (Future)

| Package | Purpose |
|---------|---------|
| `pytest-xdist` | Parallel test execution |
| `faker` | Generate test data |
| `freezegun` | Time-based testing |

## Sources

- [Click Testing Documentation](https://click.palletsprojects.com/en/8.1.x/testing/) (HIGH confidence)
- [Pytest Fixtures Best Practices](https://docs.pytest.org/en/stable/explanation/fixtures.html) (HIGH confidence)
- [Pytest Monkeypatching](https://docs.pytest.org/en/stable/how-to/monkeypatch.html) (HIGH confidence)
- [Pytest tmp_path for Temp Directories](https://docs.pytest.org/en/stable/how-to/tmp_path.html) (HIGH confidence)

---

*Feature research for: pytest testing coverage*
*Researched: 2026-03-25*
