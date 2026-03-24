# Quick Task 260325-2am: src.cli fetch支持指定一个或多个链接

**Completed:** 2026-03-24
**Commit:** (pending)

## Summary

Added URL argument support to the `fetch` command. Users can now:

- `rss-reader fetch https://example.com` - Crawl a single URL
- `rss-reader fetch https://example.com https://python.org` - Crawl multiple URLs
- `rss-reader fetch --all` - Fetch all subscribed feeds (existing behavior unchanged)
- `rss-reader fetch` (no args) - Shows help message

## Changes

### src/cli/feed.py

1. Added `urls` argument to `fetch` command via `@click.argument("urls", nargs=-1, required=False)`
2. Added URL crawling logic that calls `crawl_url()` from `src.application.crawl`
3. Reports success (green) or failure (red) for each URL
4. Returns exit code 1 if any URL fails
5. Preserved all existing `--all` behavior

## Verification

```bash
# Help shows new syntax
rss-reader fetch --help

# Single URL
rss-reader fetch https://example.com

# Multiple URLs
rss-reader fetch https://ex.com https://python.org

# Existing --all still works
rss-reader fetch --all
```

## Notes

- SSL certificate errors on some URLs are environment issues, not code issues
- SOCKS proxy warnings indicate config.yaml has proxy settings
