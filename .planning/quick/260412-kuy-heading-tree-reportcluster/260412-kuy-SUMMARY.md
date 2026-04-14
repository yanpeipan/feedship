# Quick Task 260412-kuy: heading_tree 对应 ReportCluster

**Completed:** 2026-04-12
**Commit:** 3cdddd9

## Summary

- 去掉 `group_clusters()` 中间函数，不再用 hardcoded layer key
- `_entity_report_async` 内直接遍历 `heading_tree.children`，用 `tag in node.title` 做匹配
- LLM 分类结果通过 `dimensions[0]` 取 tag，与 heading title 做子串匹配
- `group_clusters` 从 `__init__.py` 导出中移除
- `heading_tree` 为 None 时仍有 fallback 行为（不 crash）
