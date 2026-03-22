---
phase: 06-unified-display-refresh-integration
plan: "06-01"
subsystem: database
tags: [sqlite, github-api, rss, unified-display]

# Dependency graph
requires:
  - phase: 04-github-api-client-releases-integration
    provides: GitHub releases stored in github_releases table with GitHubRepo and GitHubRelease models
provides:
  - Unified article listing with GitHub releases (list_articles returns feed + GitHub)
  - Unified search with GitHub releases (search_articles includes GitHub content)
  - source_type field distinguishes "feed" from "github" articles
affects:
  - 06-02 (refresh integration)
  - future CLI display commands

# Tech tracking
tech-stack:
  added: []
  patterns:
    - UNION ALL query combining feed articles and GitHub releases
    - LIKE search for GitHub content (FTS5 not available for github_releases.body)
    - source_type field pattern for distinguishing content sources

key-files:
  created: []
  modified:
    - src/articles.py

key-decisions:
  - "Used UNION ALL instead of separate queries for unified article listing"
  - "Used LIKE search for GitHub releases (body not in FTS5) - avoids schema changes"
  - "feed_id filter returns only feed articles when specified (GitHub has no feed_id)"

patterns-established:
  - "UNION ALL pattern for combining multiple content sources in list_articles"

requirements-completed: [GH-07]

# Metrics
duration: 2min
completed: 2026-03-22
---

# Phase 06 Plan 01: Unified Display - GitHub Integration Summary

**GitHub releases appear alongside feed articles in unified listing and search with source info**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-22T19:17:38Z
- **Completed:** 2026-03-22T19:19:05Z
- **Tasks:** 3
- **Files modified:** 1 (src/articles.py)

## Accomplishments
- ArticleListItem extended with source_type, repo_id, repo_name, release_tag fields
- list_articles returns unified feed articles and GitHub releases via UNION ALL
- search_articles includes GitHub releases via LIKE search on tag_name, name, body

## Task Commits

Each task was committed atomically:

1. **Task 1: Add source tracking to ArticleListItem** - `125ca69` (feat)
2. **Task 2: Modify list_articles to include GitHub releases** - `2792a67` (feat)
3. **Task 3: Modify search_articles to include GitHub content** - `7a3a8fa` (feat)

## Files Created/Modified

- `src/articles.py` - Extended ArticleListItem with GitHub fields; list_articles uses UNION ALL; search_articles uses LIKE for GitHub

## Decisions Made

- Used UNION ALL for combining feed and GitHub queries in list_articles
- Used LIKE search for GitHub releases (github_releases.body not indexed in FTS5)
- When feed_id is provided, only feed articles are returned (GitHub has no feed_id association)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 06-02 (refresh integration) can use the unified list_articles and search_articles functions
- GitHub releases display requires no additional schema changes
- Ready for CLI display command updates in subsequent plans

---
*Phase: 06-unified-display-refresh-integration*
*Completed: 2026-03-22*
