# Summary: 260409-r5y — 最终日报不完整，没有翻译

## Problem

`--language zh` 时英文标题没有被翻译成中文。

**Root Cause:** Two issues:
1. `render_report` had `if target_lang != "zh":` which skipped pre-translation for zh reports
2. `_translate_titles_batch_async` had `if target_lang == "zh" or not titles:` which returned early without translating

## Fixes Applied

**Commit `a211e42`:**
- `src/application/report.py` — Changed pre-translation logic to always run, but filter titles based on whether translation is needed:
  - `target_lang == "zh"` → translate non-Chinese titles to Chinese
  - `target_lang != "zh"` → translate Chinese titles to target language

**Commit `2e5103f`:**
- `src/application/report.py` — Removed `target_lang == "zh"` early return in `_translate_titles_batch_async`

## Verification

```bash
uv run feedship --debug report --since 2026-04-07 --until 2026-04-10 --language zh
```

Then check the generated report for Chinese translations of English titles.

## Commits

- `a211e42` — fix(report): translate non-Chinese titles when target_lang==zh
- `2e5103f` — fix(report): remove zh skip in translate_titles_batch_async
- `1f8e974` — docs: update last_activity for quick task 260409-r5y
