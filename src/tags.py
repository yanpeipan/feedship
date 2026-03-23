"""Tag management and rule-based tagging.

Provides tag CRUD and rule-based auto-tagging for articles.
"""

from __future__ import annotations

from src.db import add_tag, tag_article


def run_auto_tagging() -> dict:
    """Auto-tagging is no longer supported.

    Returns empty dict.
    """
    return {}
