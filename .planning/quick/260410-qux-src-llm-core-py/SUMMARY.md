---
name: 260410-qux-summary
description: 精简 src/llm/core.py — 移除未使用代码和冗余异常
type: project
---

# 260410-qux Summary: 精简 src/llm/core.py

## Completed

### Task 1: 移除未使用的便利函数 ✅
- 移除: `summarize_text`, `score_quality`, `extract_keywords`, `truncate_content`, `get_encoding_for_model`
- 保留: `batch_summarize_articles`（report_generation.py 有调用）
- 验证: `uv run python -c "from src.llm import llm_complete; print('OK')"` ✅

### Task 2: 移除冗余异常类 ✅
- 移除: `ContentTruncated`, `FeedWeightGated`（从未 raise/无外部 catch）
- 保留: `LLMError`, `DailyCapExceeded`, `ProviderUnavailable`（raised in code）
- 验证: `uv run python -m py_compile src/llm/core.py && echo OK` ✅

### Task 3: 简化 _get_litellm_kwargs ✅
- 整个函数已移除 — Router 接管了 provider 路由逻辑

### Task 4: 简化 LLMConfig ✅
- 移除字段: `provider`, `base_url`, `ollama_base_url`, `fallback_chain`, `max_tokens_per_call`, `weight_gate_min`, `recency_gate_hours`
- 测试通过 ✅

### Task 5: 清理 __init__.py 导出 ✅
- 移除: `ContentTruncated`, `FeedWeightGated`, `truncate_content`, `get_encoding_for_model`, `summarize_text`, `score_quality`, `extract_keywords`

## Results

- **删除**: 520 行代码（core.py, __init__.py, test_llm.py）
- **commit**: `837fc9e refactor(llm): simplify core.py after Router migration`
- **测试**: test_llm.py 5/5 通过
