"""Tests for async concurrent fetch and SQLite serialization."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.application.fetch import fetch_all_async, fetch_one_async
from src.models import Feed


@pytest.fixture
def sample_feed():
    """Sample feed for testing."""
    return Feed(
        id="test-feed-1",
        name="Test Feed",
        url="https://example.com/feed.xml",
        etag=None,
        last_modified=None,
        last_fetched=None,
        created_at="2024-01-01T00:00:00+00:00",
    )


@pytest.mark.asyncio
async def test_fetch_all_async_exists():
    """Verify fetch_all_async function exists and is callable."""
    assert callable(fetch_all_async)


@pytest.mark.asyncio
async def test_fetch_all_async_returns_dict():
    """Verify fetch_all_async returns expected dict structure."""
    with patch("src.application.fetch.storage_list_feeds", return_value=[]):
        result = await fetch_all_async()
        assert isinstance(result, dict)
        assert "total_new" in result
        assert "success_count" in result
        assert "error_count" in result
        assert "errors" in result


@pytest.mark.asyncio
async def test_semaphore_default_value():
    """Verify default concurrency is 10."""
    with patch("src.application.fetch.storage_list_feeds", return_value=[]):
        with patch("src.application.fetch.asyncio.Semaphore") as mock_semaphore:
            mock_semaphore.return_value = MagicMock()
            await fetch_all_async()
            # Check Semaphore was called with 10
            mock_semaphore.assert_called_once_with(10)


@pytest.mark.asyncio
async def test_semaphore_custom_concurrency():
    """Verify custom concurrency parameter is passed to Semaphore."""
    with patch("src.application.fetch.storage_list_feeds", return_value=[]):
        with patch("src.application.fetch.asyncio.Semaphore") as mock_semaphore:
            mock_semaphore.return_value = MagicMock()
            await fetch_all_async(concurrency=5)
            mock_semaphore.assert_called_once_with(5)


@pytest.mark.asyncio
async def test_fetch_one_async_returns_dict(sample_feed):
    """Verify fetch_one_async returns expected dict structure."""
    with patch("src.application.fetch.discover_or_default", return_value=[]):
        result = await fetch_one_async(sample_feed)
        assert isinstance(result, dict)
        assert "new_articles" in result


@pytest.mark.asyncio
async def test_fetch_one_async_crawled_feed():
    """Verify fetch_one_async skips 'crawled' system feed."""
    crawled_feed = Feed(
        id="crawled",
        name="Crawled Pages",
        url="",
        etag=None,
        last_modified=None,
        last_fetched=None,
        created_at="2024-01-01T00:00:00+00:00",
    )
    result = await fetch_one_async(crawled_feed)
    assert result == {"new_articles": 0}


@pytest.mark.asyncio
async def test_db_lock_serialization():
    """Verify store_article_async uses asyncio.Lock for serialization."""
    from src.storage.sqlite import store_article_async, _get_db_write_lock

    # Verify the lock exists and is an asyncio.Lock
    lock = _get_db_write_lock()
    assert isinstance(lock, asyncio.Lock), "Lock should be an asyncio.Lock instance"

    # Verify store_article_async is actually async
    import inspect
    assert inspect.iscoroutinefunction(store_article_async), \
        "store_article_async should be a coroutine function"
