---
phase: quick-httpx-deprecation
plan: "01"
type: execute
wave: "1"
depends_on: []
files_modified:
  - src/providers/rss_provider.py
  - src/discovery/fetcher.py
  - src/discovery/__init__.py
  - src/discovery/deep_crawl.py
autonomous: true
must_haves:
  truths:
    - "All httpx imports removed from src/providers/rss_provider.py"
    - "All httpx imports removed from src/discovery/fetcher.py"
    - "All httpx imports removed from src/discovery/__init__.py"
    - "All httpx imports removed from src/discovery/deep_crawl.py"
    - "RSS feed fetching uses scrapling Fetcher instead of httpx"
    - "Discovery feed validation uses scrapling Fetcher instead of httpx"
  artifacts:
    - path: src/providers/rss_provider.py
      provides: Feed fetching with scrapling Fetcher
      contains: "from scrapling import Fetcher"
    - path: src/discovery/fetcher.py
      provides: Feed validation with scrapling Fetcher
      contains: "from scrapling import Fetcher"
    - path: src/discovery/deep_crawl.py
      provides: Deep crawl HTTP fetching with scrapling Fetcher
      contains: "from scrapling import Fetcher"
  key_links:
    - from: src/providers/rss_provider.py
      to: scrapling.Fetcher
      via: "Fetcher.get(url) replacing httpx.get()"
    - from: src/discovery/fetcher.py
      to: scrapling.Fetcher
      via: "asyncio.to_thread(Fetcher.head) replacing httpx.AsyncClient.head()"
    - from: src/discovery/deep_crawl.py
      to: scrapling.Fetcher
      via: "asyncio.to_thread(Fetcher.head/get) replacing httpx.AsyncClient"
---

<objective>
Replace all httpx usage with scrapling Fetcher across providers and discovery modules.

Purpose: Consolidate HTTP fetching to use a single library (scrapling) instead of maintaining both httpx and scrapling.
Output: src/providers/rss_provider.py, src/discovery/fetcher.py, src/discovery/__init__.py, src/discovery/deep_crawl.py using scrapling Fetcher exclusively.
</objective>

<execution_context>
@/Users/y3/radar/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@src/providers/rss_provider.py
@src/discovery/fetcher.py
@src/discovery/deep_crawl.py
@src/discovery/__init__.py
@pyproject.toml
</context>

<interfaces>
<!-- Fetcher API from scrapling (used in existing codebase) -->
<!-- StealthyFetcher: fetcher.fetch(url, timeout=30000) -> response with .body attribute -->
<!-- Fetcher: Fetcher.get(url) or fetcher.fetch(url) for sync requests -->
<!-- DynamicFetcher: for JS-rendered pages -->
<!-- For async wrappers, use asyncio.to_thread(Fetcher.get, url) -->
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Replace httpx in src/providers/rss_provider.py</name>
  <files>src/providers/rss_provider.py</files>
  <action>
    1. Remove `import httpx` (line 13)
    2. In `fetch_feed_content()` (line 54): Replace `httpx.get(url, headers=request_headers, timeout=30.0, follow_redirects=True)` with `Fetcher.get(url, headers=request_headers)` (Fetcher handles redirects by default). Use `from scrapling import Fetcher` inside the function (lazy import pattern used elsewhere).
    3. In `match()` method (line 174-177): Replace `import httpx` + `httpx.head(url, timeout=10.0, follow_redirects=True)` with `Fetcher.head(url)` or `Fetcher.get(url)` with headers=BROWSER_HEADERS. Fetcher does not have a separate head() method, so use `.get()` with `request_headers=BROWSER_HEADERS`.
    4. In `crawl_async()` (lines 270-274): Replace `httpx.AsyncClient` with `asyncio.to_thread(Fetcher.get, url)` pattern. The async crawl should fetch synchronously in thread.
    5. In `feed_meta()` (line 422): Replace `httpx.get(url, headers=BROWSER_HEADERS, timeout=5.0, follow_redirects=True)` with `Fetcher.get(url, headers=BROWSER_HEADERS)` (use asyncio.to_thread since feed_meta is sync).
    6. Update docstrings to remove "Raises httpx.*" references.
    7. Keep `_crawl_with_scrapling()` as-is (already uses Fetcher).
    8. Keep `_crawl_with_scrapling_async()` as-is.

    Note: Fetcher.get() returns response with .body (bytes), .status (int), .url, .headers. Access status via response.status, body via response.body, headers via response.headers.get().
  </action>
  <verify>
    <automated>grep -n "^import httpx" src/providers/rss_provider.py; grep -n "httpx\." src/providers/rss_provider.py; echo "Exit code 0 means no httpx found"</automated>
  </verify>
  <done>src/providers/rss_provider.py uses scrapling Fetcher exclusively, no httpx imports or calls remain</done>
</task>

<task type="auto">
  <name>Task 2: Replace httpx in src/discovery/fetcher.py and __init__.py</name>
  <files>src/discovery/fetcher.py, src/discovery/__init__.py</files>
  <action>
    1. In src/discovery/fetcher.py:
       - Remove `import httpx` (line 7)
       - Replace `async def validate_feed()` body: use `asyncio.to_thread(Fetcher.head, url)` instead of `httpx.AsyncClient().head()`. Fetcher.head() does not exist as a class method - use `Fetcher().fetch(url, method='HEAD')` or use `Fetcher().fetch(url)` with method override.
       - Actually: Fetcher doesn't have a head() method. Use `asyncio.to_thread(Fetcher.get, url)` instead - it returns the full response and we can check status. Since validate_feed only needs status and content-type, a GET is fine (like the current httpx approach).
       - Alternative: use `from scrapling import Fetcher; F = Fetcher(); asyncio.to_thread(F.fetch, url, method='HEAD')` but method kwarg may not be supported. Simpler: just use GET since validate_feed needs Content-Type anyway.
       - Return same tuple format (is_valid, feed_type).

    2. In src/discovery/__init__.py:
       - Remove `import httpx` (line 8) - not actually used.
  </action>
  <verify>
    <automated>grep -n "^import httpx" src/discovery/fetcher.py src/discovery/__init__.py; grep -n "httpx\." src/discovery/fetcher.py src/discovery/__init__.py; echo "Exit 0 = no httpx"</automated>
  </verify>
  <done>src/discovery/fetcher.py and __init__.py use scrapling Fetcher, no httpx imports remain</done>
</task>

<task type="auto">
  <name>Task 3: Replace httpx in src/discovery/deep_crawl.py</name>
  <files>src/discovery/deep_crawl.py</files>
  <action>
    1. In `_quick_validate_feed()` (lines 63-90):
       - Remove `import httpx` inside function
       - Replace `async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client: response = await client.head(url)` with `asyncio.to_thread(Fetcher.get, url)` wrapped in async.
       - Note: Fetcher.get() does not have a method parameter. The function only needs status code and content-type header - just use `Fetcher.get(url)` and check response.status and response.headers.get('content-type').
       - Also remove the outer `async with` since we're using asyncio.to_thread for sync Fetcher call.

    2. In `_extract_feed_title()` (lines 93-114):
       - Remove `import httpx` inside function
       - Replace `async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client: response = await client.get(url)` with `asyncio.to_thread(Fetcher.get, url)`.
       - Parse response.body with feedparser like the existing code does.
       - Remove the `async with` context manager wrapper.

    3. Ensure Fetcher is imported at module level (already there on line 12: `from scrapling import Fetcher, Selector, DynamicFetcher`).
  </action>
  <verify>
    <automated>grep -n "import httpx" src/discovery/deep_crawl.py; grep -n "httpx\." src/discovery/deep_crawl.py; echo "Exit 0 = no httpx"</automated>
  </verify>
  <done>src/discovery/deep_crawl.py uses scrapling Fetcher exclusively for HTTP, no httpx imports or calls remain</done>
</task>

</tasks>

<verification>
Run after all tasks:
- `grep -rn "^import httpx\|^from httpx" src/providers/ src/discovery/` returns no matches
- `grep -rn "httpx\." src/providers/ src/discovery/` returns no matches (except in comments/docstrings about exceptions - update those too)
- `grep -n "from scrapling import Fetcher" src/providers/rss_provider.py` shows Fetcher is imported
- pytest tests/test_providers.py -x passes (if httpx mocking is replaced with Fetcher patching)
</verification>

<success_criteria>
- Zero httpx imports in src/providers/ and src/discovery/
- Zero httpx API calls in src/providers/ and src/discovery/
- All feed fetching uses scrapling.Fetcher.get()
- Tests pass (may need updating HTTP mocks from httpx to Fetcher)
</success_criteria>

<output>
After completion, create `.planning/quick/260329-ldi-scraping-fetcher-httpx-httpx/260329-ldi-SUMMARY.md`
</output>
