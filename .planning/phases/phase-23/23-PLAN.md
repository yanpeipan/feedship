---
phase: 23-nanoid-code-changes
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/storage/sqlite.py
autonomous: true
requirements:
  - NANO-01

must_haves:
  truths:
    - "store_article() uses nanoid.generate() for article id generation"
    - "add_tag() uses nanoid.generate() for tag id generation"
    - "tag_article() uses nanoid.generate() for tag id generation when creating new tags"
    - "New IDs are 21-char URL-safe nanoid format instead of 36-char UUID hex"
  artifacts:
    - path: "src/storage/sqlite.py"
      contains: "from nanoid import generate"
      min_lines: 1
    - path: "src/storage/sqlite.py"
      contains: "generate()"
      min_occurrences: 3
  key_links:
    - from: "src/storage/sqlite.py"
      to: "nanoid"
      via: "from nanoid import generate"
      pattern: "from nanoid import generate"
---

<objective>
Replace uuid.uuid4() with nanoid.generate() in storage functions for URL-safe 21-char IDs.

Purpose: Switch from UUID (36-char hex) to nanoid (21-char URL-safe) for article and tag IDs.
Output: Updated src/storage/sqlite.py with nanoid-based ID generation.
</objective>

<execution_context>
@/Users/y3/radar/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@src/storage/sqlite.py
</context>

<interfaces>
<!-- nanoid.generate() returns a 21-character URL-safe string -->
<!-- Usage: from nanoid import generate; id = generate() -->
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add nanoid import and replace UUID in store_article()</name>
  <files>src/storage/sqlite.py</files>
  <read_first>
    - src/storage/sqlite.py (lines 1-15 for imports, 290-360 for store_article function)
  </read_first>
  <action>
    1. Add nanoid import at top of file:
       - After existing imports, add: `from nanoid import generate`

    2. In store_article() function (line 311):
       - REMOVE the inline `import uuid` statement
       - At line 334, CHANGE `article_id = str(uuid.uuid4())` TO `article_id = generate()`
  </action>
  <acceptance_criteria>
    - File contains `from nanoid import generate` at module level
    - store_article() contains `article_id = generate()` (not uuid.uuid4())
    - No inline `import uuid` statements remain in store_article()
  </acceptance_criteria>
  <verify>
    <automated>grep -n "from nanoid import generate" /Users/y3/radar/src/storage/sqlite.py && grep -n "article_id = generate()" /Users/y3/radar/src/storage/sqlite.py</automated>
  </verify>
  <done>store_article() uses nanoid.generate() instead of uuid.uuid4()</done>
</task>

<task type="auto">
  <name>Task 2: Replace UUID in add_tag()</name>
  <files>src/storage/sqlite.py</files>
  <read_first>
    - src/storage/sqlite.py (lines 176-190 for add_tag function)
  </read_first>
  <action>
    In add_tag() function (line 178):
    - REMOVE the inline `import uuid` statement
    - At line 181, CHANGE `tag_id = str(uuid.uuid4())` TO `tag_id = generate()`
  </action>
  <acceptance_criteria>
    - add_tag() contains `tag_id = generate()` (not uuid.uuid4())
    - No inline `import uuid` statement in add_tag()
  </acceptance_criteria>
  <verify>
    <automated>grep -n "tag_id = generate()" /Users/y3/radar/src/storage/sqlite.py</automated>
  </verify>
  <done>add_tag() uses nanoid.generate() instead of uuid.uuid4()</done>
</task>

<task type="auto">
  <name>Task 3: Replace UUID in tag_article()</name>
  <files>src/storage/sqlite.py</files>
  <read_first>
    - src/storage/sqlite.py (lines 233-258 for tag_article function)
  </read_first>
  <action>
    In tag_article() function (line 243):
    - REMOVE the inline `import uuid` statement
    - At line 244, CHANGE `tag_id = str(uuid.uuid4())` TO `tag_id = generate()`
  </action>
  <acceptance_criteria>
    - tag_article() contains `tag_id = generate()` (not uuid.uuid4())
    - No inline `import uuid` statement in tag_article()
  </acceptance_criteria>
  <verify>
    <automated>grep -n "tag_id = generate()" /Users/y3/radar/src/storage/sqlite.py</automated>
  </verify>
  <done>tag_article() uses nanoid.generate() instead of uuid.uuid4()</done>
</task>

</tasks>

<verification>
All three storage functions now use nanoid.generate() instead of uuid.uuid4():
- grep "from nanoid import generate" src/storage/sqlite.py (import exists)
- grep "generate()" src/storage/sqlite.py (3 occurrences: article_id, tag_id x2)
- grep "uuid.uuid4" src/storage/sqlite.py (no results)
</verification>

<success_criteria>
1. src/storage/sqlite.py imports `from nanoid import generate` at module level
2. store_article() uses `article_id = generate()` instead of `str(uuid.uuid4())`
3. add_tag() uses `tag_id = generate()` instead of `str(uuid.uuid4())`
4. tag_article() uses `tag_id = generate()` instead of `str(uuid.uuid4())` when creating new tags
5. No `import uuid` statements remain in these three functions
6. nanoid>=2.0.0 is already in pyproject.toml dependencies
</success_criteria>

<output>
After completion, create `.planning/phases/phase-23/23-PLAN-01-SUMMARY.md`
</output>
