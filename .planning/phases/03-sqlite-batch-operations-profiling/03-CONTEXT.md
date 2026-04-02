# Phase 3: SQLite Batch Operations & Profiling - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliverable: Batch `upsert_articles()` with O(1) commits instead of O(N), covering index on `(feed_id, published_at)`, and profiling infrastructure for ongoing performance measurement.
</domain>

<decisions>
## Implementation Decisions

### PERF-01: Batch Article Upsert

- **D-01:** Use SQLite native `INSERT ... ON CONFLICT DO UPDATE` (UPSERT) in a single transaction
  - Rationale: Single transaction reduces commit overhead from O(N) to O(1), UPSERT handles insert/update in one statement
  - Code pattern: `cursor.executemany()` with UPSERT statements inside `with get_db() as conn:`

- **D-02:** Batch failure handling: all-or-nothing transaction
  - Rationale: Simpler semantics, if any article fails the entire batch rolls back
  - Alternative (deferred): Partial batch with savepoints for future enhancement

- **D-03:** Keep existing `store_article()` for single-article use cases
  - Rationale: Used directly in tests and some code paths, breaking change avoided

### PERF-02: Covering Index

- **D-04:** Create index `CREATE INDEX IF NOT EXISTS idx_articles_feed_published ON articles(feed_id, published_at DESC)`
  - Rationale: `list_articles()` queries use `ORDER BY published_at DESC`, DESC index matches query pattern
  -覆盖: Existing queries `WHERE feed_id = ? ORDER BY published_at DESC`

### PERF-03: Profiling Infrastructure

- **D-05:** Use `py-spy` for production profiling (low-overhead sampling profiler)
  - Rationale: Can profile running processes without code changes, safe for production
  - Command: `py-spy record -o profile.svg -- python -m src.cli`

- **D-06:** Use `cProfile` for baseline benchmarks
  - Rationale: Built into Python stdlib, deterministic output for comparing before/after
  - Implementation: Add `--profile` flag to fetch commands, output to `profiles/` directory

### Claude's Discretion
- Profiling output directory location (`profiles/` vs `.profiles/`) — use `profiles/`
- Index naming (`idx_articles_feed_published` vs `articles_feed_published_idx`) — use short form
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Tech stack, existing architecture
- `.planning/REQUIREMENTS.md` — PERF-01, PERF-02, PERF-03 requirements
- `.planning/research/PITFALLS.md` — N+1 pattern details (Pitfalls #1, #2)
- `.planning/research/FEATURES.md` — Batch operations patterns
- `.planning/research/STACK.md` — Profiling tool recommendations

### Codebase
- `src/storage/sqlite/impl.py` — Existing `upsert_articles()`, `store_article()`, `store_article_async()` implementations
- `src/storage/sqlite/init.py` — Database schema and existing indexes
- `src/application/fetch.py:89` — `upsert_articles_async()` usage site
- `src/application/feed.py:269` — `upsert_articles()` usage site

### Research (existing)
- `.planning/research/SUMMARY.md` — Phase ordering rationale, batch ops first
- `.planning/research/PITFALLS.md` §N+1 Query Pattern — N+1 details confirmed in code
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/storage/sqlite/impl.py:282` — Existing `upsert_articles()` — N+1 pattern to fix
- `src/storage/sqlite/impl.py:309` — `upsert_articles_async()` — same N+1 pattern
- `get_db()` context manager — already transaction-aware

### Established Patterns
- SQLite with WAL mode already enabled
- Async writes via `asyncio.to_thread()` + `asyncio.Lock`
- `nanoid` for article IDs

### Integration Points
- `src/application/fetch.py:89` — `await upsert_articles_async(article_ids)` for async path
- `src/application/feed.py:271` — `upsert_articles(parsed_articles)` for sync path
- Tests in `tests/test_storage.py` — `test_store_article_*` tests need updating
</code_context>

<specifics>
## Specific Ideas

No specific "I want it like X" moments — standard batch SQL optimization approach.
</specifics>

<deferred>
## Deferred Ideas

### Batch Partial Failure Handling
- User accepted all-or-nothing transaction for v1.3
- Future: Partial batch with savepoints if users want resilience within batch
- Phase: Future enhancement (not v1.3)

</deferred>

---
*Phase: 03-sqlite-batch-operations-profiling*
*Context gathered: 2026-04-02*
