---
phase: quick-260413
plan: "01"
subsystem: llm
tags: [refactor, langchain, LCEL, runnable]
dependency_graph:
  requires: []
  provides:
    - LLMWrapper extending Runnable (enables pipe syntax)
  affects:
    - src/llm/chains.py (call sites updated)
    - src/llm/__init__.py (export changed)
tech_stack:
  added: []
  patterns:
    - LangChain Runnable pattern with invoke/ainvoke delegation
    - Fluent builder pattern with bind(), with_structured_output(), with_retry()
key_files:
  created: []
  modified:
    - src/llm/core.py (LLMWrapper refactored to extend Runnable, get_llm_wrapper removed)
    - src/llm/chains.py (call sites updated to use LLMWrapper())
    - src/llm/__init__.py (export changed from get_llm_wrapper to LLMWrapper)
decisions:
  - "LLMWrapper extends langchain_core.runnables.Runnable directly"
  - "Deleted get_llm_wrapper factory function entirely"
  - "All chain factories use LLMWrapper() directly"
metrics:
  duration: ~
  completed: 2026-04-13
---

# Quick Task 260413-kap: LLMWrapper Runnable Refactor Summary

## One-liner

Refactored LLMWrapper to extend langchain_core.runnables.Runnable, enabling direct LCEL pipe syntax with CLASSIFY_TRANSLATE_PROMPT | LLMWrapper().

## Truths Achieved

- [x] LLMWrapper() works directly in LCEL pipe chains
- [x] get_llm_wrapper is removed
- [x] All import tests pass

## Deviations from Plan

None - plan executed exactly as written.

## Verification

```bash
uv run python -c "
from src.llm import LLMWrapper
from src.llm.chains import get_translate_chain, get_tldr_chain, get_classify_translate_chain
from langchain_core.runnables import Runnable

assert issubclass(LLMWrapper, Runnable), 'LLMWrapper must extend Runnable'
chain1 = get_translate_chain()
chain2 = get_tldr_chain()
chain3 = get_classify_translate_chain(tag_list='tech,news', news_list='[]')
print('All imports and assertions pass')
"
```

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| src/llm/core.py exists | FOUND |
| src/llm/chains.py exists | FOUND |
| src/llm/__init__.py exists | FOUND |
| Commit 10a84f2 exists | FOUND |
