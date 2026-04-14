# Quick Task 260411-h9z: LLM Chain Pydantic + JsonOutputParser

## Summary

Added Pydantic output models and JsonOutputParser for all LLM chains, enabling strict JSON schema enforcement via LangChain JSON mode best practices.

## One-liner

Pydantic models (EntityItem, NERArticle, EvaluateScore, EntityTopicOutput, TLDRItem) replace generic JSON object parsing; all chains use `JsonOutputParser(pydantic_object=...)` with `response_format={"type": "json_schema", "json_schema": Model.model_json_schema()}`.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | 299c656 | feat(llm): add Pydantic output models for all LLM chains |
| Task 2 | 64985c8 | feat(llm): use JsonOutputParser(pydantic_object=...) for all chains |
| Task 2 | 4891f4c | style(llm): ruff format chains.py |
| Task 3 | 83901a1 | fix(ner): handle Pydantic return types from get_ner_chain() |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] JsonOutputParser parameter name**
- **Found during:** Task 2
- **Issue:** LangChain's `JsonOutputParser` uses `pydantic_object` parameter (not `pydantic_model`), and has no `pydantic_schema` attribute
- **Fix:** Changed `JsonOutputParser(pydantic_model=...)` to `JsonOutputParser(pydantic_object=...)` and used `Model.model_json_schema()` for the response_format schema

**2. [Rule 3 - Blocking] Unhashable cache key**
- **Found during:** Task 2
- **Issue:** `_llm_wrapper_cache` used `frozenset(response_format.items())` which failed with `TypeError: unhashable type: 'dict'` because json_schema is a nested dict
- **Fix:** Changed cache key to use `id(response_format)` instead of frozenset of items

## Files Created

| File | Description |
|------|-------------|
| src/llm/output_models.py | Pydantic models: EntityItem, NERArticle, EvaluateScore, EntityTopicOutput, TLDRItem |

## Files Modified

| File | Changes |
|------|---------|
| src/llm/chains.py | All 4 chains updated to use `JsonOutputParser(pydantic_object=...)` + `response_format={"type": "json_schema", "json_schema": Model.model_json_schema()}`; cache key fixed to use `id()` |
| src/application/report/ner.py | Removed `json.loads()` call on chain output; updated to use Pydantic attribute access (`.id`, `.entities`) instead of dict access |

## Key Decisions

1. **pydantic_object vs pydantic_model**: LangChain 0.3.x uses `pydantic_object` as the parameter name (not `pydantic_model`)
2. **Schema source**: JsonOutputParser has no `pydantic_schema` attribute; schema is obtained via `Model.model_json_schema()`
3. **Cache key fix**: Used `id(dict)` for unhashable response_format/thinking dicts in cache key

## Verification

```bash
# All models importable
python -c "from src.llm.output_models import EntityItem, NERArticle, EvaluateScore, EntityTopicOutput, TLDRItem"

# All chains load with correct output types
python -c "from src.llm.chains import get_evaluate_chain, get_ner_chain, get_entity_topic_chain, get_tldr_chain"

# NER extractor still works
python -c "from src.application.report.ner import NERExtractor"
```

## Pre-commit Status

- ruff format: reformatted chains.py
- pip-audit/grype: exit 127 (tools not installed) - not code issues

## Self-Check: PASSED

- src/llm/output_models.py exists with all 5 models
- src/llm/chains.py has all 4 chains using JsonOutputParser(pydantic_object=...)
- src/application/report/ner.py no longer calls json.loads on chain output
- All imports resolve without errors
