# Quick Task 260413-nco: 调研https://www.langchain.com.cn/docs/how_to/ 并提出重构BatchClassifyChain的最佳方案 - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Task Boundary

调研 LangChain 中文文档 https://www.langchain.com.cn/docs/how_to/ 并提出重构 BatchClassifyChain 的最佳方案。

</domain>

<decisions>
## Implementation Decisions

### 调研范围
- 用户选择"全部都要调研"
- LCEL RunnableLambda 工厂模式
- 529 过载错误重试策略
- 流式处理与 Generator

### Claude's Discretion
- 调研深度由研究者自行判断，以提出最佳重构方案为目标

</decisions>

<specifics>
## Specific Ideas

### 现有 BatchClassifyChain 实现
- 文件: `src/application/report/classify.py`
- 模式: 类继承 `Runnable`，内部使用 `asyncio.Semaphore` 控制并发
- 批量处理: 每次50篇文章分批，每批5个并发调用
- 错误处理: 静默失败，单批次失败不影响整体

### 现有 LangChain 优化计划
- 文档: `docs/superpowers/plans/2026-04-13-langchain-optimization.md`
- Phase 2: 提议将类改为 RunnableLambda 工厂模式
- Phase 3: 提议添加流式去重函数 dedup_streaming
- Task 10: 提议将去重逻辑从 SignalFilter 移到 dedup.py

### 已知问题
- 529 overload 错误需要指数退避重试
- 现有 event loop leak 已修复 (get_running_loop pattern)

</specifics>

<canonical_refs>
## Canonical References

- `src/application/report/classify.py` - 现有 BatchClassifyChain 实现
- `docs/superpowers/plans/2026-04-13-langchain-optimization.md` - 现有优化计划
- `src/llm/chains.py` - LLM chain 工厂函数

[No external specs — requirements fully captured in decisions above]

</canonical_refs>
