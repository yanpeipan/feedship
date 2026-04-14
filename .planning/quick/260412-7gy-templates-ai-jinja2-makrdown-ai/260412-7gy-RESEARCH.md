# Quick Task 260412-7gy: AI Daily Report Jinja2 Template - Research

**Researched:** 2026-04-12
**Domain:** Jinja2 + Markdown template for AI daily report
**Confidence:** HIGH

## Summary

Task: Create a Jinja2 + Markdown template under `src/templates/` matching the user's example format. Key requirements: date header, optional director note, five-layer AI taxonomy structure (AI应用, AI模型, AI基础设施, AI芯片, AI能源), article links in markdown format, empty state handling.

## Template Data Flow

### Current Template System

| Component | Detail |
|-----------|--------|
| Template dirs | `~/.config/feedship/templates/`, `~/.local/share/feedship/templates/`, `src/templates/` (fallback) |
| Engine | Jinja2 `Environment(FileSystemLoader(...), autoescape=False)` |
| Filters available | `dim_zh`, `format_title`, global `sum_articles` |
| Naming convention | `{name}.md` (e.g., `entity.md`, `ai_daily_report.md.j2`) |

### Data Structures Available to Templates

**`by_layer`** — dict mapping layer name to list of `EntityTopic`:
```python
{
  "AI应用": [EntityTopic(entity_name, headline, tldr, signals, dimensions, articles_count, quality_weight), ...],
  "AI模型": [...],
  ...
}
```

**`EntityTopic` attributes:**
- `entity_name` — tag/category name
- `headline` — LLM-generated summary line
- `tldr` — one-sentence summary
- `signals` — list of signal keywords
- `articles_count` — number of articles
- `dimensions` — dict mapping dimension (release/funding/research/ecosystem/policy) to list of `ArticleEnriched`

**`ArticleEnriched` attributes:**
- `title` — article title
- `link` — article URL

### Issue: `topic.sources` Does Not Exist

The CONTEXT example shows `topic.sources` with `title`/`link`, but the actual data from `_entity_report_async` provides articles nested in `topic.dimensions[dim]`. The template must use `topic.dimensions` to access articles.

**Correct access pattern:**
```jinja2
{% for topic in by_layer["AI应用"] %}
  {% for dim, articles in topic.dimensions.items() %}
    {% for article in articles %}
      [{{ article.title }}]({{ article.link }})
    {% endfor %}
  {% endfor %}
{% endfor %}
```

## Template Requirements (from CONTEXT)

### Required Variables
| Variable | Source | Description |
|----------|--------|-------------|
| `date` | `date_range.until` or passed separately | Report date |
| `director_note` | optional, pass from caller | Editor's introduction |
| `by_layer` | from `render_entity_report()` | Five-layer structure |

### Rendering Rules
| Condition | Output |
|-----------|--------|
| `director_note` exists | `💡 主编导读：{{ director_note }}` |
| Article has `link` | `[{{ article.title }}]({{ article.link }})` |
| Article has no `link` | `{{ article.title }}` (plain text) |
| Layer has no articles | `（本期暂无相关来源）` |

### Five Layers (fixed order)
1. AI应用
2. AI模型
3. AI基础设施
4. AI芯片
5. AI能源

## Architecture Patterns

### Conditional Rendering
```jinja2
{% if director_note %}
💡 主编导读：{{ director_note }}
{% endif %}
```

### Nested Loop (accessing articles from dimensions)
```jinja2
{% for topic in by_layer[layer_name] %}
  {% for dim, articles in topic.dimensions.items() %}
    {% for article in articles %}
      [{{ article.title }}]({{ article.link }})
    {% endfor %}
  {% endfor %}
{% endfor %}
```

### Empty State Check
```jinja2
{% set ns = namespace(has_articles=false) %}
{% for topic in by_layer[layer_name] %}
  {% for dim, articles in topic.dimensions.items() %}
    {% if articles %} {% set ns.has_articles = true %} {% endif %}
  {% endfor %}
{% endfor %}
{% if not ns.has_articles %}（本期暂无相关来源）{% endif %}
```

### Counting Total Articles in Layer
```jinja2
{% set total = 0 %}
{% for topic in by_layer[layer_name] %}
  {% for dim, articles in topic.dimensions.items() %}
    {% set total = total + articles|length %}
  {% endfor %}
{% endfor %}
```

## Common Pitfalls

### Pitfall 1: Assuming `topic.sources` Exists
**Problem:** Template example shows `topic.sources` but actual data has articles in `topic.dimensions[dim]`.
**Fix:** Use nested dimension loop or flatten dimensions first.

### Pitfall 2: Empty Layer Detection
**Problem:** `by_layer["AI芯片"]` may be empty list `[]`, not `None`.
**Fix:** Check `by_layer["AI芯片"] | length > 0` before iterating.

### Pitfall 3: Jinja2 Whitespace Control
**Problem:** Excessive blank lines from Jinja2 tags.
**Fix:** Use `{%-` / `-%}` whitespace strip modifiers.

## Template File Location

| Option | Path | Status |
|--------|------|--------|
| Primary | `src/templates/ai_daily_report.md.j2` | Must be created |
| Existing | `~/.config/feedship/templates/entity.md` | Reference only |

**Note:** `src/templates/` does not exist yet — will need to be created.

## Key Integration Points

1. **Template loading** — `render.py` searches template dirs in order; `src/templates/` is lowest priority
2. **Template selection** — `render_entity_report()` called with `template_name="entity"`; new template needs `template_name="ai_daily_report"` or similar
3. **Data adaptation** — Current data structure uses `dimensions` for articles; template must handle this

## Sources

- Existing template: `~/.config/feedship/templates/entity.md`
- Render module: `src/application/report/render.py`
- Data models: `src/application/report/models.py` (EntityTopic, ArticleEnriched)

## Open Questions

1. **How to pass `director_note`?** — Current `render_entity_report()` does not accept `director_note`; may need to add to `entity_topics` or pass separately in `template.render()`
2. **Should template use `src/templates/` or user config dir?** — User decision: `src/templates/` for bundled templates, `~/.config/feedship/templates/` for user customization
3. **Flatten dimensions vs. nested loop?** — Templates can either iterate `topic.dimensions[dim]` nested or pre-flatten articles in Python before rendering
