"""Tag CRUD operations for SQLite storage.

Provides functions for creating, reading, updating, and deleting tags
in the SQLite database.
"""

from __future__ import annotations

from src.models import Tag
from src.storage.sqlite.conn import get_db


def tag_exists(name: str) -> bool:
    """Check if a tag with the given name exists.

    Args:
        name: The tag name to check.

    Returns:
        True if a tag with the given name exists, False otherwise.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM tags WHERE name = ?", (name,))
        return cursor.fetchone() is not None


def add_tag(name: str, description: str | None = None) -> Tag:
    """Create a new tag and return the Tag object.

    The tag ID is generated as a UUID and created_at is set to the current time.

    Args:
        name: Display name of the tag (unique, max 100 chars).
        description: Optional description of the tag.

    Returns:
        The newly created Tag object.
    """
    import time
    import uuid

    tag_id = str(uuid.uuid4())
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")

    tag = Tag(id=tag_id, name=name, created_at=created_at, description=description)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tags (id, name, created_at, description) VALUES (?, ?, ?, ?)",
            (tag.id, tag.name, tag.created_at, tag.description),
        )
        conn.commit()
        return tag


def list_tags() -> list[Tag]:
    """List all tags ordered by name.

    Returns:
        List of Tag objects ordered by name ascending.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, created_at, description FROM tags ORDER BY name ASC"
        )
        rows = cursor.fetchall()
        return [
            Tag(
                id=row["id"],
                name=row["name"],
                created_at=row["created_at"],
                description=row["description"],
            )
            for row in rows
        ]


def get_tag(tag_id: str) -> Tag | None:
    """Get a single tag by ID.

    Args:
        tag_id: The tag ID to look up.

    Returns:
        Tag object if found, None otherwise.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, created_at, description FROM tags WHERE id = ?",
            (tag_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Tag(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            description=row["description"],
        )


def delete_tag(tag_id: str) -> bool:
    """Delete a tag by ID.

    Also removes all feed_tag associations for this tag.

    Args:
        tag_id: The ID of the tag to delete.

    Returns:
        True if the tag was deleted, False if it was not found.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM feed_tags WHERE tag_id = ?", (tag_id,))
        cursor.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted
