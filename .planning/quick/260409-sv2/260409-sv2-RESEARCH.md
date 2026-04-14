# Quick Task 260409-sv2: Combined Topic Title + Layer Classification Chain - Research

**Researched:** 2026/04/09
**Domain:** LangChain LCEL chains with litellm JSON output
**Confidence:** HIGH

## Summary

The existing codebase already demonstrates the JSON + `JsonOutputParser` pattern working with litellm in `get_evaluate_chain()`. The solution is straightforward: combine the prompts from `TOPIC_TITLE_PROMPT` and `CLASSIFY_PROMPT`, instruct the LLM to return JSON, and use `JsonOutputParser()` for parsing. No special `response_format` parameter is needed in `AsyncLLMWrapper` - LangChain's `JsonOutputParser` handles the parsing after litellm returns text.

**Primary recommendation:** Create `get_topic_title_and_layer_chain()` following the exact same pattern as `get_evaluate_chain()` - combined prompt + `JsonOutputParser()`.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Output format: structured JSON `{title: "...", layer: "..."}` with `| json` parsing
- Chain name: `get_topic_title_and_layer_chain()`
- Backward compatibility: keep existing `get_topic_title_chain` and `get_classify_chain` unchanged
- New chain replaces two calls in `_cluster_articles_into_topics`

### Claude's Discretion
- Prompt design details (exact wording combination)
- Error handling strategy
- max_tokens value for new chain

### Deferred Ideas (OUT OF SCOPE)
- None specified

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langchain-core | >= 0.3.0 | LCEL chains, output parsers | Already in project |
| litellm | >= 1.83.0 | LLM provider abstraction | Already in project |

### Key Components Used
| Component | Source | Purpose |
|-----------|--------|---------|
| `ChatPromptTemplate` | langchain-core | Prompt construction |
| `JsonOutputParser` | langchain-core | Parse LLM text response into dict |
| `StrOutputParser` | langchain-core | Parse LLM text response into string |
| `AsyncLLMWrapper` | src/llm/chains.py | LCEL Runnable wrapper for litellm |

## Architecture Patterns

### Existing Pattern: get_evaluate_chain()
```python
# Source: src/llm/chains.py:235-244
def get_evaluate_chain() -> Runnable:
    """Returns LCEL chain for report quality evaluation.

    Uses JsonOutputParser for validated JSON output instead of raw StrOutputParser.
    """
    return (
        EVALUATE_PROMPT
        | _get_llm_wrapper(MAX_TOKENS_PER_CHAIN["evaluate"])
        | JsonOutputParser()
    )
```

**Key insight:** `JsonOutputParser` is already imported and used. `AsyncLLMWrapper` does NOT pass `response_format` to litellm - it just sends text and receives text. `JsonOutputParser` handles the JSON parsing after the fact.

### Proposed Pattern: get_topic_title_and_layer_chain()

```python
# Combined prompt template
TOPIC_TITLE_AND_LAYER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a news editor. Given a group of articles on the same topic:
1. Generate a concise descriptive title (max 20 characters) that captures the key theme.
2. Classify this topic into ONE of the following five-layer cake categories:
- AI应用 (Application): AI products, tools, and services used by end users
- AI模型 (Model): AI model releases, benchmarks, research papers, training methods
- AI基础设施 (Infrastructure): Cloud platforms, MLOps tools, deployment, APIs
- 芯片 (Chip): AI hardware, GPUs, custom silicon, semiconductor news
- 能源 (Energy): AI energy consumption, data center power, carbon footprint

Return ONLY valid JSON with two fields: {{"title": "...", "layer": "..."}}. Write the title in {target_lang}.""",
        ),
        (
            "human",
            """Articles on this topic:
{article_list}

Return ONLY valid JSON: {{"title": "...", "layer": "..."}}""",
        ),
    ]
)

def get_topic_title_and_layer_chain() -> Runnable:
    """Returns LCEL chain for combined topic title + layer classification."""
    return (
        TOPIC_TITLE_AND_LAYER_PROMPT
        | _get_llm_wrapper(MAX_TOKENS_PER_CHAIN.get("topic_title_and_layer", 150))
        | JsonOutputParser()
    )
```

### Backward Compatibility

Existing chains remain unchanged:
- `get_topic_title_chain()` - returns string via `StrOutputParser`
- `get_classify_chain()` - returns string via `StrOutputParser`
- All existing callers continue to work

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parsing | Custom `json.loads()` with try/except | `JsonOutputParser()` | Built into langchain-core, handles streaming, schema validation |
| Structured output | Regex parsing | `JsonOutputParser()` | Reliable parsing with fallback error messages |
| Provider-specific JSON mode | Provider-specific `response_format` params | `JsonOutputParser()` alone | Works across all litellm providers without changes |

**Key insight:** The project already uses `JsonOutputParser` for `get_evaluate_chain()`. The same pattern applies here - no litellm-level JSON mode configuration needed.

## Common Pitfalls

### Pitfall 1: JSON OutputParser Returns Raw String on Failure
**What goes wrong:** `JsonOutputParser` may return a string (not dict) if parsing fails, depending on version.
**How to avoid:** The caller (e.g., `_cluster_articles_into_topics`) should validate the result is a dict with required keys `title` and `layer`.
**Warning signs:** `TypeError: string indices must be integers` when accessing `result["title"]`

### Pitfall 2: LLM Returns Non-JSON Text
**What goes wrong:** If LLM ignores the JSON instruction, `JsonOutputParser` may fail or return partial data.
**How to avoid:** Use error handling in the caller with fallback (e.g., use default title from first article).
**Code example:**
```python
try:
    result = await chain.ainvoke({...})
    if isinstance(result, dict):
        title = result.get("title", "Misc")[:20]
        layer = result.get("layer", "AI应用")
    else:
        # Fallback: try json.loads on the string
        parsed = json.loads(result)
        title = parsed.get("title", "Misc")[:20]
        layer = parsed.get("layer", "AI应用")
except Exception as e:
    logger.warning("Combined chain failed: %s, using fallback", e)
    title = topic["sources"][0].get("title", "Misc")[:20] if topic["sources"] else "Misc"
    layer = "AI应用"  # default
```

### Pitfall 3: max_tokens Too Small
**What goes wrong:** With two fields (title + layer), need more tokens than single-field chains.
**How to avoid:** Set `max_tokens` to ~150 (vs 50 for title-only, 100 for classify-only). Add new entry to `MAX_TOKENS_PER_CHAIN`.

## Code Examples

### Evaluator Pattern (Verified Working)
```python
# Source: src/llm/chains.py:235-244 and src/llm/evaluator.py:71-75
# This pattern already works in production
chain = get_evaluate_chain()
result = await chain.ainvoke({"report": report_text[:2000]})
# JsonOutputParser returns dict, or raises exception on parse failure
scores = result if isinstance(result, dict) else json.loads(result)
```

### Combined Chain Usage Pattern
```python
# In _cluster_articles_into_topics (proposed change)
chain = get_topic_title_and_layer_chain()
result = await chain.ainvoke({
    "article_list": article_list,
    "target_lang": _lang_name(target_lang),
})
# result is dict with "title" and "layer" keys
topic["title"] = result.get("title", "Misc")[:20]
topic["layer"] = result.get("layer", "AI应用")
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `JsonOutputParser` works with litellm without special config | Architecture Patterns | LOW - proven by existing `get_evaluate_chain()` |
| A2 | 150 max_tokens is sufficient for title + layer | Common Pitfalls | MEDIUM - may need tuning based on actual output |
| A3 | `JsonOutputParser` returns dict on success | Common Pitfalls | LOW - this is documented behavior |

## Open Questions

1. **Should the new chain use retry logic?**
   - What we know: `classify_cluster_layer()` has retry logic with exponential backoff
   - What's unclear: Should the combined chain also have retry, or rely on caller?
   - Recommendation: Let the caller (`_cluster_articles_into_topics`) handle retries, matching existing pattern

2. **What should happen if JSON parsing fails?**
   - What we know: Caller has fallback for LLM failures
   - What's unclear: Should title and layer fallbacks be different?
   - Recommendation: Title fallback to first article title (existing pattern), layer fallback to "AI应用" (most common default)

## Validation Architecture

> **Note:** This is a quick task with minimal implementation change. No new test infrastructure needed.

### Existing Test Infrastructure
- `tests/test_chains.py` - if exists, should be checked for existing chain tests
- `pytest` with asyncio mode enabled

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Command | File Exists? |
|--------|----------|-----------|---------|--------------|
| (implicit) | New chain returns dict with title+layer | unit | `pytest tests/test_chains.py -x` | needs check |

### Wave 0 Gaps
- [ ] Check if `tests/test_chains.py` exists and covers chain behavior
- [ ] If not, no new tests required for this quick task

## Security Domain

No security implications - this is a read-only LLM call that generates titles and classifications from existing article data.

## Sources

### Primary (HIGH confidence)
- `src/llm/chains.py` - existing chain implementations, `JsonOutputParser` usage
- `src/llm/evaluator.py` - how caller handles `JsonOutputParser` results
- `src/application/report.py` - existing usage of `get_topic_title_chain()` and `classify_cluster_layer()`

### Secondary (MEDIUM confidence)
- `pyproject.toml` - litellm version (>=1.83.0) confirming feature support

### Tertiary (LOW confidence)
- General LangChain `JsonOutputParser` documentation - assumes standard behavior

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - existing project patterns
- Architecture: HIGH - proven by `get_evaluate_chain()`
- Pitfalls: MEDIUM - some assumptions about error handling

**Research date:** 2026/04/09
**Valid until:** 2026/05/09 (30 days - stable pattern)
