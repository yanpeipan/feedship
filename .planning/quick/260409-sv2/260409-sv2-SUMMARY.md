# Quick 260409-sv2: Merge Topic Title + Layer Classification

## One-liner

Combined `get_topic_title_chain()` and `classify_cluster_layer()` into a single `get_topic_title_and_layer_chain()` LLM call using `JsonOutputParser`, eliminating one LLM call per topic cluster.

## Plan Reference

Plan 260409-sv2-01

## Tasks Completed

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | Add combined chain to chains.py | 9f24fc1 | src/llm/chains.py |
| 2 | Modify `_cluster_articles_into_topics` to use combined chain | 9f24fc1 | src/application/report.py |
| 3 | Remove redundant classify loop in `_cluster_articles_async` | 9f24fc1 | src/application/report.py |

## Changes

### Task 1: Added `get_topic_title_and_layer_chain()` (chains.py)

- New `TOPIC_TITLE_AND_LAYER_PROMPT` combining topic title instruction + layer classification instruction
- Output format: JSON with `{title: "...", layer: "..."}` via `JsonOutputParser()`
- Title max 20 chars; layer restricted to: AI应用, AI模型, AI基础设施, 芯片, 能源

### Task 2: Modified `_cluster_articles_into_topics` (report.py)

- Replaced `get_topic_title_chain` import with `get_topic_title_and_layer_chain`
- Updated `title_for()` inner function to call combined chain
- Parses JSON result, sets both `topic["title"]` and `topic["layer"]`
- Title fallback: `topic["sources"][0].get("title", "Misc")[:20]` if LLM fails
- Layer fallback: "AI应用" if LLM fails

### Task 3: Removed redundant classify loop (report.py)

- Removed the `for topic in all_topics: topic["layer"] = await classify_cluster_layer(...)` loop
- Topics now have `layer` set inline during topic title generation in `_cluster_articles_into_topics`
- `classify_cluster_layer()` function definition retained (not called by v2 pipeline)

## Deviations from Plan

None - plan executed exactly as written.

## Verification

```bash
uv run feedship --debug report --since 2026-04-07 --until 2026-04-10 --language zh
```

Debug logs confirm combined chain is being called (visible in LiteLLM request content showing combined prompt with JSON output instructions).

## Metrics

- Duration: ~10 minutes (including verification)
- Commits: 1 (9f24fc1)
- Files modified: 2 (src/llm/chains.py, src/application/report.py)
- Net change: +31 lines, -9 lines

## Self-Check: PASSED

- [x] Combined chain added to chains.py with JsonOutputParser
- [x] `_cluster_articles_into_topics` uses combined chain, sets topic["layer"]
- [x] Redundant classify loop removed from `_cluster_articles_async`
- [x] Commit 9f24fc1 verified in git log
