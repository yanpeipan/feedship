# Quick Task 260410-qgc: litellm Router 配置

**Completed:** 2026-04-10

## Summary

配置 litellm Router 来管理 minimax 模型。

## Changes

### `src/llm/core.py`
- `acompletion` → `llm_router.acompletion`
- 新增 Router 单例，从 `config.yaml` 的 `model_list` 初始化
- 路由策略：`usage-based-routing`，重试 2 次，超时 45s

### `config.yaml` (repo)
- 更新为 `model_list` 格式

### User config (`~/Library/Application Support/feedship/config.yaml`)
- **重要**: 实际运行时配置从 user config 读取，不是 repo 的 config.yaml
- 更新为 `model_list` 格式

## Verification

```
Router loaded with 1 models
 - minimax/MiniMax-M2.7
```
Tests: 16/16 passed

## Commit

`21712b0`
