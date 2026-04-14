# Quick Task 260409-sv2: 合并topic_title和classify_cluster_layer为一次LLM调用

## Task Boundary

合并 `_cluster_articles_into_topics` 中的两次 LLM 调用为一次：
- `get_topic_title_chain()` → 生成短标题
- `classify_cluster_layer()` → 分类到五层

## Implementation Decisions

### 输出格式
- **结构化 JSON**：返回 `{title: "...", layer: "..."}`，用 `| json` 解析
- 更可靠，避免正则解析的边界情况

### Chain 设计
- 创建新的 `get_topic_title_and_layer_chain()`
- 保留原有 `get_topic_title_chain` 和 `get_classify_chain` 不变（避免破坏其他调用方）
- 新 chain 替代 `_cluster_articles_into_topics` 中的两次调用

### 调用方式
- `render_report` 中仍然调用新 chain
- 一次调用返回 title + layer 两个值

## Specific Ideas

参考现有 chains 的实现模式：
- `src/llm/chains.py` 中已有 `get_topic_title_chain` 和 `get_classify_chain`
- 新 chain 的 prompt 组合两者的 instruction
- 使用 litellm 的 JSON mode 确保格式正确
