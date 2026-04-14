# Quick Task 260412-iku: render_report 调用改为传递 ReportData

**Completed:** 2026-04-12
**Commit:** c855075

## Summary

`render_report` 改为只接受 `ReportData` + `template_name` 两个参数。

## Changes

- `src/application/report/render.py`: `render_report(entity_topics, since, until, target_lang, template_name)` → `render_report(report_data, template_name)`
- `src/application/report/report_generation.py`: 调用前构建 `ReportData` 再传入
