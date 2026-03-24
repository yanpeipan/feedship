---
phase: 26-pytest
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - tests/conftest.py
autonomous: true
requirements:
  - TEST-01

must_haves:
  truths:
    - "pytest 9.0.2+ installed with all required plugins"
    - "asyncio_mode = 'auto' configured in pyproject.toml"
    - "tests/conftest.py has all required fixtures: temp_db_path, initialized_db, sample_feed, sample_article, cli_runner"
    - "Test conventions established: no private function testing, real DB via tmp_path"
  artifacts:
    - path: "pyproject.toml"
      provides: "pytest configuration and dependencies"
      contains: "pytest>=9.0.2, pytest-asyncio, pytest-cov, pytest-mock, pytest-click, pytest-httpx"
    - path: "tests/conftest.py"
      provides: "Root fixtures for all tests"
      contains: "temp_db_path, initialized_db, sample_feed, sample_article, cli_runner"
  key_links:
    - from: "tests/conftest.py"
      to: "src/storage/sqlite.py"
      via: "imports init_db for initialized_db fixture"
    - from: "tests/conftest.py"
      to: "src/models.py"
      via: "imports Feed, Article dataclasses for sample_feed fixture"
    - from: "tests/conftest.py"
      to: "click.testing"
      via: "CliRunner for cli_runner fixture"
---

<objective>
Set up pytest testing framework with all required fixtures and configuration.

Purpose: Foundation for v1.7 milestone - enable comprehensive testing of providers, storage, and CLI.
Output: Configured pyproject.toml with pytest plugins, expanded tests/conftest.py with all required fixtures.
</objective>

<execution_context>
@/Users/y3/radar/.claude/get-shit-done/workflows/execute-plan.md
@/Users/y3/radar/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@pyproject.toml
@tests/conftest.py
@src/storage/sqlite.py
@src/models.py

# Stack research findings
pytest==9.0.2 with plugins installed via pyproject.toml
asyncio_mode = "auto" for async test support
tmp_path fixture for per-test isolated database
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update pyproject.toml with pytest packages and asyncio_mode config</name>
  <files>pyproject.toml</files>
  <read_first>pyproject.toml</read_first>
  <action>
    Update the [project.optional-dependencies] test section to include all required packages with exact versions:

    ```toml
    [project.optional-dependencies]
    test = [
        "pytest>=9.0.2",
        "pytest-asyncio>=1.0.0",
        "pytest-cov>=7.0.0",
        "pytest-mock>=3.15.0",
        "pytest-click>=1.1.0",
        "pytest-httpx>=0.36.0",
        "pytest-xdist>=3.8.0",
    ]
    ```

    Add a new [tool.pytest.ini_options] section at the end of pyproject.toml:

    ```toml
    [tool.pytest.ini_options]
    minversion = "9.0"
    testpaths = ["tests"]
    asyncio_mode = "auto"
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
  </action>
  <verify>
    <automated>grep -A 8 '\[tool\.pytest\.ini_options\]' pyproject.toml && grep -E 'pytest-(asyncio|cov|mock|click|httpx|xdist)' pyproject.toml</automated>
  </verify>
  <done>pyproject.toml has pytest>=9.0.2, pytest-asyncio, pytest-cov, pytest-mock, pytest-click, pytest-httpx, pytest-xdist in test dependencies, and asyncio_mode = "auto" configured in [tool.pytest.ini_options]</done>
  <acceptance_criteria>
    - grep "pytest>=9.0.2" pyproject.toml returns 1 line
    - grep "pytest-asyncio>=1.0.0" pyproject.toml returns 1 line
    - grep "pytest-cov>=7.0.0" pyproject.toml returns 1 line
    - grep "pytest-mock>=3.15.0" pyproject.toml returns 1 line
    - grep "pytest-click>=1.1.0" pyproject.toml returns 1 line
    - grep "pytest-httpx>=0.36.0" pyproject.toml returns 1 line
    - grep 'asyncio_mode = "auto"' pyproject.toml returns 1 line
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Expand tests/conftest.py with all required fixtures</name>
  <files>tests/conftest.py</files>
  <read_first>tests/conftest.py</read_first>
  <action>
    Replace the content of tests/conftest.py with the following, which adds the missing fixtures while keeping the existing sample_article:

    ```python
    """Pytest fixtures for radar tests."""
    import pytest
    import tempfile
    import os
    from pathlib import Path
    from click.testing import CliRunner

    # --- Database Fixtures ---

    @pytest.fixture(scope="function")
    def temp_db_path(tmp_path):
        """Create a temporary database file path for each test (isolated per test).

        Convention: Tests must NOT share database state. Each test gets its own
        temporary database via pytest's tmp_path fixture.
        """
        db_path = tmp_path / "test.db"
        yield str(db_path)
        # Cleanup of tmp_path handled automatically by pytest


    @pytest.fixture(scope="function")
    def initialized_db(temp_db_path, monkeypatch):
        """Database that has been initialized with schema (tables created).

        Patches the storage module to use the temp_db_path before initialization.
        """
        import src.storage.sqlite as storage_module

        # Save original path
        original_path = storage_module._DB_PATH

        # Patch to use temp path
        storage_module._DB_PATH = Path(temp_db_path)

        # Initialize the schema
        storage_module.init_db()

        yield temp_db_path

        # Restore original path
        storage_module._DB_PATH = original_path


    # --- Sample Data Fixtures ---

    @pytest.fixture
    def sample_feed():
        """Sample feed for testing.

        Returns a Feed dataclass instance with test data.
        """
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
        """Sample article data for testing.

        Returns a dict with article data, compatible with store_article().
        """
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
        """Click CliRunner for testing CLI commands.

        Use isolated_filesystem() for commands that create files.
        """
        return CliRunner()


    # --- Test Conventions (documented for reference) ---

    """
    TEST CONVENTIONS FOR THIS PROJECT:

    1. NO PRIVATE FUNCTION TESTING
       - Do NOT test functions prefixed with underscore (_private_func)
       - Do NOT test implementation details
       - Test ONLY public interfaces: module-level functions, class public methods

    2. REAL DATABASE VIA tmp_path
       - Use the temp_db_path or initialized_db fixture for ALL database tests
       - Do NOT mock sqlite3 or storage functions
       - Real SQLite operations ensure integration works correctly

    3. HTTP MOCKING WITH httpx_mock
       - Use pytest-httpx's httpx_mock fixture for HTTP requests
       - Do NOT make real network calls in tests
       - Register mock responses before calling code that makes HTTP requests

    4. CLI TESTING WITH CliRunner
       - Use click.testing.CliRunner for all CLI tests
       - Use isolated_filesystem() for commands that write files
       - Pass db path explicitly via CLI arguments or monkeypatch
    """
  </action>
  <verify>
    <automated>grep -E '(def temp_db_path|def initialized_db|def sample_feed|def cli_runner|def sample_article)' tests/conftest.py</automated>
  </verify>
  <done>tests/conftest.py contains all required fixtures: temp_db_path, initialized_db, sample_feed, sample_article, cli_runner. Test conventions are documented in the module docstring.</done>
  <acceptance_criteria>
    - grep "def temp_db_path" tests/conftest.py returns fixture definition
    - grep "def initialized_db" tests/conftest.py returns fixture definition
    - grep "def sample_feed" tests/conftest.py returns fixture definition
    - grep "def sample_article" tests/conftest.py returns fixture definition
    - grep "def cli_runner" tests/conftest.py returns fixture definition
    - grep "NO PRIVATE FUNCTION TESTING" tests/conftest.py documents convention
    - grep "REAL DATABASE VIA tmp_path" tests/conftest.py documents convention
  </acceptance_criteria>
</task>

</tasks>

<verification>
Run: cd /Users/y3/radar && pip install -e ".[test]" && pytest --collect-only tests/
- Should see no collection errors
- Should see fixtures available: temp_db_path, initialized_db, sample_feed, sample_article, cli_runner
</verification>

<success_criteria>
1. pyproject.toml has pytest>=9.0.2 with pytest-asyncio, pytest-cov, pytest-mock, pytest-click, pytest-httpx, pytest-xdist
2. pyproject.toml has asyncio_mode = "auto" in [tool.pytest.ini_options]
3. tests/conftest.py has all 5 fixtures: temp_db_path, initialized_db, sample_feed, sample_article, cli_runner
4. Test conventions documented in conftest.py module docstring
</success_criteria>

<output>
After completion, create `.planning/phases/26-pytest/26-pytest-SUMMARY.md`
</output>
