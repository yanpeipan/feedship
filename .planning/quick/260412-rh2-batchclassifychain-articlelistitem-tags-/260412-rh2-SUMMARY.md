---
phase: quick-260412-rh2
plan: "01"
type: execute
subsystem: report
tags: [refactor, batch-classify, article-list-item]
dependency_graph:
  requires: []
  provides: []
  affects:
    - src/application/report/report_generation.py
    - src/application/report/classify.py
    - src/application/articles.py
tech_stack:
  added: []
  patterns:
    - "ArticleListItem enriched in-place with .tags and .translation"
    - "BatchClassifyChain returns list[ArticleListItem] (not ClassifyTranslateItem)"
key_files:
  created: []
  modified:
    - path: src/application/articles.py
      desc: Added tags: list[str] and translation: str|None to ArticleListItem
    - path: src/application/report/classify.py
      desc: BatchClassifyChain returns enriched ArticleListItem list
    - path: src/application/report/report_generation.py
      desc: Simplified to use enriched ArticleListItem directly
decisions: []
metrics:
  duration: "~2 min"
  completed: "2026-04-12T11:50:00Z"
---

# Phase quick-260412-rh2 Plan 01 Summary

## One-liner

Refactored BatchClassifyChain to return enriched ArticleListItem with tags and translation attached directly, eliminating downstream manual lookups.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add tags and translation fields to ArticleListItem | 6138505 | articles.py |
| 2 | Fix mutable default (field(default_factory=list)) | 4ca542c | articles.py |
| 3 | BatchClassifyChain returns list[ArticleListItem] | 6db23d9 | classify.py |
| 4 | Simplify report_generation to use enriched ArticleListItem | 080eb5c | report_generation.py |

## Deviations from Plan

**1. [Rule 1 - Bug] Mutable list default in dataclass**
- **Found during:** Verification (uv run python test)
- **Issue:** `ValueError: mutable default <class 'list'> for field tags is not allowed`
- **Fix:** Changed `tags: list[str] = []` to `tags: list[str] = field(default_factory=list)`
- **Files modified:** src/application/articles.py
- **Commit:** 4ca542c

## Verification Results

```
Result type: ArticleListItem
Has tags: True
Has translation: True
tags: ['AI']
translation: 宣布AI突破
```

## Success Criteria

- [x] ArticleListItem has tags=list[str] and translation=str|None fields
- [x] BatchClassifyChain.ainvoke returns list[ArticleListItem] with .tags and .translation populated
- [x] report_generation.py no longer builds trans_by_id or tag_groups manually
- [x] ReportArticle construction uses art.tags and art.translation directly

## Commits

- `6138505` feat(260412-rh2): add tags and translation fields to ArticleListItem
- `4ca542c` fix(260412-rh2): use field(default_factory=list) for mutable tags default
- `6db23d9` feat(260412-rh2): BatchClassifyChain returns enriched ArticleListItem
- `080eb5c` refactor(260412-rh2): use enriched ArticleListItem directly in report_generation

## Self-Check

- [x] All modified files exist
- [x] All commit hashes found in git log
- [x] Verification test passed
