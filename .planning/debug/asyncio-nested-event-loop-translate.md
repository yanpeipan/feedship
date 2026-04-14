---
status: resolved
trigger: "asyncio.run() cannot be called from a running event loop when running report with --language zh"
created: 2026-04-09T00:00:00Z
updated: 2026-04-09T00:00:00Z
---

## Current Focus
hypothesis: "CONFIRMED - render_report is async but used asyncio.run() internally, causing nested loop error"
fix_applied: "Replaced asyncio.run(_translate_titles_batch_async(...)) with await _translate_titles_batch_async(...) since render_report is already async"
next_action: "FIXED - verified that render_report completes successfully without nested event loop error"

## Symptoms
expected: Report should generate successfully with --language zh, including translated titles
actual: RuntimeWarning: coroutine '_translate_titles_batch_async' was never awaited; asyncio.run() cannot be called from a running event loop
errors:
  - "RuntimeWarning: coroutine '_translate_titles_batch_async' was never awaited"
  - "asyncio.run() cannot be called from a running event loop"
reproduction: "uv run feedship --debug report --since 2026-04-07 --until 2026-04-10 --language zh"
started: After fix for 260409-r5y

## Eliminated
<!-- Empty -->

## Evidence
- timestamp: 2026-04-09
  checked: "src/cli/report.py line 111"
  found: "CLI calls asyncio.run(render_report(...)) where render_report is async"
  implication: "render_report runs in event loop L1"

- timestamp: 2026-04-09
  checked: "src/application/report.py line 851 and 903"
  found: "render_report is async def (line 851) and internally called asyncio.run(_translate_titles_batch_async(...)) at line 903"
  implication: "When asyncio.run() is called inside render_report, outer loop L1 is still running, causing the error"

- timestamp: 2026-04-09
  checked: "src/llm/chains.py line 77-90"
  found: "AsyncLLMWrapper.invoke() uses asyncio.new_event_loop() + run_until_complete() specifically to avoid asyncio.run() nesting issues"
  implication: "This codebase already had to work around asyncio.run() nesting"

- timestamp: 2026-04-09
  checked: "Verification test"
  found: "import + asyncio.run(render_report(...)) completes successfully with no nested loop error"
  implication: "Fix verified"

## Resolution
root_cause: "render_report is an async function (line 851) but called asyncio.run(_translate_titles_batch_async(...)) at line 903. Since render_report is called via asyncio.run() from CLI (cli/report.py:111), the outer event loop is still running when the inner asyncio.run() is executed."
fix: "Replaced asyncio.run(_translate_titles_batch_async(...)) with await _translate_titles_batch_async(...) since render_report is already async"
verification: "Verified: import works, asyncio.run(render_report(...)) completes without nested loop error"
files_changed:
  - "src/application/report.py: Changed asyncio.run(_translate_titles_batch_async(...)) to await _translate_titles_batch_async(...)"
