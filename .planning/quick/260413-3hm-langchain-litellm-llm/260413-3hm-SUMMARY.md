---
phase: quick-260413-3hm
plan: "01"
subsystem: llm
tags: [langchain, litellm, ChatLiteLLM, LCEL]
dependency_graph:
  requires: []
  provides:
    - ChatLiteLLM wrapper via _get_llm_wrapper()
  affects:
    - src/llm/chains.py
tech_stack:
  added:
    - langchain-litellm>=0.6.4
  patterns:
    - ChatLiteLLM with bind() for response_format/thinking
    - Stateless wrapper (no caching needed)
key_files:
  created: []
  modified:
    - pyproject.toml (added langchain-litellm dependency)
    - src/llm/chains.py (AsyncLLMWrapper -> ChatLiteLLM refactor)
decisions:
  - "ChatLiteLLM is stateless, no caching needed - removed _llm_wrapper_cache"
  - "response_format and thinking passed via bind() method"
  - "ChatLiteLLM uses litellm internally, model routing via litellm router preserved"
metrics:
  duration: "< 1 minute"
  completed: "2026-04-13"
---

# Quick Task 260413-3hm Summary

## One-liner

ChatLiteLLM replaces AsyncLLMWrapper in _get_llm_wrapper() for native LCEL integration and abatch() concurrency support.

## Tasks Completed

| Task | Commit | Files |
|------|--------|-------|
| Add langchain-litellm dependency | 7ab6932 | pyproject.toml |
| Refactor _get_llm_wrapper() to use ChatLiteLLM | 7ab6932 | src/llm/chains.py |
| Verify abatch() concurrency | 7ab6932 | src/llm/chains.py |

## Changes Made

### 1. pyproject.toml
- Added `langchain-litellm>=0.6.4,<1` dependency

### 2. src/llm/chains.py
- Removed `AsyncLLMWrapper` class (139 lines)
- Removed `_llm_wrapper_cache` dict
- Removed `asyncio`, `BaseMessage`, `ChatPromptValue` imports (no longer needed)
- Refactored `_get_llm_wrapper()` to return `ChatLiteLLM` instance:
  - Gets model name from `get_llm_client().config.model`
  - Creates `ChatLiteLLM(model=model, max_tokens=...)`
  - Applies `response_format` and `thinking` via `.bind()` method
  - No caching needed (ChatLiteLLM is stateless)

## Verification Results

- `ChatLiteLLM import OK`
- `Type: ChatLiteLLM` - confirmed wrapper returns correct type
- `Has abatch: True` - abatch() method available
- `abatch()` with `config={"max_concurrency": N}` works natively
- `response_format` and `thinking` bind() works correctly
- All chain functions (`get_translate_chain`, `get_tldr_chain`, `get_classify_translate_chain`) import successfully

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] langchain-litellm added to pyproject.toml
- [x] _get_llm_wrapper() returns ChatLiteLLM instance
- [x] AsyncLLMWrapper class removed from chains.py
- [x] abatch() method available on returned wrapper
- [x] Commit 7ab6932 exists

## Notes

- grype reports torch vulnerabilities (pre-existing, unrelated to this change)
- ruff hook passed successfully
