# Roadmap: Feedship

## Milestones

- 🟢 **v1.10 article view 增强** — Phase 19 (shipped 2026-04-06)
- 🟡 **v1.9 fetch --url** — Phase 18 (planned)
- ✅ **v1.8 OpenClaw 本地测试与 Skill 迭代** — Phases 14-17 (shipped 2026-04-05)
- ✅ **v1.7 OpenClaw AI Daily Report** — Phases 11-13 (shipped 2026-04-04)
- ✅ **v1.6 OpenClaw Skills** — Phase 10 (shipped 2026-04-03)
- ✅ **v1.5 Info Command** — SHIPPED 2026-04-03
- **v1.4 Patch Releases** — Complete (v1.4.4)
- **v1.3 Optimization** — Complete
- **v1.2 Twitter/X via Nitter** — Complete (v1.2.5)

---

## Phases

### v1.10 (Shipped)

<details>
<summary>✅ v1.10 article view 增强 — Phase 19 (SHIPPED 2026-04-06)</summary>

- [x] Phase 19: article view 命令增强 (1/1 plan) — completed 2026-04-06

**Goal:** 增强 `feedship article view` 命令，支持 --url/--id/--json 参数，Trafilatura 最佳实践提取内容

**Archived:** `.planning/milestones/v1.10-ROADMAP.md`

</details>

### 🚧 v1.9 fetch --url

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
- [ ] 18-01-PLAN.md — fetch --url 实现 (FETCH-01~06)

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

**Archived milestones:**

<details>
<summary>✅ v1.8 OpenClaw 本地测试与 Skill 迭代 — Phases 14-17 (SHIPPED 2026-04-04)</summary>

- [x] Phase 14: 基础流程测试 (1/1 plan) — completed 2026-04-04
- [x] Phase 15: Cron 与 Isolated Session 验证 (1/1 plan) — completed 2026-04-04
- [x] Phase 16: 报告格式验证 (1/1 plan) — completed 2026-04-04
- [x] Phase 17: 频道投递与边界情况 (1/1 plan) — completed 2026-04-04

**Archived:** `.planning/milestones/v1.8-ROADMAP.md`

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 19. article view 增强 | v1.10 | 1/1 | Complete | 2026-04-06 |
| 18. fetch --url 实现 | v1.9 | 0/1 | Not Started | — |
| 14. 基础流程测试 | v1.8 | 1/1 | Complete | 2026-04-04 |
| 15. Cron 与 Isolated Session | v1.8 | 1/1 | Complete | 2026-04-04 |
| 16. 报告格式验证 | v1.8 | 1/1 | Complete | 2026-04-04 |
| 17. 频道投递与边界情况 | v1.8 | 1/1 | Complete | 2026-04-04 |

---

_See `.planning/milestones/` for archived milestone roadmaps_
