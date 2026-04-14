# Research: Enable JSON Mode on evaluate/entity_topic/tldr Chains

## 背景

任务 260411-42p 已在 NER chain 验证 litellm JSON mode 有效，方案为 `response_format={"type": "json_object"}` 通过 `extra_body` 透传给 litellm。本任务将该模式推广到其余三个 JSON chain。

## 当前状态

| Chain | 启用 JSON mode | Prompt 说明 |
|-------|---------------|-------------|
| `get_evaluate_chain()` | ❌ 未启用 | 系统消息含 "Return ONLY valid JSON" |
| `get_entity_topic_chain()` | ❌ 未启用 | 系统消息含 "Return ONLY valid JSON" |
| `get_tldr_chain()` | ❌ 未启用 | 系统消息含 "Return JSON array" |
| `get_ner_chain()` | ✅ 已启用 (260411-42p) | Prompt 已简化 |

## 改动方案

沿用 NER chain 同一方案：

1. **get_evaluate_chain()**: `_get_llm_wrapper(MAX_TOKENS_PER_CHAIN["evaluate"])` → `_get_llm_wrapper(MAX_TOKENS_PER_CHAIN["evaluate"], {"type": "json_object"})`
2. **get_entity_topic_chain()**: `_get_llm_wrapper(150)` → `_get_llm_wrapper(150, {"type": "json_object"})`
3. **get_tldr_chain()**: `_get_llm_wrapper(300)` → `_get_llm_wrapper(300, {"type": "json_object"})`
4. **Prompt 简化**: 移除各 chain system message 中的冗余 JSON 说明（与 NER chain 相同处理）

## 风险

- `translate_chain` 使用 `StrOutputParser`，不需要 JSON mode，不改动
- 所有 chain 共享同一 `AsyncLLMWrapper` 缓存机制（已在上次任务验证）

## 结论

无额外研究需要，直接按 NER chain 相同模式修改即可。
