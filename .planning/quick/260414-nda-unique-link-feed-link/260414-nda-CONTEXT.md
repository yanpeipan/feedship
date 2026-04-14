# Quick Task 260414-nda: 增加约束：UNIQUE(link) 删除feed 里的link重复文章 - Context

**Gathered:** 2026-04-14
**Status:** Ready for planning

<domain>
## Task Boundary

增加约束：UNIQUE(link) 删除feed 里的link重复文章

</domain>

<decisions>
## Implementation Decisions

### 删除策略
- 无所谓 — 保留任意一条重复文章，删除其他

### 约束时机
- 先删后加 — 先删除重复数据，再添加 UNIQUE 约束

### Claude's Discretion
- 删除重复时使用 SQL: `DELETE FROM feed WHERE rowid NOT IN (SELECT MIN(rowid) FROM feed GROUP BY link)`

</decisions>

<specifics>
## Specific Ideas

- feed 表的 link 字段需要添加 UNIQUE 约束
- 36Kr RSS 存在重复 GUID 问题，导致 feed 表出现重复 link 的文章
- 现有重复数据需要清理

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above

</canonical_refs>
