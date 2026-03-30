# Quick Task 260330-hx7: Add Integration Tests for CLI Commands

## Summary

Added 7 integration tests covering missing CLI commands: discover, fetch --all, and fetch <id>.

## One-liner

Integration tests for discover and fetch CLI commands (7 tests covering discover, fetch --all, fetch by ID, and fetch multiple IDs).

## Tasks Completed

| Task | Name | Status |
|------|------|--------|
| 1 | Add discover and fetch CLI tests | PASSED |

## Tests Added

**TestFetchCommands class (5 tests):**
- `test_fetch_all_empty` - fetch --all with no feeds
- `test_fetch_all_with_feeds` - fetch --all with feeds (mocked async)
- `test_fetch_single_by_id` - fetch single feed by ID
- `test_fetch_single_by_id_not_found` - fetch non-existent ID
- `test_fetch_multiple_ids` - fetch multiple feeds by ID

**TestDiscoverCommands class (2 tests):**
- `test_discover_success` - discover with feeds found
- `test_discover_no_feeds` - discover with no feeds

## Deviations from Plan

None - plan executed exactly as written.

## Files Modified

- `tests/test_cli.py` - Added 7 new tests

## Verification

```
pytest tests/test_cli.py::TestFetchCommands tests/test_cli.py::TestDiscoverCommands -v --tb=short
7 passed
```

## Notes

- Pre-existing test failures in TestFeedCommands and TestFeedDiscovery are unrelated to these changes
- Tests mock at the appropriate layer (src.application.fetch for fetch, src.cli.discover for discover)
