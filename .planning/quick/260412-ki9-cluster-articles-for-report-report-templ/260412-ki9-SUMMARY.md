# Quick Task 260412-ki9: cluster_articles_for_report 新增参数 传入 heading_tree

**Completed:** 2026-04-12
**Commit:** 1f37571

## Summary

- `ReportData` 新增 `heading_tree: HeadingNode | None` 字段
- `cluster_articles_for_report()` 新增 `heading_tree` 参数，透传给 `_entity_report_async()`
- `_entity_report_async()` 收到 heading tree 后存入 `report_data.heading_tree`
- CLI 层：`ReportTemplate(template_name).parse()` 先解析模板结构，再传入 `cluster_articles_for_report()`
