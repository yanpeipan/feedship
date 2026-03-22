# Project Research Summary

**Project:** Personal Information System (个人资讯系统)
**Domain:** CLI tool for RSS subscription and GitHub repository monitoring
**Researched:** 2026-03-23
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a Python CLI tool for collecting, organizing, and monitoring information from RSS feeds and GitHub repositories. The system stores content in SQLite, providing a local-first, no-API personal information hub. For v1.1, the project extends GitHub releases and changelog monitoring by treating GitHub repos as a specialized feed type, reusing existing storage patterns.

The recommended approach uses feedparser for RSS parsing, httpx for HTTP operations, BeautifulSoup4+lxml for HTML scraping, Scrapling for JavaScript-rendered pages, and click for CLI. GitHub integration uses the REST API directly with Bearer token auth (avoiding unnecessary dependencies like PyGithub). The architecture cleanly extends existing patterns by adding a `feed_type` column to discriminate between RSS, GitHub releases, and GitHub changelog sources.

Key risks: GitHub API rate limits (60/hour unauthenticated), changelog format variability, and potential Playwright browser installation failures. These must be addressed in Phase 1 with proper authentication, graceful degradation for missing changelogs, and verification of browser installation.

## Key Findings

### Recommended Stack

**Summary from STACK.md**

The project uses proven, well-documented Python libraries. The v1.1 addition introduces Scrapling (Python >=3.10 required) for GitHub changelog scraping alongside existing httpx-based GitHub API calls. Key decisions: use httpx directly for GitHub REST API (no PyGithub dependency), use Scrapling with Playwright as fallback for complex pages but simple HTTP for raw markdown files.

**Core technologies:**
- **feedparser 6.0.x**: Universal RSS/Atom parser with bozo detection for malformed feeds
- **httpx 0.27.x**: HTTP client for fetching pages and GitHub API calls with async support
- **BeautifulSoup4 4.12.x + lxml 5.x**: HTML parsing with fast C-based backend
- **Scrapling 0.4.2**: Adaptive web scraping with JS support (requires Python >=3.10)
- **sqlite3** (built-in): Local database with WAL mode for concurrent access
- **click 8.1.x**: CLI framework with decorator-based commands

### Expected Features

**Summary from FEATURES.md**

**Must have (table stakes):**
- Add GitHub repo by URL - Parse owner/repo from multiple GitHub URL formats
- GitHub API release fetch - Fetch tag_name, name, body, published_at, html_url
- Display releases like articles - Unified format with existing display patterns
- Refresh detection - Compare stored version vs API to surface new releases
- Basic changelog scraping - Fetch CHANGELOG.md from default branch

**Should have (competitive):**
- GitHub token auth - Use GITHUB_TOKEN env var, increases rate limit from 60 to 5000 req/hour
- Configurable changelog path - Support HISTORY.md, CHANGELOG.rst, user-specified paths

**Defer (v2+):**
- Changelog diff detection - Show what changed between version N and N-1
- Release asset downloads - Provide download links for binaries
- Native OS notifications - Alert when new release detected

### Architecture Approach

**Summary from ARCHITECTURE.md**

The architecture extends existing patterns by introducing feed type discrimination. A `feed_type` column in the feeds table distinguishes between `rss`, `github_release`, and `github_changelog` sources while using unified article storage. Two new modules (github.py, changelog.py) handle specialized fetching while feeds.py minimal changes.

**Major components:**
1. **feeds.py** (existing, extend): Generic feed CRUD with dispatch to type-specific refresh
2. **github.py** (NEW): GitHub API client handling releases, pagination, rate limit headers
3. **changelog.py** (NEW): CHANGELOG.md fetcher using Scrapling or raw HTTP
4. **db.py** (existing): SQLite with WAL mode, add feed_type column migration

**Key patterns:**
- **Feed Type Discrimination**: Single table with type column, dispatch to refresh logic
- **GitHub API as Feed Fetcher**: Releases map directly to article schema
- **Changelog as Single Article**: Store changelog with content hash for change detection

### Critical Pitfalls

**Top 5 from PITFALLS.md (both base and v1.1):**

1. **GitHub API Rate Limit Exhaustion** - 60 req/hour unauthenticated exhausts immediately with multiple repos. Prevention: Use GITHUB_TOKEN, check X-RateLimit-Remaining headers, cache responses for minimum 1 hour.

2. **SQLite Concurrent Write Contention** - SQLite allows only one writer. Prevention: Enable WAL mode, use busy_timeout=5000, batch writes.

3. **Malformed RSS/XML Feed Parsing** - Feeds fail silently. Prevention: Use feedparser with bozo detection, check bozo flag.

4. **Changelog File Not Found / Different Filenames** - CHANGELOG.md vs HISTORY.md vs CHANGES.md. Prevention: Check multiple common filenames, detect absence gracefully.

5. **Missing GUID/Item Identity** - Duplicates or missed items. Prevention: Use GUID when present, fall back to link+pubDate hash, handle isPermaLink="false".

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Project Foundation and GitHub API Base
**Rationale:** Dependencies (Python >=3.10, Scrapling browser install) must be verified before feature work. GitHub API client is the foundation for all v1.1 features.
**Delivers:** Working GitHub API client with token auth, rate limit handling, and release fetching.
**Addresses:** Add repo by URL, GitHub API release fetch
**Avoids:** GitHub API rate limit exhaustion (Pitfall 21), no auth token (Pitfall 26)
**Research flag:** None needed - GitHub REST API is well-documented

### Phase 2: Release Refresh Integration
**Rationale:** Must complete API client before integrating refresh logic into existing feeds system.
**Delivers:** Feeds table with feed_type column, release articles stored with proper identity (tag_name as guid)
**Uses:** github.py from Phase 1
**Implements:** Feed Type Discrimination pattern
**Avoids:** Missing GUID identity issues (Pitfall 2)

### Phase 3: Changelog Fetcher
**Rationale:** Changelog fetching is independent of release integration but depends on Scrapling installation verification.
**Delivers:** changelog.py module with multi-filename detection, content hash for change detection, raw HTTP for .md files (no Scrapling needed)
**Avoids:** Scrapling timeout on large files (Pitfall 25), changelog not found (Pitfall 23), parsing garbage (Pitfall 24)

### Phase 4: Changelog Refresh Integration
**Rationale:** Depends on changelog fetcher from Phase 3.
**Delivers:** github_changelog feed_type handling, changelog articles with version detection
**Avoids:** Mixed source confusion (Pitfall 26) - clearly label source

### Phase 5: CLI Integration and Unified Refresh
**Rationale:** Final integration phase bringing everything together.
**Delivers:** `github add`, `github add-changelog`, `github list` commands, unified `fetch --all` including GitHub sources
**Avoids:** CLI interactive prompts in scripts (Pitfall 8)

### Phase Ordering Rationale

- **Dependency order:** API client (1) before refresh integration (2), fetcher (3) before changelog integration (4)
- **Risk mitigation:** Verify Scrapling/Playwright installation in Phase 1 before Phase 3-4 depend on it
- **Architecture grouping:** GitHub releases (API) grouped separately from changelog (scraping) despite similar sources
- **Pitfall alignment:** Each phase explicitly addresses specific pitfalls from research

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Changelog Fetcher):** Format detection heuristics need validation with real-world changelogs

Phases with standard patterns (skip research-phase):
- **Phase 1 (GitHub API Base):** Well-documented GitHub REST API, straightforward implementation
- **Phase 2 (Release Refresh):** Follows existing feeds.py patterns, minimal new research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Based on official documentation for all libraries |
| Features | MEDIUM | GitHub monitoring features inferred from API docs and existing patterns; user validation needed |
| Architecture | HIGH | Extends existing codebase patterns with well-understood approaches |
| Pitfalls | MEDIUM-HIGH | Base RSS pitfalls HIGH confidence; GitHub-specific pitfalls MEDIUM due to rapid API changes |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Changelog format detection:** Real-world changelog formats vary more than Keep a Changelog standard. Needs testing with 5+ actual repositories during Phase 3.
- **User validation:** MVP features are inferred from API capabilities, not validated user research. Consider user interviews before Phase 5.
- **scrapling installation reliability:** Browser installation failure modes not fully documented. Test on clean system before Phase 3 begins.

## Sources

### Primary (HIGH confidence)
- [feedparser Documentation](https://feedparser.readthedocs.io/en/latest/) - RSS/Atom parsing
- [GitHub REST API - Releases](https://docs.github.com/en/rest/releases/releases) - Release endpoint specs
- [GitHub REST API - Rate Limits](https://docs.github.com/en/rest/rate-limit/rate-limit) - Auth and limits
- [Scrapling PyPI](https://pypi.org/project/scrapling/) - Python >=3.10 requirement
- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) - Format standard
- [SQLite Documentation](https://docs.python.org/3/library/sqlite3.html) - WAL mode, busy_timeout

### Secondary (MEDIUM confidence)
- [Scrapling GitHub repo](https://github.com/D4Vinci/Scrapling) - 31k stars, active development
- [RSS Board Feed Validator](https://www.rssboard.org/) - Common feed problems

---
*Research completed: 2026-03-23*
*Ready for roadmap: yes*
