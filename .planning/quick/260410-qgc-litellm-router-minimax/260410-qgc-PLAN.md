---
name: 260410-qgc-litellm-router-minimax
description: 使用 litellm Router 配置 minimax 模型
status: in_progress
---

## Plan

### Task 1: 更新 config.yaml 使用 model_list 格式

**Files:** `config.yaml`

**Action:** 将 `llm` 配置改为 model_list 格式：
```yaml
llm:
  model_list:
    - model_name: minimax/MiniMax-M2.7
      litellm_params:
        model: anthropic/MiniMax-M2.7
        api_key: ${OPENAI_API_KEY}
        api_base: https://api.minimaxi.com/anthropic
        rpm: 60
```

**Verify:** `cat config.yaml` 显示正确的 model_list 结构

**Done:** config.yaml 更新为 model_list 格式

---

### Task 2: 修改 src/llm/core.py 使用 litellm Router

**Files:** `src/llm/core.py`

**Action:**
1. 添加 `from litellm import Router` import
2. 删除/注释现有的 `acompletion` 调用
3. 在模块级别创建 Router 单例：
```python
from litellm import Router

_model_list = settings.get("llm", {}).get("model_list", [])
_routing_strategy = settings.get("llm", {}).get("routing_strategy", "usage-based-routing")

llm_router: Router = Router(
    model_list=_model_list,
    routing_strategy=_routing_strategy,
    num_retries=2,
    timeout=45,
)
```
4. 更新 `LLMClient.complete` 使用 `llm_router.acompletion` 而非直接 `acompletion`

**Verify:** `uv run python -c "from src.llm.core import llm_router; print('Router loaded')"`

**Done:** litellm Router 单例创建并替换acompletion调用
