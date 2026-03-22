# Phase 3: Web Crawling - Research

**Researched:** 2026-03-23
**Domain:** Web content extraction, crawler ethics (robots.txt), rate limiting
**Confidence:** HIGH

## Summary

Phase 3 adds web crawling capability: users can run `crawl <url>` to fetch any webpage and store its extracted content as an article. The implementation uses Mozilla's Readability algorithm (via `readability-lxml`) for high-quality article extraction, respects robots.txt lazily (ignored by default, opt-in via `--ignore-robots`), and enforces a 2-second rate limit between requests to the same host. Crawled content is stored in the existing `articles` table with a special system feed `feed_id='crawled'` so it reuses all existing article list and search functionality.

**Primary recommendation:** Implement `crawl_url()` in a new `src/crawl.py` module, add `crawl` CLI command in `src/cli.py`, and ensure the 'crawled' system feed exists in `src/db.py` or on first use.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Use Readability algorithm for article content extraction
- **D-02:** Lazy mode — robots.txt ignored by default, `--ignore-robots` flag forces compliance
- **D-03:** Fixed 2-second delay between requests to same host
- **D-04:** Full text extraction, stored in `content` field
- **D-05:** Log and skip error handling
- **D-06:** `crawl <url>` with optional `--ignore-robots` flag
- **D-07:** Store in articles table (reuses existing article list/search)
- **D-08:** System feed `feed_id='crawled'`, display name "Crawled Pages"

### Claude's Discretion
- Exact log message wording and verbosity levels
- How to handle edge cases in Readability extraction

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-04 | `crawl <url>` - Fetch and store content from URL | New `crawl` command in cli.py using `crawl_url()` |
| CRAWL-01 | User can add website URL to crawl | `crawl_url()` accepts any HTTP/HTTPS URL |
| CRAWL-02 | System fetches HTML and extracts article-like content | `readability-lxml` `Document().summary()` extracts clean HTML content |
| CRAWL-03 | System respects robots.txt directives | `robotexclusionrulesparser` library checks Allow/Disallow rules |
| CRAWL-04 | System implements rate limiting (1-2s delay) | `time.sleep(2)` with host-based tracking dict |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **readability-lxml** | 0.8.4.1 | Article content extraction | Python port of Firefox Reader View algorithm; extracts title + clean HTML body from any webpage |
| **robotexclusionrulesparser** | 1.7.1 | robots.txt parsing | Mature library handling all robot exclusion directives (Allow, Disallow, Crawl-delay, etc.) |
| **httpx** | 0.28.1 | HTTP client | Already in project; sync API with timeout support |
| **beautifulsoup4** | 4.12.3 | HTML parsing | Already in project; works with lxml backend |
| **lxml** | 6.0.2 | Fast HTML parser | Already in project; recommended backend for BeautifulSoup |

### Installation
```bash
pip install readability-lxml robotexclusionrulesparser
```

**Verified versions:** `readability-lxml 0.8.4.1` (May 2025), `robotexclusionrulesparser 1.7.1`

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| readability-lxml | mozilla-readability | Same algorithm, readability-lxml is more actively maintained |
| readability-lxml | html2text | html2text converts to markdown, less accurate than Readability for article extraction |
| robotexclusionrulesparser | Manual regex parsing | Error-prone; robots.txt has subtle syntax rules |
| robotexclusionrulesparser | reppy | C++ based, harder to install |
| 2s fixed delay | Adaptive delay (crawl-delay directive) | D-03 explicitly specifies fixed 2s; crawl-delay adds complexity |

## Architecture Patterns

### Recommended Project Structure
```
src/
├── crawl.py       # NEW: crawl_url() with Readability extraction, robots.txt, rate limiting
├── feeds.py       # Existing: feed fetching patterns
├── articles.py    # Existing: ArticleListItem, list_articles(), search_articles()
├── db.py          # Existing: schema, init_db(), get_connection()
├── cli.py         # Existing: click commands; ADD: crawl command
└── models.py      # Existing: Feed, Article dataclasses
```

### Pattern 1: Crawl Command Flow
**What:** Single URL crawling with robots.txt check, rate limiting, content extraction
**When to use:** The `crawl <url>` CLI command
**Example:**
```python
# src/crawl.py
import time
import logging
from urllib.parse import urlparse
from typing import Optional
import httpx
from readability import Document
from robotexclusionrulesparser import RobotExclusionRulesParser

logger = logging.getLogger(__name__)

# Rate limiting state: {host: last_request_timestamp}
_rate_limit_state: dict[str, float] = {}

def crawl_url(url: str, ignore_robots: bool = False) -> Optional[dict]:
    """Fetch and extract article content from a URL.

    Args:
        url: URL to crawl
        ignore_robots: If True, skip robots.txt check

    Returns:
        Dict with title, link, content, or None on failure
    """
    parsed = urlparse(url)
    host = parsed.netloc

    # Rate limiting: wait 2s since last request to this host
    if host in _rate_limit_state:
        elapsed = time.time() - _rate_limit_state[host]
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
    _rate_limit_state[host] = time.time()

    # robots.txt check (unless ignored)
    if not ignore_robots:
        robots_url = f"{parsed.scheme}://{host}/robots.txt"
        try:
            parser = RobotExclusionRulesParser()
            response = httpx.get(robots_url, timeout=10.0)
            parser.parse(response.text)
            if not parser.can_fetch(url, "*"):
                logger.warning("Blocked by robots.txt: %s", url)
                return None
        except Exception as e:
            logger.warning("Failed to fetch robots.txt for %s: %s", host, e)
            # In lazy mode, continue on robots.txt errors

    # Fetch page content
    try:
        response = httpx.get(url, timeout=30.0)
        response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPError, httpx.TimeoutException) as e:
        logger.error("Failed to fetch %s: %s", url, e)
        return None

    # Extract content with Readability
    try:
        doc = Document(response.text)
        title = doc.title()
        # summary() returns HTML; strip tags for plain text content
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(doc.summary(), 'html.parser')
        content = soup.get_text(separator='\n', strip=True)

        return {
            'title': title,
            'link': url,
            'content': content,
        }
    except Exception as e:
        logger.error("Failed to extract content from %s: %s", url, e)
        return None
```

### Pattern 2: System Feed Creation
**What:** Ensure 'crawled' system feed exists for crawled articles
**When to use:** On first crawl or in init_db()
**Example:**
```python
# In db.py or crawl.py
def ensure_crawled_feed():
    """Create 'crawled' system feed if it doesn't exist."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM feeds WHERE id = 'crawled'")
        if cursor.fetchone() is None:
            now = datetime.now(timezone.utc).isoformat()
            cursor.execute(
                """INSERT INTO feeds (id, name, url, created_at)
                   VALUES ('crawled', 'Crawled Pages', '', ?)""",
                (now,)
            )
            conn.commit()
    finally:
        conn.close()
```

### Pattern 3: FTS5 Sync for Crawled Articles
**What:** Sync newly crawled article to FTS5 index
**When to use:** After inserting crawled article into articles table
**Example:**
```python
# Reuse pattern from refresh_feed() in feeds.py
# After INSERT INTO articles:
cursor.execute(
    """INSERT INTO articles_fts(rowid, title, description, content)
       SELECT id, title, description, content FROM articles WHERE id = ?""",
    (article_id,)
)
```

### Anti-Patterns to Avoid
- **Don't extract content before checking robots.txt:** Respect crawl directives even in lazy mode (D-02 says ignore by default, not ignore entirely)
- **Don't use a single global rate limit:** Rate limit by host (D-03: "same host"), not globally
- **Don't store raw HTML in content field:** Use Readability's `summary()` which returns clean HTML, then extract text with BeautifulSoup

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| robots.txt parsing | Custom regex on robots.txt | robotexclusionrulesparser | Edge cases: comments, wildcards, crawl-delay, sitemap directives |
| Content extraction | regex or BeautifulSoup-only extraction | readability-lxml | Readability is specifically tuned for article extraction; handles ads, nav, sidebars |
| Rate limiting by host | Global lock or simple sleep | dict-based host tracking with time tracking | Allows concurrent crawls to different hosts while respecting same-host limits |

**Key insight:** robots.txt has subtle parsing rules (comments, empty lines, wildcard handling, crawl-delay directives). A library handles these correctly; manual parsing will have edge case bugs.

## Common Pitfalls

### Pitfall 1: robots.txt Fetch Fails Silently
**What goes wrong:** If robots.txt fetch fails (404, timeout), lazy mode continues but might crawl disallowed pages
**Why it happens:** D-02 says robots.txt is "ignored by default" — but if fetch fails in lazy mode, we proceed without knowing if the page is allowed
**How to avoid:** Log a warning when robots.txt fetch fails so user knows compliance is uncertain; the `--ignore-robots` flag makes intent explicit
**Warning signs:** Warning log message "Failed to fetch robots.txt for {host}"

### Pitfall 2: Readability Fails on Non-Article Pages
**What goes wrong:** Homepages, landing pages, documentation — Readability may extract very little or wrong content
**Why it happens:** Readability is optimized for article-style pages; it looks for `<article>`, main content divs, etc.
**How to avoid:** Handle extraction failures gracefully (D-05: log and skip); consider detecting low-quality extraction (e.g., very short content < 100 chars)
**Warning signs:** Log message "Failed to extract content from {url}"

### Pitfall 3: Rate Limit State Grows Unbounded
**What goes wrong:** `_rate_limit_state` dict grows indefinitely if crawling many unique hosts
**Why it happens:** Never cleaned up
**How to avoid:** Use `collections.OrderedDict` with max size, or accept unbounded growth (for personal use, unlikely to hit memory issues)

### Pitfall 4: FTS5 Not Synced for Crawled Articles
**What goes wrong:** Crawled articles don't appear in search results
**Why it happens:** Forgot to sync to articles_fts after INSERT
**How to avoid:** Reuse the same FTS5 sync pattern from refresh_feed()

## Code Examples

### Readability Content Extraction
```python
# Source: readability-lxml documentation
from readability import Document
import httpx
from bs4 import BeautifulSoup

response = httpx.get(url, timeout=30.0)
doc = Document(response.text)

title = doc.title()  # Extract article title
html_content = doc.summary()  # Clean HTML of main content

# Convert to plain text for storage
soup = BeautifulSoup(html_content, 'html.parser')
content = soup.get_text(separator='\n', strip=True)
```

### robots.txt Check
```python
# Source: robotexclusionrulesparser documentation
from robotexclusionrulesparser import RobotExclusionRulesParser
import httpx

parser = RobotExclusionRulesParser()
response = httpx.get(f"https://{host}/robots.txt", timeout=10.0)
parser.parse(response.text)

if parser.can_fetch(url, "*"):
    # Allowed to crawl
    pass
else:
    # Blocked
    pass
```

### Rate Limiting by Host
```python
# Source: D-03 decision (2-second delay)
import time
from urllib.parse import urlparse

_rate_limit_state: dict[str, float] = {}

def respect_rate_limit(url: str) -> None:
    host = urlparse(url).netloc
    if host in _rate_limit_state:
        elapsed = time.time() - _rate_limit_state[host]
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
    _rate_limit_state[host] = time.time()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| regex content extraction | Readability algorithm | N/A | Major improvement in article extraction quality |
| ignoring robots.txt entirely | lazy mode (ignore by default, opt-in compliance) | D-02 | Balances convenience with ethics |
| no rate limiting | 2-second per-host delay | D-03 | Avoids being blocked while remaining fast |

**Deprecated/outdated:**
- `html2text` library: Less accurate than Readability for article extraction

## Open Questions

1. **What user-agent string should crawls use?**
   - What we know: Could use fake-useragent or custom string
   - What's unclear: Whether to set a recognizable user-agent for site admins
   - Recommendation: Use generic Python/httpx user-agent (e.g., "Python-httpx/0.28.1") or set custom one like "PersonalNewsReader/0.1"

2. **Should crawled articles have a GUID?**
   - What we know: Existing articles use guid from feed; crawled content has no guid
   - What's unclear: Should we generate GUID from URL hash, or use URL itself?
   - Recommendation: Use URL as guid (with crawl prefix) to avoid duplicates

3. **What pub_date should crawled articles have?**
   - What we know: Articles table has pub_date field; crawled pages don't have a feed-provided date
   - What's unclear: Use crawl time as pub_date, or try to extract from page?
   - Recommendation: Use crawl time (current timestamp) since no publication date is available from the page itself

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | Yes | 3.13.5 | — |
| httpx | HTTP fetching | Yes | 0.28.1 | — |
| beautifulsoup4 | HTML parsing | Yes | 4.12.3 | — |
| lxml | HTML parser backend | Yes | 6.0.2 | — |
| readability-lxml | Content extraction | No | — | Install via pip |
| robotexclusionrulesparser | robots.txt parsing | No | — | Install via pip |

**Missing dependencies with no fallback:**
- None — all required packages are pip-installable

**Missing dependencies with fallback:**
- `readability-lxml` — Can use `html2text` as fallback but quality will be lower
- `robotexclusionrulesparser` — Could skip check entirely (matches lazy mode intent)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (if existing test infrastructure) |
| Config file | none detected — check for pytest.ini or pyproject.toml |
| Quick run command | `pytest tests/` |
| Full suite command | `pytest -v tests/` |

*Note: No existing test infrastructure detected in scan. Phase 1/2 did not include tests.*

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-04 | `crawl <url>` command exists and accepts --ignore-robots | unit/manual | `python -m src.cli crawl --help` | N/A |
| CRAWL-01 | crawl_url() fetches any HTTP/HTTPS URL | unit | `pytest tests/test_crawl.py::test_crawl_url_fetches` | NO |
| CRAWL-02 | Readability extracts article content | unit | `pytest tests/test_crawl.py::test_readability_extraction` | NO |
| CRAWL-03 | robots.txt is respected (unless --ignore-robots) | unit | `pytest tests/test_crawl.py::test_robots_respected` | NO |
| CRAWL-04 | 2-second rate limit between same-host requests | unit | `pytest tests/test_crawl.py::test_rate_limiting` | NO |

### Sampling Rate
- **Per task commit:** `pytest tests/test_crawl.py -x`
- **Per wave merge:** Full suite not applicable (no tests yet)
- **Phase gate:** Manual verification required

### Wave 0 Gaps
- [ ] `tests/test_crawl.py` — covers CRAWL-01, CRAWL-02, CRAWL-03, CRAWL-04
- [ ] `tests/conftest.py` — shared fixtures (if needed)
- Framework install: `pip install pytest` — if not detected

*(No existing test infrastructure found — Phase 1 and 2 did not include tests)*

## Sources

### Primary (HIGH confidence)
- [readability-lxml PyPI](https://pypi.org/project/readability-lxml/) - Version 0.8.4.1, May 2025
- [robotexclusionrulesparser PyPI](https://pypi.org/project/robotexclusionrulesparser/) - Version 1.7.1
- [readability documentation](https://readibility.readthedocs.io/) - Document API (title(), summary())
- Existing codebase: `src/feeds.py` for fetch patterns, `src/db.py` for schema, `src/cli.py` for command patterns

### Secondary (MEDIUM confidence)
- [robotexclusionrulesparser patterns from general web search] - Verified library exists and has correct API

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified packages exist with correct versions
- Architecture: HIGH - Reuses established patterns from Phase 1/2
- Pitfalls: MEDIUM - Based on general web scraping experience, not specific project history

**Research date:** 2026-03-23
**Valid until:** 2026-04-23 (30 days for stable stack)
