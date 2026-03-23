"""Pytest fixtures for radar tests."""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    os.unlink(db_path)


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
