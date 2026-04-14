---
name: 260414-trc
description: 修改模板，cluster.children 不为空优先渲染children
type: quick
status: completed
date: 2026-04-14
quick_id: 260414-trc
---

## Task 1: Update template to render cluster.children

**files:**
- templates/ai_daily_report.md.j2

**action:**
修改 ai_daily_report.md.j2 模板：
- 每个 tag cluster 循环体内，判断 `{% if cluster.children %}`
- 如果 children 不为空：遍历 `{% for child in cluster.children %}`，渲染 `child.summary` 和 `child.articles`
- 否则：渲染 `cluster.summary` 和 `cluster.articles`（原有逻辑）

**verify:**
- 模板语法正确，能被 Jinja2 正确渲染
- 有 children 时输出子话题结构，无 children 时回退到 flat 结构

**done:** true
