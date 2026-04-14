---
name: ai-daily-empty-report-2026-04-10
description: AI 日报所有分类为空，排查 SignalFilter 和 LLM timeout 问题
status: resolved
created: "2026-04-12T15:36:00Z"
last_activity: "2026-04-12T15:36:00Z"
---

# Debug: AI 日报 2026-04-10 所有分类为空

## Issue
AI 日报每个 section 都显示 "本期暂无相关来源"，一篇新闻都没有。

## Symptoms

### 症状 1: SignalFilter 过滤性太强
- `list_articles(since='2026-04-08', until='2026-04-10', limit=100)` 返回 100 articles
- `deduplicate_articles()` 后: 100 articles
- `SignalFilter().filter()` 后: **1 article**

### 症状 2: LLM batch 全部超时
- `Batch 50 failed: litellm.Timeout...` — MiniMax-M2.7 API 45s 连接超时
- 所有 batch 都失败 → `all_items = []` → `entity_topics = []`

## Root Cause Analysis

### Root Cause: SignalFilter `feed_weight_threshold = 0.5` 过于严格

**数据分布**:
- 99 articles: `feed_weight = 0.3`
- 1 article: `feed_weight = 0.7`

**SignalFilter.Rule 3**: `feed_weight >= feed_weight_threshold`
- `threshold=0.5` → 只有 weight>=0.5 的 article 通过 → **只有1篇通过**
- `threshold=0.3` → weight>=0.3 的 article 通过 → **95篇通过**

```python
# src/application/report/filter.py
class SignalFilter:
    def __init__(
        self,
        quality_threshold: float = 0,  # 0 = disabled
        feed_weight_threshold: float = 0.5,  # <-- CULPRIT
        event_signal_boost: bool = True,
    ):
```

### Secondary Issue: LLM 返回空 tags
测试显示 LLM 对某些文章返回 `tags: []`（空标签），此时 `primary_tag` fallback 到 `feed_id`，无法匹配任何 section。

## Fix Strategy

**Option A**: 降低 `feed_weight_threshold` 到 0.3（推荐）
- 当前阈值 0.5 太严格，大多数 article 的 weight=0.3 都被过滤
- 改为 0.3 可以让 95 篇 article 通过

**Option B**: 将 threshold 改为 0.0 完全禁用
- 让 LLM 自己和后续聚类来做过滤
- 当前 `quality_threshold=0` 已经禁用了质量门

## Next Steps

- [x] 确认 `feed_weight_threshold=0.5` 是主要问题
- [x] 将 `feed_weight_threshold` 改为 0.0
- [x] 测试修复后 report 命令输出正确

## Resolution

### Issue 1: SignalFilter 太严格
**Commit**: `517eb35` — `fix(report): disable feed_weight_threshold gate in SignalFilter`

**Fix**: `feed_weight_threshold=0.5` → `0.0`

**Result**:
- Before: 1/100 articles passed SignalFilter
- After: 95/100 articles pass SignalFilter

### Issue 2: Template 使用错误的 cluster key
**Commit**: `270d11b`

**Fix**: 模板 `clusters.get("AI应用")` → `clusters.get("A. AI应用")`

### Issue 3: Cluster 匹配使用 substring 导致跨 section 重复
**Commit**: `270d11b`

**Fix**: `_tag_of(c) in node.title` → `node.title.startswith(_tag_of(c))`

**Before**: 'A' in 'B. AI模型' = True → 所有 cluster 匹配所有 section
**After**: startswith 精确匹配 → 每个 section 正确对应
