---
phase: 25-verification
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements:
  - NANO-03

must_haves:
  truths:
    - "New articles have nanoid-format IDs (21 chars)"
    - "article list command works with new articles"
    - "article detail <8-char-prefix> works for new articles"
    - "article open <8-char-prefix> works for new articles"
    - "Tag operations (add/remove) work on new articles"
    - "Search returns new articles correctly"
  artifacts:
    - path: "src/storage/sqlite.py"
      provides: "store_article() with nanoid.generate() at line 333"
    - path: "src/application/articles.py"
      provides: "get_article_detail() with 8-char prefix lookup at line 643"
---

<objective>
Verify all article-related operations work correctly with nanoid-format IDs (21 chars).

This is a verification phase - the actual nanoid code changes were made in Phase 23. This plan tests that:
1. New articles have 21-char nanoid IDs
2. article list/detail/open commands work with new articles
3. Tag operations work on new articles
4. Search works with new articles
</objective>

<context>
@.planning/phases/phase-23/23-PLAN-01-SUMMARY.md
@src/storage/sqlite.py
@src/cli/article.py
@src/application/articles.py
</context>

<interfaces>
<!-- Key functions being verified -->

From src/storage/sqlite.py:
- store_article() line 333: `article_id = generate()` (nanoid)
- get_article_detail() lines 643-655: 8-char prefix lookup with `LIKE ? || '%'`
- tag_article() line 244: `tag_id = generate()` (nanoid)

From src/cli/article.py:
- article_list: Uses `article.id[:8]` for display (line 106)
- article_view: Accepts article_id argument, passes to get_article_detail()
- article_open: Accepts article_id argument, passes to get_article_detail()
- article_tag: Calls tag_article() from storage

CLI commands to test:
- python -m src.cli feed add <url>
- python -m src.cli fetch --all
- python -m src.cli article list
- python -m src.cli article view <8-char-prefix>
- python -m src.cli article tag <8-char-prefix> <tag>
- python -m src.cli search <query>
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add test RSS feed and fetch articles</name>
  <files>None (CLI-only verification)</files>
  <read_first>
    - src/cli/feed.py (feed add command)
    - src/cli/crawl.py (fetch command)
  </read_first>
  <action>
    Use a public RSS feed for testing. Add the feed and fetch articles to create new articles with nanoid IDs.

    Commands to execute:
    1. Add a test RSS feed:
       python -m src.cli feed add https://hnrss.org/frontpage

    2. Fetch articles from the feed:
       python -m src.cli fetch --all

    Note the output - count of new articles fetched.
  </action>
  <verify>
    <automated>
      python -m src.cli feed list
      # Should show the new feed
    </automated>
  </verify>
  <done>Test feed added, new articles created with nanoid IDs</done>
  <acceptance_criteria>
    - "feed add" command succeeds and returns feed ID
    - "fetch --all" command fetches new articles (count > 0)
    - New articles visible in feed list
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Verify stored article IDs are 21-char nanoid format</name>
  <files>None (database verification)</files>
  <read_first>
    - src/storage/sqlite.py (lines 290-357 store_article function)
  </read_first>
  <action>
    Query the SQLite database directly to verify new article IDs are 21 characters (nanoid format).

    Run this Python script to check:
    ```python
    from src.storage.sqlite import get_db, get_db_path
    import sqlite3

    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get the most recent articles (created in this test)
    cursor.execute("""
        SELECT id, title, LENGTH(id) as id_len
        FROM articles
        ORDER BY created_at DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    print(f"Found {len(rows)} recent articles")
    for row in rows:
        print(f"  ID: {row['id']} (len={row['id_len']}) title: {row['title'][:40] if row['title'] else 'N/A'}")

    # Verify all are 21 chars
    all_21_chars = all(row['id_len'] == 21 for row in rows)
    print(f"\nAll recent articles have 21-char IDs: {all_21_chars}")
    conn.close()
    ```
  </action>
  <verify>
    <automated>
      python3 -c "
import sqlite3
from src.storage.sqlite import get_db_path
conn = sqlite3.connect(get_db_path())
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT id, LENGTH(id) as len FROM articles ORDER BY created_at DESC LIMIT 10')
rows = cursor.fetchall()
all_21 = all(r['len'] == 21 for r in rows)
print(f'Recent articles: {len(rows)}')
for r in rows:
    print(f'  {r[\"id\"]} (len={r[\"len\"]})')
print(f'All 21-char: {all_21}')
conn.close()
"
    </automated>
  </verify>
  <done>All new articles have 21-char nanoid IDs verified in database</done>
  <acceptance_criteria>
    - Query returns at least 1 article
    - All recent article IDs have length exactly 21 characters
    - IDs are URL-safe alphanumeric (nanoid format)
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Test article list with new nanoid articles</name>
  <files>None (CLI verification)</files>
  <read_first>
    - src/cli/article.py (article_list command, lines 60-114)
  </read_first>
  <action>
    Run the article list command and verify:
    1. New articles appear in the list
    2. Article IDs displayed are truncated to 8 characters
    3. List completes without errors

    Command:
    python -m src.cli article list --limit 10

    Also test verbose mode to see full IDs:
    python -m src.cli article list --limit 10 --verbose
  </action>
  <verify>
    <automated>
      python -m src.cli article list --limit 10 2>&1
      # Exit code must be 0
      # Output should show article IDs (truncated to 8 chars)
    </automated>
  </verify>
  <done>article list shows new nanoid articles correctly</done>
  <acceptance_criteria>
    - "article list" command exits with code 0
    - Output contains truncated 8-char article IDs
    - Output shows article titles/sources
    - No error messages in output
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 4: Test article view with 8-char prefix</name>
  <files>None (CLI verification)</files>
  <read_first>
    - src/storage/sqlite.py (get_article_detail, lines 626-672)
    - src/cli/article.py (article_view command, lines 117-172)
  </read_first>
  <action>
    Get the 8-char prefix of a new nanoid article and test article view with it.

    1. First get article list to find a recent article ID:
       python -m src.cli article list --limit 5 --verbose

    2. Take the first 8 characters of a nanoid article ID

    3. Test article view with the 8-char prefix:
       python -m src.cli article view <8-char-prefix>

    The prefix lookup uses LIKE query in get_article_detail() at line 643-655.
  </action>
  <verify>
    <automated>
      # Get first 8 chars of most recent article ID
      PREFIX=$(python3 -c "import sqlite3; from src.storage.sqlite import get_db_path; conn = sqlite3.connect(get_db_path()); conn.row_factory = sqlite3.Row; c = conn.cursor(); c.execute('SELECT id FROM articles ORDER BY created_at DESC LIMIT 1'); r = c.fetchone(); print(r['id'][:8] if r else ''); conn.close()")
      # Test view with prefix
      python -m src.cli article view "$PREFIX" 2>&1 | head -20
      echo "Exit code: $?"
    </automated>
  </verify>
  <done>article view <8-char-prefix> works for new nanoid articles</done>
  <acceptance_criteria>
    - "article view <8-char-prefix>" exits with code 0
    - Output shows article title, source, date, tags
    - No "Article not found" error
    - Link is displayed
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 5: Test tagging operations on new nanoid articles</name>
  <files>None (CLI verification)</files>
  <read_first>
    - src/storage/sqlite.py (tag_article line 234, untag_article line 260)
    - src/cli/article.py (article_tag command, lines 206-282)
  </read_first>
  <action>
    Test adding and removing tags on new nanoid articles.

    1. Get the 8-char prefix of a recent article:
       PREFIX=$(python3 -c "import sqlite3; from src.storage.sqlite import get_db_path; conn = sqlite3.connect(get_db_path()); conn.row_factory = sqlite3.Row; c = conn.cursor(); c.execute('SELECT id FROM articles ORDER BY created_at DESC LIMIT 1'); r = c.fetchone(); print(r['id'][:8] if r else ''); conn.close()")

    2. Add a test tag:
       python -m src.cli article tag $PREFIX test-nanoid-verification

    3. Verify tag was added (view article):
       python -m src.cli article view $PREFIX
       # Should show "test-nanoid-verification" in Tags

    4. Remove the tag:
       python -m src.cli article untag $PREFIX test-nanoid-verification

    5. Verify tag was removed:
       python -m src.cli article view $PREFIX
       # Should NOT show the tag
  </action>
  <verify>
    <automated>
      PREFIX=$(python3 -c "import sqlite3; from src.storage.sqlite import get_db_path; conn = sqlite3.connect(get_db_path()); conn.row_factory = sqlite3.Row; c = conn.cursor(); c.execute('SELECT id FROM articles ORDER BY created_at DESC LIMIT 1'); r = c.fetchone(); print(r['id'][:8] if r else ''); conn.close()")
      python -m src.cli article tag $PREFIX verify-tag 2>&1
      echo "---"
      python -m src.cli article view $PREFIX 2>&1 | grep -i "verify-tag"
      echo "---"
      python -m src.cli article untag $PREFIX verify-tag 2>&1
      echo "---"
      python -m src.cli article view $PREFIX 2>&1 | grep -i "verify-tag" || echo "Tag removed successfully"
    </automated>
  </verify>
  <done>Tag add/remove work correctly on new nanoid articles</done>
  <acceptance_criteria>
    - "article tag <prefix> <tag>" exits with code 0
    - "article view" shows the added tag
    - "article untag <prefix> <tag>" exits with code 0
    - "article view" no longer shows the removed tag
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 6: Test search returns new nanoid articles</name>
  <files>None (CLI verification)</files>
  <read_first>
    - src/storage/sqlite.py (search_articles, lines 675-723)
    - src/cli/article.py (search command, lines 285-328)
  </read_first>
  <action>
    Test that FTS5 search returns the new nanoid articles.

    1. Get a keyword from a recent article title (use first word of title)

    2. Run search:
       python -m src.cli search "<keyword>"

    3. Verify the results include new nanoid articles (check that IDs are 21 chars)
  </action>
  <verify>
    <automated>
      # Get a keyword from most recent article
      KEYWORD=$(python3 -c "import sqlite3; from src.storage.sqlite import get_db_path; conn = sqlite3.connect(get_db_path()); conn.row_factory = sqlite3.Row; c = conn.cursor(); c.execute('SELECT title FROM articles ORDER BY created_at DESC LIMIT 1'); r = c.fetchone(); print(r['title'].split()[0] if r and r['title'] else ''); conn.close()")
      echo "Searching for: $KEYWORD"
      python -m src.cli search "$KEYWORD" 2>&1
    </automated>
  </verify>
  <done>Search correctly returns new nanoid articles via FTS5</done>
  <acceptance_criteria>
    - "search" command exits with code 0
    - Search results include the new nanoid articles
    - Results display correctly with article information
  </acceptance_criteria>
</task>

</tasks>

<verification>
Overall Phase 25 verification checks:

1. Database query confirms all recent articles have 21-char IDs
2. article list command shows truncated 8-char IDs correctly
3. article view with 8-char prefix finds and displays article
4. article tag adds tag to nanoid article, article untag removes it
5. search returns nanoid articles in results

All commands must exit with code 0 and produce expected output.
</verification>

<success_criteria>
Phase 25 verification complete when ALL of:
1. New articles created with nanoid.generate() have 21-char IDs
2. article list displays new articles correctly
3. article view <8-char-prefix> works for new articles
4. article open <8-char-prefix> works (uses same get_article_detail)
5. article tag/untag work on new articles
6. search returns new articles via FTS5

These verify NANO-03: All article-related operations work correctly with nanoid format.
</success_criteria>

<output>
After completion, create `.planning/phases/phase-25-verification/25-PLAN-01-SUMMARY.md`
</output>
