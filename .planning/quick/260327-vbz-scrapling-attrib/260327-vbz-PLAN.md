---
phase: quick-260327-vbz
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/discovery/deep_crawl.py
  - src/discovery/parser.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "All Scrapling attrib access uses direct bracket notation attrib['key']"
  artifacts:
    - path: src/discovery/deep_crawl.py
      provides: Refactored attrib access
      contains: "attrib['href']"
    - path: src/discovery/parser.py
      provides: Refactored attrib access
      contains: "attrib['href']"
  key_links: []
---

<objective>
Refactor Scrapling attrib API usage to use cleaner direct bracket notation per official docs.

Purpose: Replace verbose `attrib.get('key')` with `attrib['key']` for cleaner, more idiomatic code.
Output: Updated deep_crawl.py and parser.py with consistent attrib bracket access.
</objective>

<context>
@src/discovery/deep_crawl.py
@src/discovery/parser.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace attrib.get() with attrib[] in deep_crawl.py</name>
  <files>src/discovery/deep_crawl.py</files>
  <action>
    Replace all `attrib.get('href')` with `attrib['href']` in deep_crawl.py.

    Changes:
    - Line 293: `base_tag.attrib.get('href')` → `base_tag.attrib['href']`
    - Line 297: `anchor.attrib.get('href')` → `anchor.attrib['href']`
  </action>
  <verify>
    <automated>grep -c "attrib.get" src/discovery/deep_crawl.py && echo "FAIL: attrib.get still present" || echo "PASS: no attrib.get found"</automated>
  </verify>
  <done>All attrib access uses bracket notation in deep_crawl.py</done>
</task>

<task type="auto">
  <name>Task 2: Replace attrib.get() with attrib[] in parser.py</name>
  <files>src/discovery/parser.py</files>
  <action>
    Replace all `attrib.get('key')` with `attrib['key']` in parser.py, except for 'type' which uses the pattern `attrib.get('type') or ''` to handle missing values gracefully.

    Changes:
    - Line 68: `base_tag.attrib.get('href')` → `base_tag.attrib['href']`
    - Line 72: `link.attrib.get('href')` → `link.attrib['href']`
    - Line 76: `link.attrib.get('type', '')` → `link.attrib.get('type') or ''` (handles missing by returning empty string)
    - Line 85: `link.attrib.get('title')` → `link.attrib['title']`
  </action>
  <verify>
    <automated>grep -c "attrib.get" src/discovery/parser.py && echo "FAIL: attrib.get still present" || echo "PASS: no attrib.get found"</automated>
  </verify>
  <done>All attrib access uses bracket notation in parser.py</done>
</task>

</tasks>

<verification>
Both files pass: `grep -c "attrib.get" src/discovery/deep_crawl.py src/discovery/parser.py` returns 0 matches.
</verification>

<success_criteria>
- deep_crawl.py: No `attrib.get()` calls remain
- parser.py: No `attrib.get()` calls remain
- All tests pass (if any exist for discovery module)
</success_criteria>

<output>
After completion, create `.planning/quick/260327-vbz-scrapling-attrib/260327-vbz-SUMMARY.md`
</output>
