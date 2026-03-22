# Technology Stack: Personal Information System

**Project Type:** CLI tool for RSS subscription and website crawling
**Researched:** 2026-03-22
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
│       └── scraper.py      # HTML scraping (httpx + bs4)
├── tests/
│   └── ...
├── data/                   # SQLite database storage
│   └── .gitkeep
└── README.md
```

**pyproject.toml dependencies:**
```toml
[project]
dependencies = [
    "feedparser>=6.0.0",
    "httpx>=0.27.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "click>=8.1.0",
]
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
- [PyPI feedparser](https://pypi.org/project/feedparser/) (HIGH confidence)
