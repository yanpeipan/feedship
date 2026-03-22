# Technology Stack: Personal Information System

**Project Type:** CLI tool for RSS subscription and website crawling
**Researched:** 2026-03-22 (v1.0), 2026-03-23 (v1.1 additions)
**Confidence:** HIGH

## Recommended Stack

### RSS Parsing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **feedparser** | 6.0.x | Universal feed parser | Handles RSS 0.9x, RSS 1.0, RSS 2.0, CDF, Atom 0.3, Atom 1.0. The de-facto standard for feed parsing in Python. Active maintenance, Python >=3.6 support. |

**Installation:** `pip install feedparser`

**Basic Usage:**
```python
import feedparser
feed = feedparser.parse('https://example.com/feed.xml')
for entry in feed.entries:
    print(entry.title, entry.link)
```

---

### HTML Scraping

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **httpx** | 0.27.x | HTTP client | Modern async/sync HTTP client with requests-compatible API. HTTP/2 support. Use for fetching HTML pages. |
| **BeautifulSoup4** | 4.12.x | HTML parsing | Intuitive navigation of parsed HTML. Works with multiple parsers (html.parser built-in, lxml, html5lib). |
| **lxml** | 5.x | Fast parser | C-based HTML/XML parser. Recommended backend for BeautifulSoup (faster than html.parser). |
| **Playwright** | 1.49.x | Browser automation | For JavaScript-rendered pages. Supports Chromium, WebKit, Firefox. Headless or headed. Use as fallback for SPA sites. |

**Installation:**
```bash
pip install httpx beautifulsoup4 lxml
pip install playwright && playwright install  # Optional, for JS sites
```

**Basic Usage (static pages):**
```python
import httpx
from bs4 import BeautifulSoup

response = httpx.get('https://example.com')
soup = BeautifulSoup(response.text, 'lxml')
for link in soup.find_all('a', class_='article-link'):
    print(link.get('href'))
```

**Basic Usage (JavaScript-rendered pages):**
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://example.com')
    content = page.content()
    browser.close()
```

---

### SQLite Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **sqlite3** | (built-in) | Database | No external dependencies. DB-API 2.0 compliant. Sufficient for personal information system with moderate data volumes. |
| **SQLAlchemy** | 2.0.x | ORM (optional) | Only if you need complex relationships, migrations, or prefer ORM-style code. Adds dependency overhead. |

**Recommendation:** Start with `sqlite3` (built-in). Add SQLAlchemy only if relationships or migration tooling become necessary.

**sqlite3 Basic Usage:**
```python
import sqlite3

con = sqlite3.connect('data.db')
cur = con.cursor()

# Create table
cur.execute('''CREATE TABLE IF NOT EXISTS feeds
               (id INTEGER PRIMARY KEY, url TEXT UNIQUE, title TEXT)''')

# Insert with parameterized query (prevents SQL injection)
cur.execute('INSERT OR IGNORE INTO feeds (url, title) VALUES (?, ?)',
            ('https://example.com/feed.xml', 'Example Feed'))

# Query
for row in cur.execute('SELECT * FROM feeds'):
    print(row)

con.commit()
con.close()
```

**Row Factory for dict-like access:**
```python
con.row_factory = sqlite3.Row
row = cur.execute('SELECT * FROM feeds').fetchone()
print(row['url'])  # Access by column name
```

---

### CLI Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **click** | 8.1.x | CLI framework | Decorator-based, composable, automatic help generation. Most popular modern CLI framework for Python. |
| **argparse** | (built-in) | CLI framework | Standard library. More verbose than click. Use only if avoiding dependencies is critical. |

**Recommendation:** **click** for its clean decorator syntax and widespread adoption.

**Installation:** `pip install click`

**Basic Usage:**
```python
import click

@click.group()
def cli():
    """Personal Information System CLI."""
    pass

@cli.command()
@click.option('--count', default=1, help='Number of items to process')
@click.argument('url')
def fetch(count, url):
    """Fetch entries from a feed URL."""
    click.echo(f'Fetching {count} entries from {url}')

@cli.command()
def list():
    """List all subscribed feeds."""
    click.echo('Listing all feeds...')

if __name__ == '__main__':
    cli()
```

---

## v1.1 Addition: GitHub Monitoring

### GitHub Releases API (httpx - already installed)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| httpx | 0.27.x | GitHub REST API calls | Already in use. Direct REST calls with Bearer token auth are straightforward. No new dependency needed. |

**No new installation required** - use existing httpx.

**Basic Usage:**
```python
import httpx

headers = {
    "Authorization": f"Bearer {github_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

# List releases
response = httpx.get(
    f"https://api.github.com/repos/{owner}/{repo}/releases",
    headers=headers,
    timeout=10.0
)
releases = response.json()

# Get latest release
response = httpx.get(
    f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
    headers=headers
)
latest = response.json()
# Fields: tag_name, name, body (markdown), published_at, html_url, author
```

**Rate Limits:** 60 req/hr unauthenticated, 5000 req/hr authenticated (with personal access token).

**For unauthenticated (rate limited):**
```python
# Works without token, 60 req/hr limit
response = httpx.get(
    f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
    headers={"Accept": "application/vnd.github+json"}
)
```

---

### GitHub Changelog Scraping

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **scrapling** | 0.4.2 | Adaptive web scraping with JS support | Handles dynamic content, undetected scraping, flexible extraction. Already decided in PROJECT.md. Python >=3.10 required. |

**Installation:**
```bash
pip install scrapling==0.4.2
```

**IMPORTANT:** scrapling 0.4.2 requires **Python >=3.10**. Verify your project minimum before adding.

**Basic Usage:**
```python
from scrapling import PySpider

# Initialize spider (auto-installs browser drivers if needed)
spider = PySpider(auto_install_drivers=True)

# Option 1: Raw content URL (no JS needed)
url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/CHANGELOG.md"
page = spider.fetch(url)
content = page.find("body").text if page.find("body") else page.text

# Option 2: GitHub web view (JS rendering for rendered markdown)
url = f"https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md"
page = spider.fetch(url)
# Find rendered markdown body
content = page.find(".markdown-body").text
```

**With fetchers extra (recommended for GitHub):**
```bash
pip install "scrapling[fetchers]"
```

```python
from scrapling import PySpider

spider = PySpider(auto_install_drivers=True)  # Uses Playwright under the hood

# Fetch GitHub page with JS rendering
page = spider.fetch(f"https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md")
content = page.find(".markdown-body").text
```

**Changelog file patterns to try:**
- `CHANGELOG.md` (most common)
- `CHANGELOG`
- `HISTORY.md`
- `CHANGES.md`
- `RELEASES.md`

---

## Project Structure Best Practices

```
my_rss_tool/
├── pyproject.toml          # Package metadata, dependencies
├── src/
│   └── my_rss_tool/
│       ├── __init__.py
│       ├── cli.py          # CLI commands (click)
│       ├── db.py           # Database operations (sqlite3)
│       ├── feeds.py        # Feed parsing (feedparser)
│       ├── scraper.py      # HTML scraping (httpx + bs4)
│       ├── github.py       # GitHub API + changelog (httpx + scrapling) [v1.1]
│       └── monitors.py     # Monitor management [v1.1]
├── tests/
│   └── ...
├── data/                   # SQLite database storage
│   └── .gitkeep
└── README.md
```

**pyproject.toml dependencies (v1.1):**
```toml
[project]
dependencies = [
    "feedparser>=6.0.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "click>=8.1.0",
    "scrapling>=0.4.2",     # v1.1: Changelog scraping
]
requires-python = ">=3.10"   # v1.1: Bumped from 3.6+ to 3.10+
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP Client | httpx | requests | httpx has async support and HTTP/2. requests is fine if sync-only needed. |
| Feed Parser | feedparser | planet (aggregator) | planet is an aggregator framework, not a parser. feedparser is the standard parsing library. |
| HTML Parser | BeautifulSoup4 + lxml | lxml directly | BeautifulSoup provides more convenient navigation API. |
| Browser Automation | Playwright | Selenium | Playwright has better Python support and faster execution. |
| Database | sqlite3 | PostgreSQL, MySQL | Personal tool doesn't need server-based database. |
| ORM | sqlite3 (built-in) | SQLAlchemy, Django ORM | Adds complexity. sqlite3 is sufficient for personal use cases. |
| CLI Framework | click | typer | Both are good. click has larger ecosystem and more examples. typer is more Pythonic but adds dependency on fastapi utilities. |
| GitHub API Client | httpx (direct) | PyGithub | httpx handles REST API fine with simple Bearer token auth. PyGithub adds unnecessary dependency. |
| Changelog Scraping | scrapling | Playwright only | scrapling is adaptive wrapper around Playwright with easier API. Keep Playwright for complex cases. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| PyGithub | Adds another dependency when httpx handles REST perfectly. Bearer token auth is 5 lines. | httpx directly |
| Python <3.10 with scrapling | scrapling 0.4.2 requires 3.10+ | Upgrade Python or use Playwright for JS rendering instead |
| Unauthenticated GitHub API in production | 60 req/hr limit is restrictive | Use personal access token for 5000 req/hr |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| scrapling 0.4.2 | Python >=3.10 | Hard requirement. Bumps project minimum from ~3.6 to 3.10. |
| httpx 0.27.x | Python >=3.8 | Already in use. Compatible with scrapling. |
| feedparser 6.0.x | Python >=3.6 | Existing. Works with Python 3.10+. |

---

## Sources

- [feedparser Documentation](https://feedparser.readthedocs.io/en/latest/) (HIGH confidence)
- [BeautifulSoup4 Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) (HIGH confidence)
- [Playwright for Python](https://playwright.dev/python/docs/intro) (HIGH confidence)
- [httpx Documentation](https://www.python-httpx.org/) (HIGH confidence)
- [Python sqlite3 Documentation](https://docs.python.org/3/library/sqlite3.html) (HIGH confidence)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/20/) (HIGH confidence)
- [Click Documentation](https://click.palletsprojects.com/en/8.1.x/) (HIGH confidence)
- [Typer Documentation](https://typer.tiangolo.com/) (HIGH confidence)
- [argparse Documentation](https://docs.python.org/3/library/argparse.html) (HIGH confidence)
- [PyPI: scrapling](https://pypi.org/project/scrapling/) — Version 0.4.2, Python >=3.10 (HIGH confidence)
- [PyPI: PyGithub](https://pypi.org/project/PyGithub/) — Version 2.8.1, Python >=3.8 (HIGH confidence)
- [GitHub REST API: Releases](https://docs.github.com/en/rest/releases/releases) — Endpoint specs, auth headers (HIGH confidence)
- [GitHub REST API: Contents](https://docs.github.com/en/rest/repos/contents) — File content endpoint (HIGH confidence)
