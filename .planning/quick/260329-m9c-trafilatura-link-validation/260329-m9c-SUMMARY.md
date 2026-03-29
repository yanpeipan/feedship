# Quick Task 260329-m9c: Trafilatura Link Validation Integration

## Summary

Enhanced `parse_link_elements()` with trafilatura-style `<a href>` fallback when `<link>` autodiscovery finds nothing.

## Changes

### parser.py additions

**1. LINK_VALIDATION_RE** - regex for `<a href>` fallback:
```python
LINK_VALIDATION_RE = re.compile(
    r"\.(?:atom|rdf|rss|xml)$|"
    r"\b(?:atom|rss)\b|"
    r"\?type=100$|"
    r"feeds/posts/default/?$|"
    r"\?feed=(?:atom|rdf|rss|rss2)|"
    r"feed$"
)
```

**2. BLACKLIST** - filter `/comments/` paths:
```python
BLACKLIST = re.compile(r"\bcomments\b")
```

**3. FEED_TYPE_MAP** - expanded MIME types (rss, atom, rdf, json)

**4. Fallback logic** - when no `<link>` found, scan `<a href>` with regex

## Verification

```
Test 1 <link>: [DiscoveredFeed(url='https://example.com/feed/rss.xml', ...)] ✅
Test 2 <a href> fallback: [DiscoveredFeed(url='https://example.com/feed/rss.xml', title='RSS Feed', ...)] ✅
Test 3 blacklist: [] ✅ (correctly filtered /comments/)
Test 4 JSON feed: [DiscoveredFeed(..., feed_type='json')] ✅
Test 5 external domain: [] ✅
```

All 24 provider tests pass ✅

## Commit

`refactor(260329-m9c): enhance parse_link_elements with trafilatura fallback`
