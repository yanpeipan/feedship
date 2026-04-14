---
name: entity-cluster-classify-dimensions-none-summary
description: entity_cluster.py classify_dimensions fails with None summary
type: debug
status: resolved
created: 2026-04-11
symptoms:
  expected: article.title and article.summary are both strings, concatenation works
  actual: "can only concatenate str (not 'NoneType') to str" at line 37
  reproduction: Run report generation with articles that have None summary
errors:
  - TypeError: can only concatenate str (not "NoneType") to str
    at classify_dimensions(entity_cluster.py:37)
    text = (article.title + " " + article.summary).lower()
root_cause: |
  CONFIRMED - Code logic issue: classify_dimensions() in entity_cluster.py (line 37)
  does not guard against None summary. Articles in the database can have NULL/None
  summary (e.g., if summarization was never run or LLM summarization failed silently).
  The type annotation in ArticleEnriched (summary: str) does not match runtime reality.
  Other functions in the same file (_classify_signal_* in report_generation.py) use
  .get("summary", "") pattern showing awareness of this issue, but classify_dimensions
  was missed.
files:
  - src/application/report/entity_cluster.py
fix_strategies:
  - Cast None to empty string: ((article.title or "") + " " + (article.summary or "")).lower()
  - Add guard: if article.summary is None, use ""
  - Default value: article.summary or ""
confidence: high
