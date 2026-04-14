---
name: 260412-pji
description: 把process_batch重构为BatchClassifyProcessor(Runnable)并链式调用
status: in_progress
created: 2026-04-12
last_updated: 2026-04-12
---

# Plan: 把process_batch重构为BatchClassifyProcessor(Runnable)

## Context

当前 `process_batch` 是 `_entity_report_async` 内部的嵌套 `async def`，需要转换为 `BatchClassifyProcessor(Runnable)` 类。难点：

1. **Semaphore** 是 asyncio 概念，不属于 LCEL 链式调用 — semaphore 需要在调用方（`asyncio.gather`）处理
2. **batch_offset** 需要在链的最后调整 — 可以用 `RunnableLambda` 处理
3. **`get_classify_translate_chain`** 每次调用返回新 Runnable — 需要确保链式调用正确

## Tasks

### Task 1: 创建 BatchClassifyProcessor

**文件:** `src/application/report/report_generation.py`

**Action:** 在文件顶部（import 后）添加：

```python
class BatchClassifyProcessor(Runnable):
    """LCEL Runnable for processing a batch of articles through classification.

    Input: dict with "batch_articles" (list[ArticleListItem]) and "batch_offset" (int)
    Output: list[ClassifyTranslateItem] with IDs adjusted by batch_offset
    """

    def __init__(
        self,
        tag_list: str,
        target_lang: str,
    ):
        self.tag_list = tag_list
        self.target_lang = target_lang
        self._chain = get_classify_translate_chain(
            tag_list=tag_list,
            news_list="",  # filled per-batch
            target_lang=target_lang,
        )

    def _build_news_list(self, batch_articles: list[ArticleListItem]) -> str:
        return "\n".join(
            f"{i + 1}. {art.title or ''}"
            for i, art in enumerate(batch_articles)
        )

    async def ainvoke(
        self,
        input: dict,
        config: Any = None,
    ) -> list[ClassifyTranslateItem]:
        batch_articles: list[ArticleListItem] = input["batch_articles"]
        batch_offset: int = input["batch_offset"]
        news_list = self._build_news_list(batch_articles)
        output = await self._chain.ainvoke(
            {
                "news_list": news_list,
                "tag_list": self.tag_list,
                "target_lang": self.target_lang,
            }
        )
        for item in output.items:
            item.id += batch_offset
        return output.items
```

### Task 2: 重构 _entity_report_async 中的 batch 调用逻辑

**文件:** `src/application/report/report_generation.py`

**Action:** 删除嵌套的 `process_batch` 函数，替换为：

```python
# Build processor (holds chain, tag_list, target_lang)
processor = BatchClassifyProcessor(tag_list=tag_list, target_lang=target_lang)

# Create all batches with their offset values
batches = []
for i in range(0, len(filtered), BATCH_SIZE):
    batch = filtered[i : i + BATCH_SIZE]
    batches.append({"batch_articles": batch, "batch_offset": i})

# Process batches concurrently with semaphore limit
semaphore = asyncio.Semaphore(MAX_CONCURRENT)
tasks = [
    asyncio.wait_for(
        semaphore.acquire().__aenter__(),
        timeout=None,
    ).__aexit__(None, None, None).then(
        lambda _: processor.ainvoke(batch)
    )
    for batch in batches
]
# Or simpler: wrap each ainvoke in semaphore context manager
async def run_with_semaphore(batch):
    async with semaphore:
        return await processor.ainvoke(batch)
tasks = [run_with_semaphore(batch) for batch in batches]
batch_results = await asyncio.gather(*tasks)
```

**简化写法：**

```python
async def run_with_semaphore(batch: dict) -> list[ClassifyTranslateItem]:
    async with semaphore:
        return await processor.ainvoke(batch)

tasks = [run_with_semaphore(batch) for batch in batches]
batch_results = await asyncio.gather(*tasks)
```

### Task 3: 验证

```bash
uv run feedship report --since 2026-04-08 --until 2026-04-10 --language zh --limit 5
```

## Files

- `src/application/report/report_generation.py` — 添加 `BatchClassifyProcessor` 类，删除 `process_batch` 嵌套函数

## Done

- [ ] `BatchClassifyProcessor(Runnable)` 实现
- [ ] `_entity_report_async` 使用 processor 调用
- [ ] 报告正常输出
