---
phase: quick-260412-trg
plan: "01"
type: execute
wave: "1"
depends_on: []
files_modified:
  - src/application/report/models.py
  - src/application/report/generator.py
autonomous: true
requirements:
  - quick-260412-trg-add-articles-build-reportdata
must_haves:
  truths:
    - "ReportData.add_articles() batches article additions with a tag extractor"
    - "ReportData.build() matches clusters to heading_tree nodes"
    - "generator.py uses new add_articles() and build() methods"
  artifacts:
    - path: src/application/report/models.py
      provides: "add_articles() and build() methods on ReportData"
      contains: "def add_articles"
      contains: "def build"
    - path: src/application/report/generator.py
      provides: "Replaced Layer 3/4 loop with add_articles() + build() calls"
      contains: "report_data.add_articles"
      contains: "report_data.build"
  key_links:
    - from: src/application/report/models.py
      to: src/application/report/generator.py
      via: "add_articles() and build() are called by generator"
      pattern: "report_data\\.(add_articles|build)"
---

<objective>
Add `add_articles()` and `build()` methods to ReportData class, then refactor generator.py to use them.
</objective>

<execution_context>
@/Users/y3/feedship/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@src/application/report/models.py
@src/application/report/generator.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add add_articles() and build() methods to ReportData</name>
  <files>src/application/report/models.py</files>
  <action>
Add two methods to the `ReportData` dataclass after the existing `add_article()` method:

1. **`add_articles(items: list[ArticleListItem], get_tag: Callable[[ArticleListItem], str]) -> None`**
   - Loop over `items`, calling `self.add_article(get_tag(item), item)` for each
   - Import `Callable` from `typing`

2. **`build(heading_tree: HeadingNode | None) -> None`**
   - Move the Layer 4 matching logic from generator.py lines 82-90 into this method
   - `self.clusters` is already set by `add_articles()`, this method only adds unmatched clusters
   - Logic:
     ```python
     if heading_tree is None:
         return
     clusters: dict[str, list[ReportCluster]] = {}
     for node in heading_tree.children:
         matched = self.get_cluster(node.title)
         if matched is None:
             matched = ReportCluster(name=node.title, children=[], articles=[])
         clusters.setdefault(node.title, []).append(matched)
     self.clusters = clusters
     ```
   - Import `HeadingNode` from `.template` (already imported at top of file)

Add `Callable` to the existing `from typing import ...` import line.
  </action>
  <verify>
    <automated>cd /Users/y3/feedship && python -c "from src.application.report.models import ReportData; from src.application.articles import ArticleListItem; from typing import Callable; r = ReportData(); r.add_articles([], lambda a: 'x'); print('add_articles OK'); print('build OK' if hasattr(r, 'build') else 'build MISSING')"</automated>
  </verify>
  <done>ReportData has add_articles() and build() methods, both callable without error</done>
</task>

<task type="auto">
  <name>Task 2: Refactor generator.py to use add_articles() and build()</name>
  <files>src/application/report/generator.py</files>
  <action>
In `_entity_report_async()`, replace the Layer 3 loop (lines 78-80) and Layer 4 block (lines 82-90) with:

```python
# Layer 3: Build clusters incrementally via add_articles
report_data = ReportData(
    clusters={},
    date_range={"since": since, "until": until},
    target_lang=target_lang,
    heading_tree=heading_tree,
)
report_data.add_articles(filtered, lambda a: a.tags[0] if a.tags else "unknown")

# Layer 4: Match clusters to heading_tree nodes by title
report_data.build(heading_tree)
```

Remove the manual `for art in filtered` loop and the `clusters` dict building block entirely.
  </action>
  <verify>
    <automated>cd /Users/y3/feedship && python -c "from src.application.report.generator import _entity_report_async; print('import OK')"</automated>
  </verify>
  <done>generator.py imports and uses report_data.add_articles() and report_data.build() instead of inline loops</done>
</task>

</tasks>

<verification>
Verify both methods exist and are used correctly:
1. `python -c "from src.application.report.models import ReportData; r = ReportData(); assert hasattr(r, 'add_articles'); assert hasattr(r, 'build')"`
2. `python -c "from src.application.report.generator import _entity_report_async; print('generator uses new methods')"`
</verification>

<success_criteria>
- ReportData has `add_articles(items, get_tag)` method that internally loops and calls `add_article`
- ReportData has `build(heading_tree)` method that encapsulates Layer 4 matching logic
- generator.py replaces inline loops with `report_data.add_articles(...)` and `report_data.build(...)`
</success_criteria>

<output>
After completion, create `.planning/quick/260412-trg-add-articles-build-reportdata/260412-trg-SUMMARY.md`
</output>
