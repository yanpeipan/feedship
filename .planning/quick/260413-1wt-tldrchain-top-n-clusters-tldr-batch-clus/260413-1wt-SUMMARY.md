---
phase: quick
plan: 260413-1wt
subsystem: report-generation
tags: [tldr, chain, prompt-engineering]
dependency_graph:
  requires: []
  provides: []
  affects:
    - src/application/report/tldr.py
    - src/llm/chains.py
tech_stack:
  added: []
  patterns:
    - TLDRChain per-cluster article filtering
    - Dual-perspective prompt (CEO + AI analyst)
key_files:
  created: []
  modified:
    - path: src/application/report/tldr.py
      summary: "TLDRChain now processes all clusters; each cluster passes only top_n articles to topics_block"
    - path: src/llm/chains.py
      summary: "TLDR_PROMPT upgraded with CEO + AI analyst dual perspective; max_tokens increased to 800"
decisions: []
metrics:
  duration: "~5 minutes"
  completed: "2026-04-13"
---

# Phase quick Plan 260413-1wt: TLDRChain Top-N Clusters TLDR Batch Clus Summary

## One-liner

TLDRChain now uses per-cluster top_n article filtering with CEO + AI analyst dual-perspective prompt.

## Completed Tasks

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Modify TLDRChain to use per-cluster top_n articles | 0456714 | src/application/report/tldr.py |
| 2 | Upgrade TLDR_PROMPT to CEO + AI analyst perspective | dfd02f2 | src/llm/chains.py |

## Task 1: TLDRChain Per-Cluster Top-N Article Filtering

**Changes:**
- Removed cluster-level `[: self.top_n]` slice (was lines 94-96 in original)
- `_build_topics_block` now sorts each cluster's articles by `quality_weight` descending and takes top_n before selecting first article
- Updated class docstring and `__init__` docstring to clarify `top_n` limits articles per cluster, not number of clusters
- Updated `ainvoke` docstring to reflect new 4-step flow (was 5-step with cluster sorting)

**Key code change in `_build_topics_block`:**
```python
sorted_articles = sorted(
    cluster.articles,
    key=lambda a: getattr(a, "quality_weight", 0.0) or 0.0,
    reverse=True,
)[: self.top_n]
first_article = sorted_articles[0] if sorted_articles else None
```

**Verification:** `grep -n "top_n" src/application/report/tldr.py` shows top_n used in docstrings and article filtering context only.

## Task 2: TLDR_PROMPT Dual Perspective Upgrade

**Changes:**
- System prompt replaced: "news editor" → "senior news analyst with dual perspectives"
- CEO Perspective: business impact, strategic implications, market significance, competitive landscape
- AI/Technology Analyst Perspective: technological innovations, AI/ML developments, industry trends, technical breakthroughs
- 2-3 sentence summaries combining both perspectives
- Human message updated to clarify input is top_n articles per cluster sorted by quality
- `max_tokens` increased from 300 to 800

**Verification:** `grep -n "CEO Perspective" src/llm/chains.py` and `grep -n "800" src/llm/chains.py` both return results.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- tldr.py: TLDRChain processes all clusters, each cluster's topics_block built from only top_n articles (verified via grep)
- chains.py: TLDR_PROMPT contains "CEO Perspective" and "AI analyst" language, max_tokens=800 (verified via grep)
- JSON output format unchanged, compatible with TldrJsonOutputParser
