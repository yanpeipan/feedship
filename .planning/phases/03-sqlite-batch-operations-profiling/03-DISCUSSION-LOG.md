# Phase 3: SQLite Batch Operations & Profiling - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 03-sqlite-batch-operations-profiling
**Areas discussed:** Batch Upsert Strategy, Batch Failure Handling, Profiling Approach, Covering Index Structure

---

## Batch Upsert Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite UPSERT (INSERT ON CONFLICT) | Native SQLite upsert in single transaction, executemany batch | ✓ |
| Transaction-wrapped individual inserts | BEGIN + individual store_article calls + COMMIT | |
| executemany with raw SQL | Pure executemany without UPSERT, check existence first | |

**User's choice:** SQLite UPSERT (INSERT ON CONFLICT) — auto-selected via --auto
**Notes:** [auto] Selected: "INSERT ... ON CONFLICT DO UPDATE (UPSERT) in single transaction" — single transaction reduces commit overhead from O(N) to O(1)

---

## Batch Failure Handling

| Option | Description | Selected |
|--------|-------------|----------|
| All-or-nothing transaction | Entire batch succeeds or fails together | ✓ |
| Partial batch with savepoints | Savepoint per article, continue on failure | |

**User's choice:** All-or-nothing transaction — auto-selected via --auto
**Notes:** [auto] Selected: "All-or-nothing transaction" — simpler semantics

---

## Profiling Approach

| Option | Description | Selected |
|--------|-------------|----------|
| py-spy (production) + cProfile (baseline) | py-spy for live profiling, cProfile for deterministic benchmarks | ✓ |
| py-spy only | Just production profiling | |
| cProfile only | Just baseline benchmarks | |

**User's choice:** py-spy (production) + cProfile (baseline) — auto-selected via --auto
**Notes:** [auto] Selected: "Both — py-spy for production, cProfile for baseline" — comprehensive profiling

---

## Covering Index Structure

| Option | Description | Selected |
|--------|-------------|----------|
| (feed_id, published_at DESC) | Covering index matching ORDER BY published_at DESC query pattern | ✓ |
| (feed_id, published_at ASC) | Standard ASC index | |
| (feed_id, published_at) + existing separate index | Composite but keep existing single-column indexes | |

**User's choice:** (feed_id, published_at DESC) — auto-selected via --auto
**Notes:** [auto] Selected: "(feed_id, published_at DESC)" — matches list_articles() ORDER BY published_at DESC pattern

---

## Claude's Discretion

- Profiling output directory: `profiles/` (not `.profiles/`)
- Index naming: `idx_articles_feed_published` (short form)

## Deferred Ideas

None — discussion stayed within phase scope.
