# Plan 37-02 Summary

**Phase:** 37-deep-crawling
**Plan:** 37-02
**Type:** execute
**Status:** Completed
**Completed:** 2026-03-27

## Objective

Refactor common_paths.py to remove hardcoded _SUBDIR_NAMES and _SUBGRID_PATTERNS, replacing with CSS selector-based dynamic subdirectory discovery. Also refactor _extract_links() in deep_crawl.py to use CSS selectors instead of regex-based matches_feed_path_pattern().

## Tasks Completed

### Task 1: Refactor generate_feed_candidates() to use dynamic subdirectory discovery

**Files modified:** `src/discovery/common_paths.py`

**Changes:**
- Removed `_SUBDIR_NAMES` constant (hardcoded feed/rss/blog/news/atom/feeds)
- Removed `_SUBGRID_PATTERNS` constant (hardcoded /{subdir}/rss.xml, etc.)
- Added `_discover_feed_subdirs()` helper function using CSS selectors via Scrapling
- Refactored `generate_feed_candidates()` to accept optional `html: str | None` parameter
- When HTML is provided, dynamically discovers feed subdirectories from page links

**Bug fix:** Paths starting with `/` (like `/blog/rss.xml`) are same-domain paths, not external URLs. Fixed the skip condition to only skip `javascript:`, `mailto:`, `tel:`, and `#` fragments.

**Verification:**
- `grep "_SUBDIR_NAMES" src/discovery/common_paths.py` returns 0 matches
- `grep "_SUBGRID_PATTERNS" src/discovery/common_paths.py` returns 0 matches
- `generate_feed_candidates('https://example.com')` returns root-level paths only
- `generate_feed_candidates('https://example.com', html)` discovers subdirectories dynamically

### Task 2: Refactor _extract_links() to use CSS selectors for feed link discovery

**Files modified:** `src/discovery/deep_crawl.py`

**Changes:**
- `_probe_well_known_paths()` now accepts optional `html` parameter for dynamic discovery
- `_extract_links()` now uses CSS selectors to find feed-like links directly:
  - `a[href*="rss"]`
  - `a[href*="feed"]`
  - `a[href*="atom"]`
  - `a[href$=".xml"]`
- `matches_feed_path_pattern()` kept as fallback validation
- `_discover_feeds_on_page()` passes HTML to `_probe_well_known_paths()` for dynamic discovery

**Verification:**
- `grep "a\[href\*=" src/discovery/deep_crawl.py` finds CSS selectors
- `_probe_well_known_paths` accepts `html` parameter
- `matches_feed_path_pattern` still used as fallback validation

### Task 3: Integration verification

**Verification:**
- All imports work correctly
- `generate_feed_candidates()` works with and without HTML
- Dynamic subdirectory discovery discovers `/blog/rss.xml` style paths
- CSS selectors present in `_extract_links()`

## Truths Confirmed

- [x] `generate_feed_candidates()` uses dynamic subdirectory discovery from page links, not hardcoded _SUBDIR_NAMES
- [x] `_extract_links()` in deep_crawl.py uses CSS selectors to find feed-like links, not regex filtering
- [x] Common paths module no longer contains closed list of subdirectory names
- [x] Deep crawl still respects robots.txt and rate limiting (unchanged from 37-01)

## Artifacts

| Path | Provides | Exports |
|------|----------|---------|
| `src/discovery/common_paths.py` | Dynamic subdirectory discovery via CSS selectors, removed hardcoded _SUBDIR_NAMES and _SUBGRID_PATTERNS | `generate_feed_candidates` |
| `src/discovery/deep_crawl.py` | CSS selector-based feed link filtering instead of regex | `deep_crawl` |

## Key Links

| From | To | Via | Pattern |
|------|----|-----|---------|
| `src/discovery/common_paths.py` | `src/discovery/deep_crawl.py` | `generate_feed_candidates()` called by `_probe_well_known_paths()` | `generate_feed_candidates` |
| `src/discovery/deep_crawl.py` | `src/discovery/common_paths.py` | `_extract_links()` no longer uses `matches_feed_path_pattern()` for filtering | `matches_feed_path_pattern` |

## Decisions

1. **Removed hardcoded subdirectory names:** Instead of hardcoded `("feed", "rss", "blog", "news", "atom", "feeds")`, the system now dynamically discovers subdirectories from actual page links.

2. **CSS selectors over regex filtering:** `_extract_links()` uses CSS attribute selectors (`a[href*="rss"]`) to find feed-like links directly, rather than finding all links and filtering with regex.

3. **Fixed path handling:** Paths starting with `/` (like `/blog/rss.xml`) are same-domain root-relative paths and should be discovered, not skipped.

4. **Fallback validation kept:** `matches_feed_path_pattern()` is retained as fallback validation for path checking, ensuring only valid feed paths are followed.

## Commits

- `6f0d61f` refactor(37-02): remove hardcoded _SUBDIR_NAMES, add dynamic subdirectory discovery
- `2b928ee` refactor(37-02): use CSS selectors in _extract_links for feed link discovery
- `63d15f9` test(37-02): integration verification for dynamic subdirectory discovery
