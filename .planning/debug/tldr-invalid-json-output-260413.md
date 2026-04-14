---
status: investigating
trigger: "uv run feedship report --since 2026-04-08 --until 2026-04-10 --language zh fails with 'TLDR cluster failed: Invalid json output'"
created: 2026-04-13T00:00:00Z
updated: 2026-04-13T00:30:00Z
---

## Current Focus
next_action: "Summarize findings and determine root cause"

## Symptoms
expected: Report generates with populated TLDR summaries
actual: Report saves with empty TLDR summaries, error "TLDR cluster failed: Invalid json output" appears 3 times
errors:
  - "TLDR cluster failed: Invalid json output: For troubleshooting, visit: https://docs.langchain.com/oss/python/langchain/errors/OUTPUT_PARSING_FAILURE"
reproduction: "uv run feedship report --since 2026-04-08 --until 2026-04-10 --language zh"
started: After structured output refactor (recent)

## Eliminated

- hypothesis: Empty or malformed article titles causing JSON parsing failure
  evidence: "Tested with empty titles, special characters, and Chinese punctuation - all handled correctly"
  timestamp: 2026-04-13T00:15:00Z

- hypothesis: max_tokens too low causing truncated responses
  evidence: "Tested with max_tokens=50 (too low) and got the same error, but also with max_tokens=800-5000 the error still occurs intermittently"
  timestamp: 2026-04-13T00:20:00Z

- hypothesis: Issue with strict=True in JSON schema
  evidence: "Tested with strict=False - error still occurs ~50% of the time, so strict flag is not the primary cause"
  timestamp: 2026-04-13T00:25:00Z

## Evidence

- timestamp: 2026-04-13T00:10:00Z
  checked: "chains.py get_tldr_chain() implementation"
  found: "Uses .with_structured_output(TLDRItems) with method='json_schema' (default)"
  implication: "The chain binds response_format with json_schema type and strict=True"

- timestamp: 2026-04-13T00:12:00Z
  checked: "langchain-litellm with_structured_output implementation"
  found: "When method='json_schema', binds response_format={\"type\": \"json_schema\", \"json_schema\": {...}}"
  implication: "MiniMax receives json_schema format request with strict=True"

- timestamp: 2026-04-13T00:20:00Z
  checked: "MiniMax raw response when calling LLM directly"
  found: "Model returns list with {'type': 'thinking', 'thinking': '...'} blocks and sometimes {'type': 'text', 'text': '...'} blocks"
  implication: "Model returns structured content blocks, not plain text"

- timestamp: 2026-04-13T00:25:00Z
  checked: "Failure rate testing with 30 articles"
  found: "50% failure rate (5/10 runs failed with 'Invalid json output') even with strict=False"
  implication: "Issue is not specific to strict flag - model returns empty/invalid JSON intermittently"

- timestamp: 2026-04-13T00:30:00Z
  checked: "Actual error message format"
  found: "Error shows 'Invalid json output: ' with empty text after colon, suggesting model returned empty content"
  implication: "Model is returning empty responses instead of JSON content in ~50% of calls"

## Resolution
root_cause: "MiniMax-M2.7 model intermittently returns empty responses when requested to produce JSON via json_schema response format with strict=True (the default). The model sometimes only returns thinking blocks without the actual JSON text, causing langchain's PydanticOutputParser to fail with 'Invalid json output'. This happens approximately 50% of the time with prompts containing 30+ articles."
fix: "Change get_tldr_chain() to use method='function_calling' instead of method='json_schema', OR increase max_tokens significantly, OR add retry logic with fallback when parsing fails"
verification: "Need to test with function_calling method to confirm fix"
files_changed: []
