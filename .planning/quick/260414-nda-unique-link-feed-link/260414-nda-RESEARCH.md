# Research: UNIQUE(link) Constraint on feed articles

**Date:** 2026-04-14
**Task:** 增加约束：UNIQUE(link) 删除feed 里的link重复文章
**Status:** RESEARCH COMPLETE

---

## 1. Schema Current State

**Articles table** (`src/storage/sqlite/init.py`):
- Has `UNIQUE(feed_id, guid)` — composite unique on feed+guid
- `link` column has an index (`idx_articles_link`) but **no UNIQUE constraint**
- `guid` is the deduplication key, but `link` can have duplicates across feeds or even within a feed

**Feeds table** (`src/storage/sqlite/init.py`):
- `url TEXT NOT NULL UNIQUE` — URL is already unique at feed level
- `feeds` table itself has no link column (correct — articles table has link)

---

## 2. Constraint Approach

SQLite does not support `ALTER TABLE ADD CONSTRAINT` for adding `UNIQUE` constraints to existing columns. Two options:

### Option A: Rename + Recreate (Standard SQLite pattern)
```sql
BEGIN;
ALTER TABLE articles RENAME TO articles_old;
CREATE TABLE articles ( ...existing schema..., UNIQUE(link) );
INSERT INTO articles SELECT * FROM articles_old;
DROP TABLE articles_old;
COMMIT;
```

### Option B: Create unique index (works for most cases)
```sql
CREATE UNIQUE INDEX idx_articles_link_unique ON articles(link);
```
This enforces uniqueness via index without changing the table schema. SQLite will reject inserts that violate uniqueness.

**Recommendation: Option B** — less invasive, equivalent enforcement, no data loss risk.

---

## 3. Duplicate Deletion Strategy

**Decision (from CONTEXT):** Keep any one row, delete others. No preference.

```sql
DELETE FROM articles
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM articles
    GROUP BY link
);
```

This keeps the row with the smallest `rowid` per `link` group.

---

## 4. Migration Script

A standalone script that:
1. Reports current duplicate count
2. Deletes duplicate rows
3. Creates `UNIQUE` index on `link`
4. Verifies constraint

**Script location:** `scripts/migrate_add_article_link_unique.py`

```python
"""
Migration: Add UNIQUE constraint on articles.link

Steps:
1. Count and report duplicate links
2. Delete duplicates (keep lowest rowid)
3. Create UNIQUE index on link
4. Verify constraint
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / ".local" / "share" / "feedship" / "feedship.db"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Count duplicates
    cursor.execute("""
        SELECT COUNT(*) FROM articles
        WHERE link IN (
            SELECT link FROM articles GROUP BY link HAVING COUNT(*) > 1
        )
    """)
    dup_count = cursor.fetchone()[0]
    print(f"Duplicate articles (by link): {dup_count}")

    # 2. Delete duplicates (keep smallest rowid per link)
    cursor.execute("""
        DELETE FROM articles
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM articles
            WHERE link IS NOT NULL
            GROUP BY link
        )
    """)
    deleted = cursor.rowcount
    print(f"Deleted {deleted} duplicate rows")
    conn.commit()

    # 3. Create unique index
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_articles_link_unique ON articles(link)
    """)
    print("Created UNIQUE index idx_articles_link_unique on articles(link)")
    conn.commit()

    # 4. Verify
    cursor.execute("""
        SELECT COUNT(*) FROM articles
        WHERE link IN (
            SELECT link FROM articles GROUP BY link HAVING COUNT(*) > 1
        )
    """)
    remaining = cursor.fetchone()[0]
    print(f"Remaining duplicates: {remaining}")
    print("Migration complete." if remaining == 0 else "WARNING: duplicates remain!")

    conn.close()

if __name__ == "__main__":
    main()
```

---

## 5. Integration Points

| Area | File | Change |
|------|------|--------|
| Migration | `scripts/migrate_add_article_link_unique.py` | **New file** |
| Schema init | `src/storage/sqlite/init.py` | Add `UNIQUE(link)` to `CREATE TABLE articles` (future) |
| Future insert path | `src/storage/sqlite/impl.py` | No change — UNIQUE index auto-rejects duplicates |

### Where articles are inserted:
- `src/storage/sqlite/impl.py` — `insert_article()` / `insert_articles_batch()`
- `src/application/fetch.py` — `fetch_and_process_feed()` → deduplication pipeline

### Pre-existing dedup:
- `deduplicate_articles()` in the fetch pipeline uses `content_hash` + `minhash_signature` for fuzzy dedup
- `UNIQUE(link)` adds exact-match dedup at insert time, which is a **different** mechanism

---

## 6. Action Items

1. **Create** `scripts/migrate_add_article_link_unique.py` with the script above
2. **Run** the migration script once to clean existing duplicates and add the constraint
3. **Add** `idx_articles_link` → change to `UNIQUE` index in `init.py` schema (for new installations)
4. **Verify** by running `uv run feedship list-articles --limit 1` after migration

---

## 7. Risk Assessment

- **Low risk** — duplicates are data quality issue, not functional bug
- **Reversible** — can drop index `DROP INDEX idx_articles_link_unique` if needed
- **No breaking change** — existing code that inserts articles will get `sqlite3.IntegrityError: UNIQUE constraint failed` if duplicate link is inserted (same behavior as existing `UNIQUE(feed_id, guid)` constraint)
