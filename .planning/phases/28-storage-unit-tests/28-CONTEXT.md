---
name: 28-storage-unit-tests-context
description: Phase 28 context for Storage层单元测试
type: context
phase: 28
plan: 00
---

## Phase Boundary

Write unit tests for SQLite storage layer functions using real SQLite via tmp_path fixture.

## TEST-03 Requirements

From ROADMAP.md:
1. test_storage.py covers store_article(), list_articles(), search_articles()
2. test_storage.py covers feed CRUD (add_feed, list_feeds, etc.)
3. test_storage.py covers tag operations (add_tag, tag_article, get_article_tags)
4. All tests use real SQLite via tmp_path fixture (no mocking sqlite3)

## Storage Functions to Test

From src/storage/__init__.py and src/storage/sqlite.py:

**Article operations:**
- store_article(guid, title, content, link, feed_id, pub_date) -> str (article_id)
- store_article_async(...) -> str (article_id) - async version
- list_articles(limit, feed_id) -> list[ArticleListItem]
- get_article(article_id) -> Optional[ArticleListItem]
- get_article_detail(article_id) -> Optional[dict]
- search_articles(query, limit, feed_id) -> list[ArticleListItem]
- list_articles_with_tags(limit, feed_id, tag, tags) -> list[ArticleListItem]

**Feed operations:**
- feed_exists(url) -> bool
- add_feed(feed) -> Feed
- list_feeds() -> list[Feed]
- get_feed(feed_id) -> Optional[Feed]
- remove_feed(feed_id) -> bool

**Tag operations:**
- add_tag(name) -> Tag
- list_tags() -> list[Tag]
- remove_tag(tag_name) -> bool
- get_tag_article_counts() -> dict[str, int]
- tag_article(article_id, tag_name) -> bool
- untag_article(article_id, tag_name) -> bool
- get_article_tags(article_id) -> list[str]

## Test Conventions (from Phase 26)

1. **NO PRIVATE FUNCTION TESTING** - test only public interfaces
2. **REAL DATABASE VIA tmp_path** - use initialized_db fixture for database tests
3. **HTTP MOCKING WITH httpx_mock** - use httpx_mock fixture
4. **CLI TESTING WITH CliRunner**

## Fixtures Available (from Phase 26)

- temp_db_path: temporary database path per test
- initialized_db: database with schema initialized
- sample_feed: Feed dataclass instance
- sample_article: dict with article data
- cli_runner: CliRunner instance

## Deferred Ideas

None — straightforward unit testing of existing storage interfaces.
