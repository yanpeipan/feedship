---
phase: quick
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/migrate_add_article_link_unique.py
  - src/storage/sqlite/init.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Duplicate articles with same link are deleted from database"
    - "UNIQUE constraint on articles.link prevents future duplicates"
    - "New database installations will have UNIQUE constraint from init"
  artifacts:
    - path: "scripts/migrate_add_article_link_unique.py"
      provides: "Migration script that cleans duplicates and adds constraint"
    - path: "src/storage/sqlite/init.py"
      provides: "Updated schema with UNIQUE index on link"
  key_links:
    - from: "scripts/migrate_add_article_link_unique.py"
      to: "src/storage/sqlite/init.py"
      via: "Schema reference for articles table"
---

<objective>
Add UNIQUE constraint on articles.link, delete existing duplicate articles.

Purpose: Prevent duplicate articles with the same link from being stored. 36Kr RSS has duplicate GUID issues causing duplicate articles.
Output: Migration script + updated schema
</objective>

<context>
@src/storage/sqlite/init.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create migration script</name>
  <files>scripts/migrate_add_article_link_unique.py</files>
  <action>
Create migration script at `scripts/migrate_add_article_link_unique.py` that:

1. Connects to SQLite database at `~/.local/share/feedship/feedship.db`
2. Counts duplicate articles (same link, different rowid)
3. Deletes duplicates keeping smallest rowid per link group: `DELETE FROM articles WHERE rowid NOT IN (SELECT MIN(rowid) FROM articles WHERE link IS NOT NULL GROUP BY link)`
4. Creates unique index: `CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_link_unique ON articles(link)`
5. Verifies no duplicates remain and prints summary

Use the exact DB_PATH and SQL from the RESEARCH.md findings.
  </action>
  <verify>
    <automated>python scripts/migrate_add_article_link_unique.py 2>&1</automated>
  </verify>
  <done>Migration script runs without errors, reports duplicate count deleted and constraint created</done>
</task>

<task type="auto">
  <name>Task 2: Update init.py schema</name>
  <files>src/storage/sqlite/init.py</files>
  <action>
Read `src/storage/sqlite/init.py`. Find the `CREATE TABLE articles` statement. Add a `UNIQUE(link)` index after the existing `idx_articles_link` index. The new index should be named `idx_articles_link_unique`.

Current (from RESEARCH):
```sql
CREATE INDEX idx_articles_link ON articles(link);
```

Change to:
```sql
CREATE UNIQUE INDEX idx_articles_link_unique ON articles(link);
```

This ensures new installations have the UNIQUE constraint from the start.
  </action>
  <verify>
    <automated>grep -n "idx_articles_link_unique" src/storage/sqlite/init.py</automated>
  </verify>
  <done>init.py contains `idx_articles_link_unique` UNIQUE index definition</done>
</task>

</tasks>

<verification>
Run migration on existing database and verify constraint works:
1. `python scripts/migrate_add_article_link_unique.py` - should delete duplicates and create index
2. `sqlite3 ~/.local/share/feedship/feedship.db "SELECT COUNT(*) FROM articles WHERE link IN (SELECT link FROM articles GROUP BY link HAVING COUNT(*) > 1)"` - should return 0
3. `uv run feedship list-articles --limit 1` - should work normally
</verification>

<success_criteria>
- Migration script created and executed successfully
- Duplicate articles deleted (any duplicates that existed are removed)
- UNIQUE index `idx_articles_link_unique` created on articles.link
- Schema in init.py updated to reflect the UNIQUE index for new installations
- No existing functionality broken
</success_criteria>

<output>
After completion, create `.planning/quick/260414-nda-unique-link-feed-link/260414-nda-SUMMARY.md`
</output>
