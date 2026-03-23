# Phase 13: Provider Implementations + Tag Parsers - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement concrete RSS and GitHub content providers that wrap existing feeds.py and github.py logic, plus tag parser chaining. Phase 13 delivers working providers; Phase 14 wires them into CLI commands.

</domain>

<decisions>
## Implementation Decisions

### RSS Provider Architecture
- **D-01:** RSSProvider wraps feeds.py fetch_feed_content() + parse_feed() — not add_feed/list_feeds/remove_feed (those are CLI-level operations)
- **D-02:** RSSProvider.match() detects RSS/Atom URLs — use httpx HEAD request to check Content-Type header for "application/rss" or "application/atom"
- **D-03:** RSSProvider.priority() = 50 (higher than DefaultRSSProvider's 0, lower than GitHub's 100)
- **D-04:** RSSProvider.crawl() returns List[Raw] where Raw = dict from feedparser entry
- **D-05:** RSSProvider.parse(raw) converts feedparser entry dict to Article dict with fields: title, link, guid, pub_date, description, content
- **D-06:** RSSProvider uses DefaultTagParser via tag_parsers() chain

### GitHub Provider Architecture
- **D-07:** GitHubProvider wraps github.py fetch_latest_release() + related functions — not add_github_repo/list_github_repos/remove_github_repo (CLI-level)
- **D-08:** GitHubProvider.match() detects github.com URLs using urlparse — matches https://github.com/* patterns
- **D-09:** GitHubProvider.priority() = 100 (highest, tried first)
- **D-10:** GitHubProvider.crawl() calls fetch_latest_release() and returns List[Raw] with release dict
- **D-11:** GitHubProvider.parse(raw) converts release dict to Article dict with fields: title (tag_name), link (html_url), guid (tag_name), pub_date (published_at), description (body), content (None)
- **D-12:** GitHubProvider uses DefaultTagParser via tag_parsers() chain

### Tag Parser Chaining
- **D-13:** DefaultTagParser wraps tag_rules.py match_article_to_tags() function
- **D-14:** DefaultTagParser.parse_tags(article) calls match_article_to_tags(article.title, article.description) and returns list of tag strings
- **D-15:** Provider.parse_tags() chains all tag parsers: runs each parser's parse_tags(), returns union with duplicates removed
- **D-16:** Tag parsers are loaded dynamically from src/tags/ directory (parallel to providers), matching pattern *tag*.py

### File Locations
- **D-17:** src/providers/rss_provider.py — RSSProvider class
- **D-18:** src/providers/github_provider.py — GitHubProvider class
- **D-19:** src/tags/__init__.py — TagParser registry (parallel to providers/__init__.py)
- **D-20:** src/tags/default_tag_parser.py — DefaultTagParser wrapping tag_rules.py

### Integration Notes
- **D-21:** Existing feeds.py add_feed(), refresh_feed() are NOT refactored — providers are new code that wraps similar logic
- **D-22:** github_repos table still exists in DB (per Phase 12 verification) — GitHubProvider crawls via GitHub API, not via DB
- **D-23:** Article dict structure: {title, link, guid, pub_date, description, content} — Raw is provider-specific (feedparser entry for RSS, release dict for GitHub)

</decisions>

<specifics>
## Specific Ideas

- match() uses lightweight URL parsing — no HTTP request needed for URL matching
- crawl() failure returns empty list (caller handles retry via error isolation in Phase 14)
- parse_tags() does NOT modify article dict — returns tags for caller to use
- No NotImplementedError in concrete provider methods — all methods fully implemented
- Provider files self-register via PROVIDERS.append() at module import time (same pattern as DefaultRSSProvider)

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Provider Architecture (Phase 12)
- `src/providers/base.py` — ContentProvider and TagParser Protocols with @runtime_checkable
- `src/providers/__init__.py` — ProviderRegistry with discover(), discover_or_default()
- `src/providers/default_rss_provider.py` — Example of self-registration pattern

### Existing Logic to Wrap
- `src/feeds.py` — fetch_feed_content(), parse_feed(), generate_article_id()
- `src/github.py` — parse_github_url(), fetch_latest_release()
- `src/tag_rules.py` — match_article_to_tags(), apply_rules_to_article()

### Data Models
- `src/models.py` — Feed, Article, Tag dataclasses

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- feedparser entry dict structure already has title, link, id, published, description, content fields
- github.py release dict has tag_name, name, body, html_url, published_at
- tag_rules.py has match_article_to_tags() that takes (title, description) and returns tag list

### Established Patterns
- Self-registration via module-level PROVIDERS.append()
- @runtime_checkable Protocol for isinstance() checks
- Error isolation: crawl() returns empty list on failure (not exceptions)
- Article dict as flexible return type (Raw is provider-specific)

### Integration Points
- providers/__init__.py already loads all *provider.py from src/providers/
- Need parallel src/tags/ directory for tag parser dynamic loading
- Phase 14 will wire providers into CLI via ProviderRegistry.discover()

</code_context>

<deferred>
## Deferred Ideas

None — Phase 13 scope is well-defined.

</deferred>
