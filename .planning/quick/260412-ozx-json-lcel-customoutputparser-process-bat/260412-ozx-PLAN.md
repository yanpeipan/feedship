---
name: 260412-ozx
description: 把JSON提取逻辑移到LCEL管道里，用CustomOutputParser替换process_batch中的regex
status: in_progress
created: 2026-04-12
last_updated: 2026-04-12
---

# Plan: 把JSON提取逻辑移到LCEL管道里

## Task 1: 创建 JsonRegexOutputParser

**文件:** `src/llm/chains.py`

**Action:** 在 `chains.py` 顶部（`AsyncLLMWrapper` 之前）添加一个自定义 OutputParser：

```python
import re
import json
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

class JsonRegexOutputParser(Runnable):
    """OutputParser that extracts JSON from potentially mixed LLM output.

    Wraps StrOutputParser and adds post-processing to find and parse
    a JSON array from the raw string (handles LLM outputting text before/after JSON).
    """

    def invoke(self, input: Any, config: Any = None) -> ClassifyTranslateOutput:
        raw = input if isinstance(input, str) else str(input)
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            parsed_dict = {"items": json.loads(json_match.group())}
        else:
            parsed_dict = {"items": []}
        return ClassifyTranslateOutput(**parsed_dict)

    async def ainvoke(self, input: Any, config: Any = None) -> ClassifyTranslateOutput:
        return self.invoke(input, config)
```

**Verify:** `uv run python3 -c "from src.llm.chains import JsonRegexOutputParser; print('import ok')"`

## Task 2: 修改 get_classify_translate_chain

**文件:** `src/llm/chains.py`

**Action:** 把 `StrOutputParser()` 替换为 `JsonRegexOutputParser()`：

```python
# Before
| StrOutputParser()

# After
| JsonRegexOutputParser()
```

**Verify:** Chain 返回 `ClassifyTranslateOutput` 而不是 string

## Task 3: 简化 process_batch

**文件:** `src/application/report/report_generation.py`

**Action:** 删除 `process_batch` 中的 regex JSON 提取逻辑，直接使用 chain 输出：

```python
# Before:
raw_output = await chain.ainvoke(...)
json_match = re.search(r"\[.*\]", raw_output, re.DOTALL)
...
output = ClassifyTranslateOutput(**parsed_dict)

# After:
output = await chain.ainvoke(...)
# output 已经是 ClassifyTranslateOutput
```

同时删除顶部的 `import json, re`（如果只用于此处的话需要检查是否有其他用途）。

**Verify:** `uv run python3 -c "import ast; ast.parse(open('src/application/report/report_generation.py').read())"` 无语法错误

## Files

- `src/llm/chains.py` — 添加 `JsonRegexOutputParser`，修改 `get_classify_translate_chain`
- `src/application/report/report_generation.py` — 简化 `process_batch`

## Done

- [ ] `JsonRegexOutputParser` 创建成功
- [ ] `get_classify_translate_chain` 返回 `ClassifyTranslateOutput`
- [ ] `process_batch` 不再需要 regex 解析
- [ ] `uv run feedship report --since 2026-04-08 --until 2026-04-10 --language zh --limit 5` 正常输出
