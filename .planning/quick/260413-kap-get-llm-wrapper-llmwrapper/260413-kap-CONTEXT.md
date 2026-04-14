# Quick Task 260413-kap: 废弃get_llm_wrapper，重构LLMWrapper，使其能够链式调用 - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Task Boundary

废弃 get_llm_wrapper，重构 LLMWrapper，使其能够链式调用：
CLASSIFY_TRANSLATE_PROMPT | LLMWrapper

</domain>

<decisions>
## Implementation Decisions

### LLMWrapper 链式调用实现方式
- 继承 langchain_core.runnables.Runnable，实现 __call__，天然支持 | 操作符

### get_llm_wrapper 兼容性
- 直接删除，所有调用方改成 LLMWrapper()()

</decisions>

<specifics>
## Specific Ideas

调用方式：
```python
# 之前
CLASSIFY_TRANSLATE_PROMPT | get_llm_wrapper()

# 之后
CLASSIFY_TRANSLATE_PROMPT | LLMWrapper()
```

</specifics>

<canonical_refs>
## Canonical References

无外部参考

</canonical_refs>
