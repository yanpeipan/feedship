---
phase: quick-260413
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/core.py
  - src/llm/chains.py
  - src/llm/__init__.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "LLMWrapper() works directly in LCEL pipe chains"
    - "get_llm_wrapper is removed"
    - "All import tests pass"
  artifacts:
    - path: src/llm/core.py
      provides: LLMWrapper extending Runnable
      contains: class LLMWrapper(Runnable)
    - path: src/llm/chains.py
      provides: Updated call sites using LLMWrapper()
      contains: LLMWrapper()
    - path: src/llm/__init__.py
      provides: LLMWrapper export (not get_llm_wrapper)
      contains: LLMWrapper in __all__
  key_links:
    - from: src/llm/chains.py
      to: src/llm/core.py
      via: from src.llm.core import LLMWrapper
---

<objective>
Refactor LLMWrapper to extend langchain_core.runnables.Runnable, enabling direct LCEL pipe syntax. Delete get_llm_wrapper factory function.
</objective>

<execution_context>
@/Users/y3/feedship/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
From src/llm/core.py (current):
- LLMWrapper is a factory class with __call__ returning Runnable
- get_llm_wrapper() is a factory function: LLMWrapper(...)()

From src/llm/chains.py:
- get_llm_wrapper() used in: get_translate_chain, get_tldr_chain, get_classify_translate_chain

From src/llm/__init__.py:
- Exports get_llm_wrapper only
</context>

<tasks>

<task type="auto">
  <name>Refactor LLMWrapper to extend Runnable</name>
  <files>src/llm/core.py</files>
  <action>
Replace the entire LLMWrapper class and delete get_llm_wrapper function.

New LLMWrapper must extend Runnable and implement:
1. __init__: Store response_format, thinking, structured_output, _retry_config, _bind_kwargs
2. invoke(self, input, config=None): Build router with _build_router(), call its invoke
3. ainvoke(self, input, config=None): Build router, call its ainvoke
4. _build_router(): Returns ChatLiteLLMRouter with all bound config and retry applied
5. bind(self, **kwargs) -> "LLMWrapper": Return new instance with merged _bind_kwargs
6. with_structured_output(self, schema, **kwargs) -> "LLMWrapper": Return new instance with schema
7. with_retry(self, **kwargs) -> "LLMWrapper": Return new instance with merged retry config

_Retry_TYPES stays the same. The __call__ method should be removed (Runnable uses invoke).

Delete get_llm_wrapper function entirely.
  </action>
  <verify>python -c "from src.llm.core import LLMWrapper; from langchain_core.runnables import Runnable; assert issubclass(LLMWrapper, Runnable)"</verify>
  <done>LLMWrapper extends Runnable, get_llm_wrapper removed, _build_router, bind, with_structured_output, with_retry all implemented</done>
</task>

<task type="auto">
  <name>Update chains.py call sites</name>
  <files>src/llm/chains.py</files>
  <action>
In src/llm/chains.py:
1. Change import: from src.llm.core import get_llm_wrapper -> from src.llm.core import LLMWrapper
2. In get_translate_chain(): change get_llm_wrapper() -> LLMWrapper()
3. In get_tldr_chain(): change llm = get_llm_wrapper() -> llm = LLMWrapper()
4. In get_classify_translate_chain(): change llm = get_llm_wrapper() -> llm = LLMWrapper()
</action>
  <verify>python -c "from src.llm.chains import get_translate_chain, get_tldr_chain, get_classify_translate_chain; print('chains import OK')"</verify>
  <done>All get_llm_wrapper() calls replaced with LLMWrapper()</done>
</task>

<task type="auto">
  <name>Update __init__.py exports</name>
  <files>src/llm/__init__.py</files>
  <action>
In src/llm/__init__.py:
1. Change import: from src.llm.core import get_llm_wrapper -> from src.llm.core import LLMWrapper
2. Update __all__ to export "LLMWrapper" instead of "get_llm_wrapper"
</action>
  <verify>python -c "from src.llm import LLMWrapper; print('__init__ export OK')"</verify>
  <done>LLMWrapper exported from src.llm, get_llm_wrapper removed</done>
</task>

</tasks>

<verification>
python -c "
from src.llm import LLMWrapper
from src.llm.chains import get_translate_chain, get_tldr_chain, get_classify_translate_chain
from langchain_core.runnables import Runnable

# Verify LLMWrapper is Runnable
assert issubclass(LLMWrapper, Runnable), 'LLMWrapper must extend Runnable'

# Verify all chains can be imported
chain1 = get_translate_chain()
chain2 = get_tldr_chain()
chain3 = get_classify_translate_chain(tag_list='tech,news', news_list='[]')

print('All imports and assertions pass')
"
</verification>

<success_criteria>
- LLMWrapper extends langchain_core.runnables.Runnable
- get_llm_wrapper function deleted from core.py
- chains.py uses LLMWrapper() directly (pipe syntax ready)
- src.llm.__init__ exports LLMWrapper
- Import test passes
</success_criteria>

<output>
After completion, create `.planning/quick/260413-kap-get-llm-wrapper-llmwrapper/260413-kap-SUMMARY.md`
</output>
