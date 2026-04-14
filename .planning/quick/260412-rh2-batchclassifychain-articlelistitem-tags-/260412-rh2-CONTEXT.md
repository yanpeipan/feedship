# Quick Task 260412-rh2: 重构BatchClassifyChain返回ArticleListItem - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Task Boundary

重构 `BatchClassifyChain`，返回 `list[ArticleListItem]`（而非 `list[ClassifyTranslateItem]`），在原始 ArticleListItem 上附加 `tags` 和 `translation` 字段。

</domain>

<decisions>
## Implementation Decisions

### ArticleListItem 新字段
- `tags: list[str] = []` — 分类标签
- `translation: str | None = None` — 翻译标题

### BatchClassifyChain 返回值
- 返回 `list[ArticleListItem]` — 每个 article 附加了 `.tags` 和 `.translation`
- 不再返回 `list[ClassifyTranslateItem]`

### ID 对齐
- LLM 返回的 `ClassifyTranslateItem.id` 是 1-indexed 位置
- 需要映射回原始 `ArticleListItem` 列表的 index（也是 1-indexed）
- 如果某 batch 失败返回 `[]`，对应 article 的 `.tags=[]`、`.translation=None`

### 下游简化
- `report_generation.py` 中不再需要手动 build `trans_by_id`、`tag_groups` 映射
- 可以直接用 enriched `ArticleListItem` 构建 `ReportArticle`

</decisions>

<specifics>
## Key Changes

**1. `src/application/articles.py`** — ArticleListItem 新增字段：
```python
tags: list[str] = []
translation: str | None = None
```

**2. `src/application/report/classify.py`** — BatchClassifyChain：
```python
async def ainvoke(self, input: list[ArticleListItem], config=None) -> list[ArticleListItem]:
    # 调用 LLM → ClassifyTranslateOutput
    output_items = await self._run_classify_batches(input)
    # 用 output_items enrichment 原始 ArticleListItem
    trans_by_id = {item.id: item.translation for item in output_items}
    tags_by_id = {item.id: item.tags for item in output_items}
    # 附加到原始对象
    for idx, art in enumerate(input, 1):
        art.tags = tags_by_id.get(idx, [])
        art.translation = trans_by_id.get(idx)
    return input
```

**3. `src/application/report/report_generation.py`** — 下游简化：
- 移除 `trans_by_id`、`tag_groups` 构建逻辑
- 直接用 enriched `ArticleListItem` 的 `.tags` 和 `.translation`

</specifics>

<canonical_refs>
## Canonical References

- `src/application/articles.py` — ArticleListItem 定义
- `src/application/report/classify.py` — BatchClassifyChain 当前实现
- `src/application/report/report_generation.py` — 下游消费逻辑
- `src/llm/output_models.py` — ClassifyTranslateItem

</canonical_refs>
