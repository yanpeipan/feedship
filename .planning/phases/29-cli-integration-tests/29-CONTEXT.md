---
name: 29-cli-integration-tests-context
description: Phase 29 context for CLI integration tests
type: context
phase: 29
plan: 00
---

## Phase Boundary

Write integration tests for CLI commands using CliRunner and isolated_filesystem().

## TEST-04 Requirements

From ROADMAP.md:
1. test_cli.py covers feed add/list commands
2. test_cli.py covers article list/detail commands
3. test_cli.py covers tag commands
4. All tests use CliRunner.invoke() with isolated_filesystem()
5. Error cases tested (invalid URL, duplicate feed, not found)

## CLI Commands to Test

From src/cli.py and related modules:

**Feed commands:**
- `feed add <url>` — add a new feed
- `feed list` — list all feeds with article counts
- `feed remove <feed-id>` — remove a feed

**Article commands:**
- `article list --feed <feed-id>` — list articles for a feed
- `article detail <article-prefix>` — show article detail
- `article open <article-prefix>` — open article in browser
- `article search <query>` — search articles

**Tag commands:**
- `tag add <article-id> <tag>` — add tag to article
- `tag list` — list all tags with counts
- `tag remove <article-id> <tag>` — remove tag from article

## Test Conventions (from Phase 26)

1. **NO PRIVATE FUNCTION TESTING** - test only public interfaces
2. **REAL DATABASE VIA tmp_path** - use initialized_db fixture for database tests
3. **HTTP MOCKING WITH httpx_mock** - use httpx_mock fixture
4. **CLI TESTING WITH CliRunner** - use CliRunner.invoke() with isolated_filesystem()

## Fixtures Available (from Phase 26)

- temp_db_path: temporary database path per test
- initialized_db: database with schema initialized
- sample_feed: Feed dataclass instance
- sample_article: dict with article data
- cli_runner: CliRunner instance

## CliRunner Usage Pattern

```python
from click.testing import CliRunner

def test_feed_list(cli_runner, initialized_db):
    result = cli_runner.invoke(cli, ['feed', 'list'])
    assert result.exit_code == 0
    assert 'Test Feed' in result.output
```

## Deferred Ideas

None — straightforward CLI integration testing following existing patterns.
