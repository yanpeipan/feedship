---
status: testing
phase: 38-search-result-ranking
source:
  - .planning/phases/38-search-result-ranking/38-01-SUMMARY.md
started: 2026-03-28T17:10:00Z
updated: 2026-03-28T17:10:00Z
---

## Current Test

number: 1
name: Semantic search ranking
expected: |
  Running `rss-reader search --semantic <query>` returns results ranked by multi-factor score:
  - 50% normalized cosine similarity
  - 30% normalized freshness (newer articles score higher)
  - 20% source weight (openai.com=1.0, arxiv.org=0.9, medium.com=0.5, default=0.3)

  Results with no sqlite_id (pre-v1.8 articles) are excluded from ranked results.
awaiting: user response

## Tests

### 1. Semantic search ranking
expected: |
  Running `rss-reader search --semantic <query>` returns results ranked by multi-factor score:
  - 50% normalized cosine similarity
  - 30% normalized freshness (newer articles score higher)
  - 20% source weight (openai.com=1.0, arxiv.org=0.9, medium.com=0.5, default=0.3)

  Results with no sqlite_id (pre-v1.8 articles) are excluded from ranked results.
result: pending

### 2. CLI output shows "ranked" label
expected: |
  Running `rss-reader search --semantic <query>` shows header:
  "Semantic search results (ranked):"
  instead of the old "Semantic search results (by similarity):"
result: pending

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0

## Gaps

[none yet]
