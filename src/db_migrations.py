"""Database migrations for v1.3 provider architecture.

Provides migration functions for:
- DB-01: Adding metadata TEXT column to feeds table
"""
from __future__ import annotations

import logging

from src.db import get_connection

logger = logging.getLogger(__name__)


def migrate_feeds_metadata_column() -> bool:
    """Add metadata TEXT column to feeds table if it doesn't exist.

    This column stores JSON with provider-specific data like github_token.

    Returns:
        True if column was added or already exists.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # Check if column exists using PRAGMA table_info
        cursor.execute("PRAGMA table_info(feeds)")
        columns = [row[1] for row in cursor.fetchall()]

        if "metadata" not in columns:
            cursor.execute("ALTER TABLE feeds ADD COLUMN metadata TEXT")
            conn.commit()
            logger.info("Added metadata column to feeds table")
            return True
        else:
            logger.debug("metadata column already exists")
            return True
    finally:
        conn.close()


def migrate_github_repos_to_feeds() -> int:
    """Migrate github_repos data to feeds.metadata JSON.

    DEPRECATED: github_repos table has been removed.
    Returns 0.
    """
    return 0


def migrate_drop_github_repos() -> bool:
    """Drop github_repos table after successful migration.

    DEPRECATED: github_repos table has been removed.
    Returns True.
    """
    return True


def run_v13_migrations() -> dict:
    """Run all v1.3 provider architecture migrations.

    This is the main entry point called by init_db().

    Returns:
        Dict with migration results: {
            "metadata_column_added": bool,
        }
    """
    results = {
        "metadata_column_added": False,
    }

    # DB-01: Add metadata column
    results["metadata_column_added"] = migrate_feeds_metadata_column()

    return results
