# Quick Task 260412-s9g: ReportData增加add_article方法 - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Task Boundary

给 `ReportData` 增加 `add_article(cluster_name: str, item: ArticleListItem)` 方法。

</domain>

<decisions>
## Implementation Decisions

### Method Signature
```python
def add_article(self, cluster_name: str, item: ArticleListItem) -> None:
```
- `cluster_name`: section/cluster key in `self.clusters`
- `item`: `ArticleListItem`（已enriched，有 `.tags` 和 `.translation`）

### Behavior
1. 获取或创建 `self.clusters[cluster_name]`（list）
2. 如果 list 为空，创建 `ReportCluster(name=cluster_name, ...)` 并 append
3. 将 `ArticleListItem` 转换为 `ReportArticle`（继承 ArticleListItem）并添加到 cluster.children

### Conversion
`ReportArticle` 继承 `ArticleListItem`，可直接传参构造：
```python
ReportArticle(
    id=item.id, feed_id=item.feed_id, ...
    tags=item.tags,
    translation=item.translation or "",
    dimensions=[cluster_name],  # or item.tags[0] if exists
)
```

</decisions>

<canonical_refs>
## Canonical References

- `src/application/report/models.py` — ReportData, ReportCluster, ReportArticle

</canonical_refs>
