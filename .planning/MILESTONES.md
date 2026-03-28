# Milestones

## v2.0 Search Ranking Architecture (Shipped: 2026-03-28)

**Phases completed:** 4 phases, 4 plans, 7 tasks

**Key accomplishments:**

- Extended ArticleListItem with 6 scoring fields; fixed search_articles_semantic P0 crash on INTEGER pub_date; returns raw cos_sim without weighted formula
- BM25 sigmoid normalization and freshness scoring populated in storage layer, enabling Phase 43 combine_scores application layer
- Cross-Encoder rerank with BAAI/bge-reranker-base and combine_scores using Newton's cooling law for unified ranking
- article search command wired with Phase 43 scoring infrastructure: --rerank flag, semantic path (gamma=0.2, delta=0.0), FTS5 path (gamma=0.0, delta=0.2), both using asyncio.to_thread() for Cross-Encoder reranking

---

## v1.9 Automatic Discovery Feed (Shipped: 2026-03-27)

**Phases completed:** 7 phases, 10 plans, 17 tasks

**Key accomplishments:**

- Discovery Core Module (`src/discovery/`) with HTML `<link>` tag parsing, well-known path fallback, URL resolution, and feed validation
- `discover <url>` CLI command with `--discover-deep [n]` for feed discovery without subscription
- `feed add <url> --discover --automatic` integration for discovery during subscription
- BFS crawler with visited-set deduplication, 2s/host rate limiting, and CSS selector-based link discovery
- robots.txt compliance via robotexclusionrulesparser in lazy mode
- Multi-factor ranking: `final_score = 0.5*norm_similarity + 0.3*norm_freshness + 0.2*source_weight`
- Documentation: `docs/Automatic Discovery Feed.md`

---

## v1.4 Storage Layer Enforcement (Shipped: 2026-03-24)

**Phases completed:** 20 phases, 39 plans, 99 tasks

**Key accomplishments:**

- SQLite database with WAL mode, Feed/Article dataclasses, and project dependencies configured
- Feed CRUD operations with RSS/Atom parsing, bozo detection, and article deduplication via GUID/UNIQUE constraint
- Click-based CLI with feed management and article listing commands with ANSI colors and per-feed error isolation
- Commit:
- Article search subcommand added to CLI with FTS5-powered full-text search via search_articles() function
- One-liner:
- crawl_url() function with Readability extraction, robots.txt lazy compliance, and 2-second per-host rate limiting
- `crawl` CLI command with --ignore-robots flag wrapping crawl_url() for web content extraction
- GitHub API client with URL parsing, Bearer token auth, rate limit handling, and release data models
- GitHub repo management CLI with add, list, remove, and refresh commands
- Changelog detection and scraping via raw.githubusercontent.com with database schema support for GitHub-article association
- CLI commands for viewing and refreshing GitHub repository changelogs with --refresh flag
- GitHub releases appear alongside feed articles in unified listing and search with source info
- CLI updated to display GitHub source info (repo@tag) and integrate GitHub repo refresh into fetch --all command
- FTS sync added to store_changelog_as_article() so changelog articles are searchable via articles_fts
- Tag and article tagging infrastructure with SQLite many-to-many relationship, CLI commands, and tag filtering
- Keyword/regex rule matching and AI clustering for automatic article tagging
- GitHub blob URLs extract title from H1 heading via Contents API, commits URLs use commit timestamp as pub_date, with graceful fallback on API failure
- GitHub blob URL feeds now work via `feed add` - routes to changelog storage, `fetch --all` refreshes without error
- Unified store_article() function in db.py replacing 70+ lines of inline SQL in store_changelog_as_article()
- Rich table formatting with batch tag fetching - N+1 query problem fixed
- GitHub releases can now be tagged using article tag commands with auto-detection
- ContentProvider Protocol with @runtime_checkable, ProviderRegistry with discover/discover_or_default, and DefaultRSSProvider fallback
- RSS and GitHub content providers with self-registration, wrapping existing feeds.py and github.py logic
- Tag parser plugin system with dynamic loading, DefaultTagParser wrapping tag_rules, and chain_tag_parsers() wired into RSSProvider/GitHubProvider
- fetch --all refactored to use discover_or_default() provider pattern
- feed add/list wired to provider discovery with Type column display
- CLI repo command group removed, GitHub management unified under feed command via ProviderRegistry
- New src/github_utils.py and src/github_ops.py modules with PyGithub dependency added
- GitHubProvider and crawl.py migrated from httpx-based src.github to PyGithub library
- GitHubReleaseProvider (priority 200) and ReleaseTagParser for extracting release-specific tags (version numbers, release types) from GitHub releases using PyGithub
- Plan:
- RSSProvider.feed_meta() uses lightweight httpx.get() with 5s timeout instead of expensive crawl() call
- All database operations centralized in src/storage/sqlite.py; no direct get_db() calls remain outside the storage layer.
- Phase:

---

## v1.3 Provider Architecture (Shipped: 2026-03-23)

**Phases completed:** 4 phases, 9 plans, 19 tasks

**Key accomplishments:**

- ContentProvider Protocol with @runtime_checkable, ProviderRegistry with discover/discover_or_default, and DefaultRSSProvider fallback
- RSS and GitHub content providers with self-registration, wrapping existing feeds.py and github.py logic
- Tag parser plugin system with dynamic loading, DefaultTagParser wrapping tag_rules, and chain_tag_parsers() wired into RSSProvider/GitHubProvider
- fetch --all refactored to use discover_or_default() provider pattern
- feed add/list wired to provider discovery with Type column display
- CLI repo command group removed, GitHub management unified under feed command via ProviderRegistry
- New src/github_utils.py and src/github_ops.py modules with PyGithub dependency added
- GitHubProvider and crawl.py migrated from httpx-based src.github to PyGithub library

---

## v1.2 Article List Enhancements (Shipped: 2026-03-23)

**Phases completed:** 4 phases, 5 plans, 11 tasks

**Key accomplishments:**

- GitHub blob URL feeds now work via `feed add` - routes to changelog storage, `fetch --all` refreshes without error
- Unified store_article() function in db.py replacing 70+ lines of inline SQL in store_changelog_as_article()
- Rich table formatting with batch tag fetching - N+1 query problem fixed
- GitHub releases can now be tagged using article tag commands with auto-detection

---

## v1.0 MVP (Shipped: 2026-03-22)

**Phases completed:** 3 phases, 9 plans, 12 tasks

**Key accomplishments:**

- SQLite database with WAL mode, Feed/Article dataclasses, and project dependencies configured
- Feed CRUD operations with RSS/Atom parsing, bozo detection, and article deduplication via GUID/UNIQUE constraint
- Click-based CLI with feed management and article listing commands with ANSI colors and per-feed error isolation
- Article search subcommand added to CLI with FTS5-powered full-text search via search_articles() function
- crawl_url() function with Readability extraction, robots.txt lazy compliance, and 2-second per-host rate limiting
- `crawl` CLI command with --ignore-robots flag wrapping crawl_url() for web content extraction

---

## v1.1 GitHub Monitoring + Tagging (Shipped: 2026-03-23)

**Phases completed:** 4 phases, 10 plans

**Key accomplishments:**

- GitHub API client with Bearer token auth, rate limit handling
- Changelog detection and scraping via raw.githubusercontent.com
- Unified display and refresh integration for GitHub releases and feed articles
- Tag and article tagging infrastructure with SQLite many-to-many relationship, CLI commands, and tag filtering
- Keyword/regex rule matching and AI clustering for automatic article tagging
- `tag rule edit` command to modify existing tag rules

---

## v1.2 Article List Enhancements (Shipped: 2026-03-23)

**Phases completed:** 5 phases, 5 plans, 14 tasks

**Key accomplishments:**

- GitHub blob URL support in `feed add` - routes to changelog storage automatically
- Unified `store_article()` function replacing 70+ lines of inline SQL
- Rich table formatting for article list with ID and tags columns
- `article view` and `article open` commands for article details
- GitHub release tagging with auto-detection (release vs article IDs)
