---
name: 27-provider-unit-tests-context
description: Phase 27 context for Provider单元测试
type: context
phase: 27
plan: 00
---

## Phase Boundary

Write unit tests for the Provider plugin architecture (RSSProvider, GitHubReleaseProvider, ProviderRegistry).

## Implementation Decisions

### TEST-02 Requirements
- test_providers.py covers RSSProvider.match(), crawl(), crawl_async(), parse()
- test_providers.py covers GitHubReleaseProvider.match(), priority(), crawl(), parse()
- ProviderRegistry discover() and discover_or_default() tested
- HTTP mocked via httpx_mock fixture (no real network calls)

## Specific Ideas

### Provider Interface (from Phase 12-13)
- ContentProvider Protocol: match(), priority(), crawl(), crawl_async(), parse(), tag_parsers(), parse_tags()
- RSSProvider: priority=50, match() uses httpx HEAD request, crawl() uses feedparser
- GitHubReleaseProvider: priority=100, match() supports HTTPS and git@ SSH URLs
- ProviderRegistry: discover() glob + importlib, discover_or_default() fallback

### Test Conventions (from Phase 26)
- NO PRIVATE FUNCTION TESTING - test only public interfaces
- REAL DATABASE VIA tmp_path - use initialized_db fixture
- HTTP MOCKING WITH httpx_mock - use httpx_mock fixture
- CLI TESTING WITH CliRunner

### Fixtures Available (from Phase 26)
- temp_db_path: temporary database path per test
- initialized_db: database with schema initialized
- sample_feed: Feed dataclass instance
- sample_article: dict with article data
- cli_runner: CliRunner instance

## Deferred Ideas

None — straightforward unit testing of existing interfaces.
