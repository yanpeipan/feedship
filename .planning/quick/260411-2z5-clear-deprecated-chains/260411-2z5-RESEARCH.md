# Quick Task 260411-2z5: Clear Deprecated Chains - Research

**Researched:** 2026-04-11
**Domain:** Python refactoring (function removal)
**Confidence:** HIGH

## Summary

Five deprecated chain functions need removal from `src/llm/chains.py`. Grep confirms zero callers in `src/` for all five functions. Associated PROMPTs and MAX_TOKENS_PER_CHAIN entries are also dead code and should be removed together. One test in `tests/test_report.py` also needs removal.

## Deletion Targets

### Functions to Remove (src/llm/chains.py)

| Function | Lines | Status |
|----------|-------|--------|
| `get_classify_chain` | 152-158 | Deprecated, no callers |
| `get_layer_summary_chain` | 184-190 | Deprecated, no callers |
| `get_topic_title_chain` | 211-217 | Deprecated, no callers |
| `get_topic_title_and_layer_chain` | 238-248 | Deprecated, no callers |
| `get_title_translate_chain` | 321-332 | Deprecated, no callers |

### Associated PROMPTs to Remove

| Prompt | Lines | Used Only By |
|--------|-------|--------------|
| `CLASSIFY_PROMPT` | 133-149 | `get_classify_chain` |
| `LAYER_SUMMARY_PROMPT` | 162-181 | `get_layer_summary_chain` |
| `TOPIC_TITLE_PROMPT` | 194-208 | `get_topic_title_chain` |
| `TOPIC_TITLE_AND_LAYER_PROMPT` | 221-235 | `get_topic_title_and_layer_chain` |
| `TITLE_TRANSLATE_PROMPT` | 298-309 | `get_title_translate_chain` |

### MAX_TOKENS_PER_CHAIN Cleanup

| Key | Value | Action |
|-----|-------|--------|
| `classify` | 100 | Remove (only used by deprecated `get_classify_chain`) |
| `topic_title` | 50 | Remove (only used by deprecated chains) |
| `layer_summary` | 600 | Remove (only used by deprecated `get_layer_summary_chain`) |
| `evaluate` | 200 | Keep (used by `get_evaluate_chain`) |
| `translate` | 1000 | Keep (used by `get_translate_chain`) |

### Tests to Remove

| File | Lines | Test |
|------|-------|------|
| `tests/test_report.py` | 150-165 | `test_llm_chain_classify_returns_valid_layer` (uses deprecated `get_classify_chain`) |

Note: `test_llm_chain_evaluate_returns_valid_json` (lines 167+) uses `get_evaluate_chain` which is NOT deprecated — keep it.

## Caller Verification

**Verified:** No callers found in `src/` for any of the 5 deprecated functions.

```bash
grep -r "get_classify_chain\|get_layer_summary_chain\|get_topic_title_chain\|get_topic_title_and_layer_chain\|get_title_translate_chain" src/
# Returns only the function definitions themselves
```

## Test Implications

- `tests/test_report.py::TestLLMChains::test_llm_chain_classify_returns_valid_layer` must be deleted (lines 150-165)
- `tests/test_report.py::TestLLMChains::test_llm_chain_evaluate_returns_valid_json` is unaffected — uses `get_evaluate_chain` which stays
- No other test files reference these deprecated functions

## Edit Approach

**Recommended:** Use the Edit tool to surgically remove each function block. This is safer than rewriting the entire file.

Steps:
1. Remove each `(function, PROMPT)` pair as a single edit
2. Clean up `MAX_TOKENS_PER_CHAIN` entries last
3. Delete the test function in `test_report.py`

## Files to Modify

| File | Change |
|------|--------|
| `src/llm/chains.py` | Remove 5 functions + 5 prompts + 3 MAX_TOKENS entries |
| `tests/test_report.py` | Remove lines 150-165 (one test function) |

## Non-Blocking Items

- `docs/superpowers/specs/2026-04-10-ai-report-entity-clustering-design.md` references `get_topic_title_and_layer_chain` as a design reference pattern — user decision to update or leave as historical reference.

## Assumptions Log

| # | Claim | Risk if Wrong |
|---|-------|---------------|
| A1 | No callers in `tests/` beyond the one identified test | Low — grep confirms |

## Open Questions

None — caller verification complete, deletion targets identified.
