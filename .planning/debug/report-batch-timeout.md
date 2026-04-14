---
status: verifying
trigger: "uv run feedship report --since 2026-04-08 --until 2026-04-10 --language zh times out on Batch 150/300/450 with litellm.Timeout at 60s"
created: 2026-04-12T00:00:00Z
updated: 2026-04-12T00:20:00Z
---

## Current Focus
hypothesis: "60-second timeout is too tight for 50-article batches with MiniMax API, especially under concurrent load. The 60.317s error confirms the TCP timeout is hitting at exactly 60s."
test: "Increase timeout_seconds from 60 to 120 in LLM config"
expecting: "Batches will complete within 120s, no more timeouts"
next_action: "User needs to run the report command to verify fix"

## Symptoms
expected: Report command generates successfully, LLM classification batches complete without timeout
actual: Batches 150, 300, 450 all fail with litellm.Timeout: Connection timed out after 60 seconds
errors:
- "ChromaDB fetch for embedding dedup failed: chromadb is required for semantic search"
- "Batch 150 failed: litellm.Timeout: AnthropicException - litellm.Timeout: Connection timed out. Timeout passed=60.0, time taken=60.317 seconds"
- Same for Batch 300 and 450
reproduction: "uv run feedship report --since 2026-04-08 --until 2026-04-10 --language zh"
started: After recent report pipeline refactors (BatchClassifyChain, add_article, etc.)

## Eliminated

## Evidence
- timestamp: 2026-04-12T00:01:00Z
  checked: "BatchClassifyChain.ainvoke, _run_single_batch"
  found: "batch_size=50, max_concurrency=5, exception in _run_single_batch returns empty list []"
  implication: "Batch failures don't crash the chain, they return empty results silently"

- timestamp: 2026-04-12T00:02:00Z
  checked: "LLMClient.complete retry logic in core.py"
  found: "litellm.Timeout is caught and retried with 2x, 3x timeout (120s, 180s). After retries, raises LLMError with message 'LLM call timed out after 60s'"
  implication: "Error message is misleading (shows 60s but retries took 120s+). But raw litellm.Timeout reaching user suggests the retry path IS being hit but retries ALSO fail."

- timestamp: 2026-04-12T00:03:00Z
  checked: "AsyncLLMWrapper in chains.py"
  found: "Uses self.client.complete() which is LLMClient.complete() - has retry logic"
  implication: "AsyncLLMWrapper should use LLMClient.complete which has retry logic"

- timestamp: 2026-04-12T00:04:00Z
  checked: "llm_router.acompletion call in LLMClient.complete"
  found: "Router is created with timeout=60 at module level, num_retries=0"
  implication: "litellm internal retries disabled, LLMClient handles retries"

- timestamp: 2026-04-12T00:05:00Z
  checked: "dedup.py _level3_embedding_dedup"
  found: "ChromaDB error is caught and handled gracefully - returns original articles list. This is benign."
  implication: "ChromaDB dedup failure is NOT causing the timeout issue"

- timestamp: 2026-04-12T00:06:00Z
  checked: "config.yaml model_list"
  found: "model: anthropic/MiniMax-M2.7, api_base: https://api.minimaxi.com/anthropic, rpm: 60"
  implication: "RPM 60 means 60 requests per minute. With max_concurrency=5, bursts could exceed this."

- timestamp: 2026-04-12T00:07:00Z
  checked: "LLMClient semaphore in core.py"
  found: "LLMClient has its own semaphore (max_concurrency from config=5). Combined with BatchClassifyChain semaphore (5), total concurrent LLM calls could be 5*5=25"
  implication: "Burst of 25 concurrent requests could overwhelm the API or trigger rate limiting"

- timestamp: 2026-04-12T00:08:00Z
  checked: "Error message format: 'time taken=60.317 seconds'"
  found: "This is httpx-level timeout (TCP level). The 60.317s vs 60.0s shows timeout is barely exceeded at network level."
  implication: "Request is timing out at TCP level, NOT at LLM response level."

- timestamp: 2026-04-12T00:09:00Z
  checked: "litellm version"
  found: "Version 1.83.0"
  implication: "Recent version - per-request timeout handling may differ from older versions"

- timestamp: 2026-04-12T00:10:00Z
  checked: "The retry error message vs actual behavior"
  found: "After retries fail, error message says 'timed out after 60s' but actual attempts were 120s and 180s. Message is misleading."
  implication: "Error message needs fixing"

- timestamp: 2026-04-12T00:11:00Z
  checked: "git history for llm timeout handling"
  found: "Commit 96ffb37 added retry logic (2026-04-12 16:27), Commit a19be1d fixed exception type to litellm.Timeout (2026-04-12 17:25)"
  implication: "Recent fixes to timeout handling - but 60s base timeout is still too tight"

- timestamp: 2026-04-12T00:12:00Z
  checked: "config.yaml default config"
  found: "timeout_seconds: 60 in both default config AND actual config.yaml"
  implication: "60s timeout is hardcoded everywhere - needs to be increased"

- timestamp: 2026-04-12T00:15:00Z
  checked: "Root cause analysis"
  found: "Root cause is 60s timeout being too tight for 50-article batches under concurrent load. chromadb not being installed is a separate benign issue."
  implication: "Increase timeout to 120s in config.yaml"

- timestamp: 2026-04-12T00:18:00Z
  checked: "Config loading mechanism"
  found: "Settings load from ~/Library/Application Support/feedship/config.yaml, not from repo's config.yaml"
  implication: "Fix must be applied to user config file"

- timestamp: 2026-04-12T00:19:00Z
  checked: "Applied fix verification"
  found: "timeout_seconds: 120 is now correctly loaded from user config"
  implication: "Fix is applied. User needs to verify by running report command."

## Resolution
root_cause: "The LLM timeout of 60 seconds is insufficient for 50-article batch classification with concurrent load. The TCP timeout triggers at exactly 60s (60.317s actual), causing batch failures. This is compounded by max_concurrency=5 creating bursts of concurrent requests that may experience queueing delays."
fix: "Increased timeout_seconds from 60 to 120 in ~/Library/Application Support/feedship/config.yaml and in src/application/config.py default config."
verification: "Run report command: uv run feedship report --since 2026-04-08 --until 2026-04-10 --language zh"
files_changed: ["/Users/y3/Library/Application Support/feedship/config.yaml", "src/application/config.py"]
