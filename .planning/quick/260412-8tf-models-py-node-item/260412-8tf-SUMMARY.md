# Quick Task 260412-8tf: Add Node and Item Abstract Classes — Summary

**Status:** Complete
**Commit:** 16b72d1

## What Was Added

Added two abstract base classes to `src/models.py`:

- **`Node`**: Abstract base for container entities (Feed, Group) — `id: str`, allows extra fields
- **`Item`**: Abstract base for leaf entities (Article) — `id: str`, `created_at: str`, forbids extra fields

## Files Modified

- `src/models.py` (+25 lines)
