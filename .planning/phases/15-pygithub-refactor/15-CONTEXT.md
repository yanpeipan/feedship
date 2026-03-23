# Phase 15: PyGithub Refactor - Context

**Gathered:** 2026-03-24 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace custom GitHub API implementation in `src/github.py` with PyGithub library. Delete `src/github.py` after refactoring. GitHubProvider and crawl.py should use PyGithub for all GitHub API calls.

</domain>

<decisions>
## Implementation Decisions

### Scope: What to Replace
- **D-01:** Only `fetch_latest_release()` replaced with PyGithub for GitHubProvider.crawl()
- **D-02:** crawl.py GitHub API calls (`fetch_github_file_metadata`, `fetch_github_commit_time`) also refactored to use PyGithub — scope includes all GitHub API calls
- **D-03:** `detect_changelog_file()` and `fetch_changelog_content()` use raw.githubusercontent.com (not GitHub API) — stay with httpx
- **D-04:** `src/github.py` deleted after refactoring complete

### Scope: What Stays
- **D-05:** `parse_github_url()` stays (moved to utility module) — pure URL parsing, no API dependency
- **D-06:** DB operations (`store_release`, `get_repo_releases`, etc.) stay in github.py or move to db.py — SQLite operations, not GitHub API

### Technical: PyGithub Integration
- **D-07:** PyGithub initialized with `Github(os.environ.get("GITHUB_TOKEN"))` — same env var as current
- **D-08:** Module-level `Github` singleton for reuse across calls (not per-call instantiation)
- **D-09:** Rate limit handling via PyGithub internal mechanism — custom `check_rate_limit/is_rate_limited/get_wait_time` removed
- **D-10:** Custom `RateLimitError` and `GitHubAPIError` replaced by PyGithub's `RateLimitException` and `GithubException`
- **D-11:** Add `PyGithub` to dependencies (version 2.x)

### Data: github_repos Table
- **D-12:** `github_repos` table still exists in DB — Phase 12 migration was partial (github_repos data NOT migrated to feeds.metadata per Phase 12 verification)
- **D-13:** DB operations continue using `github_repos` table as-is (no change to data layer in this phase)

### File Changes
- **D-14:** `src/github.py` deleted
- **D-15:** New utility module `src/github_utils.py` created with `parse_github_url()` function

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Provider Architecture (Phase 13)
- `src/providers/github_provider.py` — GitHubProvider that wraps github.py (to be updated)
- `src/providers/base.py` — ContentProvider Protocol

### GitHub Integration
- `src/github.py` — Current implementation to replace (808 lines)
- `src/crawl.py` — Contains `fetch_github_file_metadata()` and `fetch_github_commit_time()` using github.py get_headers()

### Dependencies
- `pyproject.toml` — Need to add PyGithub 2.x dependency

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `parse_github_url()` in github.py:44-78 — pure URL parsing with regex, can be extracted unchanged
- DB operations use simple SQLite, not GitHub API — can stay as-is

### Established Patterns
- GITHUB_TOKEN env var for auth (already used)
- Error classes (RateLimitError, GitHubAPIError) currently raised — will be replaced by PyGithub exceptions
- httpx used for non-API calls (raw.githubusercontent.com) — stays

### Integration Points
- GitHubProvider.crawl() calls `fetch_latest_release()` — needs PyGithub
- crawl.py uses `get_headers()` from github.py for API calls — needs update
- URL parsing used by both GitHubProvider and CLI — stays accessible

</code_context>

<deferred>
## Deferred Ideas

- Feeds.metadata migration for github_repos data — noted but not in Phase 15 scope (would be separate phase)
- OPML import/export — out of scope
- Multi-user support — out of scope

</deferred>
