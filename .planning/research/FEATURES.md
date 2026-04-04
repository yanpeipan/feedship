# Feature Research: OpenClaw Scheduled AI Daily Report Delivery

**Domain:** Scheduled AI messaging via OpenClaw cron + agent delivery
**Researched:** 2026-04-04
**Confidence:** HIGH (verified via OpenClaw CLI v2026.4.2 `--help` output)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist for scheduled report delivery. Missing these = feature feels broken or incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Cron schedule expression | Users need to specify WHEN reports fire | LOW | Standard 5-field cron (`0 8 * * *`), use `--cron` |
| `--session isolated` for background jobs | Scheduled jobs must not pollute main chat | LOW | `main` = interactive, `isolated` = fresh sub-agent |
| `--announce` (or deprecated `--deliver`) for delivery | Reports must reach user, not disappear | LOW | `--announce` is the modern flag |
| `--channel` for delivery target | Users choose their chat platform | LOW | whatsapp, telegram, feishu, discord, etc. |
| `--to` for recipient | Reports must go to a specific destination | LOW | E.164 number, Telegram chatId, Discord channel |
| `--name` for cron job identification | Users need to manage multiple jobs | LOW | Names appear in `cron list` output |
| Gateway running for cron to fire | Cron depends on gateway daemon | LOW | `openclaw gateway status` to verify |
| Timezone support with `--tz` | Users want reports at local time | LOW | IANA timezone (e.g., `Asia/Shanghai`) |

### Differentiators (Competitive Advantage)

Features that set the delivery system apart. Not required, but valuable for a premium experience.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `--best-effort-deliver` for resilient delivery | Don't fail cron if delivery channel is down | MEDIUM | Prevents cron going red on temporary delivery failures |
| `--failure-alert` for monitoring | Admin gets notified when reports fail | MEDIUM | Configure alert channel + cooldown |
| `--light-context` for faster execution | Smaller context bootstrap = faster reports | LOW | Skip full context initialization |
| `--expect-final` to wait for complete response | Long reports complete before delivery | MEDIUM | Agent may stream; this waits for final |
| `--thinking medium` for balanced quality | Control AI reasoning depth per job | LOW | off/minimal/low/medium/high/xhigh |
| Multiple delivery channels (`--channel` + `--reply-channel`) | Send summary to different channel than agent runs | MEDIUM | Main agent on one platform, delivery elsewhere |
| Session key persistence (`--session-key`) | Resume same session across runs | MEDIUM | Key format: `agent:my-agent:my-session` |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|------------|
| `systemEvent` + `main` session for background tasks | "Simpler" - one session for everything | Main session only processes when agent is free; background tasks never execute unattended | Use `--message` + `--session isolated` |
| Skipping `--announce` to "just run silently" | Unclear why output is needed | Output generated but lost - cron completes with no visible result | Always include `--announce` for informational jobs |
| Using `main` session for recurring cron | Reuse conversation history | History accumulates, context bloats, reports get confused | Use `isolated` + write state to files if continuity needed |
| No timezone (`--tz`) - relying on UTC | Cleaner cron expression | Reports fire at wrong local time | Always specify `--tz` explicitly |
| Short timeout for complex reports | Fast cron completion | Report truncated or fails mid-generation | Use `--timeout-seconds 600` for digest-scale tasks |

## Feature Dependencies

```
[Cron Schedule: --cron "0 8 * * *"]
         │
         └──requires──> [Gateway Running]
                              │
                              └──requires──> [Delivery Channel Configured]
                                                   │
                                                   └──requires──> [Recipient: --to +1234567890]
         │
         └──requires──> [Session: --session isolated]
                              │
                              └──requires──> [--announce for delivery]

[Feedship CLI: feedship fetch --all, feedship article list]
         │
         └──requires──> [Feedship Installed with ml/cloudflare extras]

[AI Daily Report Generation]
         │
         └──requires──> [feedship articles fetched]
         └──requires──> [OpenClaw agent with feedship-ai-daily skill]
```

### Dependency Notes

- **Cron requires gateway:** Without `openclaw gateway` running, cron jobs never fire. No queue, no retry.
- **`--session isolated` is mandatory for background jobs:** Using `main` session means the job waits for interactive attention.
- **`--announce` is required for visible output:** Without it, agent runs but output disappears.
- **Feedship extras are required:** Basic `pip install feedship` lacks ML search and advanced fetching.

## MVP Definition

### Launch With (v1.7)

Minimum viable scheduled delivery:

- [ ] `openclaw cron add` with daily schedule (`--cron "0 8 * *"`)
- [ ] `--session isolated` for autonomous background execution
- [ ] `--announce` for delivery to chat
- [ ] `--channel whatsapp` (or configured default channel)
- [ ] `--to +1234567890` for specific recipient
- [ ] `--agent feedship-ai-daily` invoking the skill
- [ ] `--name "feedship-ai-daily"` for job management
- [ ] `--timeout-seconds 600` (10 minutes for full digest)
- [ ] Gateway running verification step

### Add After Validation (v1.8)

Features to add once core is working:

- [ ] `--failure-alert` with separate alert channel
- [ ] `--best-effort-deliver` to survive delivery outages
- [ ] `--session-key` for session continuity across runs
- [ ] Multiple cron schedules (morning + evening digest)

### Future Consideration (v2+)

Features to defer until product-market fit is established:

- [ ] Multi-channel fan-out (same report to multiple platforms)
- [ ] Adaptive scheduling (based on article volume)
- [ ] Interactive follow-up sessions for report clarification

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| `--cron` daily schedule | HIGH | LOW | P1 |
| `--session isolated` | HIGH | LOW | P1 |
| `--announce` delivery | HIGH | LOW | P1 |
| `--channel` + `--to` targeting | HIGH | LOW | P1 |
| `--name` job identification | MEDIUM | LOW | P1 |
| `--tz` timezone | MEDIUM | LOW | P2 |
| `--timeout-seconds 600` | MEDIUM | LOW | P2 |
| `--failure-alert` | MEDIUM | MEDIUM | P2 |
| `--best-effort-deliver` | MEDIUM | MEDIUM | P2 |
| `--light-context` | LOW | LOW | P3 |
| `--expect-final` | LOW | MEDIUM | P3 |
| `--session-key` persistence | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | OpenClaw Cron | Traditional Cron (systemd timer) | Our Approach |
|---------|--------------|----------------------------------|--------------|
| Natural language scheduling | Via `--cron` expression | No (must write cron expr) | Standard cron expr with `--tz` |
| Delivery to chat | Native via `--announce` | No (logs only) | `--announce --channel whatsapp --to +123` |
| Session isolation | `--session isolated` | N/A (stateless) | Required for background autonomy |
| AI agent execution | `--agent <id>` | No (shell only) | `--agent feedship-ai-daily` |
| Failure alerting | `--failure-alert` | Manual log monitoring | Built-in alert system |
| Multi-channel delivery | `--reply-channel` override | No | Fan-out to multiple platforms |

## Complete Cron Command Examples

### Minimal (P1 launch):
```bash
openclaw cron add \
  --name "feedship-ai-daily" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --session isolated \
  --announce \
  --timeout-seconds 600
```

### Full-featured (P2 add-ons):
```bash
openclaw cron add \
  --name "feedship-ai-daily" \
  --description "Daily AI news digest from feedship subscriptions" \
  --agent feedship-ai-daily \
  --cron "0 8 * * *" \
  --tz Asia/Shanghai \
  --session isolated \
  --announce \
  --channel whatsapp \
  --to +15555550123 \
  --timeout-seconds 600 \
  --thinking medium \
  --best-effort-deliver \
  --failure-alert \
  --failure-alert-channel telegram \
  --failure-alert-to @admin \
  --failure-alert-after 3 \
  --failure-alert-cooldown 4h \
  --name "feedship-ai-daily"
```

### On-demand (non-cron):
```bash
openclaw agent \
  --agent feedship-ai-daily \
  --message "Generate daily digest" \
  --deliver \
  --channel whatsapp \
  --to +15555550123
```

## Sources

- OpenClaw CLI v2026.4.2 — verified via `openclaw cron add --help`, `openclaw agent --help`, `openclaw channels --help`
- Existing ai-daily SKILL.md: `/Users/y3/feedship/skills/ai-daily/SKILL.md` (v1.1)
- Existing feedship SKILL.md: `/Users/y3/feedship/skills/feedship/SKILL.md` (v1.5)
- PITFALLS.md from prior research: `/Users/y3/feedship/.planning/research/PITFALLS.md`
- STACK.md from prior research: `/Users/y3/feedship/.planning/research/STACK.md`

---
*Feature research for: OpenClaw scheduled AI daily report delivery*
*Researched: 2026-04-04*
