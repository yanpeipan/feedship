"""Tests for src.llm module.

Tests cover:
- LLM wrapper initialization
- JSON mode support (json_object vs json_schema)
"""

import asyncio
import json

import pytest


class TestJSONModeSupport:
    """Tests for JSON mode support via LiteLLM.

    Verifies that json_object and json_schema modes work correctly with the
    configured LLM provider. These are integration tests that call the real API
    and may be affected by provider-specific behavior.
    """

    def _is_valid_json(self, s: str) -> bool:
        """Check if string is valid JSON (optionally with leading/trailing whitespace)."""
        s = s.strip()
        if not s:
            return False
        try:
            json.loads(s)
            return True
        except (json.JSONDecodeError, ValueError):
            return False
