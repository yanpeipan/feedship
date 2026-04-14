---
status: verifying
trigger: "MiniMax 支持 Anthropic API 兼容端点 `https://api.minimaxi.com/anthropic`，需要配置到 LLM provider chain 中"
created: 2026-04-10T00:00:00Z
updated: 2026-04-10T00:00:00Z
---

## Current Focus
root_cause: "No `minimax_anthropic` provider configured in LLM client to route Anthropic-format requests through MiniMax's Anthropic-compatible endpoint at `https://api.minimaxi.com/anthropic`"
fix: "Added `minimax_anthropic` provider to `_PROVIDER_MODEL_MAP` (maps to `anthropic/` prefix) and `_get_litellm_kwargs()` (sets `api_base` to `https://api.minimaxi.com/anthropic`)"

## Symptoms
expected: LLM client uses `https://api.minimaxi.com/anthropic` as the API base URL for anthropic-compatible requests through MiniMax
actual: Missing provider configuration for MiniMax Anthropic-compatible endpoint
errors: None
reproduction: Check LLM client configuration files
started: New issue, MiniMax Anthropic兼容端点可用

## Eliminated

## Evidence
- timestamp: 2026-04-10
  checked: src/llm/core.py lines 141-152, 247-262
  found: `_PROVIDER_MODEL_MAP` had `minimax` provider but not `minimax_anthropic`. `_get_litellm_kwargs()` only handled `minimax` for api_base, not a separate anthropic-compatible endpoint.
  implication: "Anthropic-format requests (using `anthropic/` prefix) would route to default Anthropic API instead of MiniMax's compatible endpoint"

## Resolution
root_cause: "No `minimax_anthropic` provider configured in LLM client to route Anthropic-format requests through MiniMax's Anthropic-compatible endpoint at `https://api.minimaxi.com/anthropic`"
fix: "Added `minimax_anthropic` provider to `_PROVIDER_MODEL_MAP` and `_get_litellm_kwargs()`"
verification: "Manual verification - provider can be used with `force_provider='minimax_anthropic'` or added to fallback_chain"
files_changed: ["/Users/y3/.config/superpowers/worktrees/feedship/entity-clustering/src/llm/core.py"]
