# Roadmap: Feedship

## Milestones

- 🟡 **v1.9 fetch --url** — Phase 18 (in progress)
- ✅ **v1.8 OpenClaw 本地测试与 Skill 迭代** — Phases 14-17 (shipped 2026-04-05)
- ✅ **v1.7 OpenClaw AI Daily Report** — Phases 11-13 (shipped 2026-04-04)
- ✅ **v1.6 OpenClaw Skills** — Phase 10 (shipped 2026-04-03)
- ✅ **v1.5 Info Command** — SHIPPED 2026-04-03
- **v1.4 Patch Releases** — Complete (v1.4.4)
- **v1.3 Optimization** — Complete
- **v1.2 Twitter/X via Nitter** — Complete (v1.2.5)

---

## Phases

### v1.9 (Current)

**Goal:** 对 `feedship fetch` 增加 `--url` 支持，允许不保存到数据库直接抓取 URL

---

### Phase 18: fetch --url 实现

**Goal:** 实现 `--url` 参数和 `articles` 字段返回

**Depends on:** None

**Requirements:** FETCH-01, FETCH-02, FETCH-03, FETCH-04, FETCH-05, FETCH-06

**Success Criteria** (what must be TRUE):
1. `feedship fetch --url https://github.com/trending --json` 能抓取并返回 articles
2. 返回的 JSON 包含 `articles` 数组，每个 article 有 title/link/description/published_at
3. `--url` 和 `--id` 互斥，同时使用时报错
4. 无效 URL 或无 provider 时返回友好错误信息
5. GitHub Trending URL 抓取成功

**Plans**:
- [x] 18-01-PLAN.md — fetch --url 实现 (FETCH-01~06)

---

### Phase 14: 基础流程测试

**Goal:** 验证 feedship-ai-daily skill 在 OpenClaw 中的基础运行流程

**Depends on:** None

**Requirements:** FUND-01, FUND-02, FUND-03, FUND-04

**Success Criteria** (what must be TRUE):
1. `openclaw run feedship-ai-daily` 能被 OpenClaw 正确加载
2. `feedship fetch --all` 正常抓取所有订阅源
3. `feedship article list --since YYYY-MM-DD` 正确按日期过滤
4. `feedship search` 语义搜索返回相关结果

**Plans**:
- [x] 14-01-PLAN.md — 基础流程测试 (FUND-01~04)

---

### Phase 15: Cron 与 Isolated Session 验证

**Goal:** 验证 cron job 在 isolated session 下的行为

**Depends on:** Phase 14

**Requirements:** CRON-01, CRON-02, CRON-03, CRON-04

**Success Criteria** (what must be TRUE):
1. `openclaw cron add` 能创建 feedship-ai-daily cron job
2. cron job 在 isolated session 下 `feedship` 命令 PATH 可达
3. `--announce` flag 正确把报告投递到飞书 channel
4. `openclaw cron run <job-id>` 能立即触发 job

**Plans**:
- [x] 15-01-PLAN.md — Cron + Isolated Session 验证 (CRON-01~04)

---

### Phase 16: 报告格式验证

**Goal:** 验证 6-section 报告格式的完整性

**Depends on:** Phase 14

**Requirements:** REPORT-01, REPORT-02, REPORT-03, REPORT-04

**Success Criteria** (what must be TRUE):
1. 报告包含完整的 A~F 六个 section
2. Section E 能提取有效的创业相关内容
3. Section F 能提取有效的内容角度
4. 空数据场景有友好提示

**Plans**: TBD

---

### Phase 17: 频道投递与边界情况

**Goal:** 验证飞书投递和边界情况处理

**Depends on:** Phase 15

**Requirements:** CHANNEL-01, CHANNEL-02, CHANNEL-03, EDGE-01, EDGE-02, EDGE-03, EDGE-04

**Success Criteria** (what must be TRUE):
1. 飞书 channel 能收到完整报告
2. markdown 格式在飞书端正确渲染
3. 缺失依赖（feedship/ml/cloudflare）有清晰提示
4. gateway 未启动时有启动指引

**Plans**: TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 18. fetch --url 实现 | v1.9 | 1/1 | In Progress | — |
| 14. 基础流程测试 | v1.8 | 1/1 | Complete | 2026-04-04 |
| 15. Cron 与 Isolated Session | v1.8 | 1/1 | Complete | 2026-04-04 |
| 16. 报告格式验证 | v1.8 | 1/1 | Complete | 2026-04-04 |
| 17. 频道投递与边界情况 | v1.8 | 1/1 | Complete | 2026-04-04 |

---

_See `.planning/milestones/` for archived milestone roadmaps_
