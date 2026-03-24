# Phase 18: Storage Layer Enforcement - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-03-25
**Phase:** 18-Storage Layer Enforcement
**Mode:** assumptions
**Areas analyzed:** Technical Approach, Scope: Article Operations, Scope: Feed Operations, Scope: Crawl Operations, Scope: CLI SQL, Scope: AI Tagging, API Design

## Assumptions Presented

| Assumption | Confidence | Evidence |
|-----------|-----------|----------|
| All SQL operations belong in `src/storage/` | Confident | `src/storage/sqlite.py`, `src/application/articles.py`, `src/application/feed.py`, `src/application/crawl.py`, `src/cli/article.py`, `src/tags/ai_tagging.py` |
| Move article operations to storage | Confident | `src/application/articles.py` lines 49-381 |
| Move feed operations to storage | Confident | `src/application/feed.py` lines 65-184 |
| Move `ensure_crawled_feed()` to storage | Confident | `src/application/crawl.py` lines 185-195 |
| Replace CLI direct SQL with storage function | Confident | `src/cli/article.py` lines 250-257 |
| Move embedding operations to storage | Confident | `src/tags/ai_tagging.py` lines 81-127 |
| `get_db()` stays in `src/storage/sqlite.py` | Confident | `src/storage/__init__.py` exports pattern |
| Storage functions return domain objects | Likely | `ArticleListItem` dataclass pattern |
| Import from `src.storage` not `src.storage.sqlite` | Confident | Already established pattern |

## Corrections Made

No corrections — all assumptions confirmed.

## Auto-Resolved

No auto-resolution needed — all assumptions were Confident.

## External Research

No external research needed — all evidence from codebase analysis.
