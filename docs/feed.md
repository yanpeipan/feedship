# Feed Provider Architecture

## Overview

Feed fetch is powered by a **plugin-based provider system**. Each URL type (RSS, GitHub, etc.) has its own provider that handles fetching, parsing, and tagging. No more `github_repos` table — everything is unified under `feeds` with provider logic handling type-specific behavior.

## Directory Structure

```
src/
├── cli.py                    # CLI (repo commands removed)
├── providers/
│   ├── rss_provider.py
│   └── github_provider.py
└── tags/
    └── default_tag_parser.py # AI-powered tagging
```

## Fetch Flow

```
fetch --all
  │
  ├─ feeds = list all feeds
  │
  ├─ providers = dynamically load all from src/providers/
  │
  └─ for each feed:
       │
       ├─ matched = providers.filter(p => p.match(feed.url))
       │             if empty: matched = [default_rss_provider]
       │
       ├─ sort matched by priority() descending
       │
       ├─ for provider in matched (try until crawl succeeds):
       │    try:
       │        raws = provider.crawl(feed.url)
       │    except Exception as e:
       │        log.error(f"{provider}: {e}")
       │        continue to next provider
       │
       ├─ articles = provider.parse(raw) for raw in raws
       │
       ├─ for article in articles:
       │    for tag_parser in provider.tag_parsers():
       │        tags = tag_parser.parse_tags(article)
       │    article.tags = merge_all_tags(tags)  # union, deduplicated
       │
       ├─ articles = feed_rules(articles)  # no-op, returns all
       │
       └─ store(articles)
```

## Provider Interface

```python
class Provider(ABC):
    @abstractmethod
    def match(self, url: str) -> bool:
        """Return True if this provider handles the URL."""

    @abstractmethod
    def priority(self) -> int:
        """Higher = tried first. Default RSS returns 0."""

    @abstractmethod
    def crawl(self, url: str) -> List[Raw]:
        """Fetch raw content from URL."""

    @abstractmethod
    def parse(self, raw: Raw) -> Article:
        """Convert Raw to Article."""

    def tag_parsers(self) -> List[TagParser]:
        """Return tag parsers for articles from this provider."""

    def parse_tags(self, article: Article) -> List[Tag]:
        """Parse tags for an article."""
```

## TagParser Interface

```python
class TagParser(ABC):
    @abstractmethod
    def parse_tags(self, article: Article) -> List[Tag]:
        """Return tags for this article."""
```

**Tag merging:** Union of all tags from all tag parsers, deduplicated.
`['a', 'b'] + ['a', 'c'] = ['a', 'b', 'c']`

## Provider Loading

- Discover: `glob("src/providers/*.py")`
- Import each module
- Class must be registered in a known registry (e.g., `PROVIDERS` dict)
- Load order: alphabetical by filename
- **Rule: Providers must not import each other** (avoid circular deps)
- Shared logic goes in `src/plugins/base.py`

## Database Schema

### feeds table — existing columns unchanged, new column:

```sql
ALTER TABLE feeds ADD COLUMN metadata TEXT;  -- JSON, e.g. {"github_token": "ghp_xxx"}
```

### github_repos table — drop after migration

Migration:
1. For each `github_repos` row with no corresponding `feeds` row: create a `feeds` row with `url = "https://github.com/{owner}/{repo}"` and `metadata = {"github_token": "...", "repo": "...", "owner": "..."}`
2. For `github_repos` rows with a corresponding `feeds` row: update `feeds.metadata` with token info
3. Drop `github_repos` table

## CLI Changes

- Remove: `repo add`, `repo list`, `repo remove`, `repo refresh`
- Keep: `feed add`, `feed list`, `feed remove`, `feed refresh`
- `feed add <url>` automatically selects the correct provider via `match()`
- GitHub URLs handled by `github_provider` automatically

## Default RSS Provider

- `match(url)` returns `False` (only matched as fallback)
- When no provider matches: `matched = [default_rss_provider]`
- `priority()` returns `0` (lowest)
