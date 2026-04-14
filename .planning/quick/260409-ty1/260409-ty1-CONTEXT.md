# Quick Task 260409-ty1: 去重前置 + 批量摘要优化

## Task Boundary

优化 `_cluster_articles_async` 中的处理顺序和摘要调用方式：
1. **去重前置** — 先去重，再对剩余文章做 summarize（避免浪费 LLM 调用）
2. **批量摘要** — 收集需要摘要的文章，一次 LLM 调用批量处理

## Problem

当前流程：
```
list_articles_for_llm()
        │
        ▼
process_one()  ← 对每篇调用 LLM summarize
        │
        ▼
deduplicate_articles()  ← 去重，可能丢弃已 summarize 的文章 → LLM 调用浪费
```

问题：
- 去重前就调用 LLM，浪费
- 逐篇调用效率低

## Solution

新流程：
```
list_articles_for_llm()
        │
        ▼
deduplicate_articles()  ← 第一步：先去重
        │
        ▼
批量 summarize()  ← 只对去重后的文章做批量摘要
        │
        ▼
_cluster_articles_into_topics()
```

## Batch Summarization Design

不使用现有的 `summarize_article_content()`（逐篇），而是：

1. 收集需要摘要的文章（无 summary 且 feed_weight >= 0.7）
2. 构造批量 prompt，包含多篇文章的内容
3. 一次 LLM 调用返回多个摘要
4. 解析结果，更新文章的 summary 和 quality_score

或者：保持逐篇调用但移到去重之后（简单改法）。

## 约束

- 不改变现有的 `summarize_article_content()` 行为
- 保持 `auto_summarize` 参数逻辑
- 保持 `pending_writes_v2` 批量 DB 写入模式
