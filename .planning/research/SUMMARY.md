# Project Research Summary

**Project:** 个人资讯系统 (Personal Information System)
**Domain:** CLI tool for RSS subscription and website crawling with async support
**Researched:** 2026-03-25
**Confidence:** HIGH

## Executive Summary

v1.7 milestone introduces pytest testing framework for this Python CLI application. The application uses Click for CLI, SQLite for storage, httpx/feedparser for HTTP/feed fetching, and asyncio/uvloop for async concurrency. Research across all four domains confirms the recommended testing stack is well-established with proven patterns.

Key insight: This project has existing minimal tests (4 test files) but lacks proper fixtures, provider tests, storage tests, and CLI integration tests. The v1.7 milestone addresses these gaps systematically.

## Key Findings

### Recommended Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **pytest** | 9.0.2 | Test framework with auto-discovery and fixture support |
| **pytest-asyncio** | 1.3.0 | Async test support with `asyncio_mode = "auto"` |
| **pytest-cov** | 7.1.0 | Code coverage reporting |
| **pytest-mock** | 3.15.1 | Mocking with `mocker` fixture and auto-cleanup |
| **pytest-click** | 1.1.0 | CLI testing with `cli_runner` fixture |
| **pytest-httpx** | 0.36.0 | HTTP mocking for httpx requests |
| **pytest-xdist** | 3.8.0 | Parallel test execution |

### Test Organization

**Recommended: Flat structure** (not nested)
```
tests/
├── conftest.py              # Root fixtures: temp_db, cli_runner, sample data
├── test_fetch.py           # Existing: async fetch tests
├── test_config.py          # Existing: config tests
├── test_providers.py       # NEW: Provider plugin tests
├── test_storage.py        # NEW: SQLite storage layer tests
└── test_cli.py            # NEW: CLI integration tests
```

**Rationale:** Project has ~10 source modules. Nested structure adds complexity without proportional benefit for a personal CLI tool.

### Fixture Scope Strategy

| Fixture | Scope | Rationale |
|---------|-------|-----------|
| `temp_db_path` | session | Expensive file I/O, safe to share |
| `initialized_db` | function | Tests may modify data, need isolation |
| `sample_feed` | function | Stateless, cheap |
| `sample_article` | function | Stateless, cheap |
| `cli_runner` | session | CliRunner is stateless |

### Critical Pitfalls to Avoid

1. **Testing private functions** — Break on refactoring. Test public interfaces only.
2. **Over-mocking database** — Use real SQLite with `tmp_path` fixture, not mocked sqlite3.
3. **Missing edge cases** — Test empty feeds, malformed HTML, network timeouts.
4. **Click CLI subprocess** — Use `CliRunner.invoke()`, not `subprocess.run()`.
5. **Async event loop issues** — Configure pytest-asyncio properly for uvloop.
6. **Fixture state leakage** — Use function scope for test data fixtures.

## Requirements (TEST-01 through TEST-04)

### TEST-01: pytest测试框架
**引入pytest测试框架，配置conftest.py和基础fixtures**
- Install pytest packages (9.0.2, pytest-asyncio, pytest-cov, pytest-mock, pytest-click, pytest-httpx, pytest-xdist)
- Configure `asyncio_mode = "auto"` in pyproject.toml
- Create root `tests/conftest.py` with fixtures: `temp_db_path`, `initialized_db`, `sample_feed`, `sample_article`, `cli_runner`
- Establish testing conventions (no private function testing, real DB fixtures)

### TEST-02: Provider单元测试
**为Provider插件架构编写单元测试**
- `test_providers.py`: RSSProvider, GitHubReleaseProvider, GitHubProvider
- Mock HTTP with `httpx_mock` fixture
- Test: match(), priority(), crawl(), crawl_async(), parse(), tag_parsers()
- Test ProviderRegistry discover() and discover_or_default()

### TEST-03: Storage层单元测试
**为Storage层SQLite操作编写单元测试**
- `test_storage.py`: All CRUD operations in `src/storage/sqlite.py`
- Use `initialized_db` fixture with `tmp_path`
- Test: store_article(), list_articles(), search_articles(), feed CRUD, tag operations

### TEST-04: CLI集成测试
**为CLI命令编写集成测试**
- `test_cli.py`: CLI commands using CliRunner
- Test: feed add/list, article list/detail, tag commands
- Use `isolated_filesystem()` for file operations
- Test error cases (invalid URL, duplicate feed, not found)

## Phase Structure

| Phase | Goal | Requirements | Plans |
|-------|------|--------------|-------|
| 26 | pytest框架搭建 | TEST-01 | 1 plan |
| 27 | Provider单元测试 | TEST-02 | 1 plan |
| 28 | Storage层单元测试 | TEST-03 | 1 plan |
| 29 | CLI集成测试 | TEST-04 | 1 plan |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via PyPI |
| Architecture | HIGH | Flat structure recommended for this project size |
| Fixtures | HIGH | Standard pytest patterns well-established |
| Pitfalls | HIGH | All pitfalls documented with prevention strategies |

## Sources

- [pytest 9.0.2 - PyPI](https://pypi.org/project/pytest/9.0.2/)
- [pytest-asyncio 1.3.0 - PyPI](https://pypi.org/project/pytest-asyncio/1.3.0/)
- [pytest-cov 7.1.0 - PyPI](https://pypi.org/project/pytest-cov/7.1.0/)
- [pytest-mock 3.15.1 - PyPI](https://pypi.org/project/pytest-mock/3.15.1/)
- [pytest-click 1.1.0 - PyPI](https://pypi.org/project/pytest-click/1.1.0/)
- [pytest-httpx 0.36.0 - PyPI](https://pypi.org/project/pytest-httpx/0.36.0/)
- [Click Testing Documentation](https://click.palletsprojects.com/en/stable/testing/)

---

*Research completed: 2026-03-25*
*Ready for roadmap: yes*
