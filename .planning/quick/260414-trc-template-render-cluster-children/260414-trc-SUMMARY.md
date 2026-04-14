# 260414-trc Summary: 模板优先渲染 cluster.children

## Objective

修改 ai_daily_report.md.j2 模板，当 cluster.children 不为空时优先渲染子话题层级。

## Completed

每个 tag 分区（AI应用/AI模型/AI基础设施/AI芯片/AI能源）内的渲染逻辑：
- `{% if cluster.children %}` → 遍历 `{% for child in cluster.children %}`，渲染 `child.summary` + `child.articles`
- `{% else %}` → 回退到原有逻辑：`cluster.summary` + `cluster.articles`

## Commit

`9924217` - feat(template): render cluster.children if present, else cluster.articles
