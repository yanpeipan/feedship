# Quick Task 260411-0sg: 梳理report逻辑架构并计算3333篇新闻LLM调用次数给出优化方案 - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Task Boundary

梳理report逻辑架构，计算3333篇新闻需要多少次LLM调用，激活AI架构师给出完整优化方案

</domain>

<decisions>
## Implementation Decisions

### 优化方向
- 平衡质量与调用次数
- 保留关键步骤，仅优化冗余步骤
- 不追求极致压缩，也不追求全量分析

</decisions>

<specifics>
## Specific Ideas

当前pipeline已知的LLM调用点：
1. NERExtractor: batch_size=10, 并发=3 → 334次调用/3333篇
2. EntityClusterer: max_entities=50, 并发=5 → 50次调用
3. TLDRGenerator: 1次调用 (top 10)
4. Title translation: 1次批量调用

可能的优化方向：
- NER batch_size可调整（当前10偏小？）
- entity clustering可研究批次大小
- 标题翻译可考虑缓存
- 是否需要预过滤低质量文章减少LLM调用

</specifics>

<canonical_refs>
## Canonical References

src/application/report_generation.py
src/application/report/ner.py
src/application/report/entity_cluster.py
src/application/report/tldr.py
src/llm/chains.py

[No external specs — requirements fully captured in decisions above]

</canonical_refs>
