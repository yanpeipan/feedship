# Domain Pitfalls: Personal RSS Reader and Website Crawler

**Project:** Personal RSS Reader and Website Crawler
**Researched:** 2026-03-22
**Confidence:** MEDIUM-HIGH

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Malformed RSS/XML Feed Parsing

**What goes wrong:** Feeds fail to parse silently or throw exceptions, causing items to be missed or the entire feed to be skipped.

**Why it happens:**
- Many feeds are not strictly compliant with RSS 2.0 or Atom specifications
- Feeds may contain invalid XML characters, unescaped special characters (<, >, & in content)
- Entity references may be malformed (e.g., `&amp;lt;` instead of `&lt;`)
- Encoding declarations may be missing or incorrect (UTF-8 vs ISO-8859-1)

**Consequences:**
- User misses important content from favorite feeds
- Silent failures create "black holes" where items disappear
- Partial parsing may corrupt data or create duplicates

**Prevention:**
- Use a robust feed parsing library (e.g., feedparser for Python) with bozo detection
- Implement fallback parsing strategies for malformed feeds
- Always check the `bozo` flag and `bozo_exception` in feedparser
- Sanitize HTML content within feeds before storage

**Detection:** Log all parsing failures with the full exception, feed URL, and timestamp. Track "silent failures" where items were expected but not found.

---

### Pitfall 2: Missing or Unreliable GUID/Item Identity

**What goes wrong:** Duplicate items appear repeatedly, or items are incorrectly marked as duplicates.

**Why it happens:**
- Not all feeds include `<guid>` elements (only ~96.4% per RSS Board analysis)
- Some feeds use permalinks as GUID values, which change if the URL structure changes
- GUIDs may be non-unique across different feeds
- Atom feeds use `id` elements with different semantics than RSS GUIDs

**Consequences:**
- Duplicate entries flood the reader, annoying users
- If using link as fallback identity, URL changes cause re-appearance of "new" old items
- Cross-feed deduplication may incorrectly merge unrelated items

**Prevention:**
- Use GUID when present and unique
- Fall back to `<link>` + `<pubDate>` hash when GUID is missing
- Handle `isPermaLink="false"` attribute correctly
- For Atom, use the full `urn:uuid:` style identifier, not just the link
- Log when falling back to link-based deduplication for visibility

**Detection:** Monitor for feeds that generate >50% duplicate rate, which indicates identity resolution problems.

---

### Pitfall 3: SQLite Concurrent Write Contention

**What goes wrong:** Database locks cause write failures, timeouts, or "database is locked" errors.

**Why it happens:**
- SQLite allows only ONE writer at a time
- Multiple crawler threads or concurrent CLI invocations compete for the write lock
- Long-running transactions block writers
- WAL checkpoint operations can briefly block writers

**Consequences:**
- Feed updates fail and must be retried
- Crawler processes crash or hang waiting for lock
- Data loss if writes are not properly queued/retry
- Corruption if multiple processes force-kill while writing

**Prevention:**
- Enable WAL mode (`PRAGMA journal_mode=WAL;`) for better concurrent read/write performance
- Use write batching to consolidate multiple writes into single transactions
- Implement exponential backoff retry (3-5 attempts) for locked database
- Set `PRAGMA busy_timeout=5000;` to wait 5 seconds for locks
- Consider a single writer queue if multiple processes must update
- Never open SQLite across network file systems

**Correct Configuration:**
```sql
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
PRAGMA cache_size=-4000;  -- 4MB
```

---

### Pitfall 4: Website Crawling Rate Limiting and Blocking

**What goes wrong:** Crawler gets blocked (403, 429), IP temporarily banned, or served captcha/challenges.

**Why it happens:**
- No delay between requests overwhelms the target server
- Missing or suspicious User-Agent header triggers bot detection
- No respect for `Crawl-delay` in robots.txt
- Accessing too many pages from same domain in short window
- Cloudflare, reCAPTCHA, or other anti-bot measures activate

**Consequences:**
- Feed source becomes unavailable
- Server admin blocks your IP
- Served degraded content (CAPTCHA, limited pages)
- Legal risk if ignoring explicit crawl instructions

**Prevention:**
- Implement request throttling: minimum 1-2 seconds between requests to same domain
- Respect `Crawl-delay:` directive in robots.txt (often 1-60 seconds)
- Use a polite User-Agent that identifies your crawler with a contact URL
- Implement exponential backoff when receiving 429 or 5xx errors
- Track per-domain request history and respect rate limits
- Consider using headless browser (Puppeteer/Playwright) for JavaScript-heavy sites

**Sample polite request:**
```
User-Agent: MyRSSReader/1.0 (https://myproject.example.com; contact@example.com)
Accept: text/html,application/rss+xml,application/atom+xml
```

---

### Pitfall 5: Ignoring robots.txt Directives

**What goes wrong:** Crawler accesses disallowed content, violates site terms, or gets blocked.

**Why it happens:**
- robots.txt is treated as optional or "merely a suggestion"
- Parser incorrectly interprets directives (allow/disallow order matters)
- Wildcards not handled correctly (* matches path segments incorrectly)
- Crawl-delay not implemented
- Sitemaps referenced in robots.txt not fetched

**Consequences:**
- Legal liability in jurisdictions where robots.txt has legal weight (e.g., CFAA in US)
- IP blocking
- Being labeled as a "bad bot" in shared block lists
- Missing feed discovery if not parsing `<link rel="alternate">` and sitemap references

**Prevention:**
- Parse robots.txt before every crawl session (it can change)
- Follow the RFC 9309 standard for robots.txt parsing
- Key rules: most specific match wins, path is case-sensitive, order doesn't matter
- Cache robots.txt for up to 24 hours, not indefinitely
- Also check X-Robots-Tag HTTP headers and robots meta tags in HTML
- Always check for `<link rel="alternate" type="application/rss+xml">` for feed discovery

---

### Pitfall 6: Date/Time Parsing Chaos

**What goes wrong:** Items appear in wrong order, future dates show as "new", timezone confusion.

**Why it happens:**
- RSS 2.0 uses RFC 822 dates which have ambiguous timezone representations
- PubDate may be in the future (scheduled posts) or far in the past
- No timezone specified means the parser must guess (often assumes local time)
- Atom uses ISO 8601 with varying precision (date vs datetime vs datetimetz)
- Server time vs publication time vs crawl time get confused

**Consequences:**
- Items sorted incorrectly in feed reader
- "Future items" displayed or hidden unexpectedly
- Items with missing dates sorted unpredictably
- Users see wrong timestamps

**Prevention:**
- Always normalize to UTC internally
- Handle RFC 822 formats carefully: `+0530`, `-0700`, `GMT`, `EST`, `EDT`
- The timezone offset in RFC 822 is the offset FROM UTC, not the timezone name
- For Atom, prefer `published` over `updated` for display purposes
- Log feeds with unparseable dates for manual review
- Default to crawl time if feed provides no valid date

---

### Pitfall 7: Deduplication Hash Collisions

**What goes wrong:** Different items incorrectly identified as duplicates, or duplicates not detected.

**Why it happens:**
- Simple hash functions (MD5, SHA1) may have collisions (rare but possible)
- Hashing only a portion of the URL (e.g., domain only) causes false duplicates
- Normalization differences: trailing slashes, query parameters, case sensitivity
- Content hashes change when feed entries are edited

**Consequences:**
- Users miss new items that were incorrectly deduplicated
- Different items incorrectly merged in reader
- Confusion about why some items don't appear

**Prevention:**
- Use strong hash (SHA256) for content-based deduplication
- When using URL-based deduplication, normalize URLs first:
  - Remove trailing slashes
  - Lowercase domain
  - Remove `utm_*` query parameters
  - Sort remaining query parameters
- Track both GUID-based and content-based duplicates separately
- Periodically re-check items that "aged out" of deduplication window

---

### Pitfall 8: CLI Interactive Prompts in Scripts

**What goes wrong:** Scripts hang waiting for input, CI/CD pipelines fail, automation breaks.

**Why it happens:**
- CLI waits for confirmation when run non-interactively (TTY detection fails)
- Password/passphrase prompts don't work in headless environments
- Pipelines can't provide stdin input
- Tool behavior differs based on whether stdout is a terminal

**Consequences:**
- Cron jobs and automation fail silently or timeout
- User must manually intervene in automated workflows
- Scripts hang indefinitely
- Confusion about why "it works on my machine"

**Prevention:**
- Detect TTY and fail fast with clear error if stdin required: `if [ ! -t 0 ]; then ...`
- Provide `--yes` or `--force` flags to skip confirmation prompts
- Support environment variables for sensitive inputs
- Make default behavior script-friendly, require flags for dangerous actions
- Never require interactive input for core functionality
- If confirmation required, default to "no" for non-interactive contexts

---

## Moderate Pitfalls

Issues that cause frustration, work stoppage, or require rework.

### Pitfall 9: CDATA Section Handling

**What goes wrong:** Content appears wrapped in `CDATA[...]]>` markers, or CDATA sections are stripped incorrectly.

**Why it happens:**
- Many feeds use CDATA to embed HTML or special characters
- Parser may return raw CDATA wrapper instead of content
- Nested CDATA (rare) breaks naive string matching
- UTF-8 BOM bytes inside CDATA cause encoding issues

**Prevention:**
- Use proper XML parser that handles CDATA as text, not markup
- Feedparser handles this correctly; raw xml.etree may not
- Strip CDATA markers only if parser didn't already handle it
- Test with feeds known to use CDATA extensively (WordPress, Medium)

---

### Pitfall 10: Relative URL Resolution

**What goes wrong:** Links and images in feed content point to dead URLs.

**Why it happens:**
- Feeds contain relative URLs like `/images/logo.png` without base URL context
- Links reference the feed URL instead of the article URL for resolution
- Some feeds use `xml:base` attribute for explicit base URL
- Image sources broken in email/HTML rendering without full URLs

**Prevention:**
- Use feed parsing library that resolves relative URLs automatically
- The base for resolution should be the feed's `<link>`, not the feed URL itself
- Apply `xml:base` attribute when present per RFC 3986
- Always store resolved (absolute) URLs in database

---

### Pitfall 11: Encoding Declaration Mismatch

**What goes wrong:** Special characters display as mojibake, accented text is corrupted.

**Why it happens:**
- XML declaration claims `encoding="UTF-8"` but actual content is ISO-8859-1
- HTTP Content-Type header contradicts XML declaration
- HTML entities in attributes not decoded properly
- Windows-1252 characters (smart quotes, em-dashes) not handled

**Prevention:**
- Always default to UTF-8 for database storage
- Use encoding detection libraries (chardet) for ambiguous cases
- Log encoding inconsistencies for feed owner review
- Handle Windows-1252 as fallback for legacy feeds

---

### Pitfall 12: Large Result Set Pagination

**What goes wrong:** Queries slow to a crawl as database grows, memory exhaustion.

**Why it happens:**
- `SELECT * FROM items` without LIMIT loads entire table
- No cursor-based pagination; offset grows linearly expensive
- All items fetched to memory for "pagination" in application code
- Missing indexes on ORDER BY columns

**Prevention:**
- Use cursor-based pagination: `WHERE id < :last_id ORDER BY id DESC LIMIT :page_size`
- Add indexes on (`feed_id`, `published`) for feed-scoped queries
- Never use `OFFSET` for large datasets; it requires scanning all prior rows
- Implement streaming/chunked reads for bulk operations

---

### Pitfall 13: Feed Discovery Failures

**What goes wrong:** User provides website URL, application fails to find RSS/Atom feed.

**Why it happens:**
- No `<link rel="alternate" type="application/rss+xml">` in HTML `<head>`
- Feed URL not at standard paths (`/feed`, `/rss`, `/atom.xml`)
- HTML page loads via JavaScript (SPA) before feed links are injected
- Site uses multiple feed formats with different URLs

**Prevention:**
- Fetch HTML page and parse `<head>` for feed autodiscovery links
- Check common feed paths as fallback
- For SPA sites, use headless browser to render before parsing
- Query Google's Feed API or Substack API as fallback
- Present user with multiple feed options if multiple discovered

---

### Pitfall 14: Namespace Extension Ignored

**What goes wrong:** Content from popular extensions (iTunes, Dublin Core, Media RSS) silently dropped.

**Why it happens:**
- Parser configured for basic RSS 2.0 only
- Namespace prefixes vary across feeds (`dc:creator` vs `author`)
- Extensions add valuable metadata (podcast duration, author, categories)

**Prevention:**
- Configure parser to handle common namespaces:
  - Dublin Core: `http://purl.org/dc/elements/1.1/`
  - iTunes: `http://www.itunes.com/dtds/podcast-1.0.dtd`
  - Media RSS: `http://search.yahoo.com/mrss/`
  - Atom: `http://www.w3.org/2005/Atom`
- Map namespace elements to normalized internal fields

---

### Pitfall 15: Missing Graceful Degradation

**What goes wrong:** Application crashes completely when one feed fails.

**Why it happens:**
- No per-feed error handling; one bad feed kills entire crawl
- Network errors propagate up uncaught
- Malformed data in database breaks queries
- Dependencies on external services (feed update server) not handled

**Prevention:**
- Wrap each feed fetch in try/catch with timeout
- Continue processing other feeds when one fails
- Store failed feed status: last successful fetch, error message, retry count
- Implement circuit breaker: pause feed after N consecutive failures
- Log failures for operator review but don't stop processing

---

## Minor Pitfalls

Nuisance issues that reduce quality but are recoverable.

### Pitfall 16: Secret Exposure in Process List

**What goes wrong:** Passwords, API keys, tokens visible in `ps aux` output.

**Why it happens:**
- Credentials passed as command-line arguments
- Environment variables visible in `/proc/*/environ`
- Config files with credentials world-readable

**Prevention:**
- Never pass secrets as CLI flags; use environment variables or config files
- Use `.netrc` or similar for HTTP authentication
- Set config file permissions to `0600`
- Prefer stdin for secret input when possible

---

### Pitfall 17: Color Output Without NO_COLOR Support

**What goes wrong:** ANSI escape codes pollute logs, break grep/pipeline, look wrong in terminals.

**Why it happens:**
- Colors always enabled, even when output is piped
- Terminal detection unreliable
- Users with colorblindness can't read output

**Prevention:**
- Check for `NO_COLOR` environment variable (https://no-color.org/)
- Use `--color=auto|always|never` flag pattern
- Default to `auto` (colors only when stdout is a TTY)
- Test with `NO_COLOR=1` to verify clean output

---

### Pitfall 18: Silent Success with Empty Result

**What goes wrong:** User doesn't know if feed had no new items or fetch failed.

**Why it happens:**
- Same "success" message whether 0 or 100 items processed
- No differentiation between "nothing new" and "couldn't check"
- Exit code 0 even when errors occurred

**Prevention:**
- Use exit codes: 0=success, 1=error, 2=partial success with warnings
- Print summary: `Fetched 0 new items (3 existing), 1 feed skipped due to error`
- Provide `--verbose` flag for detailed per-feed status
- Consider structured output (JSON) for programmatic consumption

---

### Pitfall 19: Inefficient Delete Operations

**What goes wrong:** Deleting old items locks database for minutes.

**Why it happens:**
- `DELETE FROM items WHERE ...` without limiting batch size
- `VACUUM` runs automatically after large delete, blocking all access
- No soft-delete strategy for "archiving" old items

**Prevention:**
- Delete in batches of 100-1000 rows, with PRAGMA vacuum between
- Use soft delete (mark `deleted_at` timestamp) for large archival operations
- Schedule VACUUM during low-usage periods
- Consider partitioning table by date for efficient old-data removal

---

### Pitfall 20: Feed URL vs Feed ID Confusion

**What goes wrong:** Feed not updating, duplicates after URL change, "feed not found".

**Why it happens:**
- Using feed URL as unique identity; URL changes break everything
- Feed moves to new domain but old URL redirects not followed
- Feed merges with another, same items but different ID

**Prevention:**
- Use internal UUID/ID independent of URL
- Track URL history: if same feed found at new URL, migrate items
- Follow HTTP redirects (301, 302) on feed URL
- Allow user to manually reassign feed URL if migration not detected
- Store `last_url` to detect URL changes and alert user

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Feed parsing implementation | Pitfalls 1, 2, 6, 9, 10, 11 | Use feedparser library; handle all edge cases from day one |
| Database schema | Pitfalls 3, 7, 12, 19 | Proper indexing, WAL mode, batch operations |
| HTTP fetching | Pitfalls 4, 5, 13 | Rate limiting, robots.txt, headless browser for JS |
| CLI interface | Pitfalls 8, 16, 17, 18 | POSIX conventions, no-interactive-default, proper exit codes |
| Deduplication logic | Pitfalls 2, 7, 20 | Hash-based with fallback; UUID identity separate from URL |
| Feed discovery | Pitfall 13 | Multiple strategies; never assume single feed URL |

---

## Sources

- [RSS 2.0 Specification](https://www.rssboard.org/rss-specification) - RSS specification, GUID requirements
- [RSS Board Feed Validator](https://www.rssboard.org/) - Common feed problems, validation issues
- [feedparser Documentation](https://feedparser.readthedocs.io/) - Bozo detection, encoding handling, normalization
- [SQLite When to Use](https://www.sqlite.org/whentouse.html) - Concurrent access limitations, network filesystem warnings
- [SQLite WAL Mode](https://www.sqlite.org/wal.html) - Write-Ahead Logging concurrency model
- [SQLite Pragma Documentation](https://www.sqlite.org/pragma.html) - journal_mode, synchronous, busy_timeout
- [SQLite Data Types](https://www.sqlite.org/datatype3.html) - Type affinity, comparison behavior
- [Google Robots Meta Tag Documentation](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag) - Crawler directives
- [POSIX Utility Conventions](https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap12.html) - CLI argument syntax standards
- [CLIG Design Guidelines](https://clig.dev/) - CLI best practices, common mistakes
- [NO_COLOR Standard](https://no-color.org/) - Color output conventions
- [RFC 9309: robots.txt](https://www.rfc-editor.org/rfc/rfc9309) - robots.txt parsing standard

---

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| RSS parsing pitfalls | HIGH | Based on RSS Board analysis and feedparser documentation |
| Web crawling issues | MEDIUM | General web scraping wisdom; specific anti-bot measures change rapidly |
| SQLite performance | HIGH | Based on official SQLite documentation |
| CLI usability | MEDIUM-HIGH | Based on POSIX standards and clig.dev guidelines |
| Deduplication | MEDIUM | Well-understood patterns; implementation nuances vary |

---

# Domain Pitfalls: GitHub API Monitoring and Scrapling (v1.1)

**Project:** Adding GitHub Releases and Changelog monitoring to existing CLI app
**Researched:** 2026-03-23
**Confidence:** MEDIUM

## Critical Pitfalls

Mistakes that cause rewrites or major issues specific to adding GitHub monitoring features.

### Pitfall 21: GitHub API Unauthenticated Rate Limit Exhaustion

**What goes wrong:**
Script monitors multiple GitHub repositories but hits the 60 requests/hour limit within minutes. After limit is hit, GitHub returns `403 Forbidden` with `rate limit exceeded` message. All subsequent monitoring fails silently or with errors.

**Why it happens:**
The project already has a 2s rate limit for general web scraping, but GitHub API is far more restrictive. Unauthenticated requests are limited to 60/hour per IP. Monitoring even 10 repositories with a single check per repository exhausts this instantly.

**Consequences:**
- GitHub monitoring completely stops working
- User doesn't know monitoring failed
- Confusing errors from 403 responses

**Prevention:**
1. **Use authentication** — Personal Access Token (PAT) raises limit to 5,000 requests/hour
2. **Implement token rotation** if monitoring many repos
3. **Cache aggressively** — Store last response, only fetch if >1 hour since last check
4. **Check rate limit headers** before each request: `X-RateLimit-Remaining` and `X-RateLimit-Reset`

**Detection:**
- Check `X-RateLimit-Remaining` header before each request
- Log warning when remaining < 10
- Handle 403 responses with specific "rate limit exceeded" message

**Phase to address:**
**Phase 1 (GitHub API integration)** — Token authentication and rate limit handling must be built into initial implementation, not bolted on later.

---

### Pitfall 22: Scrapling Playwright Browser Installation Failure

**What goes wrong:**
`pip install "scrapling[fetchers]"` succeeds but `scrapling install` fails due to missing system dependencies. Playwright browsers (Chromium, Firefox, WebKit) do not install. The changelog scraping feature fails at runtime with `BrowserExecutionError` or similar.

**Why it happens:**
Scrapling with fetchers requires Playwright's browser binaries. `playwright install` downloads several hundred MB of browser executables and requires system-level dependencies (fonts, libraries, SSL certs on Linux). macOS may require additional Xcode components.

**Consequences:**
- Feature completely broken on fresh install
- Users report "scraping doesn't work"
- CI/CD pipelines fail

**Prevention:**
1. **Document browser installation** as a required setup step
2. **Test installation** in CI/development environment
3. **Provide fallback** — if Playwright fails, use simple HTTP + BeautifulSoup for changelog fetching
4. **Verify installation works** before feature development continues

**Detection:**
- `scrapling install` command fails with dependency errors
- Runtime `BrowserExecutionError` when trying to scrape

**Phase to address:**
**Phase 1 (Setup/dependencies)** — Browser installation must be verified before Phase 2 (feature development) begins.

---

### Pitfall 23: Changelog File Not Found / Different Filenames

**What goes wrong:**
System expects `CHANGELOG.md` but repository uses `CHANGES.md`, `HISTORY.md`, `CHANGELOG.markdown`, or has no changelog at all. Scraping returns empty or 404. User sees no updates for repos that do have changelogs under different names.

**Why it happens:**
There is no standard changelog filename or format. GitHub also auto-generates a "Recent releases" page for repositories that lack a changelog file. Different projects use different conventions.

**Consequences:**
- User thinks feature is broken for specific repos
- Missed changelogs from popular projects
- Confusion about which repos have changelogs

**Prevention:**
1. **Check multiple common filenames**: `CHANGELOG.md`, `CHANGELOG`, `CHANGES.md`, `HISTORY.md`, `CHANGELOG.markdown`
2. **Check GitHub releases API** as fallback — release notes are often better structured
3. **Detect absence gracefully** — if no changelog found, mark as "no changelog" not "error"

**Detection:**
- Successful API response but empty content
- 404 on expected changelog path
- User reports "GitHub repo X has updates but nothing shows"

**Phase to address:**
**Phase 1 (GitHub API integration)** — File detection logic belongs in initial implementation.

---

### Pitfall 24: Changelog Parsing Produces Garbage Output

**What goes wrong:**
CHANGELOG.md is fetched but content is unstructured markdown. Release entries are concatenated, dates missing, version numbers not parseable. User sees raw markdown instead of structured "v2.0.0 - 2026-01-15 - Added X, Fixed Y".

**Why it happens:**
Changelogs are written for humans, not machines. Formats vary wildly:
- Semantic changelog (Keep a Changelog standard)
- Auto-generated from git commits
- Custom formats with arbitrary structures
- Some are just "v1.0, v1.1, v1.2" bullet points

**Consequences:**
- Parsed output is unreadable
- User can't understand what changed between versions
- Feature appears broken despite data being fetched

**Prevention:**
1. **Parse for version headers** (`## [v1.2.3]` or `## Version 1.2.3`) as primary signal
2. **Extract release date** from header line or ISO format near version
3. **Limit parsing scope** — show latest 3-5 releases only
4. **Graceful degradation** — if parsing fails, show raw content with warning

**Detection:**
- Parsed output has no clear version boundaries
- Release dates all showing same date or missing
- Content appears truncated or jumbled

**Phase to address:**
**Phase 1 (GitHub API integration)** — Parsing strategy must be designed upfront, not improvised.

---

### Pitfall 25: Scrapling Adaptive Parser Timeout on Large Changelogs

**What goes wrong:**
Repository has a massive CHANGELOG.md (10,000+ lines). Scrapling's adaptive parsing takes 30+ seconds or times out. User waits, then sees timeout error. Meanwhile the 2s rate limit on other sites has already kicked in.

**Why it happens:**
Scrapling's adaptive parsing runs JavaScript and analyzes page structure. Large markdown files served as HTML can trigger expensive parsing. Default timeout may be too short for large files.

**Consequences:**
- User experiences long wait times
- Timeout errors for legitimate large changelogs
- Resource exhaustion on repeated failures

**Prevention:**
1. **For raw markdown files** — use simple HTTP fetch, not Scrapling (no JS needed for .md files)
2. **Set appropriate timeouts** — markdown files need less time than SPAs
3. **Fetch only relevant sections** if possible
4. **Cache parsed results** — avoid re-parsing same changelog

**Detection:**
- Single request takes >10 seconds
- `TimeoutError` in logs
- Memory usage spikes during parsing

**Phase to address:**
**Phase 2 (Scraping integration)** — Timeout and fetch strategy needs testing before release.

---

### Pitfall 26: Mixing GitHub API and HTML Scraping for Same Repo

**What goes wrong:**
System fetches releases via GitHub API (structured JSON) but changelog via scraping (HTML). These show different information. API shows formal releases, scraping shows in-development changelog. User confused why "v2.0" appears in API but "v1.9.9" is latest in scraper.

**Why it happens:**
GitHub releases (API) and CHANGELOG.md content are often out of sync. Releases are created manually when version ships. CHANGELOG.md is updated throughout development. These represent different timelines.

**Consequences:**
- Same version appears in both sources with different content
- User reports "these numbers don't match"
- Confusion about which source to trust

**Prevention:**
1. **Choose one source** — prefer GitHub Releases API for release tracking
2. **Use changelog for change details** — releases for version numbers/dates
3. **Clearly label** — "Release v2.0.0 (API)" vs "Changelog entry for v2.0.0 (scraped)"
4. **Consider user's actual need** — if they want releases, use API only; if they want development progress, use changelog only

**Detection:**
- Same version appears in both sources with different content
- User reports "these numbers don't match"

**Phase to address:**
**Phase 1 (Requirements validation)** — Source strategy must be decided before implementation.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use unauthenticated GitHub API | No token setup needed | 60 req/hour limit, easily exhausted | Never for production monitoring |
| Skip changelog parsing, show raw | Fast to implement | Poor UX, hard to read | MVP only, must improve before release |
| Single timeout for all requests | Simple code | Timeouts on fast endpoints, failures on slow | Never - configure per-request |
| No caching of GitHub responses | Always fresh data | Rate limit exhaustion, slow response | Never - minimum 1 hour cache |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GitHub API | Ignoring `X-RateLimit-Remaining` header | Check header before each request, pause if < 10 |
| GitHub API | Assuming 200 always means success | Handle `304 Not Modified` (conditional request success) |
| GitHub API | Not handling `403` gracefully | Retry with exponential backoff after reset time |
| Scrapling | Using Playwright for markdown files | Direct HTTP fetch is faster and sufficient |
| Scrapling | Not running `playwright install` | Document as required setup step; check in CI |
| Changelog | Expecting standard format | Try multiple parsers, fall back to raw display |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No GitHub response caching | Rapid rate limit exhaustion | Cache with 1-hour minimum TTL | At >5 monitored repos |
| Scrapling for every check | 30+ second delays on large changelogs | Use direct HTTP for .md files | Changelog > 1000 lines |
| Concurrent API requests | 100 concurrent limit exceeded | Sequential requests with delay | At >50 monitored repos |
| Parsing full changelog history | Memory bloat | Limit to latest 5 releases | Repository with 100+ releases |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoding GitHub PAT in source | Token exposed in repo history | Use environment variable `GITHUB_TOKEN` |
| No token validation | Invalid/missing token causes silent failures | Verify token works with `GET /user` on startup |
| Storing GitHub token in plain text config | Token theft if config file compromised | Encrypt config or use OS keychain |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Silent rate limit exhaustion | User doesn't know monitoring stopped | Show warning on CLI: "GitHub rate limit reached, retry at [time]" |
| Generic error on changelog not found | User thinks feature broken | Friendly message: "No CHANGELOG.md found for [repo]" |
| Mixing release sources without explanation | User confused by conflicting version numbers | Show source badge: "(API)" vs "(changelog)" |
| Long wait with no progress indication | User thinks app frozen | Show "Checking [repo]..." messages |

---

## "Looks Done But Isn't" Checklist

- [ ] **GitHub API:** Rate limit handling verified with 10+ repos checked - not just single repo test
- [ ] **GitHub API:** Token authentication verified - unauthenticated path fully tested with error handling
- [ ] **Scrapling:** Browser installation tested on clean system - not just existing Playwright installation
- [ ] **Changelog parsing:** Tested with 5+ real-world changelogs of varying formats - not just one ideal case
- [ ] **Changelog parsing:** Graceful degradation verified - raw output shown when parsing fails
- [ ] **Error messages:** User-friendly messages for all failure modes - not stack traces
- [ ] **Caching:** Verified that repeated checks don't exhaust rate limit - check after 1 hour

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Rate limit exhausted | LOW | Wait for reset (check `X-RateLimit-Reset` header for timestamp), implement caching |
| Browser installation failure | MEDIUM | Run `playwright install --force`, install system dependencies |
| Changelog not found | LOW | User adds correct filename, system detects automatically next run |
| Parsing produces garbage | MEDIUM | Switch to raw display mode, improve parsing regex patterns |

---

## Pitfall-to-Phase Mapping (v1.1 GitHub Monitoring)

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| GitHub API rate limit exhaustion | Phase 1: GitHub API base | Test with 10 repos, verify < 60 requests made |
| Playwright browser installation | Phase 1: Setup/dependencies | `scrapling install` succeeds on clean install |
| Changelog file not found | Phase 1: GitHub API integration | Test with repos using non-standard filenames |
| Changelog parsing garbage | Phase 1: Content parsing | Visual verification of parsed output |
| Scrapling timeout on large files | Phase 2: Scraping integration | Test with largest expected changelog |
| Mixed source confusion | Phase 1: Requirements | Document which source for which data |

---

## Sources

- [GitHub REST API Rate Limits](https://docs.github.com/en/rest/overview/rate-limits-for-the-rest-api) (HIGH confidence - official docs)
- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) (HIGH confidence - industry standard)
- [Scrapling PyPI](https://pypi.org/project/scrapling/) (HIGH confidence - official package page)
- [Playwright PyPI](https://pypi.org/project/playwright/) (HIGH confidence - official package page)

---

## Confidence Assessment (v1.1)

| Area | Level | Reason |
|------|-------|--------|
| GitHub API pitfalls | HIGH | Based on official GitHub documentation with specific rate limit numbers |
| Scrapling/Playwright issues | MEDIUM | Based on official package docs, known installation complexity |
| Changelog parsing | MEDIUM | Keep a Changelog standard is authoritative, but real-world formats vary widely |
| Performance traps | MEDIUM | General patterns apply, project-specific tuning needed |

---

*Pitfalls research for: GitHub monitoring and changelog scraping in Python CLI app*
*Researched: 2026-03-23*
