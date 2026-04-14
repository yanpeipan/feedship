---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/application/report/template.py
  - src/application/report/render.py
  - src/application/report/__init__.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "ReportTemplate class encapsulates Jinja2 template environment"
    - "ReportTemplate.render() is async and accepts (report_data, template_name)"
    - "module-level render_report() remains backward-compatible"
  artifacts:
    - path: src/application/report/template.py
      provides: ReportTemplate class
      exports: ReportTemplate
    - path: src/application/report/render.py
      provides: backward-compatible render_report wrapper
  key_links:
    - from: src/application/report/__init__.py
      to: src/application/report/template.py
      via: ReportTemplate export
---

<objective>
Introduce a ReportTemplate class that encapsulates template-related functionality (Jinja2 environment setup, template discovery, rendering). Keep the existing module-level render_report() as a backward-compatible wrapper.
</objective>

<context>
@src/application/report/render.py
@src/application/report/models.py
@src/application/report/__init__.py

## Current render.py

```python
async def render_report(
    report_data: ReportData,
    template_name: str = "entity",
) -> str:
    """Render entity report using Jinja2."""
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    template_dirs = [
        Path.home() / ".local" / "share" / "feedship" / "templates",
        Path(__file__).parent.parent.parent.parent / "templates",
    ]
    env = Environment(
        loader=FileSystemLoader([str(d) for d in template_dirs]),
        autoescape=select_autoescape(),
    )
    try:
        template = env.get_template(f"{template_name}.md")
    except Exception:
        raise

    return template.render(report_data=report_data)
```

## Target: ReportTemplate class

```python
class ReportTemplate:
    """Encapsulates Jinja2 template environment for report rendering."""

    def __init__(self, template_dirs: list[Path] | None = None):
        """Initialize with optional custom template directories."""
        ...

    @property
    def environment(self) -> Environment:
        """The underlying Jinja2 Environment (lazy init)."""
        ...

    async def render(self, report_data: ReportData, template_name: str = "entity") -> str:
        """Render report using specified template. Async for consistency."""
        ...

    def get_template(self, template_name: str) -> Template:
        """Get template by name from the environment."""
        ...
```

## Backward compatibility

```python
# render.py
async def render_report(report_data: ReportData, template_name: str = "entity") -> str:
    """Backward-compatible wrapper using default ReportTemplate."""
    template = ReportTemplate()
    return await template.render(report_data, template_name)
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create ReportTemplate class in template.py</name>
  <files>src/application/report/template.py</files>
  <action>
Create `src/application/report/template.py` with the `ReportTemplate` class:

1. Import required modules: `Path`, `jinja2.Environment`, `jinja2.FileSystemLoader`, `jinja2.select_autoescape`, `jinja2.Template`
2. Import `ReportData` from `.models`
3. Implement `ReportTemplate` class:
   - `__init__(self, template_dirs: list[Path] | None = None)` — if None, use default dirs
   - `_template_dirs` property — returns list of Path objects (default: user's ~/.local/share/feedship/templates + project templates)
   - `environment` property — lazy-init and cache Jinja2 Environment with FileSystemLoader
   - `get_template(self, template_name: str)` — get template from env, appends ".md" automatically
   - `render(self, report_data: ReportData, template_name: str = "entity")` — async method that calls get_template and renders with `report_data=report_data`
4. Use `functools.cached_property` or manual caching for the environment to avoid recreating on each render
5. DO NOT make it a dataclass — it has behavior (methods)
</action>
  <verify>
<automated>cd /Users/y3/feedship && python -c "from src.application.report.template import ReportTemplate; t = ReportTemplate(); print('ReportTemplate import OK')"</automated>
  </verify>
  <done>ReportTemplate class defined with __init__, environment property, get_template, and async render methods</done>
</task>

<task type="auto">
  <name>Task 2: Refactor render.py to use ReportTemplate</name>
  <files>src/application/report/render.py</files>
  <action>
Refactor `src/application/report/render.py`:

1. Import `ReportTemplate` from `.template`
2. Replace the inline Jinja2 Environment code in `render_report()` with a call to `ReportTemplate().render(report_data, template_name)`
3. Keep the function signature identical: `async def render_report(report_data: ReportData, template_name: str = "entity") -> str`
4. Remove the inline `from pathlib import Path`, `from jinja2 import ...` imports from inside the function (they now live in template.py)
5. Keep `group_clusters` function unchanged
</action>
  <verify>
<automated>cd /Users/y3/feedship && python -c "from src.application.report.render import render_report, group_clusters; print('render.py refactor OK')"</automated>
  </verify>
  <done>render_report is a thin async wrapper calling ReportTemplate().render()</done>
</task>

<task type="auto">
  <name>Task 3: Update __init__.py exports</name>
  <files>src/application/report/__init__.py</files>
  <action>
Update `src/application/report/__init__.py` to export `ReportTemplate`:

1. Add `from .template import ReportTemplate` to imports
2. Add `"ReportTemplate"` to the `__all__` list
</action>
  <verify>
<automated>cd /Users/y3/feedship && python -c "from src.application.report import ReportTemplate; print('ReportTemplate exported OK')"</automated>
  </verify>
  <done>ReportTemplate is importable from src.application.report package</done>
</task>

</tasks>

<verification>
Run all three verification commands. All must pass without errors.
</verification>

<success_criteria>
- ReportTemplate class exists in src/application/report/template.py
- ReportTemplate.__init__ accepts optional template_dirs list
- ReportTemplate.render is async and accepts (report_data, template_name)
- ReportTemplate.environment property returns Jinja2 Environment
- module-level render_report() still works (backward compatible)
- ReportTemplate is exported from src.application.report package
</success_criteria>

<output>
After completion, create `.planning/quick/260412-jhx-src-application-report-template/260412-jhx-SUMMARY.md`
</output>
