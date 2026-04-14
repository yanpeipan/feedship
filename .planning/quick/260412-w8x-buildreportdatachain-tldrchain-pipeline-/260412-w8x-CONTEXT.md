# Quick Task 260412-w8x: BuildReportDataChain + TLDRChain pipeline refactor - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Task Boundary

改造 report 生成 pipeline，将 add_articles + build 封装为 BuildReportDataChain (Layer 3)，新增 TLDRChain (Layer 4) 为每个有文章的 ReportCluster 生成一句话 TLDR，写入 ReportCluster.summary。

Pipeline 结构：
  BatchClassifyChain (Layer 2)
      ↓
  BuildReportDataChain (Layer 3)  ← 同步 CPU，包装成 async Runnable
      ↓
  TLDRChain (Layer 4)              ← LLM summarization，支持 top_n + target_lang

</domain>

<decisions>
## Implementation Decisions

### TLDR scope
- **所有层级递归** — TLDR 运行在所有有文章的 ReportCluster 上，包括 cluster.children 中的嵌套集群

### BuildReportDataChain
- **包装成 Runnable** — 实现 LangChain Runnable 接口，async ainvoke，支持 pipeline 组合
- 虽然内部 add_articles + build 是同步 CPU 操作，但包装后 pipeline 接口一致

### TLDR input content
- 使用 cluster.articles 的 title + translation 字段拼接 topics_block
- 格式与旧 TLDRGenerator 兼容，每条 article 输出一行

### TLDR output field
- 写入 ReportCluster.summary（已存在字段，非旧的 .tldr）

### TLDR batching
- get_tldr_chain 批量一次处理多个 cluster（单 LLM call）
- top_n 参数控制每个 cluster 取多少篇 articles 做摘要（默认 100，取 quality_weight 最高的）

### entity_id for TLDRItem
- 使用 cluster.name 作为 entity_id（normalized）
- 旧 TLDRItem.entity_id 字段保留兼容

</decisions>

<specifics>
## Specific Ideas

- BuildReportDataChain.ainvoke(input: ReportData, heading_tree) → ReportData
  - 内部调用 report_data.add_articles + report_data.build()
  - 纯同步，返回值仍为 ReportData

- TLDRChain(report_data, top_n=100, target_lang="zh")
  - 递归遍历所有 cluster（通过 _all_clusters 辅助方法）
  - 过滤出有文章的 cluster，按 quality_weight 取 top_n
  - 批量调用 get_tldr_chain，生成 tldr 写入 cluster.summary

</specifics>

<canonical_refs>
## Canonical References

- src/application/report/generator.py (_entity_report_async)
- src/application/report/models.py (ReportData, ReportCluster, ReportArticle)
- src/application/report/classify.py (BatchClassifyChain)
- src/application/report/tldr.py (TLDRGenerator — 待删除)
- src/llm/chains.py (get_tldr_chain, TLDRItem)
- src/llm/output_models.py (TLDRItem)

</canonical_refs>
