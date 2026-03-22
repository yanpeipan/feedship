# Phase 3: Web Crawling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-23
**Phase:** 03-web-crawling
**Areas discussed:** Content Extraction, robots.txt, Rate Limiting, Content Scope, Error Handling, CLI Design, Storage, Feed Source

---

## Content Extraction

| Option | Description | Selected |
|--------|-------------|----------|
| Heuristic extraction | BeautifulSoup + custom heuristics. Simple, fast, good for structured sites. | |
| Readability algorithm | Firefox Reader View. Best quality, heavier dependency. | ✓ |
| Trafilatura library | Specialized article extraction. Good middle ground, external dependency. | |

**User's choice:** Readability
**Notes:** User asked which option has best effect and drawbacks. Readability chosen for extraction quality.

## robots.txt Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Strict | Always respect robots.txt before crawling | |
| Lazy mode (recommended) | Ignore by default, --ignore-robots to force | ✓ |
| Smart mode | Respect by default, --ignore-robots to override | |

**User's choice:** Lazy mode (option 2)
**Notes:** User selected option 2 directly.

## Rate Limiting

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 1s delay (recommended) | Simple, meets most scenarios | |
| Fixed 2s delay | More conservative, avoids blocking | ✓ |
| Configurable delay | User specifies --delay value | |

**User's choice:** Fixed 2s delay (option 2)
**Notes:** User selected option 2 directly.

## Content Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Full text extraction (recommended) | All visible text from page | ✓ |
| Smart segmentation | Identify main article body, skip nav/sidebar/ads | |
| Title + description only | Just title, meta description, first paragraphs | |

**User's choice:** Full text extraction
**Notes:** User selected option 1 directly.

## Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Log and skip (recommended) | Log error, continue with other URLs | ✓ |
| Partial storage | Store whatever was extracted, even if incomplete | |
| Strict fail | Any failure causes entire operation to fail | |

**User's choice:** Log and skip
**Notes:** User selected option 1 directly.

## CLI Command Design

| Option | Description | Selected |
|--------|-------------|----------|
| Single URL (recommended) | `crawl <url>` — simple, one URL at a time | |
| Batch mode | `crawl add <url>` then `crawl fetch` | |
| Single with options | `crawl <url> --ignore-robots` — option to force | ✓ |

**User's choice:** Single with options
**Notes:** User selected option 3 directly.

## Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Store in articles table (recommended) | Reuse existing list/search functionality | ✓ |
| New pages table | Separate crawled content from feed articles | |

**User's choice:** Store in articles table
**Notes:** User selected option 1 directly.

## Feed Source Display

| Option | Description | Selected |
|--------|-------------|----------|
| Show domain name | Extract domain from URL as source | |
| Fixed label | "[Crawled]" or "[Web]" | |
| System feed (recommended) | Internal "Crawled Pages" feed, feed_id='crawled' | ✓ |

**User's choice:** System feed "Crawled Pages"
**Notes:** User selected option 3 directly.

---

## Deferred Ideas

None — discussion stayed within phase scope

---

*Phase: 03-web-crawling*
*Discussion log: 2026-03-23*
