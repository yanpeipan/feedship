# Plan 17-01 Summary: CLI Package Split + DB Context Manager

**Plan:** 17-anti-refactoring-01
**Completed:** 2026-03-24
**Tasks:** 9/9

## Commits

| Commit | Description |
|--------|-------------|
| `b2c0056` | feat(17-anti-01): add get_db() context manager to db.py |
| `294a908` | feat(17-anti-01): migrate db.py functions to use get_db() context manager |
| `7392900` | feat(17-anti-01): create src/cli/ package structure |
| `4c595f2` | feat(17-anti-01): migrate application/feed.py to use get_db() |
| `830109f` | feat(17-anti-01): migrate articles.py to use get_db() |
| `8d32c7c` | feat(17-anti-01): migrate crawl.py to use get_db() |
| `f93b3d2` | feat(17-anti-01): migrate ai_tagging.py to use get_db() |
| `b98d0ce` | feat(17-anti-01): delete old cli.py and update cli/__init__.py |
| `3e33673` | fix(17-anti-refactoring-01): add missing submodule imports to cli/__init__.py |

## Key Changes

### 1. DB Context Manager
- Added `get_db()` context manager to `src/db.py`
- Migrated 28 bare `get_connection()` calls across 6 files to use `with get_db() as conn:`
- Files migrated: `db.py`, `application/feed.py`, `articles.py`, `crawl.py`, `ai_tagging.py`

### 2. CLI Package Split
- Created `src/cli/` package with 5 modules:
  - `__init__.py` - main entry point, imports submodules to register commands
  - `feed.py` - feed add/list/remove/refresh + fetch --all
  - `article.py` - article list/view/open/search/tag
  - `tag.py` - tag add/list/remove + rule subcommands
  - `crawl.py` - crawl command
- Deleted old monolithic `src/cli.py` (798 lines)
- pyproject.toml entry point updated to `src.cli:cli`

### 3. Duplicate Elimination
- Removed duplicate `_store_article()` from `application/feed.py`
- Now uses `db.store_article()` exclusively

## Files Modified

- `src/db.py` - Added get_db() context manager, migrated 10 functions
- `src/cli/__init__.py` - Main CLI entry point with submodule imports
- `src/cli/feed.py` - Feed management commands (new file)
- `src/cli/article.py` - Article management commands (new file)
- `src/cli/tag.py` - Tag management commands (new file)
- `src/cli/crawl.py` - Crawl command (new file)
- `src/application/feed.py` - Migrated to get_db(), removed duplicate _store_article
- `src/articles.py` - Migrated 6 functions to get_db()
- `src/crawl.py` - Migrated to get_db()
- `src/ai_tagging.py` - Migrated 5 functions to get_db()
- `pyproject.toml` - Updated entry point

## Verification

```bash
# CLI loads and all commands registered
python -c "from src.cli import cli; cli(['--help'], standalone_mode=False)"

# No bare get_connection() outside db.py
grep -rn "get_connection()" src/ --include="*.py" | grep -v "_get_connection\|get_db"
# Returns: nothing
```
