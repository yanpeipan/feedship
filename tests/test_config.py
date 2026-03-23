"""Tests for src.config module."""
import pytest
from zoneinfo import ZoneInfo


def test_get_timezone_returns_zoneinfo():
    """get_timezone should return a ZoneInfo object."""
    from src.config import get_timezone
    result = get_timezone()
    assert isinstance(result, ZoneInfo)


def test_get_timezone_default_is_asia_shanghai():
    """get_timezone should default to Asia/Shanghai."""
    from src.config import get_timezone
    result = get_timezone()
    assert str(result) == "Asia/Shanghai"
