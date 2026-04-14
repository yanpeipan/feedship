# Quick Task 260412-jvp: ReportTemplate 初始化绑定 template_name，render/parse 不再传参

**Completed:** 2026-04-12
**Commit:** 89f1f45

## Summary

- `ReportTemplate.__init__` 新增 `template_name: str = "entity"` 参数，存为 `self._template_name`
- `render(report_data)` 去掉 `template_name` 参数，使用 `self._template_name`，渲染结果缓存至 `self._rendered`
- `parse()` 去掉 `rendered` 参数，直接解析 `self._rendered`；未渲染时抛 `RuntimeError`
- `render.py` 的向后兼容包装器改为 `ReportTemplate(template_name=template_name).render(report_data)`
