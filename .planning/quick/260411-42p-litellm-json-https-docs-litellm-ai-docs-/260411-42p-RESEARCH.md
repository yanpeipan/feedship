# Research: litellm JSON Mode for NER Chain

## 背景

NER chain 目前依赖 `JsonOutputParser` 解析 LLM 输出，并在 `ner.py` 中使用 `_extract_json` 正则提取 JSON（已计划删除）。切换到 litellm 原生 JSON mode 可让 LLM 直接输出结构化 JSON，减少解析失败概率。

## litellm JSON Mode 用法

### 核心 API

litellm 的 `acompletion()` 支持 `response_format` 参数：

```python
response = await litellm.acompletion(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "..."}],
    response_format={"type": "json_object"},  # 或 json_schema
)
```

- `{"type": "json_object"}` — 通用 JSON 对象，无 schema 约束
- `{"type": "json_schema", "json_schema": {"type": "object", "properties": {...}}}}` — 带 schema 约束

### 支持的模型

- OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo` (0624 版本+)
- Anthropic: `claude-3-5-sonnet`, `claude-3-opus` 等（需 `extra_body` 传递）
- Azure OpenAI: 支持
- 其他 provider 视模型能力而定

### 已知限制

- `response_format` 与 `thinking` 不可同时使用（某些模型）
- 不支持的 model 会报错：需按决策抛出异常

## 实现方案

### 方案 A：在 LLMClient.complete() 增加 response_format 参数

在 `LLMClient.complete()` 签名中增加 `response_format: dict | None = None`，透传给 `litellm.acompletion()`。

```python
async def complete(
    self,
    prompt: str,
    *,
    max_tokens: int = 300,
    temperature: float = 0.3,
    extra_body: dict | None = None,
    response_format: dict | None = None,  # 新增
) -> str:
    ...
    kwargs["response_format"] = response_format  # 新增
```

Chain 层通过 `AsyncLLMWrapper._ainvoke_raw()` 的 `extra_body` 传递或新增参数。

### 方案 B：通过 extra_body 传递 response_format

将 `response_format` 放入 `extra_body` dict 中传给 litellm，优点是无需改 `complete()` 签名。

```python
extra_body = {"response_format": {"type": "json_object"}}
```

litellm 会将其正确路由到 provider。

### 推荐：方案 B（最小改动）

只需在 `AsyncLLMWrapper` 构造时或调用时指定 `extra_body["response_format"]`，无需修改 `LLMClient.complete()` 签名。

具体改动点：

1. **`AsyncLLMWrapper.__init__`** 增加 `response_format: dict | None = None` 参数，存入 `self._response_format`
2. **`AsyncLLMWrapper._ainvoke_raw`** 将 `response_format` 加入 `extra_body`
3. **`_get_llm_wrapper`** 增加缓存键支持（按 `max_tokens` + `response_format` 组合）
4. **`get_ner_chain()`** 创建 wrapper 时传入 `response_format={"type": "json_object"}`
5. **NER prompt** 移除关于 JSON 的冗余说明（JSON mode 下模型保证输出 JSON）
6. **`ner.py`** 删除 `_extract_json` 调用（已在用户任务中完成）

### 降级策略

当 model 不支持 JSON mode 时，litellm 会抛出异常。决策为"抛出异常"，所以无需额外降级逻辑——异常自然传播。

## 风险

1. **model 兼容性**：需确认当前部署的 model 支持 `response_format`。不支持则直接报错。
2. **所有 chain 统一切换**：当前只改 NER，后续推广时注意回退路径（指向上述方案 B 的改动点即可）

## 下一步

1. 在 `src/llm/chains.py` 的 `AsyncLLMWrapper` 和 `_get_llm_wrapper` 实现方案 B
2. `get_ner_chain()` 启用 `response_format={"type": "json_object"}`
3. 简化 NER prompt（移除冗余 JSON 说明）
4. 验证 litellm 支持该参数
