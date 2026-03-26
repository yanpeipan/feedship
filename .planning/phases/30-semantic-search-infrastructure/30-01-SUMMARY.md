---
phase: 30-semantic-search-infrastructure
plan: "30-01"
subsystem: storage
tags:
  - chromadb
  - vector-storage
  - semantic-search
requires:
  - SEM-01
provides:
  - ChromaDB PersistentClient singleton
  - "articles" collection access
  - SentenceTransformer embedding function
affects:
  - src/storage/__init__.py
tech_stack:
  added:
    - chromadb (import only, dependency not yet installed)
    - platformdirs (already in pyproject.toml)
    - sentence-transformers (already in pyproject.toml)
  patterns:
    - Module-level singleton pattern (matching get_db() in sqlite.py)
    - Lazy initialization for client
key_files:
  created:
    - src/storage/vector.py (new file, ChromaDB client infrastructure)
  modified:
    - src/storage/__init__.py (added exports for get_chroma_collection, _get_embedding_function)
decisions:
  - D-01: ChromaDB PersistentClient as module-level singleton in src/storage/
  - D-02: Storage directory via platformdirs.user_data_dir(appname="rss-reader") + "/chroma"
  - D-06: Collection named "articles" with article ID, content, title, url metadata
  - D-07: Exports in src/storage/__init__.py alongside existing storage API
---

# Phase 30 Plan 01: ChromaDB Client Infrastructure Summary

## One-liner

ChromaDB PersistentClient singleton with `get_chroma_collection()` returning the "articles" collection, using SentenceTransformer embeddings stored in `~/.local/share/rss-reader/chroma/`.

## Files Created/Modified

| File | Change |
|------|--------|
| `src/storage/vector.py` | Created (ChromaDB client infrastructure) |
| `src/storage/__init__.py` | Modified (added exports) |

## Key Implementation Decisions Applied

1. **D-01 (Module-level singleton)**: `_chroma_client` module-level variable with lazy `_get_chroma_client()` function following the same pattern as `get_db()` in sqlite.py.

2. **D-02 (Storage directory)**: Uses `platformdirs.user_data_dir(appname="rss-reader") + "/chroma"` for cross-platform storage at `~/.local/share/rss-reader/chroma/`.

3. **D-06 (Collection metadata)**: Collection "articles" created with metadata description; actual metadata fields (article_id, content, title, url) to be set when adding embeddings.

4. **D-07 (Exports)**: Added `get_chroma_collection` and `_get_embedding_function` to `src/storage/__init__.py` alongside existing sqlite exports.

## Verification

```
grep -n "PersistentClient\|_chroma_client\|get_chroma_collection\|_get_embedding_function\|platformdirs" src/storage/vector.py
# Returns: 10 occurrences across all required patterns

grep -n "vector\|chroma\|get_chroma_collection" src/storage/__init__.py
# Returns: imports from src.storage.vector and exports get_chroma_collection
```

## Deviations from Plan

None - plan executed exactly as written.

## Commits

- `044cbe5` - feat(30-semantic-search): add ChromaDB PersistentClient singleton

## Notes

- `chromadb` package is not yet installed in the environment (present in pyproject.toml as a dependency). The import statement `import chromadb` is correct per the plan and will work once dependencies are installed.
- The embedding function uses `all-MiniLM-L6-v2` model (384 dimensions), consistent with `src/tags/ai_tagging.py`.

## Self-Check: PASSED

- `src/storage/vector.py` exists
- Contains `_chroma_client` module-level variable initialized to `None`
- Contains `_get_chroma_client()` function that creates `PersistentClient`
- Contains `get_chroma_collection()` function returning collection named "articles"
- Uses `platformdirs.user_data_dir(appname="rss-reader") + "/chroma"` for directory
- Contains `_get_embedding_function()` using `SentenceTransformer("all-MiniLM-L6-v2")`
- ChromaDB import is `import chromadb`
- `src/storage/__init__.py` exports `get_chroma_collection`
- Commit `044cbe5` exists
