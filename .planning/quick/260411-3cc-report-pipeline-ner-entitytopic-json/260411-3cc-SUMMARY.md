# Quick Task 260411-3cc Summary

## Task
修复 report pipeline 的 NER 和 EntityTopic JSON 解析失败问题，以及移除废弃的标题翻译代码。

## Changes

### 1. All JSON chains: add `thinking: disabled`

Added `extra_body={"thinking": {"type": "disabled"}}` to:
- `get_ner_chain()` — NER extraction
- `get_entity_topic_chain()` — entity topic generation
- `get_tldr_chain()` — TLDR generation
- `get_evaluate_chain()` — report quality evaluation

### 2. Removed dead title translation code

Removed from `src/application/report/report_generation.py`:
- `_clean_translation()` function
- `_is_chinese()` function
- `_title_translate_cache` dict
- `_translate_title_sync()` function
- `_translate_titles_batch_async()` function
- `_format_article_title()` function
- `env.filters["format_title"]` registration
- Unused `get_llm_client` import

## Root Cause

MiniMax models return thinking blocks (reasoning traces) that pollute the JSON output.
JsonOutputParser expects clean JSON but gets markdown-formatted thinking text mixed with JSON.
Adding `thinking: disabled` tells MiniMax to skip the reasoning trace and output clean JSON directly.

## Verification

- All JSON chains confirmed with `grep -n "thinking.*disabled" src/llm/chains.py`
- No dead translation code: `grep "_translate_titles_batch_async\|_format_article_title" → no matches`

## Commit

`795166f` fix(report): disable thinking on all JSON chains to fix JSON parsing
