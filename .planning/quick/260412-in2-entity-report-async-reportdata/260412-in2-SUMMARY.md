# Quick Task 260412-in2: 简化 _entity_report_async 返回值为 ReportData

**Completed:** 2026-04-12
**Commit:** 05d2dcd

## Summary

`_entity_report_async` 和 `cluster_articles_for_report` 直接返回 `ReportData`，不再构建废弃的 dict 结构。

## Changes

- 删除了 `entity_topic_dicts`、`articles_clusters`、`layers_data` 构建代码
- 删除了 `tldr_gen` 调用
- 两个函数签名改为 `-> ReportData`
