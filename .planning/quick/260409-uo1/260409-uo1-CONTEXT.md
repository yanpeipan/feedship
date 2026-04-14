# Quick Task 260409-uo1: 优化LLM调用从730次降至~150次

## Task Boundary

将 report pipeline 的 LLM 调用从最坏情况 730 次优化到 ~150 次。

## Problem (from prior analysis)

| 调用类型 | 次数 | 优化方式 |
|---|---|---|
| summarize_text (逐篇) | 200 | 批量处理 |
| score_quality (逐篇) | 200 | 合并到summary chain |
| extract_keywords (逐篇) | 200 | 合并到summary chain |
| topic_title+layer (逐簇) | 30 | 保持（已合并） |
| title翻译 (逐标题) | 100 | 提高并发 |

**核心优化**：批量 summarize + 提高翻译并发。

## Research Focus

1. 如何批量 summarize 多篇文章（现有的 `summarize_article_content` 是逐篇调用）
2. 如何设计批量 prompt 同时返回 summary/quality/keywords
3. 提高 semaphore 到合理值（如 5-10）
4. 保持向后兼容，不破坏现有功能

## Constraints

- 不改变现有的 `summarize_article_content()` 输出格式（向后兼容）
- 保持 `pending_writes_v2` 批量 DB 写入模式
- 优化后结果质量不能下降
