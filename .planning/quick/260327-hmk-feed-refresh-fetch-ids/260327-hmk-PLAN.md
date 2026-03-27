---
phase: quick
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/cli/feed.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "feed refresh command no longer exists in CLI"
  artifacts:
    - path: src/cli/feed.py
      contains: "No feed_refresh function definition"
  key_links: []
---

<objective>
删除 feed_refresh 命令，因其功能与 fetch &lt;id&gt; 完全重叠。
</objective>

<execution_context>
@/Users/y3/radar/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@src/cli/feed.py

feed_refresh (lines 172-193) 与 fetch &lt;id&gt; (lines 196-243) 功能相同：
- 两者都调用 fetch_one(feed_id)
- 两者都显示 new_articles count
- feed_refresh 是冗余命令
</context>

<tasks>

<task type="auto">
  <name>Task 1: 删除 feed_refresh 命令</name>
  <files>src/cli/feed.py</files>
  <action>
    删除 feed_refresh 函数定义 (lines 172-193)，包括：
    - @feed.command("refresh") 装饰器
    - def feed_refresh(ctx, feed_id) 函数体
    - docstring

    保留 fetch 命令，它已经提供相同功能：fetch &lt;feed_id&gt;
  </action>
  <verify>grep -n "feed_refresh" src/cli/feed.py 返回无匹配</verify>
  <done>feed_refresh 命令已删除，fetch &lt;id&gt; 提供相同功能</done>
</task>

</tasks>

<verification>
- `grep -n "feed_refresh" src/cli/feed.py` 返回无匹配
- `python -c "from src.cli.feed import feed; print('OK')"` 成功
- CLI help 显示 feed 子命令列表不包含 refresh
</verification>

<success_criteria>
feed_refresh 命令不再存在于 CLI 中。
</success_criteria>

<output>
After completion, create `.planning/quick/260327-hmk-feed-refresh-fetch-ids/260327-hmk-SUMMARY.md`
</output>
