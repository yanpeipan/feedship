---
phase: quick-tiz-report-data-add-article
plan: "01"
type: execute
wave: 1
depends_on: []
files_modified:
  - src/application/report/generator.py
autonomous: true
requirements:
  - []
must_haves:
  truths:
    - "ReportData is built incrementally via add_article()"
    - "heading_tree nodes matched to clusters by name"
    - "No manual tag_groups/ReportArticle construction"
  artifacts:
    - path: "src/application/report/generator.py"
      provides: "Simplified report data construction using add_article()"
      min_lines: 90
  key_links:
    - from: "src/application/report/generator.py"
      to: "ReportData.add_article"
      via: "loop calling add_article(primary_tag, art)"
    - from: "src/application/report/generator.py"
      to: "ReportData.get_cluster"
      via: "heading_tree node.title lookup"
---

<objective>
用 ReportData.add_article() 简化 generator.py 的报告数据构建逻辑

Purpose: 移除冗余的手动构建 tag_groups → ReportCluster → clusters 流程，改用 add_article() 直接增量构建
Output: 简化后的 generator.py，ReportData 使用 add_article() 构建
</objective>

<context>
@src/application/report/models.py
  - ReportData.add_article(cluster_name, item) 用法：找/建 cluster，加 article
  - ReportData.get_cluster(name) 递归查找

@src/application/report/generator.py (当前问题)
  - 第 72-77 行: 手动构建 tag_groups 字典 (冗余)
  - 第 79-117 行: 遍历 tag_groups 构建 ReportArticle + ReportCluster (冗余)
  - 第 124-125 行: _tag_of() 使用 .dimensions[0] 但 dimensions 已移除
  - 第 129-133 行: 用 _tag_of() 匹配 heading_tree 节点 (应直接用 node.title)
  - 第 81-84 行: 内联 import ReportArticle/ReportCluster (顶部已有)
</context>

<tasks>

<task type="auto">
  <name>Task 1: 简化 _entity_report_async 使用 add_article()</name>
  <files>src/application/report/generator.py</files>
  <action>
1. 删除第 72-77 行的 tag_groups 构建 (for art in filtered 循环 + defaultdict)
2. 删除第 79-117 行的 entity_topics 构建 (ReportArticle 列表推导 + 遍历 tag_groups 创建 ReportCluster)
3. 删除第 124-125 行的 _tag_of() 函数
4. 删除第 81-84 行的内联 import (ReportArticle, ReportCluster 顶部已有)
5. 在 Layer 2 (classify chain) 之后，用以下逻辑替换:

   # Build clusters incrementally via add_article
   report_data = ReportData(
       clusters={},
       date_range={"since": since, "until": until},
       target_lang=target_lang,
       heading_tree=heading_tree,
   )
   for art in filtered:
       primary_tag = art.tags[0] if art.tags else "unknown"
       report_data.add_article(primary_tag, art)

6. 替换第 127-133 行的 clusters 构建逻辑，用 node.title 直接查找:

   clusters: dict[str, list[ReportCluster]] = {}
   for node in (heading_tree.children if heading_tree else []):
       matched = report_data.get_cluster(node.title)
       if matched is None:
           matched = ReportCluster(name=node.title, children=[], articles=[])
       clusters.setdefault(node.title, []).append(matched)

   report_data.clusters = clusters
</action>
  <verify>
    <automated>python -c "from src.application.report.generator import _entity_report_async; print('import ok')"</automated>
  </verify>
  <done>tag_groups + entity_topics 循环已删除，add_article() 增量构建生效，_tag_of() 已删除，clusters 按 node.title 匹配</done>
</task>

</tasks>

<verification>
验证: python -c "from src.application.report.generator import cluster_articles_for_report; print('ok')"
</verification>

<success_criteria>
1. generator.py 不再包含 tag_groups 变量
2. generator.py 不再包含 entity_topics 变量
3. _tag_of() 函数已删除
4. 内联 import ReportArticle/ReportCluster 已删除
5. report_data.add_article() 在 for art in filtered 循环中被调用
6. clusters 按 node.title (而非 dimensions) 匹配
</success_criteria>

<output>
After completion, create `.planning/quick/260412-tiz-report-data-add-article-generator-py-tag/260412-tiz-SUMMARY.md`
</output>
