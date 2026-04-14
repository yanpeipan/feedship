---
name: 260410-qux-src-llm-core-py
description: 精简 src/llm/core.py 代码
status: in_progress
---

## Plan

### Task 1: 移除未使用的便利函数

**Files:** `src/llm/core.py`

移除：`summarize_text`, `score_quality`, `extract_keywords`, `truncate_content`, `get_encoding_for_model`, `batch_summarize_articles`（保留因为 report_generation.py 有调用）

**Verify:** `uv run python -c "from src.llm import llm_complete; print('OK')"`

### Task 2: 移除冗余异常类

**Files:** `src/llm/core.py`, `src/llm/__init__.py`

移除：`ContentTruncated`, `FeedWeightGated`（从未 raise/无外部 catch）
保留：`LLMError`, `DailyCapExceeded`, `ProviderUnavailable`（raised in code, 文档有用）

**Verify:** `uv run python -m py_compile src/llm/core.py && echo OK`

### Task 3: 简化 _get_litellm_kwargs

**Files:** `src/llm/core.py`

移除 ollama/azure/openai 分支逻辑（Router 已接管），只保留 base_url 逻辑。

**Verify:** `uv run python -c "from src.llm.core import LLMClient; print('OK')"`

### Task 4: 简化 LLMConfig

**Files:** `src/llm/core.py`

移除字段：`provider`, `fallback_chain`, `ollama_base_url`, `max_tokens_per_call`, `weight_gate_min`, `recency_gate_hours`（Router 不需要）

**Verify:** Tests pass

### Task 5: 清理 __init__.py 导出

**Files:** `src/llm/__init__.py`

移除不再导出的：`ContentTruncated`, `FeedWeightGated`, `truncate_content`, `get_encoding_for_model`, `summarize_text`, `score_quality`, `extract_keywords`

**Verify:** Tests pass
