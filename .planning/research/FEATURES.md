# Feature Research: Plugin-Based Provider Architecture

**Domain:** RSS Reader CLI - Feed Provider Plugin System
**Researched:** 2026-03-23
**Confidence:** MEDIUM (Web search unavailable; based on training data and codebase analysis)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **URL-based feed detection** | Users add URLs; system should auto-detect feed type | LOW | Already exists via `is_github_blob_url()`, `is_github_commits_url()` |
| **RSS/Atom parsing** | Standard feeds are RSS or Atom format | LOW | Already exists via `feedparser` in `feeds.py` |
| **Provider registration** | System must know which providers exist | LOW | Registry pattern with `match()` method per provider |
| **Refresh orchestration** | Unified refresh command across all providers | LOW | `refresh_feed()` already handles GitHub blob specially |
| **Tag rule application** | Auto-tagging after article storage | MEDIUM | Already exists via `tag_rules.py`, but needs chaining support |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Plugin priority ordering** | Most specific provider wins (e.g., GitHub before generic URL) | MEDIUM | `priority` integer; higher = checked first |
| **Provider-specific tag parsers** | Each provider can have custom tag extraction logic | MEDIUM | `tag_parsers` list chains results |
| **Chained tag parsing** | Multiple tag parsers combine results (union) | MEDIUM | Each parser sees original text + previous parser tags |
| **Graceful fallthrough** | Unknown URL types fall through to generic crawler | LOW | Catch-all provider at priority 0 |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Plugin hot-reloading** | "Add plugin without restart" appeal | Complexity, race conditions, security | CLI restart is fine for personal tool |
| **Plugin configuration per-instance** | "Different settings per feed" | State management explosion | Global plugin config + feed metadata |
| **Async plugin execution** | "Faster parallel fetching" | Thread safety, rate limiting complexity | Sequential for now; add async later if needed |
| **Plugin dependency ordering** | "Plugin A must run before Plugin B" | Circular dependency risk, complexity | Flat priority system; explicit `after` field if needed |

---

## Provider Plugin Pattern Analysis

### The Core Pattern: `match(URL) -> bool`

Each provider declares which URLs it can handle via a `match()` method:

```python
class FeedProvider:
    """Base class for feed providers."""

    def match(self, url: str) -> bool:
        """Return True if this provider can handle the URL."""
        raise NotImplementedError

    def priority(self) -> int:
        """Return priority (higher = checked first). Default 0."""
        return 0

    def crawl(self, url: str) -> Optional[dict]:
        """Fetch content from URL. Returns dict with keys: title, link, content, pub_date."""
        raise NotImplementedError

    def parse(self, content: bytes, url: str) -> list[Article]:
        """Parse fetched content into article list."""
        raise NotImplementedError

    def tag_parsers(self) -> list[TagParser]:
        """Return list of tag parsers for this provider. Empty = use global only."""
        return []
```

### Priority System

Providers are sorted by priority descending. First match wins.

```
Priority 100: GitHubProvider       (handles github.com URLs)
Priority  50: RSSProvider          (handles RSS/Atom feeds)
Priority  10: CrawlProvider        (handles arbitrary URLs via Readability)
Priority   0: FallbackProvider      (catch-all, lowest priority)
```

**Example priority assignment:**
```python
class GitHubProvider(FeedProvider):
    def priority(self) -> int:
        return 100  # Checked first

    def match(self, url: str) -> bool:
        return "github.com" in url.lower()

class RSSProvider(FeedProvider):
    def priority(self) -> int:
        return 50  # Checked second

    def match(self, url: str) -> bool:
        # Check if URL likely returns RSS/Atom
        return url.endswith(('.rss', '.atom', '.xml'))
```

### Crawl vs Parse Separation

The `crawl()` and `parse()` methods serve different purposes:

| Method | Responsibility | Input | Output |
|--------|---------------|-------|--------|
| `crawl()` | HTTP fetch, error handling, headers | URL string | Raw content bytes + metadata (etag, last_modified) |
| `parse()` | Content structure interpretation | Raw bytes + URL | List of `Article` objects |

**Why separate?** Allows caching at crawl layer while testing different parse strategies.

**Current codebase mapping:**
- `feeds.py::fetch_feed_content()` = crawl for RSS
- `feeds.py::parse_feed()` = parse for RSS
- `crawl.py::crawl_url()` = combined crawl+parse for generic URLs
- `github.py` = GitHub API calls (crawl via REST, parse into Release objects)

### Tag Parser Chaining Pattern

Tag parsers extract tags from article content. Each provider can have multiple tag parsers that chain:

```python
class TagParser:
    """Base class for tag parsers."""

    def parse(self, article: Article, context: dict) -> list[str]:
        """Extract tags from article.

        Args:
            article: The article to tag
            context: Dict with keys:
                - 'title': article title
                - 'description': article description/summary
                - 'content': article content
                - 'url': article URL
                - 'provider_tags': tags from previous parsers in chain

        Returns:
            List of tag names to apply (union with previous parser results)
        """
        raise NotImplementedError
```

**Chaining behavior:** Results are accumulated across parsers (union, not intersection).

```python
# Provider with chained tag parsers
class GitHubProvider(FeedProvider):
    def tag_parsers(self) -> list[TagParser]:
        return [
            LanguageTagParser(),      # Extract "python", "rust", etc.
            TopicTagParser(),         # Extract "cli", "web", "api", etc.
            OrgTagParser(),           # Extract org name from URL
        ]

# Chaining logic in caller:
def apply_tag_parsers(provider: FeedProvider, article: Article) -> list[str]:
    all_tags = []
    context = build_context(article)

    for parser in provider.tag_parsers():
        try:
            tags = parser.parse(article, {**context, 'provider_tags': all_tags})
            all_tags.extend(tags)
        except Exception as e:
            logger.warning(f"Tag parser {parser.__class__.__name__} failed: {e}")

    return list(set(all_tags))  # Deduplicate
```

---

## Feature Dependencies

```
FeedProvider.match()
    └──requires──> FeedProvider.priority() (for ordering)

FeedProvider.crawl()
    └──requires──> FeedProvider.parse() (result passed to parse)

FeedProvider.parse()
    └──requires──> TagParser.parse() (for tagging)
                       └──requires──> TagParser chain (union accumulation)

RefreshOrchestrator
    ├──requires──> All registered providers (sorted by priority)
    └──requires──> Database storage (store_article)
                       └──requires──> Tag rule application (tag_rules.py)
```

### Dependency Notes

- **Provider ordering by priority:** The registry must sort providers before checking `match()`. This is critical - GitHub provider must be checked before generic URL crawler.
- **Parse requires crawl result:** You cannot call `parse()` without first calling `crawl()` to get raw content.
- **Tag parsers chain after parse:** Tag parsing happens post-storage in current implementation (`apply_rules_to_article` after `refresh_feed` commit). In plugin model, this could be provider-specific.
- **Tag parser union vs intersection:** Currently `match_article_to_tags()` applies ALL matching rules (union). Chaining should preserve this behavior.

---

## MVP Definition

### Launch With (v1.3)

Minimum viable plugin architecture - what's needed to validate the concept.

- [ ] **Provider registry** - Dict or list storing registered providers, sorted by priority
- [ ] **Base `FeedProvider` class** - Abstract class with `match()`, `priority()`, `crawl()`, `parse()`, `tag_parsers()`
- [ ] **RSS provider implementation** - Wraps existing `feeds.py::refresh_feed()` logic
- [ ] **GitHub provider implementation** - Wraps existing `github.py` release/changelog logic
- [ ] **Priority-based dispatch** - `get_provider_for_url(url)` returns first matching provider
- [ ] **Unified refresh** - `refresh_url(url)` uses correct provider based on match

### Add After Validation (v1.4)

Features to add once core is working.

- [ ] **Crawl provider** - Wraps `crawl.py::crawl_url()` for arbitrary URLs
- [ ] **Tag parser chain** - Each provider can specify `tag_parsers()`
- [ ] **Provider tag parsers override** - Provider-specific parsers supplement global rules
- [ ] **CLI: `feed add` uses provider match** - Auto-detect provider type from URL

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Plugin discovery** - Auto-load plugins from `~/.radar/plugins/` directory
- [ ] **Plugin configuration** - Per-provider settings (auth tokens, custom headers)
- [ ] **Async parallel refresh** - Fetch from multiple providers concurrently

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Provider registry + dispatch | HIGH | LOW | P1 |
| RSS provider (wrap existing) | HIGH | LOW | P1 |
| GitHub provider (wrap existing) | HIGH | LOW | P1 |
| Priority-based match | HIGH | LOW | P1 |
| Crawl provider | MEDIUM | MEDIUM | P2 |
| Tag parser chaining | MEDIUM | MEDIUM | P2 |
| Plugin discovery | LOW | HIGH | P3 |
| Async refresh | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | FreshRSS (self-hosted) | Newsboat (terminal) | Our Approach |
|---------|----------------------|---------------------|--------------|
| Provider types | RSS/Atom only | RSS/Atom only | Plugin-based (RSS, GitHub, Crawl) |
| URL auto-detection | Manual feed search | Manual | match() method per provider |
| Tag extraction | None | None | Tag parser chain per provider |
| Priority/fallthrough | N/A | N/A | priority() integer method |

**Key insight:** Most RSS readers don't have plugin architectures because they're single-purpose. Our差异化 is supporting multiple source types (RSS, GitHub, generic URL) through unified interface.

---

## Implementation Sketch

### Provider Registry

```python
# src/providers/__init__.py
from abc import ABC, abstractmethod
from typing import Optional

class FeedProvider(ABC):
    @abstractmethod
    def match(self, url: str) -> bool:
        """Check if this provider handles the URL."""
        pass

    def priority(self) -> int:
        """Provider priority (higher = checked first)."""
        return 0

    @abstractmethod
    def crawl(self, url: str) -> tuple[Optional[bytes], dict]:
        """Fetch URL content. Returns (content, metadata_dict)."""
        pass

    @abstractmethod
    def parse(self, content: bytes, url: str) -> list[dict]:
        """Parse content into articles. Returns list of article dicts."""
        pass

    def tag_parsers(self) -> list['TagParser']:
        """Return tag parsers for this provider."""
        return []

class TagParser(ABC):
    @abstractmethod
    def parse(self, article: dict, context: dict) -> list[str]:
        """Extract tags from article."""
        pass

# Global registry
_providers: list[FeedProvider] = []

def register_provider(provider: FeedProvider) -> None:
    _providers.append(provider)
    _providers.sort(key=lambda p: p.priority(), reverse=True)

def get_provider_for_url(url: str) -> Optional[FeedProvider]:
    for provider in _providers:
        if provider.match(url):
            return provider
    return None
```

### RSS Provider (Wraps existing feeds.py)

```python
# src/providers/rss.py
class RSSProvider(FeedProvider):
    def priority(self) -> int:
        return 50

    def match(self, url: str) -> bool:
        return any(ext in url.lower() for ext in ['.rss', '.atom', '.xml', '/feed'])

    def crawl(self, url: str) -> tuple[Optional[bytes], dict]:
        from src.feeds import fetch_feed_content
        content, etag, last_modified, status = fetch_feed_content(url)
        return content, {'etag': etag, 'last_modified': last_modified}

    def parse(self, content: bytes, url: str) -> list[dict]:
        from src.feeds import parse_feed
        entries, bozo_flag, _ = parse_feed(content, url)
        # Convert feedparser entries to article dicts
        return [convert_entry(e) for e in entries]
```

### GitHub Provider (Wraps existing github.py)

```python
# src/providers/github.py
class GitHubProvider(FeedProvider):
    def priority(self) -> int:
        return 100  # Highest - GitHub URLs first

    def match(self, url: str) -> bool:
        return 'github.com' in url.lower()

    def crawl(self, url: str) -> tuple[Optional[bytes], dict]:
        # GitHub uses API, not raw fetch
        return None, {'url': url}

    def parse(self, content: bytes, url: str) -> list[dict]:
        from src.github import refresh_github_repo, get_github_repo_by_owner_repo
        from src.crawl import is_github_blob_url

        github_blob = is_github_blob_url(url)
        if github_blob:
            owner, repo, branch, path = github_blob
            gh_repo = get_github_repo_by_owner_repo(owner, repo)
            if gh_repo:
                result = refresh_changelog(gh_repo.id)
                # Convert to article dict
                return [convert_changelog_result(result)]
        # Handle release detection via API
        ...
```

---

## Sources

- Feedparser documentation (existing codebase patterns) - HIGH confidence
- Python plugin patterns (training data) - MEDIUM confidence
- Tag rule chaining (existing `tag_rules.py::match_article_to_tags`) - HIGH confidence

---

*Feature research for: Plugin-Based Provider Architecture v1.3*
*Researched: 2026-03-23*
