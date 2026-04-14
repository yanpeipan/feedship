---
status: resolved
trigger: "entity-cluster-quality-score"
created: 2026-04-11T00:00:00Z
updated: 2026-04-11T00:00:00Z
---

## Current Focus
hypothesis: quality_score is often NULL in DB for some articles; the sum() calls in entity_cluster.py don't handle None
test: sum() with generator expression on quality_score fails when any value is None
expecting: None + int fails with TypeError
next_action: Archive session after human verification confirmed

## Symptoms
expected: Articles cluster by entity topic with quality_score summing correctly
actual: TypeError when summing quality_score — some article has None quality_score
errors: TypeError: unsupported operand type(s) for +: 'int' and 'NoneType' at entity_cluster.py:73
reproduction: Run `feedship report` on a feed with articles that have no quality_score
started: Started after recent changes to storage/quality_score SELECT

## Eliminated

## Evidence
- timestamp: 2026-04-11T00:00:00Z
  checked: entity_cluster.py lines 65-85
  found: Line 73 uses `sum(a.quality_score for a in x[1])` - fails if any quality_score is None
  implication: Need to handle None quality_score in sum()
- timestamp: 2026-04-11T00:00:00Z
  checked: entity_cluster.py lines 135-160
  found: Lines 139 and 156 also have `sum(a.quality_score for a in entity_articles)` with same issue
  implication: All three sum() calls need to handle None
- timestamp: 2026-04-11T00:00:00Z
  checked: commit 05a0910 message
  found: "quality_score is often NULL in DB" - confirms quality_score can be None
  implication: This is expected DB state, code must handle None
- timestamp: 2026-04-11T00:00:00Z
  checked: list_articles SELECT in articles.py
  found: quality_score is properly selected after a040d42 fix
  implication: The issue is not SELECT missing - it's that DB values are genuinely NULL
- timestamp: 2026-04-11T00:00:00Z
  checked: Fix applied and unit test
  found: Test with None quality_score now succeeds
  implication: Fix is correct

## Resolution
root_cause: sum() in entity_cluster.py cannot add int + None. quality_score is legitimately NULL in the database for some articles, and the code didn't handle this.
fix: Replace `a.quality_score` with `a.quality_score or 0` in all three sum() calls (lines 73, 139, 156)
verification: User confirmed fix works in real workflow
files_changed: [src/application/report/entity_cluster.py]
