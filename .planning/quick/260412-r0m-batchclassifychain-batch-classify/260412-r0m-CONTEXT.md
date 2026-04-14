# Quick Task 260412-r0m: 创建BatchClassifyChain类，聚合batch classify相关代码 - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Task Boundary

创建 `BatchClassifyChain` 类，把 `_build_news_list`、`_run_classify_batch`、batching + semaphore 并发逻辑聚合起来。放在 `src/application/report/classify.py`。

</domain>

<decisions>
## Implementation Decisions

### Location
- **Decision**: `src/application/report/classify.py` (new dedicated file)
- **Why**: Keeps `report_generation.py` lean; classify pipeline logic内聚，可单独测试

### Error Handling
- **Decision**: Silent fallback — batch 失败时 log warning，返回 `[]`，不抛异常
- **Why**: 与当前 `_run_classify_batch` 行为一致；部分 batch 失败不影响其他 batch

### LCEL Runnable
- **Decision**: 实现 LCEL Runnable 接口 (`invoke` + `ainvoke` + `batch` + `abatch`)
- **Why**: 未来可接入 `|` chain 风格；当前可能用不上但无额外成本

### Class Interface
- 输入: `list[ArticleListItem]`
- 输出: `list[ClassifyTranslateItem]`（合并所有 batch 结果）
- 参数: `tag_list`, `target_lang`, `batch_size=50`, `max_concurrency=5`

</decisions>

<specifics>
## Specific Ideas

```python
class BatchClassifyChain(Runnable):
    """输入 list[ArticleListItem]，内部自动分批并发，返回 list[ClassifyTranslateItem]"""

    def __init__(self, tag_list: str, target_lang: str, batch_size: int = 50, max_concurrency: int = 5):
        ...

    def _build_news_list(self, articles: list) -> str:
        ...

    async def ainvoke(self, input: list, config=None) -> list:
        # batching + semaphore 并发逻辑
        ...

    def invoke(self, input: list, config=None):
        return asyncio.run(self.ainvoke(input, config))
```

</specifics>

<canonical_refs>
## Canonical References

- `src/application/report/report_generation.py` — 当前实现（`_build_news_list`, `_run_classify_batch`, `_entity_report_async`）
- `src/llm/chains.py` — `get_classify_translate_chain`
- `src/llm/output_models.py` — `ClassifyTranslateItem`, `ClassifyTranslateOutput`

</canonical_refs>
