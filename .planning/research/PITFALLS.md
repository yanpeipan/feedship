# Pitfalls Research: Adding pytest to Existing Python CLI Project

**Domain:** Python pytest testing for CLI applications with SQLite and async code
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH

## Executive Summary

Adding pytest to an existing untested codebase requires discipline to avoid common mistakes that create brittle, over-mocked tests that verify implementation details rather than behavior. This project specifically needs to test Click CLI commands, SQLite storage operations, and async fetch functionality with uvloop/httpx.

## Critical Pitfalls

### Pitfall 1: Testing Private Functions

**What goes wrong:**
Tests break when internal implementation changes, even when behavior remains correct. Refactoring becomes risky because tests become obstacles rather than safeguards.

**Why it happens:**
Developers naturally reach for "test everything" and end up testing `_private_functions`, `__init__` internals, and implementation details because they are visible and concrete.

**How to avoid:**
- Test only public interfaces (module-level functions, class public methods)
- If a function is complex enough to need testing, consider whether it should be public
- Ask: "Would this test break if I refactored internals but kept behavior identical?"

**Warning signs:**
- Tests importing modules with `from src.module import _private_func`
- Test names containing words like "internal", "helper", "private"
- Tests that assert on intermediate state rather than final outcomes

**Phase to address:**
TEST-01 (pytest framework setup) should establish testing conventions that prevent this.

---

### Pitfall 2: Over-Mocking Database Layer

**What goes wrong:**
Tests mock `sqlite3.connect` or storage functions, creating a false sense of security. Tests pass but real database operations fail in production because the mock never matched reality.

**Why it happens:**
Developers want fast, isolated tests and reach for `unittest.mock.patch` on database functions. This is especially tempting when the database layer is complex.

**How to avoid:**
- Use in-memory SQLite (`:memory:`) for tests rather than mocking
- Create a test database once per test session, reset between tests
- Use `tmp_path` fixture to create isolated temporary database files

**Warning signs:**
- `mock.patch("sqlite3.connect")` in tests
- Tests that never actually touch a real database
- Assertions that mock was called rather than assertions on data

**Correct approach for this project:**
```python
@pytest.fixture
def test_db(tmp_path):
    """Create isolated test database."""
    db_path = tmp_path / "test.db"
    # Copy schema if needed, or create fresh
    yield db_path
    # Cleanup automatic via tmp_path cleanup

@pytest.fixture
def storage(test_db):
    """Storage instance pointing at test database."""
    from src.storage.sqlite import Storage
    return Storage(test_db)
```

**Phase to address:**
TEST-02 (Provider tests) and TEST-03 (Storage tests) must use real database fixtures.

---

### Pitfall 3: Not Testing Edge Cases

**What goes wrong:**
Tests only cover the happy path. Edge cases like empty feeds, malformed HTML, network timeouts, and database locks are never tested, leading to production failures.

**Why it happens:**
Happy path tests are easier to write. Edge cases require understanding failure modes and setting up appropriate conditions.

**How to avoid:**
- List edge cases before writing tests: empty, None, zero, max values, malformed input
- Add tests for each failure mode the code is supposed to handle
- Use `@pytest.mark.parametrize` for testing multiple edge cases

**Warning signs:**
- Tests that only use "normal" inputs
- No tests for error conditions (400, 500 responses, timeouts)
- No tests for empty results (empty feed, no articles found)

**Phase to address:**
TEST-02 (Provider tests) should include edge case coverage.

---

### Pitfall 4: Click CLI Tests Using Subprocess

**What goes wrong:**
Tests invoke the CLI via `subprocess.run()` or `os.system()`, capturing output but making assertions difficult. This also slows tests significantly.

**Why it happens:**
It feels natural to "actually run" the CLI. The `click.testing.CliRunner` is not always discovered.

**How to avoid:**
Use `click.testing.CliRunner` for all CLI tests:

```python
from click.testing import CliRunner
from src.cli.main import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_fetch_command(runner, test_db):
    """Test fetch command with isolated filesystem."""
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ['--db', str(test_db), 'fetch'])
        assert result.exit_code == 0
```

**Warning signs:**
- `subprocess.run`, `os.system`, or `Popen` in test code
- Tests that cannot assert on exception details
- Slow test execution from process spawning

**Phase to address:**
TEST-04 (CLI tests) must use CliRunner properly.

---

### Pitfall 5: Async Test Event Loop Issues

**What goes wrong:**
Tests hang, fail with "event loop already running", or produce inconsistent results with async code using uvloop. Tests might pass in isolation but fail together.

**Why it happens:**
uvloop replaces the default asyncio event loop. pytest-asyncio may not handle this correctly without proper configuration. Fixture and test scopes can conflict with event loop lifecycle.

**How to avoid:**
- Use `pytest-asyncio` with proper configuration
- Mark async tests with `@pytest.mark.asyncio`
- For uvloop, ensure event loop is created and closed properly per test
- Use function-scoped event loops (default) to avoid state leakage

**Correct configuration for uvloop:**
```python
# conftest.py
import pytest
import asyncio
import uvloop

@pytest.fixture(scope="function")
def event_loop():
    """Create function-scoped event loop for uvloop."""
    loop = uvloop.new_event_loop()
    yield loop
    loop.close()
```

**Warning signs:**
- "RuntimeError: event loop is running" errors
- Tests that hang indefinitely
- Intermittent failures that depend on test order
- Memory leaks from unreleased event loops

**Phase to address:**
TEST-01 setup must configure async testing correctly.

---

### Pitfall 6: Fixture Scope Causing State Leakage

**What goes wrong:**
Tests pass individually but fail when run together. Data from one test appears in another. Database state persists between tests.

**Why it happens:**
Session or module-scoped fixtures share state across tests. If fixtures aren't properly isolated or reset, tests become order-dependent.

**How to avoid:**
- Use function-scoped fixtures by default for test data
- Reset database state in fixtures, not just at session start
- If using module scope, ensure proper teardown

**Warning signs:**
- Tests pass with `pytest -v` but fail with `pytest` (verbose can mask issues)
- Tests must be run in specific order
- "Database locked" errors appearing randomly
- Data from deleted feeds still appearing

**Phase to address:**
TEST-01 (conftest.py setup) must establish proper fixture scopes.

---

### Pitfall 7: Testing Click Context Without Proper Isolation

**What goes wrong:**
CLI tests pollute the real database or configuration files. Tests modify production data or depend on environment variables that aren't set in test context.

**Why it happens:**
Click applications often use global state (current working directory, environment variables, default database paths). Tests don't properly isolate from this.

**How to avoid:**
- Use `runner.isolated_filesystem()` for tests that create files
- Use `monkeypatch` to set environment variables per test
- Explicitly pass `--db` with test database path in CLI tests

**Warning signs:**
- Tests that leave files in current directory
- Tests that depend on `HOME` or `USER` environment variables
- "Database already exists" errors when running tests multiple times

**Phase to address:**
TEST-04 (CLI integration tests) must use proper isolation.

---

## Moderate Pitfalls

### Pitfall 8: Asserting on Exact Exception Messages

**What goes wrong:**
Tests fail when error messages change, even though the error behavior is correct.

**How to avoid:**
Assert on exception type first, message second:
```python
with pytest.raises(OperationalError):
    # Only verify the operation fails, not the exact message
    storage.locked_operation()
```

---

### Pitfall 9: Not Testing Provider Plugin Architecture

**What goes wrong:**
Tests only test the concrete implementations, missing bugs in the plugin loading, registry lookup, or protocol adherence.

**How to avoid:**
- Test that the registry correctly loads providers
- Test that `ContentProvider` protocol is actually implemented
- Test provider priority ordering

---

### Pitfall 10: Forgetting to Test TagParser Chaining

**What goes wrong:**
Tag parser chain may break silently if one parser fails. Multiple parsers returning conflicting results may not be handled.

**How to avoid:**
- Test `chain_tag_parsers` with mock parsers
- Test behavior when one parser raises exception
- Test deduplication logic

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| SQLite + pytest | Using production database file | Use `tmp_path` or `:memory:` |
| SQLite + async | Database locks from concurrent writes | Serialize writes via Lock in tests |
| Click + CliRunner | Forgetting `isolated_filesystem` | Always use for file-creating commands |
| httpx + tests | Making real network requests | Use `respx` or `httpx-mock` |
| uvloop + pytest | Event loop not properly closed | Use fixture-scoped loop with cleanup |
| feedparser + tests | Mocking the entire library | Use sample RSS/Atom fixtures |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Real network in tests | Tests slow, flaky, depend on internet | Use fixtures with sample data or mocks | At 100+ tests, CI becomes unusable |
| Session-scoped DB fixture | Tests leak state between modules | Use function scope for test data | When tests modified by different developers |
| Too many parametrized tests | Combinatorial explosion | Limit parameters, test boundary cases | With 5+ parameters of 3+ values each |

---

## Security Mistakes (Testing Context)

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoded credentials in test fixtures | Accidental exposure in VCS | Use environment variables or `.env.example` |
| Test database in VCS | Production-like data leaked | Use `tmp_path`, ignore test DBs in `.gitignore` |
| Secrets in mock responses | False sense of security | Use fake/example credentials in test data |

---

## "Looks Done But Isn't" Checklist

- [ ] **CLI tests:** Often only test happy path -- verify error cases tested
- [ ] **Provider tests:** Often miss testing plugin loading failures -- verify registry tests exist
- [ ] **Storage tests:** Often mock database instead of using real one -- verify integration tests
- [ ] **Async tests:** Often don't actually test concurrency -- verify race conditions tested

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Over-mocked tests | HIGH | Rewrite to use real database fixtures; remove mocks incrementally |
| State leakage | MEDIUM | Clear database between tests; check fixture scopes |
| Event loop issues | MEDIUM | Reconfigure pytest-asyncio; ensure uvloop properly closed |
| Click isolation | LOW | Add CliRunner.isolated_filesystem(); verify no file pollution |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Testing private functions | TEST-01: Setup conventions | Code review checklist for test imports |
| Over-mocking database | TEST-03: Storage tests | Tests must use real `Storage` with `tmp_path` |
| Missing edge cases | TEST-02: Provider tests | Parametrized tests for RSS empty, malformed |
| Click CLI subprocess | TEST-04: CLI tests | Verify only `CliRunner.invoke` used |
| Async event loop issues | TEST-01: pytest-asyncio config | Tests must run clean with `-v --tb=short` |
| Fixture state leakage | TEST-01: conftest fixtures | `pytest --collect-only` then run to verify isolation |
| Click context isolation | TEST-04: CLI integration | Verify no files in cwd after tests |

---

## Sources

- [pytest Fixture Documentation](https://docs.pytest.org/en/latest/explanation/fixtures.html) (HIGH confidence)
- [Click Testing Documentation](https://click.palletsprojects.com/en/latest/testing/) (HIGH confidence)
- [Python sqlite3 Documentation](https://docs.python.org/3/library/sqlite3.html) (HIGH confidence)
- [pytest xunit setup](https://docs.pytest.org/en/latest/how-to/xunit_setup.html) (HIGH confidence)
- [pytest unittest integration](https://docs.pytest.org/en/latest/how-to/unittest.html) (HIGH confidence)

---

*Pitfalls research for: pytest testing on Python CLI with SQLite and async*
*Researched: 2026-03-25*
