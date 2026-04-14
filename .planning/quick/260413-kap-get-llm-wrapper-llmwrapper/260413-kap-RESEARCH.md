# Quick Task: LLMWrapper Runnable Refactor - Research

**Researched:** 2026/04/13
**Domain:** langchain-core Runnable interface, LCEL chain composition
**Confidence:** HIGH

## Summary

The task is to refactor `LLMWrapper` from a factory class into a `langchain_core.runnables.Runnable` subclass, enabling direct pipe syntax: `CLASSIFY_TRANSLATE_PROMPT | LLMWrapper(...)`. Currently `get_llm_wrapper()` creates and calls the factory immediately, returning a `ChatLiteLLMRouter` - but `LLMWrapper` itself is not chainable.

## Key Findings

### Current Architecture (core.py)

```python
class LLMWrapper:  # NOT a Runnable
    def __call__(self) -> Runnable:  # Factory - creates new Runnable each call
        wrapper = ChatLiteLLMRouter(router=llm_router)
        if self.response_format: wrapper = wrapper.bind(...)
        if self.structured_output: wrapper = wrapper.with_structured_output(...)
        return wrapper.with_retry(stop_after_attempt=2, retry_if_exception_type=...)

def get_llm_wrapper(...) -> Runnable:  # Factory function
    return LLMWrapper(...)()
```

Usage in chains.py:
```python
TRANSLATE_PROMPT | get_llm_wrapper() | StrOutputParser()  # get_llm_wrapper() returns Runnable
```

### Required Changes

`LLMWrapper` must extend `Runnable` and implement:

| Method | Purpose | Implementation |
|--------|---------|----------------|
| `invoke(input, config)` | Sync entry point | Build router with current config, call its invoke |
| `ainvoke(input, config)` | Async entry point | Build router, call its ainvoke |
| `bind(**kwargs)` | Returns new LLMWrapper with merged kwargs | Store in new instance |
| `with_structured_output(schema)` | Returns new LLMWrapper with schema set | Store in new instance |
| `with_retry(**kwargs)` | Returns new LLMWrapper with retry config | Store in new instance |

`batch()` and `abatch()` have default implementations that use thread pool - no override needed.

### New Architecture

```python
class LLMWrapper(Runnable):
    def __init__(
        self,
        response_format: dict | None = None,
        thinking: dict | None = None,
        structured_output: type[BaseModel] | None = None,
        _retry_config: dict | None = None,
        **bind_kwargs,
    ):
        self.response_format = response_format
        self.thinking = thinking
        self.structured_output = structured_output
        self._retry_config = _retry_config or {"stop_after_attempt": 2, "retry_if_exception_type": _RETRY_TYPES}
        self._bind_kwargs = bind_kwargs

    def invoke(self, input, config=None):
        router = self._build_router()
        return router.invoke(input, config)

    def ainvoke(self, input, config=None):
        router = self._build_router()
        return router.ainvoke(input, config)

    def _build_router(self) -> ChatLiteLLMRouter:
        router = ChatLiteLLMRouter(router=llm_router)
        if self.response_format:
            router = router.bind(response_format=self.response_format)
        if self.thinking:
            router = router.bind(thinking=self.thinking)
        for k, v in self._bind_kwargs.items():
            router = router.bind(**{k: v})
        if self.structured_output:
            router = router.with_structured_output(self.structured_output)
        return router.with_retry(**self._retry_config)

    def bind(self, **kwargs) -> "LLMWrapper":
        """Return new LLMWrapper with kwargs merged."""
        new_kwargs = {**self._bind_kwargs, **kwargs}
        return LLMWrapper(
            response_format=self.response_format,
            thinking=self.thinking,
            structured_output=self.structured_output,
            _retry_config=self._retry_config,
            **new_kwargs,
        )

    def with_structured_output(self, schema, **kwargs) -> "LLMWrapper":
        return LLMWrapper(
            response_format=self.response_format,
            thinking=self.thinking,
            structured_output=schema,
            _retry_config=self._retry_config,
            **self._bind_kwargs,
        )

    def with_retry(self, **kwargs) -> "LLMWrapper":
        merged_retry = {**self._retry_config, **kwargs}
        return LLMWrapper(
            response_format=self.response_format,
            thinking=self.thinking,
            structured_output=self.structured_output,
            _retry_config=merged_retry,
            **self._bind_kwargs,
        )
```

### New Usage Pattern

```python
# Old (deprecated):
get_llm_wrapper() | StrOutputParser()

# New:
LLMWrapper() | StrOutputParser()

# With structured output:
LLMWrapper().with_structured_output(MyModel)

# Chained config:
LLMWrapper(response_format={"type": "json"}).with_retry(stop_after_attempt=3)

# In chains.py:
CLASSIFY_TRANSLATE_PROMPT | LLMWrapper() | JsonOutputParser() | RunnableLambda(validate)
```

## Pitfalls

1. **Config not preserved on chaining**: When calling `.bind().with_structured_output()`, each call must return a new `LLMWrapper` with ALL config (including previous binds) preserved.

2. **`_build_router()` called on every invoke**: Current factory creates new router per call. Runnable pattern requires this - OK for retry to work properly per-call.

3. **`ChatLiteLLMRouter` is already Runnable**: We delegate to it, so LCEL composition works through it. No need to reimplement pipe (`|`) - `Runnable.pipe()` handles it.

4. **`batch`/`abatch` default impl**: Uses thread pool to call `invoke` in parallel - works correctly with our per-call router creation.

## Don't Hand-Roll

- **Retry logic**: Already handled by `router.with_retry()` - don't implement custom retry in `invoke`
- **LCEL pipe chain**: Handled by `Runnable` base class - don't implement `__or__`, `__ror__`

## Deprecation Path

1. Mark `get_llm_wrapper()` with deprecation warning using `warnings.warn("Deprecated, use LLMWrapper() directly", DeprecationWarning, stacklevel=2)`
2. Update chains.py to use `LLMWrapper()` directly
3. `__init__.py` should export `LLMWrapper` (add to `__all__`)
4. Remove `get_llm_wrapper` in a future version

## Code Examples

### Runnable.invoke flow

```python
# In LLMWrapper.invoke():
def invoke(self, input, config=None):
    router = ChatLiteLLMRouter(router=llm_router)
    # Apply stored config
    if self.response_format:
        router = router.bind(response_format=self.response_format)
    if self.structured_output:
        router = router.with_structured_output(self.structured_output)
    # Apply retry
    return router.with_retry(
        stop_after_attempt=self._retry_config["stop_after_attempt"],
        retry_if_exception_type=self._retry_config["retry_if_exception_type"],
    ).invoke(input, config)
```

### Chain composition

```python
# LCEL pipe works because LLMWrapper is now Runnable
prompt | model | output_parser

# Where model = LLMWrapper().with_structured_output(MyModel)
# and output_parser = JsonOutputParser()
```

## Sources

- [VERIFIED: langchain_core.runnables.Runnable] - Standard langchain interface
- [VERIFIED: ChatLiteLLMRouter.invoke] - Delegates to underlying router
- [VERIFIED: Runnable.batch default impl] - Uses thread pool executor calling invoke

## Open Questions

1. **Backward compatibility**: Does `get_llm_wrapper()` need to be kept for any external callers? The refactor goal says "废弃" (deprecate) so probably OK to mark deprecated but keep working.
