---
phase: 10-article-detail-view
plan: "01"
type: execute
subsystem: cli
tags:
  - article-view
  - article-open
  - rich
dependency_graph:
  requires: []
  provides:
    - src/articles.py: get_article_detail function
    - src/cli.py: article view command
    - src/cli.py: article open command
  affects:
    - src/articles.py
    - src/cli.py
tech_stack:
  added:
    - rich.panel.Panel
    - platform.system() for cross-platform browser opening
    - subprocess.run for opening URLs
  patterns:
    - get_article_detail returns dict with content and tags
    - article view uses rich Panel with metadata table
    - article open uses platform-specific browser commands
key_files:
  created: []
  modified:
    - src/articles.py (added get_article_detail)
    - src/cli.py (added article view and article open)
decisions:
  - Use rich Panel with Table for metadata display
  - Truncate content to 2000 chars unless --verbose
  - Use platform.system() for cross-platform open commands
metrics:
  duration: ~2 minutes
  completed: 2026-03-23
---

# Phase 10 Plan 01: Article Detail View Summary

## One-liner

Article detail view and open-in-browser commands: `article view <id>` shows full article with rich formatting, `article open <id>` opens URL in default browser.

## Completed Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add get_article_detail function | 59a416d | src/articles.py |
| 2 | Add article view command | 279288a | src/cli.py |
| 3 | Add article open command | 927edeb | src/cli.py |

## Must-Haves Verification

### Truths Verified

- [x] User can run `article view <id>` and see full article details including content
- [x] User can run `article open <id>` to open article URL in browser
- [x] Detail view shows title, source/feed, date, tags, link, and full content
- [x] View and open commands work with truncated 8-char IDs

### Artifacts

- [x] `src/articles.py` provides `get_article_detail` function that fetches full article with content
- [x] `src/cli.py` provides `article view` and `article open` commands

## Implementation Details

### get_article_detail Function

Added to `src/articles.py`:
- Accepts article_id (full 32-char or truncated 8-char)
- Exact ID match first, then LIKE query for truncated IDs
- SELECT includes content field (missing from existing get_article)
- JOIN with feeds table for feed_name
- Calls get_article_tags() to include tags list
- Returns dict with all fields or None if not found

### article view Command

Added to `src/cli.py`:
- `@article.command("view")` decorator
- Takes `article_id` as required argument
- `--verbose` flag for full content without truncation
- Uses rich.Panel with title (article title) and subtitle (feed_name | date)
- Metadata Table shows: Source, Date, Tags, Link
- Content truncated to 2000 chars unless --verbose
- Error handling with red colored messages

### article open Command

Added to `src/cli.py`:
- `@article.command("open")` decorator
- Takes `article_id` as required argument
- Uses `open_in_browser()` helper function
- Platform detection: Darwin (open), Linux (xdg-open), Windows (start)
- Error if article not found or no link available
- Success message in green: "Opened {url} in browser"

## Requirements Marked Complete

- ARTICLE-05: `article view <id>` command exists and shows full article details
- ARTICLE-06: Detail view shows title, source/feed, date, tags, link, and full content
- ARTICLE-07: `article open <id>` command opens article URL in default browser

## Deviations from Plan

None - plan executed exactly as written.

## Commits

- 59a416d: feat(10-01): add get_article_detail function to articles.py
- 279288a: feat(10-01): add article view command to cli.py
- 927edeb: feat(10-01): add article open command to cli.py
